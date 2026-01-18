#!/usr/bin/env python3
"""
数据采集监控和自动恢复脚本

功能:
1. 检查最新数据的采集时间
2. 如果超过15分钟没有新数据，认为采集进程异常
3. 自动重启采集进程
4. 发送通知（可选）
"""

import sqlite3
import subprocess
import os
import sys
from datetime import datetime, timedelta
import pytz

# 配置
DB_PATH = '/home/user/webapp/crypto_data.db'
COLLECT_SCRIPT = '/home/user/webapp/collect_and_store.py'
MAX_DELAY_MINUTES = 15  # 最大允许延迟（分钟）

def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)

def check_latest_data():
    """检查最新数据时间"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取最新快照时间
        cursor.execute('SELECT MAX(snapshot_time) FROM crypto_snapshots')
        latest_snapshot = cursor.fetchone()[0]
        
        conn.close()
        
        if not latest_snapshot:
            return None, None
        
        # 解析时间
        latest_time = datetime.strptime(latest_snapshot, '%Y-%m-%d %H:%M:%S')
        beijing_tz = pytz.timezone('Asia/Shanghai')
        latest_time = beijing_tz.localize(latest_time)
        
        return latest_snapshot, latest_time
    
    except Exception as e:
        print(f"❌ 检查数据失败: {e}")
        return None, None

def is_collect_process_running():
    """检查采集进程是否在运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'collect_and_store.py'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 检查进程失败: {e}")
        return False

def start_collect_process():
    """启动采集进程"""
    try:
        print("\n🔄 正在启动数据采集进程...")
        
        # 确保脚本有执行权限
        os.chmod(COLLECT_SCRIPT, 0o755)
        
        # 启动采集进程（后台运行）
        subprocess.Popen(
            ['python3', COLLECT_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        print("✅ 数据采集进程已启动")
        return True
    
    except Exception as e:
        print(f"❌ 启动进程失败: {e}")
        return False

def main():
    """主函数"""
    print("="*80)
    print("🔍 数据采集监控检查")
    print("="*80)
    
    now = get_beijing_time()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查最新数据
    latest_snapshot, latest_time = check_latest_data()
    
    if not latest_snapshot:
        print("\n❌ 数据库中没有任何数据")
        print("   建议: 手动运行 collect_and_store.py 初始化数据")
        return
    
    # 计算时间差
    time_diff = (now - latest_time).total_seconds() / 60
    
    print(f"最新数据: {latest_snapshot}")
    print(f"距今: {time_diff:.1f} 分钟")
    
    # 判断是否需要恢复
    if time_diff > MAX_DELAY_MINUTES:
        print(f"\n⚠️  警告: 已经 {time_diff:.1f} 分钟没有新数据!")
        print(f"   超过阈值 {MAX_DELAY_MINUTES} 分钟")
        
        # 检查进程是否在运行
        is_running = is_collect_process_running()
        
        if is_running:
            print("\n🔍 采集进程正在运行，但没有产生新数据")
            print("   可能原因:")
            print("   1. 进程卡死或异常")
            print("   2. 网络连接问题")
            print("   3. 目标网站变更")
            print("\n   建议: 手动检查 collect_and_store.py 的日志")
        else:
            print("\n❌ 采集进程未运行!")
            print("   尝试自动恢复...")
            
            if start_collect_process():
                print("\n✅ 采集进程已自动恢复")
                print("   请等待10分钟后检查是否有新数据")
            else:
                print("\n❌ 自动恢复失败")
                print("   建议: 手动运行 python3 collect_and_store.py")
    else:
        print(f"\n✅ 数据采集正常")
        print(f"   最近 {time_diff:.1f} 分钟内有数据更新")
    
    print("="*80)

if __name__ == '__main__':
    main()
