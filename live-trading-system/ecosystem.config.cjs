module.exports = {
  apps: [
    {
      name: 'vite-dev-3000',
      script: 'npm',
      args: 'run dev',
      cwd: '/home/user/webapp',
      instances: 1,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'development',
        PORT: 3000
      },
      error_file: '/home/user/webapp/logs/vite-error.log',
      out_file: '/home/user/webapp/logs/vite-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      // 防止频繁重启
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000,
      autorestart: true,
      // 启动延迟
      wait_ready: true,
      listen_timeout: 10000
    },
    {
      name: 'wrangler-dev-8080',
      script: 'npm',
      args: 'run dev:sandbox',
      cwd: '/home/user/webapp',
      instances: 1,
      exec_mode: 'cluster',
      watch: false,
      max_memory_restart: '800M', // Wrangler需要更多内存
      cron_restart: '0 3 * * *', // 每天凌晨3点自动重启，防止端口失效
      env: {
        NODE_ENV: 'development',
        PORT: 8080,
        NODE_OPTIONS: '--max-old-space-size=768' // 增加Node.js堆内存
      },
      error_file: '/home/user/webapp/logs/wrangler-error.log',
      out_file: '/home/user/webapp/logs/wrangler-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      // 防止频繁重启
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000,
      autorestart: true,
      // 启动延迟
      wait_ready: true,
      listen_timeout: 15000
    }
  ]
};
