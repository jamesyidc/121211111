module.exports = {
  apps: [{
    name: 'flask-app',
    script: '/usr/local/bin/python3',
    args: '/home/user/webapp/source_code/app_new.py',
    cwd: '/home/user/webapp/source_code',
    interpreter: 'none',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      FLASK_APP: 'app_new.py',
      FLASK_ENV: 'production',
      PORT: 5000
    },
    error_file: '/home/user/webapp/logs/flask-app-error.log',
    out_file: '/home/user/webapp/logs/flask-app-out.log',
    log_file: '/home/user/webapp/logs/flask-app-combined.log',
    time: true
  }]
};
