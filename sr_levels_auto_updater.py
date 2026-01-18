#!/usr/bin/env python3
"""
支撑压力线数据自动更新器
每5分钟运行一次 update_support_resistance_jsonl.py
"""
import subprocess
import time
from datetime import datetime

def run_update_script():
    """运行数据更新脚本"""
    try:
        result = subprocess.run(
            ['python3', 'update_support_resistance_jsonl.py'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=180
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ SR levels更新完成")
        if result.returncode != 0 and result.stderr:
            print(f"⚠️ 错误输出: {result.stderr[:200]}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 更新失败: {e}")

if __name__ == '__main__':
    print(f"🚀 支撑压力线数据自动更新器启动")
    print(f"⏰ 更新间隔: 5分钟")
    
    while True:
        run_update_script()
        print(f"⏳ 等待5分钟...\n")
        time.sleep(300)  # 5分钟
