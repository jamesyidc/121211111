#!/usr/bin/env python3
"""
自动更新 latest_sar_slope.jsonl
从 sar_jsonl 目录的数据生成最新的合并文件
"""

import sys
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')
sys.path.insert(0, '/home/user/webapp')

from sar_slope_jsonl_manager import SARSlopeJSONLManager

def update_latest_sar_slope():
    """更新 latest_sar_slope.jsonl 文件"""
    try:
        manager = SARSlopeJSONLManager(sar_jsonl_dir='/home/user/webapp/data/sar_jsonl')
        count = manager.export_to_jsonl(
            output_file='/home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl'
        )
        
        print(f"✅ 成功更新 latest_sar_slope.jsonl，包含 {count} 个币种")
        return True
    
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_daemon(interval=300):
    """
    守护进程模式 - 每5分钟更新一次
    
    参数:
        interval: 更新间隔（秒），默认300秒（5分钟）
    """
    print(f"🚀 启动 SAR Slope 更新守护进程")
    print(f"   更新间隔: {interval}秒 ({interval//60}分钟)")
    print(f"   数据源: /home/user/webapp/data/sar_jsonl/")
    print(f"   目标文件: /home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl")
    print("=" * 60)
    
    cycle_count = 0
    
    while True:
        try:
            cycle_count += 1
            print(f"\n[周期 {cycle_count}] 开始更新...")
            
            if update_latest_sar_slope():
                print(f"✅ 更新成功")
            else:
                print(f"❌ 更新失败")
            
            print(f"⏰ 等待 {interval}秒后进行下一次更新...")
            time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⏹️  守护进程已停止")
            break
        
        except Exception as e:
            print(f"❌ 异常错误: {e}")
            import traceback
            traceback.print_exc()
            print(f"⏰ 60秒后重试...")
            time.sleep(60)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='更新 latest_sar_slope.jsonl')
    parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    parser.add_argument('--interval', type=int, default=300, help='更新间隔（秒），默认300')
    
    args = parser.parse_args()
    
    if args.daemon:
        run_daemon(interval=args.interval)
    else:
        # 单次运行
        update_latest_sar_slope()
