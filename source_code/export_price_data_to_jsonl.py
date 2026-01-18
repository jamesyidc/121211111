#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将比价系统数据从数据库导出到JSONL文件
包括：price_baseline、price_breakthrough_events、price_comparison_stats
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

# 路径配置
DB_PATH = '/home/user/webapp/databases/crypto_data.db'
JSONL_DIR = '/home/user/webapp/data/price_comparison_jsonl'

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def ensure_directory():
    """确保目录存在"""
    Path(JSONL_DIR).mkdir(parents=True, exist_ok=True)
    log(f"✅ 数据目录已创建: {JSONL_DIR}")

def export_price_baseline():
    """导出价格基准数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, highest_price, highest_count, lowest_price, lowest_count,
                   last_price, highest_ratio, lowest_ratio, last_update_time, 
                   created_at, display_order
            FROM price_baseline
            ORDER BY display_order
        ''')
        
        rows = cursor.fetchall()
        
        output_file = os.path.join(JSONL_DIR, 'price_baseline.jsonl')
        with open(output_file, 'w') as f:
            for row in rows:
                data = dict(row)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        conn.close()
        
        log(f"✅ 价格基准数据已导出: {len(rows)} 条记录 -> {output_file}")
        return len(rows)
        
    except Exception as e:
        log(f"❌ 导出价格基准数据失败: {e}")
        return 0

def export_breakthrough_events():
    """导出突破事件数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, event_type, price, previous_extreme_price, 
                   event_time
            FROM price_breakthrough_events
            ORDER BY event_time DESC
        ''')
        
        rows = cursor.fetchall()
        
        output_file = os.path.join(JSONL_DIR, 'price_breakthrough_events.jsonl')
        with open(output_file, 'w') as f:
            for row in rows:
                data = dict(row)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        conn.close()
        
        log(f"✅ 突破事件数据已导出: {len(rows)} 条记录 -> {output_file}")
        return len(rows)
        
    except Exception as e:
        log(f"❌ 导出突破事件数据失败: {e}")
        return 0

def export_comparison_stats():
    """导出统计汇总数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, stat_date, today_new_high, today_new_low,
                   three_days_new_high, three_days_new_low,
                   seven_days_new_high, seven_days_new_low, record_time
            FROM price_comparison_stats
            ORDER BY stat_date DESC
        ''')
        
        rows = cursor.fetchall()
        
        output_file = os.path.join(JSONL_DIR, 'price_comparison_stats.jsonl')
        with open(output_file, 'w') as f:
            for row in rows:
                data = dict(row)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        conn.close()
        
        log(f"✅ 统计汇总数据已导出: {len(rows)} 条记录 -> {output_file}")
        return len(rows)
        
    except Exception as e:
        log(f"❌ 导出统计汇总数据失败: {e}")
        return 0

def create_latest_snapshot():
    """创建最新数据快照（用于快速读取）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取所有币种的最新数据
        cursor.execute('''
            SELECT symbol, highest_price, highest_count, lowest_price, lowest_count,
                   last_price, highest_ratio, lowest_ratio, last_update_time
            FROM price_baseline
            ORDER BY display_order
        ''')
        
        rows = cursor.fetchall()
        
        # 写入最新快照
        output_file = os.path.join(JSONL_DIR, 'latest_price_baseline.jsonl')
        with open(output_file, 'w') as f:
            for row in rows:
                data = dict(row)
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        conn.close()
        
        log(f"✅ 最新数据快照已创建: {len(rows)} 条记录 -> {output_file}")
        return len(rows)
        
    except Exception as e:
        log(f"❌ 创建最新快照失败: {e}")
        return 0

def export_summary():
    """导出汇总统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 统计数据
        stats = {}
        
        # 币种总数
        cursor.execute('SELECT COUNT(*) FROM price_baseline')
        stats['total_coins'] = cursor.fetchone()[0]
        
        # 突破事件总数
        cursor.execute('SELECT COUNT(*) FROM price_breakthrough_events')
        stats['total_breakthrough_events'] = cursor.fetchone()[0]
        
        # 创新高/创新低分布
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM price_breakthrough_events
            GROUP BY event_type
        ''')
        breakthrough_stats = {}
        for row in cursor.fetchall():
            breakthrough_stats[row[0]] = row[1]
        stats['breakthrough_by_type'] = breakthrough_stats
        
        # 最近更新时间
        cursor.execute('SELECT MAX(last_update_time) FROM price_baseline')
        stats['last_update_time'] = cursor.fetchone()[0]
        
        # 导出时间
        stats['export_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.close()
        
        # 写入汇总文件
        output_file = os.path.join(JSONL_DIR, 'summary.json')
        with open(output_file, 'w') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        log(f"✅ 汇总统计已导出 -> {output_file}")
        log(f"   总币种: {stats['total_coins']}")
        log(f"   突破事件: {stats['total_breakthrough_events']}")
        log(f"   最后更新: {stats['last_update_time']}")
        
        return stats
        
    except Exception as e:
        log(f"❌ 导出汇总统计失败: {e}")
        return None

def main():
    """主函数"""
    log("=" * 60)
    log("开始导出比价系统数据到JSONL")
    log("=" * 60)
    
    # 确保目录存在
    ensure_directory()
    
    # 导出各类数据
    baseline_count = export_price_baseline()
    events_count = export_breakthrough_events()
    stats_count = export_comparison_stats()
    latest_count = create_latest_snapshot()
    
    # 导出汇总信息
    summary = export_summary()
    
    log("=" * 60)
    log("✅ 数据导出完成!")
    log("=" * 60)
    log(f"价格基准: {baseline_count} 条")
    log(f"突破事件: {events_count} 条")
    log(f"统计汇总: {stats_count} 条")
    log(f"最新快照: {latest_count} 条")
    log(f"输出目录: {JSONL_DIR}")
    log("=" * 60)

if __name__ == '__main__':
    main()
