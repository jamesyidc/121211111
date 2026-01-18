#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单自动开仓守护进程
定期扫描逃顶信号并自动开仓
"""

import time
import sys
import traceback
from datetime import datetime
import pytz
from anchor_auto_opener import AnchorAutoOpener

# 配置
SCAN_INTERVAL = 30  # 扫描间隔（秒）
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def main():
    """主循环"""
    print("=" * 80)
    print("🚀 锚点单自动开仓守护进程启动")
    print(f"⏰ 启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔄 扫描间隔: {SCAN_INTERVAL}秒")
    print("=" * 80)
    print()
    
    opener = AnchorAutoOpener()
    
    while True:
        try:
            # 执行一次扫描和处理
            result = opener.scan_and_process()
            
            # 等待下一次扫描
            time.sleep(SCAN_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  收到停止信号，正在退出...")
            sys.exit(0)
            
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            traceback.print_exc()
            print(f"⏰ 等待{SCAN_INTERVAL}秒后继续...\n")
            time.sleep(SCAN_INTERVAL)


if __name__ == '__main__':
    main()
