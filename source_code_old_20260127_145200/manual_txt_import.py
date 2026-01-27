#!/usr/bin/env python3
"""
手动TXT文件导入工具
用法: python3 manual_txt_import.py <txt_file_path>
"""
import sys
import os

# 重用google_drive_snapshot_collector.py的逻辑
from google_drive_snapshot_collector import parse_txt_file, save_to_database, init_database

def main():
    if len(sys.argv) < 2:
        print("用法: python3 manual_txt_import.py <txt_file_path>")
        print("示例: python3 manual_txt_import.py /mnt/aidrive/2025-12-09_1240.txt")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    
    if not os.path.exists(txt_file):
        print(f"错误: 文件不存在: {txt_file}")
        sys.exit(1)
    
    print(f"开始导入文件: {txt_file}")
    
    # 初始化数据库
    init_database()
    
    # 解析文件
    snapshot_data, coins_data = parse_txt_file(txt_file)
    
    if not snapshot_data or not coins_data:
        print("错误: 解析文件失败")
        sys.exit(1)
    
    # 保存到数据库
    if save_to_database(snapshot_data, coins_data):
        print("✅ 导入成功！")
        print(f"   快照时间: {snapshot_data['snapshot_time']}")
        print(f"   急涨/急跌: {snapshot_data['rush_up']}/{snapshot_data['rush_down']}")
        print(f"   状态: {snapshot_data['status']}")
        print(f"   币种数量: {len(coins_data)}")
    else:
        print("❌ 保存失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
