module.exports = {
  apps: [{
    name: 'escape-signals-2h-monitor',
    script: '/home/user/webapp/monitor_escape_signals_2h.py',
    interpreter: 'python3',
    cwd: '/home/user/webapp',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      PYTHONUNBUFFERED: '1'
    },
    error_file: '/home/user/webapp/logs/escape_signals_2h_monitor_error.log',
    out_file: '/home/user/webapp/logs/escape_signals_2h_monitor_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true
  }]
};
