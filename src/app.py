from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import subprocess
import os
import threading
import signal
import pty
import select
import termios
import struct
import fcntl

app = Flask(__name__, template_folder='web', static_folder='web/static')
app.config['SECRET_KEY'] = 'playwright-aio-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

SCRIPT_PATH = '/workspace/main.py'
current_process = None

# Terminal session storage
terminal_sessions = {}
terminal_fd = None
terminal_child_pid = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/script', methods=['GET'])
def get_script():
    try:
        with open(SCRIPT_PATH, 'r') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/script', methods=['POST'])
def save_script():
    try:
        data = request.json
        content = data.get('content', '')
        with open(SCRIPT_PATH, 'w') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/script/download', methods=['GET'])
def download_script():
    try:
        return send_file(SCRIPT_PATH, as_attachment=True, download_name='main.py')
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/run', methods=['POST'])
def run_script():
    global current_process

    if current_process and current_process.poll() is None:
        return jsonify({'success': False, 'error': 'Script is already running'}), 400

    try:
        def run_and_stream():
            global current_process

            proc = subprocess.Popen(
                ['python3', '-u', SCRIPT_PATH],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # No buffering
                cwd='/workspace',
                env={**os.environ, 'PYTHONUNBUFFERED': '1'},
                start_new_session=True  # Create new session (better than preexec_fn)
            )

            current_process = proc
            socketio.emit('script_started', {'pid': proc.pid}, namespace='/')
            socketio.sleep(0)

            try:
                while proc.poll() is None:
                    # Non-blocking read using select
                    ready, _, _ = select.select([proc.stdout], [], [], 0.1)
                    if ready:
                        line = proc.stdout.readline()
                        if line:
                            socketio.emit('script_output', {'output': line}, namespace='/')
                            socketio.sleep(0)
                    else:
                        socketio.sleep(0.01)

                # Read any remaining output
                for line in proc.stdout:
                    socketio.emit('script_output', {'output': line}, namespace='/')
                    socketio.sleep(0)

            except (BrokenPipeError, ValueError, OSError):
                pass

            # Get return code (non-blocking)
            returncode = proc.poll()
            if returncode is None:
                returncode = -15

            socketio.emit('script_finished', {'returncode': returncode}, namespace='/')
            socketio.sleep(0)
            current_process = None

        socketio.start_background_task(run_and_stream)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_script():
    global current_process

    if not current_process or current_process.poll() is not None:
        return jsonify({'success': False, 'error': 'No script is running'}), 400

    try:
        # Store the PID to kill
        pid_to_kill = current_process.pid

        def kill_process():
            """Kill the process in a background task"""
            try:
                # Try to kill the session group first
                try:
                    os.killpg(pid_to_kill, signal.SIGKILL)
                except (ProcessLookupError, OSError, PermissionError):
                    # If that fails, try killing the process directly
                    try:
                        os.kill(pid_to_kill, signal.SIGKILL)
                    except:
                        pass
            except Exception:
                pass

        # Schedule the kill in a background task
        socketio.start_background_task(kill_process)

        # Return immediately
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/install', methods=['POST'])
def install_package():
    try:
        data = request.json
        package = data.get('package', '')

        if not package:
            return jsonify({'success': False, 'error': 'Package name required'}), 400

        def install_and_stream():
            import time

            process = subprocess.Popen(
                ['pip', 'install', package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue

                socketio.emit('install_output', {'output': line}, namespace='/')
                socketio.sleep(0)

            process.wait()
            socketio.emit('install_finished', {'returncode': process.returncode}, namespace='/')
            socketio.sleep(0)

        socketio.start_background_task(install_and_stream)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def read_and_forward_pty_output(fd, sid):
    """Read from PTY and forward to client"""
    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        try:
            timeout_sec = 0
            (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
            if data_ready:
                output = os.read(fd, max_read_bytes).decode('utf-8', errors='ignore')
                socketio.emit('terminal_output', {'output': output}, room=sid, namespace='/')
        except (OSError, ValueError):
            break

@socketio.on('terminal_start')
def handle_terminal_start():
    """Start a new terminal session"""
    global terminal_fd, terminal_child_pid

    if terminal_fd is not None:
        emit('terminal_output', {'output': 'Terminal already running\r\n'})
        return

    try:
        # Create a new PTY
        (child_pid, fd) = pty.fork()

        if child_pid == 0:
            # Child process - execute shell
            os.chdir('/workspace')
            subprocess.run(['/bin/bash', '-l'])
        else:
            # Parent process
            terminal_fd = fd
            terminal_child_pid = child_pid

            # Set initial terminal size (will be updated by client)
            set_winsize(fd, 24, 80)

            # Make the file descriptor non-blocking
            flag = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)

            # Start background task to read output
            sid = request.sid
            socketio.start_background_task(target=read_and_forward_pty_output, fd=fd, sid=sid)

            # Send ready signal - client should send resize event after this
            emit('terminal_ready', {})
    except Exception as e:
        emit('terminal_output', {'output': f'Error starting terminal: {str(e)}\r\n'})

@socketio.on('terminal_input')
def handle_terminal_input(data):
    """Handle input from the client"""
    global terminal_fd

    if terminal_fd is None:
        return

    try:
        input_data = data.get('input', '')
        os.write(terminal_fd, input_data.encode('utf-8'))
    except (OSError, ValueError):
        pass

@socketio.on('terminal_resize')
def handle_terminal_resize(data):
    """Handle terminal resize"""
    global terminal_fd

    if terminal_fd is None:
        return

    rows = data.get('rows', 50)
    cols = data.get('cols', 120)
    set_winsize(terminal_fd, rows, cols)

@socketio.on('disconnect')
def handle_disconnect():
    """Clean up terminal on disconnect"""
    global terminal_fd, terminal_child_pid

    if terminal_fd is not None:
        try:
            os.close(terminal_fd)
        except:
            pass
        terminal_fd = None

    if terminal_child_pid is not None:
        try:
            os.kill(terminal_child_pid, signal.SIGTERM)
        except:
            pass
        terminal_child_pid = None

def set_winsize(fd, rows, cols):
    """Set the window size of the PTY"""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)
