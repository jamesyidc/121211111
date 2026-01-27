#!/usr/bin/env python3
"""
数据采集自动监控守护进程
功能：每隔N分钟自动检查数据采集状态，如果发现漏采则自动触发采集
"""

import time
import subprocess
import json
from datetime import datetime
import pytz
import sys

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
CHECK_INTERVAL = 5 * 60  # 每5分钟检查一次
LOG_FILE = '/home/user/webapp/monitor_daemon.log'

def log(message):
    """记录日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    except:
        pass

def check_and_recover():
    """检查并自动恢复数据采集"""
    try:
        log("开始检查数据采集状态...")
        
        result = subprocess.run(
            ['python3', '/home/user/webapp/monitor_data_collection.py', 'check', '--silent'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                status = data.get('status', {})
                action_taken = data.get('action_taken', False)
                
                log(f"检查完成: {status.get('reason', '未知状态')}")
                
                if action_taken:
                    collection_result = data.get('collection_result', {})
                    if collection_result.get('success'):
                        log("✅ 检测到漏采，已自动触发数据采集，采集成功!")
                    else:
                        log(f"⚠️ 检测到漏采，已触发采集但失败: {collection_result.get('message', '未知')}")
                else:
                    log("✓ 数据采集正常，无需操作")
                
                return True
            except json.JSONDecodeError as e:
                log(f"❌ 解析检查结果失败: {e}")
                log(f"   输出: {result.stdout[:500]}")
                return False
        else:
            log(f"❌ 检查失败，无输出 (退出码: {result.returncode})")
            if result.stderr:
                log(f"   错误: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        log("⏱️ 检查超时（超过5分钟）")
        return False
    except Exception as e:
        log(f"❌ 检查过程发生异常: {e}")
        return False

def main():
    """主循环"""
    log("="*80)
    log("🚀 数据采集自动监控守护进程启动")
    log(f"   检查间隔: {CHECK_INTERVAL // 60} 分钟")
    log(f"   日志文件: {LOG_FILE}")
    log("="*80)
    
    check_count = 0
    
    try:
        while True:
            check_count += 1
            log(f"\n第 {check_count} 次检查")
            
            check_and_recover()
            
            log(f"等待 {CHECK_INTERVAL // 60} 分钟后进行下一次检查...\n")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        log("\n接收到中断信号，守护进程停止")
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ 守护进程异常退出: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
