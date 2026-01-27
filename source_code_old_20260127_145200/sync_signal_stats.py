#!/usr/bin/env python3
"""
同步做多做空信号统计数据
从外部API获取数据并保存到本地数据库
"""
import requests
import sqlite3
from datetime import datetime, timezone, timedelta
import time

# 北京时间时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 外部信号API地址
EXTERNAL_API = "https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/api/filtered-signals/stats"

def fetch_signal_stats():
    """从外部API获取信号统计"""
    try:
        params = {
            'limit': 200,
            'rsi_short_threshold': 65,
            'rsi_long_threshold': 30
        }
        
        response = requests.get(EXTERNAL_API, params=params, timeout=10)
        data = response.json()
        
        if data.get('success'):
            return data
        else:
            print(f"❌ API返回失败: {data}")
            return None
            
    except Exception as e:
        print(f"❌ 获取数据失败: {e}")
        return None

def save_to_database(data):
    """保存数据到本地数据库"""
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 提取数据
        summary = data.get('summary', {})
        breakdown = data.get('breakdown', {})
        
        # 生成记录时间（北京时间，精确到分钟）
        beijing_now = datetime.now(BEIJING_TZ)
        record_time = beijing_now.strftime('%Y-%m-%d %H:%M:00')
        
        # 提取做多做空统计
        total_count = summary.get('total', 0)
        long_count = summary.get('long', 0)
        short_count = summary.get('short', 0)
        
        # 提取细分统计（抄底、底部、顶部）
        chaodi_count = breakdown.get('抄底做多', 0)
        dibu_count = breakdown.get('底部做多', 0)
        dingbu_count = breakdown.get('顶部做空', 0)
        
        # 检查是否已存在
        cursor.execute(
            'SELECT id FROM signal_stats_history WHERE record_time = ?',
            (record_time,)
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"⏭️  记录已存在: {record_time}")
            conn.close()
            return False
        
        # 插入数据
        cursor.execute('''
            INSERT INTO signal_stats_history 
            (record_time, total_count, long_count, short_count,
             chaodi_count, dibu_count, dingbu_count, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_time,
            total_count,
            long_count,
            short_count,
            chaodi_count,
            dibu_count,
            dingbu_count,
            EXTERNAL_API
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 保存成功: {record_time}")
        print(f"   总计: {total_count}, 做多: {long_count}, 做空: {short_count}")
        print(f"   抄底: {chaodi_count}, 底部: {dibu_count}, 顶部: {dingbu_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 70)
    print("同步做多做空信号统计数据")
    print("=" * 70)
    
    # 获取数据
    print("\n1. 从外部API获取数据...")
    data = fetch_signal_stats()
    
    if not data:
        print("❌ 获取数据失败，退出")
        return
    
    print(f"✅ 获取成功")
    
    # 保存数据
    print("\n2. 保存到本地数据库...")
    success = save_to_database(data)
    
    if success:
        # 显示数据库统计
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM signal_stats_history')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM signal_stats_history')
        time_range = cursor.fetchone()
        
        conn.close()
        
        print(f"\n📊 数据库统计:")
        print(f"   总记录数: {total}")
        print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")
    
    print("=" * 70)

if __name__ == '__main__':
    main()
