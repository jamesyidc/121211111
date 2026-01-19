module.exports = {
  apps: [
    {
      name: 'major-events-monitor',
      script: '/home/user/webapp/major-events-system/major_events_monitor.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp/major-events-system',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/major-events-error.log',
      out_file: '/home/user/webapp/logs/major-events-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'anchor-data-collector',
      script: '/home/user/webapp/major-events-system/anchor_data_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp/major-events-system',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/anchor-collector-error.log',
      out_file: '/home/user/webapp/logs/anchor-collector-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    }
  ]
};
