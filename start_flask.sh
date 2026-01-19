#!/bin/bash
cd /home/user/webapp
source venv/bin/activate 2>/dev/null || true
export FLASK_APP=source_code/app_new.py
export FLASK_ENV=production
python3 source_code/app_new.py
