#!/usr/bin/env python3
"""
技术指标自动同步守护进程
每5分钟自动运行一次，为新K线计算并同步技术指标
"""

import time
import subprocess
import sys
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
SYNC_INTERVAL = 300  # 5分钟 = 300秒

def run_sync():
    """运行技术指标同步脚本"""
    try:
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*80}")
        print(f"⏰ {now} - 开始同步技术指标")
        print(f"{'='*80}")
        
        # 运行同步脚本
        result = subprocess.run(
            [sys.executable, 'sync_technical_indicators.py'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )
        
        if result.returncode == 0:
            print("✅ 同步成功")
            # 只显示最后几行输出
            lines = result.stdout.strip().split('\n')
            for line in lines[-10:]:
                print(f"  {line}")
        else:
            print(f"❌ 同步失败 (退出码: {result.returncode})")
            print(f"错误: {result.stderr}")
        
        now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"⏰ {now} - 同步完成")
        print(f"{'='*80}\n")
        
    except subprocess.TimeoutExpired:
        print("❌ 同步超时（超过2分钟）")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主循环"""
    print("=" * 80)
    print("🚀 技术指标自动同步守护进程")
    print("=" * 80)
    print(f"⏰ 启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"⏱️  同步间隔: {SYNC_INTERVAL}秒 (每5分钟)")
    print(f"📊 监控对象: 所有币种的5m和1H K线")
    print("=" * 80)
    
    # 首次立即运行一次
    print("\n🚀 执行首次同步...")
    run_sync()
    
    # 然后进入定时循环
    while True:
        try:
            # 等待到下一个5分钟整点
            now = time.time()
            wait_time = SYNC_INTERVAL - (now % SYNC_INTERVAL)
            
            next_run = datetime.fromtimestamp(now + wait_time, BEIJING_TZ)
            print(f"💤 等待下次同步... 下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(wait_time)
            
            # 运行同步
            run_sync()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  收到停止信号，正在关闭守护进程...")
            break
        except Exception as e:
            print(f"\n❌ 主循环错误: {e}")
            import traceback
            traceback.print_exc()
            # 等待5分钟后重试
            time.sleep(SYNC_INTERVAL)

if __name__ == '__main__':
    main()
