{
  "apps": [
    {
      "script": "index.js",
      "watch": "."
    },
    {
      "script": "./service-worker/",
      "watch": [
        "./service-worker"
      ]
    },
    {
      "name": "coin-price-tracker",
      "script": "source_code/coin_price_tracker.py",
      "interpreter": "python3",
      "cwd": "/home/user/webapp",
      "instances": 1,
      "autorestart": true,
      "watch": false,
      "max_memory_restart": "500M",
      "env": {
        "PYTHONUNBUFFERED": "1"
      },
      "error_file": "logs/coin_price_tracker_error.log",
      "out_file": "logs/coin_price_tracker.log",
      "log_date_format": "YYYY-MM-DD HH:mm:ss"
    }
  ],
  "deploy": {
    "production": {
      "user": "SSH_USERNAME",
      "host": "SSH_HOSTMACHINE",
      "ref": "origin/master",
      "repo": "GIT_REPOSITORY",
      "path": "DESTINATION_PATH",
      "pre-deploy-local": "",
      "post-deploy": "npm install && pm2 reload ecosystem.config.js --env production",
      "pre-setup": ""
    }
  }
}
