#!/bin/bash
# Server Monitor - Startup Script
# This script runs the server monitoring system

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Log file
LOG_FILE="/home/user/webapp/server_monitor_daemon.log"

# Check if already running
if pgrep -f "python.*server_monitor.py.*--monitor" > /dev/null; then
    echo "Server monitor is already running"
    exit 1
fi

# Start the monitor in background
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting server monitor..." >> "$LOG_FILE"
nohup python3 server_monitor.py --monitor 60 >> "$LOG_FILE" 2>&1 &

MONITOR_PID=$!
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Server monitor started with PID: $MONITOR_PID" >> "$LOG_FILE"
echo "Server monitor started with PID: $MONITOR_PID"
echo "Check logs: tail -f $LOG_FILE"
