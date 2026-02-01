#!/usr/bin/env python3
"""
加密货币数据自动采集守护进程
每10分钟自动采集一次数据，不受网页刷新影响
"""
import time
import subprocess
import sys
import os
from datetime import datetime
import signal

# 全局变量
running = True
collect_script = '/home/user/webapp/collect_and_store.py'
log_file = '/home/user/webapp/auto_collect.log'
pid_file = '/home/user/webapp/auto_collect.pid'

def signal_handler(signum, frame):
    """处理终止信号"""
    global running
    print(f"\n收到信号 {signum}，准备停止...")
    log_message("收到停止信号，守护进程即将退出")
    running = False

def log_message(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}\n"
    
    # 输出到控制台
    print(log_entry.strip())
    
    # 写入日志文件
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"写入日志失败: {e}")

def write_pid():
    """写入PID文件"""
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        log_message(f"PID文件已创建: {pid_file} (PID: {os.getpid()})")
    except Exception as e:
        log_message(f"创建PID文件失败: {e}")

def remove_pid():
    """删除PID文件"""
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
            log_message("PID文件已删除")
    except Exception as e:
        log_message(f"删除PID文件失败: {e}")

def collect_data():
    """执行数据采集"""
    try:
        log_message("=" * 60)
        log_message("开始采集数据...")
        
        # 执行采集脚本
        result = subprocess.run(
            ['python3', collect_script],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            log_message("✅ 数据采集成功")
            # 记录输出的关键信息
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if '数据采集时间' in line or '快照ID' in line or '等级' in line:
                    log_message(f"   {line.strip()}")
        else:
            log_message(f"❌ 数据采集失败 (返回码: {result.returncode})")
            if result.stderr:
                log_message(f"错误信息: {result.stderr[:200]}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        log_message("❌ 数据采集超时（超过5分钟）")
        return False
    except Exception as e:
        log_message(f"❌ 数据采集异常: {e}")
        return False

def main():
    """主函数"""
    global running
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill命令
    
    # 写入PID文件
    write_pid()
    
    log_message("=" * 60)
    log_message("🚀 加密货币数据自动采集守护进程已启动")
    log_message(f"📂 采集脚本: {collect_script}")
    log_message(f"📝 日志文件: {log_file}")
    log_message(f"🔄 采集间隔: 10分钟")
    log_message("=" * 60)
    
    # 检查采集脚本是否存在
    if not os.path.exists(collect_script):
        log_message(f"❌ 采集脚本不存在: {collect_script}")
        remove_pid()
        sys.exit(1)
    
    # 立即执行第一次采集
    log_message("🎯 执行首次数据采集...")
    collect_data()
    
    # 主循环
    interval = 600  # 10分钟 = 600秒
    last_collect_time = time.time()
    
    while running:
        try:
            # 计算距离下次采集的时间
            elapsed = time.time() - last_collect_time
            remaining = interval - elapsed
            
            if remaining <= 0:
                # 到达采集时间
                collect_data()
                last_collect_time = time.time()
            else:
                # 显示倒计时
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                
                # 每60秒输出一次倒计时
                if int(elapsed) % 60 == 0:
                    log_message(f"⏰ 距离下次采集还有: {minutes}分{seconds}秒")
                
                # 休眠1秒
                time.sleep(1)
                
        except KeyboardInterrupt:
            log_message("\n收到键盘中断信号")
            break
        except Exception as e:
            log_message(f"❌ 主循环异常: {e}")
            time.sleep(10)  # 出错后等待10秒再继续
    
    # 清理并退出
    log_message("=" * 60)
    log_message("🛑 守护进程已停止")
    log_message("=" * 60)
    remove_pid()

if __name__ == '__main__':
    main()
