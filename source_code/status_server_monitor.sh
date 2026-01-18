#!/bin/bash
# Server Monitor - Status Check Script

echo "=============================="
echo "Server Monitor Status"
echo "=============================="

# Check if monitor is running
if pgrep -f "python.*server_monitor.py.*--monitor" > /dev/null; then
    PID=$(pgrep -f "python.*server_monitor.py.*--monitor")
    echo "Status: RUNNING (PID: $PID)"
    echo ""
    
    # Show current disk usage
    echo "Current Disk Usage:"
    df -h / | tail -1 | awk '{print "  Used: " $3 " / " $2 " (" $5 ")"}'
    echo ""
    
    # Show recent log entries
    echo "Recent Activity (last 10 lines):"
    if [ -f /home/user/webapp/server_monitor.log ]; then
        tail -10 /home/user/webapp/server_monitor.log | sed 's/^/  /'
    else
        echo "  No log file found"
    fi
else
    echo "Status: NOT RUNNING"
    echo ""
    echo "To start the monitor, run:"
    echo "  ./start_server_monitor.sh"
fi

echo "=============================="
