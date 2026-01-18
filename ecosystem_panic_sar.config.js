module.exports = {
  apps: [
    {
      name: 'panic-collector',
      script: '/home/user/webapp/panic_collector_jsonl.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/panic_collector_error.log',
      out_file: '/home/user/webapp/logs/panic_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },
    {
      name: 'sar-bias-collector',
      script: '/home/user/webapp/sar_bias_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/sar_bias_collector_error.log',
      out_file: '/home/user/webapp/logs/sar_bias_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    }
  ]
};
