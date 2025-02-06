#!/bin/bash

Xvfb :99 -screen 0 1240x800x24 &
export DISPLAY=:99 &
DISPLAY=:99 fluxbox &
x11vnc -display :99 -nopw -forever &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 &