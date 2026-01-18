"""
修复后的后台更新线程逻辑
"""
import time
from datetime import datetime, timedelta

UPDATE_CYCLE = 180  # 3分钟
GDRIVE_WAIT_TIME = 10  # 第10秒
GDRIVE_WAIT_MAX = 15   # 第15秒

def background_updater_fixed():
    """
    修复后的后台定时更新线程
    
    问题修复：
    1. 简化时间计算逻辑
    2. 确保每次循环都能正确到达采集窗口
    3. 固定的UPDATE_CYCLE间隔
    """
    print("🚀 后台更新线程启动（已修复版本）")
    print(f"⏰ 更新周期: {UPDATE_CYCLE}秒 ({UPDATE_CYCLE/60:.1f}分钟)")
    print(f"⏰ 数据采集窗口: 每个周期的第{GDRIVE_WAIT_TIME}-{GDRIVE_WAIT_MAX}秒")
    print("="*70)
    
    while True:
        try:
            current_time = datetime.now()
            current_minute = current_time.minute
            current_second = current_time.second
            
            print(f"\n⏰ 当前时间: {current_time.strftime('%H:%M:%S')}")
            
            # 计算距离下一个3分钟周期的开始还有多少时间
            minutes_since_cycle = current_minute % 3
            
            if minutes_since_cycle == 0:
                # 当前在3分钟周期的开始分钟 (0, 3, 6, 9, ...)
                if current_second < GDRIVE_WAIT_TIME:
                    # 在第0-9秒，等待到第10秒
                    wait_seconds = GDRIVE_WAIT_TIME - current_second
                    print(f"✅ 在3分钟周期开始，等待{wait_seconds}秒到第{GDRIVE_WAIT_TIME}秒...")
                    time.sleep(wait_seconds)
                    print(f"✅ 到达采集窗口，开始更新数据")
                elif current_second <= GDRIVE_WAIT_MAX:
                    # 在第10-15秒，立即执行
                    print(f"✅ 正好在采集窗口内（第{current_second}秒），立即开始")
                else:
                    # 在第16-59秒，已经错过窗口，等到下一个周期
                    wait_seconds = UPDATE_CYCLE - current_second + GDRIVE_WAIT_TIME
                    print(f"⚠️  已过本周期采集窗口，等待{wait_seconds}秒到下一个周期...")
                    time.sleep(wait_seconds)
                    print(f"✅ 到达下一个采集窗口，开始更新数据")
            else:
                # 不在3分钟周期的开始，计算等到下一个周期的时间
                minutes_to_wait = 3 - minutes_since_cycle
                seconds_to_wait = minutes_to_wait * 60 - current_second + GDRIVE_WAIT_TIME
                print(f"⏰ 等待{seconds_to_wait}秒（{seconds_to_wait/60:.1f}分钟）到下一个采集窗口...")
                time.sleep(seconds_to_wait)
                print(f"✅ 到达采集窗口，开始更新数据")
            
            # ===== 执行数据更新 =====
            print(f"\n📡 [{datetime.now().strftime('%H:%M:%S')}] 开始数据更新...")
            
            # 这里调用实际的更新函数
            # update_cache()
            # sync_signal_stats()
            # sync_panic_wash_data()
            print("   1. 更新首页数据缓存")
            print("   2. 同步信号统计数据")
            print("   3. 同步恐慌清洗数据")
            
            print(f"✅ 数据更新完成")
            
            # ===== 等待到下一个周期 =====
            next_update = datetime.now() + timedelta(seconds=UPDATE_CYCLE)
            print(f"⏰ 下次更新时间: {next_update.strftime('%H:%M:%S')}")
            print(f"⏰ 休眠{UPDATE_CYCLE}秒...")
            print("="*70)
            
            time.sleep(UPDATE_CYCLE)
            
        except Exception as e:
            print(f"\n❌ 后台更新线程错误: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"⏰ 60秒后重试...\n")
            time.sleep(60)

if __name__ == '__main__':
    print("测试修复后的后台更新逻辑（Ctrl+C停止）")
    background_updater_fixed()
