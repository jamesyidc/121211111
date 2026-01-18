#!/usr/bin/env python3
"""
逃顶信号数据自动更新器
每5分钟运行一次 fill_escape_signal_stats.py
"""
import subprocess
import time
from datetime import datetime

def run_fill_script():
    """运行数据补全脚本"""
    try:
        result = subprocess.run(
            ['python3', 'fill_escape_signal_stats.py'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300
        )
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ 数据更新完成")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"⚠️ 错误输出: {result.stderr}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ 更新失败: {e}")

if __name__ == '__main__':
    print(f"🚀 逃顶信号数据自动更新器启动")
    print(f"⏰ 更新间隔: 5分钟")
    
    while True:
        run_fill_script()
        print(f"⏳ 等待5分钟...\n")
        time.sleep(300)  # 5分钟
