module.exports = {
  apps: [{
    name: 'liquidation-alert-monitor',
    script: '/home/user/webapp/source_code/liquidation_alert_monitor.py',
    interpreter: 'python3',
    cwd: '/home/user/webapp',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    error_file: '/home/user/webapp/logs/liquidation_alert_error.log',
    out_file: '/home/user/webapp/logs/liquidation_alert_out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    }
  }]
};
