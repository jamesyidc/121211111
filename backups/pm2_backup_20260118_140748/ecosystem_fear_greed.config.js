module.exports = {
  apps: [
    {
      name: 'fear-greed-collector',
      script: '/home/user/webapp/fear_greed_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      cron_restart: '0 10 * * *',  // 每天上午10点执行
      autorestart: false,
      watch: false,
      max_memory_restart: '200M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/fear_greed_error.log',
      out_file: '/home/user/webapp/logs/fear_greed_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    }
  ]
};
