module.exports = {
  apps: [{
    name: 'liquidation-1h-collector',
    script: 'source_code/liquidation_1h_collector.py',
    interpreter: 'python3',
    cwd: '/home/user/webapp',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      PYTHONUNBUFFERED: '1',
      TZ: 'Asia/Shanghai'
    },
    error_file: 'logs/liquidation_1h_collector_error.log',
    out_file: 'logs/liquidation_1h_collector_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    merge_logs: true
  }]
};
