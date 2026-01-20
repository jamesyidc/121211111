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
    },
    {
      name: 'unified-data-collector',
      script: '/home/user/webapp/major-events-system/unified_data_collector.py',
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
      error_file: '/home/user/webapp/logs/unified-collector-error.log',
      out_file: '/home/user/webapp/logs/unified-collector-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'sar-slope-collector',
      script: '/home/user/webapp/source_code/sar_slope_jsonl_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/sar_slope_collector_error.log',
      out_file: '/home/user/webapp/logs/sar_slope_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'escape-signal-calculator',
      script: '/home/user/webapp/source_code/escape_signal_calculator.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/escape_signal_calculator_error.log',
      out_file: '/home/user/webapp/logs/escape_signal_calculator_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'coin-price-tracker',
      script: '/home/user/webapp/source_code/coin_price_tracker.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/coin_price_tracker_error.log',
      out_file: '/home/user/webapp/logs/coin_price_tracker_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'support-resistance-collector',
      script: '/home/user/webapp/source_code/support_resistance_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/support_resistance_collector_error.log',
      out_file: '/home/user/webapp/logs/support_resistance_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'panic-wash-collector',
      script: '/home/user/webapp/panic_collector_jsonl.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/panic_collector_error.log',
      out_file: '/home/user/webapp/logs/panic_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'anchor-profit-monitor',
      script: '/home/user/webapp/source_code/anchor_profit_monitor.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/anchor_profit_monitor_error.log',
      out_file: '/home/user/webapp/logs/anchor_profit_monitor_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'liquidation-1h-collector',
      script: '/home/user/webapp/source_code/liquidation_1h_collector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/liquidation_1h_collector_error.log',
      out_file: '/home/user/webapp/logs/liquidation_1h_collector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'gdrive-detector',
      script: '/home/user/webapp/source_code/gdrive_final_detector.py',
      interpreter: 'python3',
      cwd: '/home/user/webapp',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '300M',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/user/webapp/logs/gdrive_detector_error.log',
      out_file: '/home/user/webapp/logs/gdrive_detector_out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 5000
    }
  ]
};
