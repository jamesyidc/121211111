module.exports = {
  apps: [
    {
      name: 'pm2-monitor-api',
      script: './pm2-monitor-server.cjs',
      cwd: '/home/user/webapp',
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production',
        PM2_MONITOR_PORT: 9000
      },
      error_file: '/home/user/webapp/logs/pm2-monitor-error.log',
      out_file: '/home/user/webapp/logs/pm2-monitor-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      autorestart: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 3000
    }
  ]
};
