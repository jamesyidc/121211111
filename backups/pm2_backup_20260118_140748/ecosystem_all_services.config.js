module.exports = {
  apps: [
    // === Web服务 ===
    {
      name: 'flask-app',
      script: 'source_code/app_new.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      error_file: './logs/flask-app-error.log',
      out_file: './logs/flask-app-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1',
        FLASK_ENV: 'production'
      }
    },

    // === 数据采集器 ===
    {
      name: 'coin-price-tracker',
      script: 'source_code/coin_price_tracker.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/coin_price_tracker_error.log',
      out_file: './logs/coin_price_tracker_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      cron_restart: '*/30 * * * *',  // 每30分钟重启一次
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'support-resistance-snapshot',
      script: 'source_code/support_resistance_snapshot_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      error_file: './logs/sr_snapshot_error.log',
      out_file: './logs/sr_snapshot_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'price-speed-collector',
      script: 'source_code/price_speed_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/price_speed_collector_error.log',
      out_file: './logs/price_speed_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'v1v2-collector',
      script: 'source_code/v1v2_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/v1v2_collector_error.log',
      out_file: './logs/v1v2_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'crypto-index-collector',
      script: 'source_code/crypto_index_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      error_file: './logs/crypto_index_collector_error.log',
      out_file: './logs/crypto_index_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'okx-day-change-collector',
      script: 'source_code/okx_day_change_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/okx_day_change_error.log',
      out_file: './logs/okx_day_change_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'sar-slope-collector',
      script: 'source_code/sar_slope_jsonl_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/sar_slope_error.log',
      out_file: './logs/sar_slope_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'liquidation-1h-collector',
      script: 'source_code/liquidation_1h_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/liquidation_1h_error.log',
      out_file: './logs/liquidation_1h_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },

    // === 监控服务 ===
    {
      name: 'anchor-profit-monitor',
      script: 'source_code/anchor_profit_monitor.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/anchor_profit_monitor_error.log',
      out_file: './logs/anchor_profit_monitor_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'escape-signal-monitor',
      script: 'source_code/escape_signal_monitor.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      error_file: './logs/escape_signal_monitor_error.log',
      out_file: './logs/escape_signal_monitor_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    }
  ]
};
