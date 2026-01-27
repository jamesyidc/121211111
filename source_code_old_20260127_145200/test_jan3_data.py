#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版历史数据回填 - 测试用
先获取1月3日一天的数据来验证方法是否可行
"""

import requests
from datetime import datetime, timedelta
import pytz
import time
import json

TZ = pytz.timezone('Asia/Shanghai')
OKX_API_BASE = "https://www.okx.com/api/v5"

# 测试：获取BTC在1月3日的30分钟K线
start = datetime(2026, 1, 3, 0, 0, 0, tzinfo=TZ)
end = datetime(2026, 1, 3, 23, 59, 59, tzinfo=TZ)

start_ts = int(start.timestamp() * 1000)
end_ts = int(end.timestamp() * 1000)

print(f"🎯 目标日期: {start.strftime('%Y-%m-%d')}")
print(f"🎯 起始时间戳: {start_ts}")
print(f"🎯 结束时间戳: {end_ts}")
print()

# 使用after参数获取
params = {
    'instId': 'BTC-USDT-SWAP',
    'bar': '30m',
    'after': str(start_ts),
    'limit': '100'
}

url = f"{OKX_API_BASE}/market/candles"
response = requests.get(url, params=params, timeout=10)

if response.status_code == 200:
    data = response.json()
    print(f"✅ API响应成功")
    print(f"📊 返回K线数: {len(data.get('data', []))}")
    
    if data.get('data'):
        klines = data['data']
        
        print(f"\n📋 前10条K线:")
        for i, kline in enumerate(klines[:10]):
            ts = int(kline[0])
            kline_time = datetime.fromtimestamp(ts/1000, TZ)
            close_price = float(kline[4])
            print(f"   {i+1}. {kline_time.strftime('%Y-%m-%d %H:%M:%S')} | ${close_price:.2f}")
        
        # 统计1月3日的K线
        jan3_klines = []
        for kline in klines:
            ts = int(kline[0])
            kline_time = datetime.fromtimestamp(ts/1000, TZ)
            if kline_time.date() == start.date():
                jan3_klines.append((kline_time, float(kline[4])))
        
        print(f"\n🎯 1月3日的K线数: {len(jan3_klines)}")
        
        if jan3_klines:
            print(f"\n✅ 成功！可以获取1月3日的数据！")
            print(f"   第一条: {jan3_klines[0][0].strftime('%Y-%m-%d %H:%M:%S')} | ${jan3_klines[0][1]:.2f}")
            print(f"   最后一条: {jan3_klines[-1][0].strftime('%Y-%m-%d %H:%M:%S')} | ${jan3_klines[-1][1]:.2f}")
        else:
            print(f"\n❌ 失败：没有获取到1月3日的K线")
            print(f"   可能原因：API只返回了更早或更晚的数据")

EOF
