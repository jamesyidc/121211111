#!/usr/bin/env python3
"""
修复2026-01-17 23:00和23:30的数据错误

问题：这两个时间点使用了错误的基准价格（使用了当时的实时价格作为基准），
     导致涨跌幅接近0%，而实际应该是83%左右

解决方案：使用22:30的基准价格重新计算23:00和23:30的涨跌幅
"""
import json
import os
from datetime import datetime
import pytz

# 配置
DATA_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
BACKUP_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl.backup.before_fix_2330'
TZ = pytz.timezone('Asia/Shanghai')

def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   修复 2026-01-17 23:00 和 23:30 数据错误                  ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")
    
    # 1. 读取所有数据
    print("📖 读取数据文件...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    records = [json.loads(line) for line in lines]
    print(f"✅ 读取完成: {len(records)} 条记录\n")
    
    # 2. 找到关键时间点的数据
    print("🔍 定位关键时间点...")
    target_times = ['2026-01-17 23:00:00', '2026-01-17 23:30:00']
    reference_time = '2026-01-17 22:30:00'
    base_time = '2026-01-17 00:00:00'
    
    # 找到各个时间点的索引
    indices = {}
    for i, record in enumerate(records):
        collect_time = record['collect_time']
        if collect_time in target_times + [reference_time, base_time]:
            indices[collect_time] = i
            print(f"  找到 {collect_time}: 索引 {i}")
    
    if reference_time not in indices:
        print(f"❌ 错误: 找不到参考时间点 {reference_time}")
        return
    
    if base_time not in indices:
        print(f"❌ 错误: 找不到基准时间点 {base_time}")
        return
    
    # 3. 获取基准价格（使用00:00的base_price）
    print(f"\n📊 获取基准价格（来自 {base_time}）...")
    base_record = records[indices[base_time]]
    base_prices = {}
    
    for symbol, data in base_record['day_changes'].items():
        base_prices[symbol] = data['base_price']
        print(f"  {symbol}: ${base_prices[symbol]:.8f}")
    
    # 4. 创建备份
    print(f"\n💾 创建备份: {BACKUP_FILE}")
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line)
    print("✅ 备份完成")
    
    # 5. 修复23:00和23:30的数据
    print(f"\n🔧 开始修复数据...\n")
    
    for target_time in target_times:
        if target_time not in indices:
            print(f"⚠️  警告: 找不到 {target_time}，跳过")
            continue
        
        idx = indices[target_time]
        record = records[idx]
        
        print(f"📝 修复 {target_time}:")
        print(f"  修复前 total_change: {record['total_change']:.4f}%")
        
        # 重新计算每个币种的涨跌幅
        new_changes = {}
        total_change = 0
        
        for symbol, data in record['day_changes'].items():
            current_price = data['current_price']
            base_price = base_prices[symbol]
            
            if base_price > 0:
                change_pct = ((current_price - base_price) / base_price) * 100
            else:
                change_pct = 0
            
            new_changes[symbol] = {
                "base_price": base_price,
                "current_price": current_price,
                "change_pct": round(change_pct, 4)
            }
            
            total_change += change_pct
        
        # 更新记录
        record['day_changes'] = new_changes
        record['total_change'] = round(total_change, 4)
        record['average_change'] = round(total_change / len(new_changes), 4)
        
        records[idx] = record
        
        print(f"  修复后 total_change: {record['total_change']:.4f}%")
        print(f"  ✅ 修复完成\n")
    
    # 6. 保存修复后的数据
    print("💾 保存修复后的数据...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print("✅ 保存完成\n")
    
    # 7. 验证修复结果
    print("✅ 验证修复结果:")
    print(f"  22:30: {records[indices[reference_time]]['total_change']:.4f}%")
    for target_time in target_times:
        if target_time in indices:
            idx = indices[target_time]
            print(f"  {target_time.split()[1][:5]}: {records[idx]['total_change']:.4f}%")
    
    print("\n" + "="*66)
    print("🎉 修复完成！")
    print(f"📁 备份文件: {BACKUP_FILE}")
    print(f"📁 数据文件: {DATA_FILE}")
    print("="*66)

if __name__ == "__main__":
    main()
