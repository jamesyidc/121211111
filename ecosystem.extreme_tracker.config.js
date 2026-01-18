module.exports = {
  apps: [{
    name: 'extreme-value-tracker',
    script: '/home/user/webapp/source_code/extreme_value_tracker.py',
    interpreter: 'python3',
    cwd: '/home/user/webapp',
    args: '10',  // 每10分钟检查一次
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '300M',
    env: {
      PYTHONUNBUFFERED: '1',
      PYTHONIOENCODING: 'utf-8'
    },
    error_file: '/home/user/webapp/logs/extreme_tracker_error.log',
    out_file: '/home/user/webapp/logs/extreme_tracker_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true,
    min_uptime: '10s',
    max_restarts: 10
  }]
};
