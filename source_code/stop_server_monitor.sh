#!/bin/bash
# Server Monitor - Stop Script

LOG_FILE="/home/user/webapp/server_monitor_daemon.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Stopping server monitor..." >> "$LOG_FILE"

# Find and kill the monitor process
if pgrep -f "python.*server_monitor.py.*--monitor" > /dev/null; then
    pkill -f "python.*server_monitor.py.*--monitor"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Server monitor stopped" >> "$LOG_FILE"
    echo "Server monitor stopped successfully"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Server monitor is not running" >> "$LOG_FILE"
    echo "Server monitor is not running"
fi
