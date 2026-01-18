#!/usr/bin/env python3
"""
回填1小时爆仓金额历史数据
从 panic_wash_index.jsonl 中提取 hour_1_amount 数据
"""

import json
import sys
from datetime import datetime
import pytz

# 北京时间
TZ = pytz.timezone('Asia/Shanghai')

# 数据文件
PANIC_DATA_FILE = '/home/user/webapp/data/panic_jsonl/panic_wash_index.jsonl'
LIQUIDATION_DATA_FILE = '/home/user/webapp/data/liquidation_1h/liquidation_1h.jsonl'

print("=" * 80)
print("🔄 开始回填1小时爆仓金额历史数据")
print("=" * 80)

# 读取panic历史数据
print(f"\n📖 读取panic历史数据: {PANIC_DATA_FILE}")
panic_records = []
with open(PANIC_DATA_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                record = json.loads(line)
                panic_records.append(record)
            except json.JSONDecodeError as e:
                print(f"⚠️ 跳过无效记录: {e}")
                continue

print(f"✅ 读取成功: {len(panic_records)} 条记录")
print(f"   时间范围: {panic_records[0]['record_time']} ~ {panic_records[-1]['record_time']}")

# 读取现有的liquidation数据（避免重复）
print(f"\n📖 读取现有liquidation数据: {LIQUIDATION_DATA_FILE}")
existing_timestamps = set()
try:
    with open(LIQUIDATION_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    existing_timestamps.add(record['timestamp'])
                except:
                    pass
    print(f"✅ 现有数据: {len(existing_timestamps)} 条")
except FileNotFoundError:
    print("⚠️ 文件不存在，将创建新文件")

# 转换并写入
print(f"\n🔄 开始转换并回填数据...")
converted_count = 0
skipped_count = 0

new_records = []

for record in panic_records:
    try:
        # 解析时间
        record_time = record['record_time']
        dt = datetime.strptime(record_time, '%Y-%m-%d %H:%M:%S')
        dt = TZ.localize(dt)
        timestamp = int(dt.timestamp())
        
        # 跳过已存在的记录
        if timestamp in existing_timestamps:
            skipped_count += 1
            continue
        
        # 提取数据
        hour_1_amount = record.get('hour_1_amount', 0)
        panic_index = record.get('panic_index')
        hour_24_amount = record.get('hour_24_amount')
        total_position = record.get('total_position')
        
        # 单位转换：panic数据中hour_1_amount是万美元，直接使用
        # （根据第一条数据 4.416097073377961 判断，应该已经是万美元）
        
        # 创建新记录
        new_record = {
            'timestamp': timestamp,
            'datetime': record_time,
            'hour_1_amount': round(float(hour_1_amount), 2)
        }
        
        # 添加可选字段
        if panic_index is not None:
            new_record['panic_index'] = round(float(panic_index), 4)
        if hour_24_amount is not None:
            new_record['hour_24_amount'] = round(float(hour_24_amount), 2)
        if total_position is not None:
            new_record['total_position'] = round(float(total_position), 2)
        
        new_records.append(new_record)
        converted_count += 1
        
    except Exception as e:
        print(f"❌ 转换失败: {record.get('record_time', 'unknown')} - {e}")
        continue

print(f"\n✅ 转换完成:")
print(f"   转换记录: {converted_count} 条")
print(f"   跳过记录: {skipped_count} 条（已存在）")

# 按时间排序
new_records.sort(key=lambda x: x['timestamp'])

# 写入文件
if new_records:
    print(f"\n💾 写入数据到: {LIQUIDATION_DATA_FILE}")
    
    # 读取所有现有数据
    all_records = []
    try:
        with open(LIQUIDATION_DATA_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        all_records.append(json.loads(line))
                    except:
                        pass
    except FileNotFoundError:
        pass
    
    # 合并新旧数据
    all_records.extend(new_records)
    
    # 按时间排序
    all_records.sort(key=lambda x: x['timestamp'])
    
    # 写回文件
    with open(LIQUIDATION_DATA_FILE, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 写入成功: {len(all_records)} 条记录")
    print(f"   最早时间: {all_records[0]['datetime']}")
    print(f"   最新时间: {all_records[-1]['datetime']}")
else:
    print("\n⚠️ 没有新数据需要写入")

print("\n" + "=" * 80)
print("✅ 回填完成！")
print("=" * 80)
