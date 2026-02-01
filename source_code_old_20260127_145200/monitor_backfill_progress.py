#!/usr/bin/env python3
"""
实时监控回填进度
"""

import os
import time
import subprocess
from datetime import datetime

LOG_FILE = '/home/user/webapp/logs/coin_price_backfill.log'
DATA_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'

def get_latest_progress():
    """获取最新进度"""
    try:
        # 读取日志最后100行
        result = subprocess.run(
            ['tail', '-100', LOG_FILE],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.strip().split('\n')
        
        # 查找最新的进度信息
        progress_info = None
        current_date = None
        
        for line in reversed(lines):
            if '进度:' in line and '已完成:' in line:
                progress_info = line
                break
            if '🔄 处理日期:' in line:
                current_date = line.split('处理日期:')[-1].strip()
        
        # 统计数据文件行数
        result = subprocess.run(
            ['wc', '-l', DATA_FILE],
            capture_output=True,
            text=True
        )
        data_count = int(result.stdout.split()[0])
        
        return {
            'progress_line': progress_info,
            'current_date': current_date,
            'data_count': data_count,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def main():
    """主函数"""
    print("="*80)
    print("27币种历史数据回填 - 实时进度监控")
    print("="*80)
    print()
    
    last_count = 0
    
    while True:
        info = get_latest_progress()
        
        os.system('clear')
        
        print("="*80)
        print("📊 实时进度监控")
        print("="*80)
        print()
        print(f"⏰ 当前时间: {info['timestamp']}")
        print()
        
        if 'error' in info:
            print(f"❌ 错误: {info['error']}")
        else:
            print(f"📁 数据文件: {DATA_FILE}")
            print(f"📈 当前行数: {info['data_count']} 条")
            
            if last_count > 0:
                diff = info['data_count'] - last_count
                if diff > 0:
                    print(f"🔄 新增数据: +{diff} 条")
            
            print()
            
            if info['current_date']:
                print(f"📅 处理日期: {info['current_date']}")
            
            if info['progress_line']:
                print(f"📊 最新进度: {info['progress_line'].split(' - INFO - ')[-1]}")
            
            print()
            print("-"*80)
            print("预期总数: 672个时间节点")
            print("目标覆盖: 2026-01-03 至 2026-01-16 (14天)")
            print("-"*80)
            
            last_count = info['data_count']
        
        print()
        print("⏸️  按 Ctrl+C 退出监控")
        
        time.sleep(5)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ 监控已停止")
