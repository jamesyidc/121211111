#!/usr/bin/env python3
"""
测试逃顶信号Telegram通知
"""
import sys
sys.path.append('/home/user/webapp/source_code')

from escape_signal_telegram_monitor import EscapeSignalTelegramMonitor

def main():
    print("="*60)
    print("🧪 测试逃顶信号Telegram通知系统")
    print("="*60)
    
    monitor = EscapeSignalTelegramMonitor()
    
    print("\n📊 检查空单盈亏状态...")
    monitor.check_short_positions()
    
    print("\n📊 检查2h和24h极值...")
    monitor.check_escape_peaks()
    
    print("\n✅ 测试完成")
    print("="*60)

if __name__ == '__main__':
    main()
