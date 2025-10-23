FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    x11vnc \
    xvfb \
    fluxbox \
    websockify \
    net-tools \
    python3-pip \
    git \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc && \
    git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify && \
    ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Install Python packages
RUN pip install --no-cache-dir \
    playwright \
    flask \
    flask-cors \
    flask-socketio \
    eventlet

# Install Playwright browsers (Chromium, Firefox, WebKit)
RUN playwright install chromium firefox webkit && \
    playwright install-deps chromium firefox webkit

# Create working directory
WORKDIR /workspace

# Copy the default Playwright script
COPY scripts/main.py /workspace/main.py

# Copy Flask app and web interface
COPY src/app.py /app/app.py
COPY src/web /app/web

# Copy startup script
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose ports
# 8080: Web interface
# 6080: noVNC
# 5900: VNC
EXPOSE 8080 6080 5900

# Set display and resolution (Full HD)
ENV DISPLAY=:99
ENV RESOLUTION=1920x1080x24
ENV VNC_RESOLUTION=1920x1080

# Start services
ENTRYPOINT ["/docker-entrypoint.sh"]
