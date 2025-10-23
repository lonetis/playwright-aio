# Playwright AIO - Project Structure

## Overview
This project provides a Docker-based all-in-one Playwright Python runner with a comprehensive web interface.

## File Structure

```
playwright-aio/
├── src/                       # Application source code
│   ├── app.py                # Flask backend API server
│   └── web/                  # Web interface
│       └── index.html        # Monaco Editor, noVNC, Terminal UI
├── scripts/                   # Scripts and utilities
│   ├── main.py               # Default Playwright script (user-editable)
│   └── docker-entrypoint.sh  # Container startup script
├── .github/
│   └── workflows/
│       └── publish.yml       # GitHub Actions for GHCR publishing
├── Dockerfile                 # Main Docker image definition
├── start.sh                   # Build/start container locally
├── stop.sh                    # Stop and remove container
├── README.md                  # User documentation
├── PROJECT_STRUCTURE.md       # This file
├── .dockerignore              # Docker build exclusions
└── .gitignore                 # Git exclusions
```

## Components

### Docker Container
- **Base Image**: `mcr.microsoft.com/playwright/python:v1.55.0-jammy`
- **Browsers**: Chromium, Firefox, WebKit (all pre-installed)
- **Display Server**: Xvfb (X Virtual Framebuffer) - Full HD 1920x1080
- **Window Manager**: Fluxbox (lightweight)
- **VNC Server**: x11vnc with local scaling
- **VNC Web Client**: noVNC with responsive scaling
- **Web Server**: Flask with SocketIO (eventlet)

### Web Interface Features
1. **Monaco Editor**: VS Code-like editor with auto-save (2s debounce)
2. **Script Execution**: Run/Stop buttons with real-time output streaming
3. **Browser View**: Full HD noVNC view with responsive scaling
4. **Package Manager**: Install Python packages via pip
5. **Interactive Terminal**: Full bash terminal with xterm.js and PTY support
6. **Download**: Download edited scripts locally

### Port Mappings
- **8080**: Flask web interface
- **6080**: noVNC browser view
- **5900**: VNC server (localhost only)

### API Endpoints

#### Script Management
- `GET /api/script` - Get current script content
- `POST /api/script` - Save script content
- `GET /api/script/download` - Download script file

#### Execution
- `POST /api/run` - Execute the script
- `POST /api/stop` - Stop running script

#### Package Management
- `POST /api/install` - Install Python package

#### WebSocket Events (SocketIO)
- `script_started` - Script execution started
- `script_output` - Real-time output line (unbuffered)
- `script_finished` - Script execution completed (with exit code)
- `install_output` - Package installation output
- `install_finished` - Installation completed
- `terminal_start` - Start interactive terminal session
- `terminal_input` - Send input to terminal (stdin)
- `terminal_output` - Terminal output (PTY)
- `terminal_resize` - Resize terminal window
- `terminal_ready` - Terminal session ready

## Usage Scenarios

### Quick Start (GHCR)
```bash
docker run -d --name playwright-aio -p 8080:8080 -p 6080:6080 --shm-size=2gb ghcr.io/lonetis/playwright-aio:latest
```

> **Note**: `--shm-size=2gb` is required to prevent browser crashes (default 64MB is too small)

### Local Development
Build and start:
```bash
./start.sh
```

Stop:
```bash
./stop.sh
```

## GitHub Actions Workflow

The `.github/workflows/publish.yml` automatically publishes to GitHub Container Registry on:
- Push to `main` branch
- Version tags (`v*`)
- Manual workflow dispatch

## Environment Variables

- `DISPLAY=:99` - X display number
- `RESOLUTION=1920x1080x24` - VNC screen resolution

## Browser Usage

All three browsers are pre-installed. Set `headless=False` to view in noVNC:

```python
# Chromium (Chrome/Edge)
browser = p.chromium.launch(headless=False)

# Firefox
browser = p.firefox.launch(headless=False)

# WebKit (Safari)
browser = p.webkit.launch(headless=False)
```

## Security Notes

- Container runs with default Docker security
- No authentication on web interface (intended for local use)
- Ports should not be exposed to public networks
- For production use, add authentication and HTTPS
