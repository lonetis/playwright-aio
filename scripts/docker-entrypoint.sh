#!/bin/bash

# Start Xvfb with fixed Full HD resolution
Xvfb :99 -screen 0 $RESOLUTION -ac -nolisten tcp -noreset &
sleep 2

# Start window manager
fluxbox &
sleep 1

# Start x11vnc with proper settings for single desktop
x11vnc -display :99 -nopw -listen localhost -xkb -forever -shared -rfbport 5900 -repeat -nowcr -nowf -noxdamage &
sleep 2

# Start noVNC
/opt/novnc/utils/novnc_proxy --vnc localhost:5900 --listen 6080 &
sleep 2

# Start Flask web application
cd /app
python3 app.py
