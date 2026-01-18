module.exports = {
  apps: [
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
    }
  ]
};

