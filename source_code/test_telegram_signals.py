#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Telegram信号系统
"""

import requests
import json

API_BASE = "http://localhost:5000"

print("=" * 60)
print("🧪 Telegram信号系统测试")
print("=" * 60)
print()

# 1. 测试支撑压力线API
print("1️⃣ 测试支撑压力线API:")
try:
    url = f"{API_BASE}/api/support-resistance/latest-signal"
    response = requests.get(url, timeout=5)
    data = response.json()
    print(f"   ✅ API响应成功")
    print(f"   数据: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
except Exception as e:
    print(f"   ❌ 失败: {e}")
print()

# 2. 测试计次预警API (需要先重启Flask)
print("2️⃣ 测试计次预警API:")
try:
    url = f"{API_BASE}/api/latest"
    response = requests.get(url, timeout=5)
    data = response.json()
    print(f"   ✅ API响应成功")
    if 'count' in data:
        print(f"   计次: {data.get('count')}")
        print(f"   状态: {data.get('status')}")
except Exception as e:
    print(f"   ❌ 失败: {e}")
print()

# 3. 测试交易信号API
print("3️⃣ 测试交易信号API:")
try:
    url = f"{API_BASE}/api/trading-signals/analyze"
    response = requests.get(url, timeout=5)
    data = response.json()
    print(f"   ✅ API响应成功")
    signals = data.get('signals', [])
    print(f"   信号数量: {len(signals)}")
except Exception as e:
    print(f"   ❌ 失败: {e}")
print()

# 4. 测试K线指标API
print("4️⃣ 测试K线指标API:")
try:
    url = f"{API_BASE}/api/kline-indicators/signals"
    response = requests.get(url, timeout=5)
    data = response.json()
    print(f"   ✅ API响应成功")
    counts = data.get('data', {}).get('counts', {})
    print(f"   买点4: {counts.get('buy_point_4', 0)}")
    print(f"   卖点1: {counts.get('sell_point_1', 0)}")
except Exception as e:
    print(f"   ❌ 失败: {e}")
print()

print("=" * 60)
print("✅ 测试完成")
print("=" * 60)
