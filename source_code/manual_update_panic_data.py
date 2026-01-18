#!/usr/bin/env python3
"""
手动更新恐慌清洗数据
用法：python3 manual_update_panic_data.py "10.77-绿|5-多头主升区间-99305-2.26-92.18-2025-12-03 17:00:00"
"""

import sys
import sqlite3
from datetime import datetime

def parse_and_save(data_line):
    """解析并保存数据"""
    try:
        parts = data_line.split('|')
        if len(parts) != 2:
            print(f"❌ 格式错误，应为: 指标|其他数据")
            return False
        
        panic_indicator = parts[0].strip()
        right = parts[1].strip().split('-')
        
        if len(right) < 7:
            print(f"❌ 右侧数据不完整，需要7个字段")
            return False
        
        # 解析字段
        data = {
            'panic_indicator': panic_indicator.split('-')[0],
            'panic_color': panic_indicator.split('-')[1] if '-' in panic_indicator else None,
            'trend_rating': int(right[0]),
            'market_zone': right[1],
            'liquidation_24h_people': int(right[2]),
            'liquidation_24h_amount': float(right[3]),
            'total_position': float(right[4]),
            'record_time': f"{right[5]} {right[6]}"
        }
        
        print(f"\n{'='*70}")
        print(f"📊 解析结果:")
        print(f"{'='*70}")
        for key, value in data.items():
            print(f"  {key}: {value}")
        print(f"{'='*70}")
        
        # 保存到文件
        with open('/home/user/webapp/panic_wash_latest.txt', 'w', encoding='utf-8') as f:
            f.write(data_line)
        print(f"\n✅ 已保存到 panic_wash_latest.txt")
        
        # 保存到数据库
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO panic_wash_history 
            (record_time, panic_indicator, panic_color, trend_rating, market_zone,
             liquidation_24h_people, liquidation_24h_amount, total_position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['record_time'], data['panic_indicator'], data['panic_color'], 
              data['trend_rating'], data['market_zone'], data['liquidation_24h_people'],
              data['liquidation_24h_amount'], data['total_position']))
        
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        
        if affected > 0:
            print(f"✅ 已保存到数据库")
        else:
            print(f"⚠️  数据已存在，未插入")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("="*70)
        print("📝 手动更新恐慌清洗数据")
        print("="*70)
        print("\n用法:")
        print('  python3 manual_update_panic_data.py "数据行"')
        print("\n格式示例:")
        print('  10.77-绿|5-多头主升区间-99305-2.26-92.18-2025-12-03 17:00:00')
        print("\n字段说明:")
        print('  恐慌指标-颜色|趋势评级-市场区间-24h爆仓人数-24h爆仓金额-全网持仓量-日期 时间')
        print("="*70)
        sys.exit(1)
    
    data_line = sys.argv[1]
    success = parse_and_save(data_line)
    
    if success:
        print(f"\n{'='*70}")
        print(f"✅ 数据更新成功！")
        print(f"{'='*70}")
    else:
        print(f"\n{'='*70}")
        print(f"❌ 数据更新失败")
        print(f"{'='*70}")
        sys.exit(1)
