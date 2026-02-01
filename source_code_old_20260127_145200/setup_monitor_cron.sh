#!/bin/bash
# Setup cron job for server monitor
# Runs the monitor check every hour

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create cron job entry
CRON_JOB="0 * * * * cd $SCRIPT_DIR && python3 server_monitor.py --check >> /home/user/webapp/server_monitor_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "server_monitor.py --check"; then
    echo "Cron job already exists"
    echo "Current cron jobs:"
    crontab -l | grep "server_monitor"
    exit 0
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo "✓ Cron job added successfully"
    echo "Monitor will run every hour at :00"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep "server_monitor"
    echo ""
    echo "To remove this cron job, run:"
    echo "  crontab -e"
    echo "  # Then delete the line containing 'server_monitor.py'"
else
    echo "✗ Failed to add cron job"
    exit 1
fi
