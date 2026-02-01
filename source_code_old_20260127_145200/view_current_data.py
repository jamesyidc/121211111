#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据查看工具 - 查看当前已采集的数据
"""

import json
import os
from datetime import datetime

DATA_FILE = "/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl"

def view_current_data():
    """查看当前数据"""
    
    if not os.path.exists(DATA_FILE):
        print("❌ 数据文件不存在")
        return
    
    # 读取所有记录
    records = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    pass
    
    if not records:
        print("❌ 无数据记录")
        return
    
    print("=" * 80)
    print(f"📊 当前数据概况")
    print("=" * 80)
    print(f"总记录数: {len(records)}")
    print(f"最早时间: {records[0]['collect_time']}")
    print(f"最新时间: {records[-1]['collect_time']}")
    print()
    
    # 按日期分组
    by_date = {}
    for record in records:
        date = record['collect_time'][:10]
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(record)
    
    print("📅 按日期统计:")
    for date in sorted(by_date.keys()):
        count = len(by_date[date])
        print(f"   {date}: {count} 个节点 ({count/48*100:.1f}%)")
    
    print()
    print("=" * 80)
    print(f"📈 最近5条记录详情")
    print("=" * 80)
    
    for record in records[-5:]:
        collect_time = record['collect_time']
        total_coins = record['total_coins']
        valid_coins = record['valid_coins']
        
        # 计算27币总和
        total_change = sum(coin['change_pct'] for coin in record['coins'].values())
        
        print(f"\n⏰ {collect_time}")
        print(f"   币种: {valid_coins}/{total_coins}")
        print(f"   27币总和: {total_change:+.4f}%")
        
        # 显示涨跌幅前3的币种
        coins_sorted = sorted(
            record['coins'].items(),
            key=lambda x: x[1]['change_pct'],
            reverse=True
        )
        
        print(f"   📈 涨幅最大:")
        for symbol, data in coins_sorted[:3]:
            if data['change_pct'] > 0:
                print(f"      {symbol}: {data['change_pct']:+.4f}%")
        
        print(f"   📉 跌幅最大:")
        for symbol, data in coins_sorted[-3:]:
            if data['change_pct'] < 0:
                print(f"      {symbol}: {data['change_pct']:+.4f}%")

if __name__ == '__main__':
    view_current_data()
