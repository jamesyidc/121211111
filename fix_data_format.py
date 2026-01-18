#!/usr/bin/env python3
"""
修复coin_prices_30min.jsonl数据格式
- 统一字段名：coins -> day_changes
- 添加total_change字段（27币涨跌幅总和）
- 补全19:30-21:30的数据
"""
import os
import sys
import json
import requests
import time
from datetime import datetime, timedelta
import pytz
import shutil

# 配置
TZ = pytz.timezone('Asia/Shanghai')
DATA_DIR = '/home/user/webapp/data/coin_price_tracker'
JSONL_FILE = os.path.join(DATA_DIR, 'coin_prices_30min.jsonl')
BACKUP_FILE = os.path.join(DATA_DIR, 'coin_prices_30min.jsonl.backup_format')

# 27个币种
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

# OKX API
OKX_API_BASE = "https://www.okx.com/api/v5"

def fetch_okx_price(symbol):
    """获取OKX实时价格"""
    try:
        inst_id = f"{symbol}-USDT-SWAP"
        url = f"{OKX_API_BASE}/market/ticker"
        params = {"instId": inst_id}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                last_price = float(data['data'][0]['last'])
                return last_price, None
            else:
                return None, f"API返回错误: {data.get('msg', 'Unknown')}"
        else:
            return None, f"HTTP {response.status_code}"
    except Exception as e:
        return None, str(e)

def get_today_start():
    """获取今天00:00的时间"""
    now = datetime.now(TZ)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def fetch_base_prices_for_date(date_str):
    """获取指定日期00:00的基准价格（用于补全数据）"""
    print(f"📊 获取 {date_str} 00:00 的基准价格...")
    
    base_prices = {}
    success_count = 0
    
    for symbol in SYMBOLS:
        price, error = fetch_okx_price(symbol)
        
        if price:
            base_prices[symbol] = price
            success_count += 1
            print(f"  ✅ {symbol}: ${price:.8f}")
        else:
            print(f"  ❌ {symbol}: {error}")
        
        time.sleep(0.05)
    
    print(f"✅ 基准价格获取完成: {success_count}/{len(SYMBOLS)}")
    return base_prices

def normalize_record(record):
    """规范化单条记录格式"""
    normalized = {
        "collect_time": record.get("collect_time"),
        "timestamp": record.get("timestamp"),
        "base_date": record.get("base_date"),
        "total_coins": record.get("total_coins", 27),
        "valid_coins": record.get("valid_coins", 27)
    }
    
    # 处理 coins/day_changes 字段
    coin_data = record.get("day_changes") or record.get("coins") or {}
    
    # 统一为 day_changes
    normalized["day_changes"] = coin_data
    
    # 计算 total_change（27币涨跌幅总和）
    total_change = sum(
        coin_info.get("change_pct", 0)
        for coin_info in coin_data.values()
    )
    normalized["total_change"] = round(total_change, 4)
    
    # 计算 average_change
    valid_count = sum(1 for v in coin_data.values() if v.get("current_price", 0) > 0)
    if valid_count > 0:
        normalized["average_change"] = round(total_change / valid_count, 4)
    else:
        normalized["average_change"] = 0
    
    # 统计成功/失败数量
    success_count = sum(1 for v in coin_data.values() if v.get("current_price", 0) > 0)
    failed_count = len(SYMBOLS) - success_count
    normalized["success_count"] = success_count
    normalized["failed_count"] = failed_count
    
    return normalized

def generate_missing_time_slots():
    """生成需要补全的时间点（19:30到现在，每30分钟）"""
    slots = []
    now = datetime.now(TZ)
    
    # 从19:30开始
    start_time = datetime(2026, 1, 17, 19, 30, 0, tzinfo=TZ)
    
    # 对齐到30分钟
    current = start_time
    while current <= now:
        # 向下对齐到最近的30分钟
        minute = (current.minute // 30) * 30
        aligned_time = current.replace(minute=minute, second=0, microsecond=0)
        
        if aligned_time > datetime(2026, 1, 17, 19, 0, 0, tzinfo=TZ):
            slots.append(aligned_time)
        
        current += timedelta(minutes=30)
    
    return slots

def collect_data_for_time(target_time, base_prices):
    """为指定时间点采集数据"""
    print(f"\n📊 采集 {target_time.strftime('%Y-%m-%d %H:%M:%S')} 的数据...")
    
    current_prices = {}
    success_count = 0
    
    for symbol in SYMBOLS:
        price, error = fetch_okx_price(symbol)
        
        if price:
            current_prices[symbol] = price
            success_count += 1
            print(f"  ✅ {symbol}: ${price:.8f}")
        else:
            print(f"  ❌ {symbol}: {error}")
        
        time.sleep(0.05)
    
    # 计算涨跌幅
    day_changes = {}
    for symbol in SYMBOLS:
        if symbol in base_prices and symbol in current_prices:
            base_price = base_prices[symbol]
            current_price = current_prices[symbol]
            
            if base_price > 0:
                change_pct = ((current_price - base_price) / base_price) * 100
                day_changes[symbol] = {
                    "base_price": base_price,
                    "current_price": current_price,
                    "change_pct": round(change_pct, 4)
                }
            else:
                day_changes[symbol] = {
                    "base_price": 0,
                    "current_price": current_price,
                    "change_pct": 0
                }
        else:
            day_changes[symbol] = {
                "base_price": base_prices.get(symbol, 0),
                "current_price": current_prices.get(symbol, 0),
                "change_pct": 0
            }
    
    # 计算总和
    total_change = sum(v["change_pct"] for v in day_changes.values())
    average_change = total_change / len(SYMBOLS) if len(SYMBOLS) > 0 else 0
    
    # 构建记录
    record = {
        "collect_time": target_time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(target_time.timestamp()),
        "base_date": target_time.strftime("%Y-%m-%d"),
        "day_changes": day_changes,
        "total_change": round(total_change, 4),
        "average_change": round(average_change, 4),
        "total_coins": len(SYMBOLS),
        "valid_coins": success_count,
        "success_count": success_count,
        "failed_count": len(SYMBOLS) - success_count
    }
    
    print(f"✅ 数据采集完成: {success_count}/{len(SYMBOLS)} 成功")
    print(f"📈 27币涨跌幅总和: {total_change:.4f}%")
    
    return record

def main():
    print("=" * 60)
    print("🔧 修复 coin_prices_30min.jsonl 数据格式")
    print("=" * 60)
    
    # 1. 备份原文件
    print(f"\n1️⃣  备份原文件...")
    shutil.copy2(JSONL_FILE, BACKUP_FILE)
    print(f"✅ 已备份到: {BACKUP_FILE}")
    
    # 2. 读取并规范化现有数据
    print(f"\n2️⃣  规范化现有数据...")
    records = []
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                normalized = normalize_record(record)
                records.append(normalized)
            except Exception as e:
                print(f"  ⚠️  第{line_num}行解析失败: {e}")
    
    print(f"✅ 成功规范化 {len(records)} 条记录")
    
    # 检查最后一条记录的时间
    if records:
        last_time_str = records[-1]["collect_time"]
        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
        last_time = TZ.localize(last_time)
        print(f"📅 最后一条记录: {last_time_str}")
    
    # 3. 补全缺失的时间点
    print(f"\n3️⃣  补全缺失的时间点...")
    missing_slots = generate_missing_time_slots()
    
    if missing_slots:
        print(f"📋 需要补全 {len(missing_slots)} 个时间点:")
        for slot in missing_slots:
            print(f"  - {slot.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取今天的基准价格
        print(f"\n📊 获取今天00:00的基准价格...")
        base_prices = {}
        
        # 尝试从已有数据中找基准价格
        for record in records:
            if record["base_date"] == "2026-01-17":
                if "day_changes" in record:
                    for symbol, data in record["day_changes"].items():
                        if symbol not in base_prices and data.get("base_price", 0) > 0:
                            base_prices[symbol] = data["base_price"]
        
        print(f"✅ 从历史数据中找到 {len(base_prices)} 个币种的基准价格")
        
        # 如果基准价格不完整，从API获取
        if len(base_prices) < len(SYMBOLS):
            print(f"⚠️  基准价格不完整，从API获取...")
            api_base_prices = fetch_base_prices_for_date("2026-01-17")
            for symbol, price in api_base_prices.items():
                if symbol not in base_prices:
                    base_prices[symbol] = price
        
        # 为每个缺失时间点采集数据
        for slot in missing_slots:
            new_record = collect_data_for_time(slot, base_prices)
            records.append(new_record)
            time.sleep(1)  # 避免请求过快
    else:
        print("✅ 没有缺失的时间点")
    
    # 4. 按时间排序
    print(f"\n4️⃣  按时间排序...")
    records.sort(key=lambda x: x["timestamp"])
    print(f"✅ 排序完成")
    
    # 5. 写回文件
    print(f"\n5️⃣  写回文件...")
    with open(JSONL_FILE, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 已写入 {len(records)} 条记录")
    
    # 6. 验证
    print(f"\n6️⃣  验证结果...")
    print(f"📊 总记录数: {len(records)}")
    print(f"📅 时间范围: {records[0]['collect_time']} 至 {records[-1]['collect_time']}")
    
    # 检查最后5条记录
    print(f"\n📋 最后5条记录:")
    for record in records[-5:]:
        total_change = record.get("total_change", 0)
        print(f"  {record['collect_time']}: 27币总和={total_change:+.4f}%, valid={record.get('valid_coins', 0)}/27")
    
    print(f"\n" + "=" * 60)
    print("✅ 数据格式修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
