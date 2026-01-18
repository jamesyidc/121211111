#!/usr/bin/env python3
"""
修复00:00数据，确保涨跌幅为0%

修复逻辑：
- 找到所有 HH:MM:SS 为 00:00:00 的记录
- 将 base_price 设为 current_price（确保涨跌幅为0%）
- 重新计算 total_change 和 average_change
"""
import json
import os
from datetime import datetime
import pytz

# 配置
DATA_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
BACKUP_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl.backup.before_fix_0000'
TZ = pytz.timezone('Asia/Shanghai')

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   修复所有00:00数据，确保涨跌幅为0%                        ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    # 1. 读取所有数据
    print("📖 读取数据文件...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    records = [json.loads(line) for line in lines]
    print(f"✅ 读取完成: {len(records)} 条记录\n")
    
    # 2. 找到所有00:00的记录
    print("🔍 查找所有00:00的记录...")
    indices_00 = []
    for i, record in enumerate(records):
        collect_time = record['collect_time']
        if collect_time.endswith(' 00:00:00'):
            indices_00.append(i)
            print(f"  找到 {collect_time}: 索引 {i}")
    
    if not indices_00:
        print("\n⚠️  没有找到00:00的记录，无需修复")
        return
    
    print(f"\n找到 {len(indices_00)} 条00:00记录需要修复\n")
    
    # 3. 创建备份
    print(f"💾 创建备份: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line)
    print("✅ 备份完成\n")
    
    # 4. 修复所有00:00的记录
    print("🔧 开始修复数据...\n")
    
    for idx in indices_00:
        record = records[idx]
        collect_time = record['collect_time']
        
        print(f"📝 修复 {collect_time}:")
        print(f"  修复前 total_change: {record['total_change']:.4f}%")
        
        # 将base_price设为current_price
        new_changes = {}
        for symbol, data in record['day_changes'].items():
            current_price = data['current_price']
            
            new_changes[symbol] = {
                "base_price": current_price,  # 设为current_price，确保涨跌幅为0
                "current_price": current_price,
                "change_pct": 0.0  # 涨跌幅为0
            }
        
        # 更新记录
        record['day_changes'] = new_changes
        record['total_change'] = 0.0
        record['average_change'] = 0.0
        
        records[idx] = record
        
        print(f"  修复后 total_change: {record['total_change']:.4f}%")
        print(f"  ✅ 修复完成\n")
    
    # 5. 保存修复后的数据
    print("💾 保存修复后的数据...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print("✅ 保存完成\n")
    
    # 6. 验证修复结果
    print("✅ 验证修复结果:")
    for idx in indices_00:
        record = records[idx]
        print(f"  {record['collect_time']}: {record['total_change']:.4f}%")
    
    print("\n" + "="*66)
    print("🎉 修复完成！")
    print(f"📁 备份文件: {BACKUP_FILE}")
    print(f"📁 数据文件: {DATA_FILE}")
    print(f"✅ 修复了 {len(indices_00)} 条00:00记录，所有涨跌幅已设为0%")
    print("="*66)

if __name__ == "__main__":
    main()
