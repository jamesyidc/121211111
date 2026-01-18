#!/usr/bin/env python3
"""
重新修复1月17日的数据 - 统一基准价格为00:00的价格
"""
import json
import shutil
from datetime import datetime
import pytz

TZ = pytz.timezone('Asia/Shanghai')
DATA_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
BACKUP_FILE = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl.backup_base_price'

# 27个币种
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

def main():
    print("=" * 60)
    print("🔧 修复1月17日数据的基准价格")
    print("=" * 60)
    
    # 1. 备份
    print("\n1️⃣  备份原文件...")
    shutil.copy2(DATA_FILE, BACKUP_FILE)
    print(f"✅ 已备份到: {BACKUP_FILE}")
    
    # 2. 读取所有数据
    print("\n2️⃣  读取数据...")
    records = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    print(f"✅ 读取 {len(records)} 条记录")
    
    # 3. 提取正确的基准价格（00:00）
    print("\n3️⃣  提取正确的基准价格...")
    correct_base_prices = {}
    
    for record in records:
        if record['collect_time'] == '2026-01-17 00:00:00':
            for symbol, data in record['day_changes'].items():
                # 00:00时，base_price 和 current_price 应该相同或非常接近
                base_price = data['base_price']
                current_price = data['current_price']
                # 使用00:00的价格作为基准
                correct_base_prices[symbol] = base_price
            break
    
    print(f"✅ 提取了 {len(correct_base_prices)} 个币种的基准价格")
    print(f"   BTC基准价: {correct_base_prices.get('BTC', 0):.2f}")
    print(f"   ETH基准价: {correct_base_prices.get('ETH', 0):.2f}")
    
    # 4. 修复1月17日的所有记录
    print("\n4️⃣  修复1月17日的数据...")
    fixed_count = 0
    
    for record in records:
        if not record['collect_time'].startswith('2026-01-17'):
            continue
        
        # 跳过00:00（它本身就是基准）
        if record['collect_time'] == '2026-01-17 00:00:00':
            continue
        
        # 重新计算涨跌幅
        for symbol in SYMBOLS:
            if symbol in record['day_changes'] and symbol in correct_base_prices:
                coin_data = record['day_changes'][symbol]
                current_price = coin_data['current_price']
                base_price = correct_base_prices[symbol]
                
                # 重新计算涨跌幅
                if base_price > 0:
                    change_pct = ((current_price - base_price) / base_price) * 100
                    coin_data['base_price'] = base_price
                    coin_data['change_pct'] = round(change_pct, 4)
        
        # 重新计算 total_change
        total_change = sum(
            coin_data.get('change_pct', 0)
            for coin_data in record['day_changes'].values()
        )
        record['total_change'] = round(total_change, 4)
        
        # 重新计算 average_change
        valid_count = sum(
            1 for coin_data in record['day_changes'].values()
            if coin_data.get('current_price', 0) > 0
        )
        if valid_count > 0:
            record['average_change'] = round(total_change / valid_count, 4)
        
        fixed_count += 1
    
    print(f"✅ 修复了 {fixed_count} 条1月17日的记录")
    
    # 5. 写回文件
    print("\n5️⃣  写回文件...")
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f"✅ 已写入 {len(records)} 条记录")
    
    # 6. 验证修复结果
    print("\n6️⃣  验证修复结果...")
    print("\\n检查1月17日关键时间点的BTC数据:")
    print("时间\\t\\t\\t基准价\\t\\t当前价\\t\\t涨跌幅\\t27币总和")
    print("-" * 90)
    
    for record in records:
        if record['collect_time'].startswith('2026-01-17'):
            time_str = record['collect_time']
            # 只显示部分关键时间点
            if any(t in time_str for t in ['00:00:00', '06:00:00', '12:00:00', '18:00:00', '19:00:00', '20:00:00', '21:00:00']):
                btc_data = record['day_changes'].get('BTC', {})
                base_price = btc_data.get('base_price', 0)
                current_price = btc_data.get('current_price', 0)
                change_pct = btc_data.get('change_pct', 0)
                total_change = record.get('total_change', 0)
                
                print(f"{time_str}\\t{base_price:.1f}\\t\\t{current_price:.1f}\\t\\t{change_pct:+.2f}%\\t{total_change:+.2f}%")
    
    print("\n" + "=" * 60)
    print("✅ 基准价格修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
