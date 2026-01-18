#!/usr/bin/env python3
"""
每日文件夹ID定时调度器
使用schedule库实现每天定时自动更新文件夹ID
"""
import schedule
import time
import subprocess
import sys
from datetime import datetime

SCRIPT_PATH = "/home/user/webapp/auto_update_daily_folder.py"
LOG_FILE = "/home/user/webapp/scheduler.log"

def log(message):
    """写入日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

def run_update():
    """执行更新脚本"""
    log("⏰ 触发定时更新任务")
    
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        log(f"更新脚本输出:\n{result.stdout}")
        
        if result.returncode == 0:
            log("✅ 更新任务执行成功")
        else:
            log(f"⚠️  更新任务返回代码: {result.returncode}")
            if result.stderr:
                log(f"错误信息: {result.stderr}")
                
    except subprocess.TimeoutExpired:
        log("❌ 更新任务超时")
    except Exception as e:
        log(f"❌ 执行更新任务时出错: {e}")

def main():
    """主函数"""
    log("=" * 70)
    log("🚀 每日文件夹ID定时调度器已启动")
    log("=" * 70)
    log("📅 调度计划:")
    log("   - 每天 00:01 自动更新文件夹ID（主更新）")
    log("   - 每天 00:15 自动更新文件夹ID（备份）")
    log("   - 每天 08:00 检查一次（二次备份）")
    log("=" * 70)
    
    # 启动时立即执行一次
    log("🔄 启动时执行首次更新...")
    run_update()
    
    # 设置定时任务
    schedule.every().day.at("00:01").do(run_update)  # 每天0点01分
    schedule.every().day.at("00:15").do(run_update)  # 每天0点15分备份
    schedule.every().day.at("08:00").do(run_update)  # 每天早上8点备份检查
    
    log("✅ 定时任务已设置，开始监听...")
    
    # 持续运行
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            log("⚠️  收到中断信号，退出调度器")
            break
        except Exception as e:
            log(f"❌ 调度器运行错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
