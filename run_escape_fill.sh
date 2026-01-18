#!/bin/bash
cd /home/user/webapp
python3 fill_escape_signal_stats.py >> logs/escape_fill.log 2>&1
