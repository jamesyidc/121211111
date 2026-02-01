#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAR斜率数据定时导出器
每30秒更新一次SAR斜率数据到JSONL
"""

import sys
import time
from datetime import datetime

sys.path.insert(0, '/home/user/webapp/source_code')
from sar_slope_jsonl_manager import SARSlopeJSONLManager

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def main():
    """主函数"""
    log("🔄 开始更新SAR斜率数据...")
    
    manager = SARSlopeJSONLManager()
    count = manager.export_to_jsonl()
    
    if count > 0:
        log(f"✅ 更新完成: {count} 个币种")
    else:
        log("⚠️  无数据更新")

if __name__ == '__main__':
    log("🚀 SAR斜率定时导出器启动")
    log("📅 更新间隔: 每30秒一次")
    
    while True:
        try:
            main()
            log("⏰ 等待30秒后开始下一轮更新...")
            time.sleep(30)
        except KeyboardInterrupt:
            log("⚠️  收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 更新出错: {e}")
            log("⏰ 等待10秒后重试...")
            time.sleep(10)
