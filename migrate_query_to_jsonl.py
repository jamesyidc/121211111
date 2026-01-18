#!/usr/bin/env python3
"""
从SQLite迁移Query数据到JSONL，并从最新TXT文件导入数据
"""
import sys
sys.path.append('/home/user/webapp/source_code')

import sqlite3
import json
import re
from query_jsonl_manager import QueryJSONLManager

DB_PATH = '/home/user/webapp/databases/crypto_data.db'

def migrate_db_to_jsonl():
    """将数据库数据迁移到JSONL"""
    print("=" * 80)
    print("🔄 Query数据迁移: SQLite → JSONL")
    print("=" * 80)
    
    try:
        manager = QueryJSONLManager()
        
        # 1. 迁移快照数据
        print("\n1️⃣ 迁移快照数据...")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot_date, snapshot_time, rush_up, rush_down, diff, count, 
                   status, price_lowest, price_newhigh, count_score_display, 
                   count_score_type, rise_24h_count, fall_24h_count, created_at
            FROM crypto_snapshots
            WHERE snapshot_time IS NOT NULL
            ORDER BY snapshot_time DESC
        """)
        
        snapshots = []
        for row in cursor.fetchall():
            snapshot = {
                'snapshot_date': row[0],
                'snapshot_time': row[1],
                'rush_up': int(row[2]) if row[2] is not None else 0,
                'rush_down': int(row[3]) if row[3] is not None else 0,
                'diff': int(row[4]) if row[4] is not None else 0,
                'count': int(row[5]) if row[5] is not None else 0,
                'status': row[6] if row[6] else '',
                'price_lowest': int(row[7]) if row[7] is not None else 0,
                'price_newhigh': int(row[8]) if row[8] is not None else 0,
                'count_score_display': row[9] if row[9] else '',
                'count_score_type': row[10] if row[10] else '',
                'rise_24h_count': int(row[11]) if row[11] is not None else 0,
                'fall_24h_count': int(row[12]) if row[12] is not None else 0,
                'created_at': row[13] if row[13] else None
            }
            snapshots.append(snapshot)
        
        print(f"   找到 {len(snapshots)} 条快照记录")
        
        if snapshots:
            manager.write_snapshots(snapshots, backup=False)
        
        # 2. 迁移币种数据
        print("\n2️⃣ 迁移币种数据...")
        cursor.execute("""
            SELECT snapshot_time, symbol, change, rush_up, rush_down, update_time,
                   high_price, high_time, decline, change_24h, rank, current_price,
                   priority_level, ratio1, ratio2, index_order
            FROM crypto_coin_data
            WHERE snapshot_time IS NOT NULL
            ORDER BY snapshot_time DESC, index_order ASC
        """)
        
        coins = []
        for row in cursor.fetchall():
            ratio1 = float(row[13]) if row[13] is not None else 0
            ratio2 = float(row[14]) if row[14] is not None else 0
            
            # 重新计算优先级
            priority = manager.calculate_priority(ratio1, ratio2)
            
            coin = {
                'snapshot_time': row[0],
                'symbol': row[1],
                'change': row[2] if row[2] else '',
                'rush_up': int(row[3]) if row[3] is not None else 0,
                'rush_down': int(row[4]) if row[4] is not None else 0,
                'update_time': row[5] if row[5] else '',
                'high_price': float(row[6]) if row[6] is not None else 0,
                'high_time': row[7] if row[7] else '',
                'decline': float(row[8]) if row[8] is not None else 0,
                'change_24h': float(row[9]) if row[9] is not None else 0,
                'rank': row[10] if row[10] else '',
                'current_price': float(row[11]) if row[11] is not None else 0,
                'priority': priority,  # 使用重新计算的优先级
                'ratio1': ratio1,  # 最高占比
                'ratio2': ratio2,  # 最低占比
                'index_order': int(row[15]) if row[15] is not None else 999
            }
            coins.append(coin)
        
        print(f"   找到 {len(coins)} 条币种记录")
        
        if coins:
            manager.write_coins(coins, backup=False)
        
        conn.close()
        
        # 3. 验证迁移结果
        print("\n3️⃣ 验证迁移结果...")
        stats = manager.get_statistics()
        print(f"   快照记录数: {stats['total_snapshots']}")
        print(f"   币种记录数: {stats['total_coins']}")
        print(f"   唯一时间点: {stats['unique_times']}")
        print(f"   最新时间: {stats['latest_time']}")
        
        print("\n" + "=" * 80)
        print("✅ 迁移完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


def parse_txt_to_jsonl(txt_content: str, snapshot_time: str):
    """解析TXT内容并导入到JSONL
    
    TXT格式说明：
    - 透明标签_急涨总和=急涨：14
    - 透明标签_急跌总和=急跌：18
    - 透明标签_五种状态=状态：震荡无序
    - 透明标签_差值结果=差值：-4
    - 透明标签_计次=3
    - 透明标签_比价最低得分=比价最低 0 0
    - 透明标签_仓位得分=比价创新高 仓位加10% 1
    
    币种数据格式：
    序号|币名|急涨|急跌|更新时间|历史高位|高位时间|距离高位跌幅|24涨幅|排行|当前价格|最高占比|最低占比
    """
    print("\n" + "=" * 80)
    print("📄 解析TXT文件并导入JSONL")
    print("=" * 80)
    
    try:
        manager = QueryJSONLManager()
        lines = txt_content.strip().split('\n')
        
        # 1. 解析快照数据
        print("\n1️⃣ 解析快照数据...")
        rush_up = 0
        rush_down = 0
        status = ''
        diff = 0
        count = 0
        price_lowest = 0
        price_newhigh = 0
        
        for line in lines:
            line = line.strip()
            
            # 急涨
            match = re.search(r'急涨[:：]\s*(\d+)', line)
            if match:
                rush_up = int(match.group(1))
                print(f"   急涨: {rush_up}")
            
            # 急跌
            match = re.search(r'急跌[:：]\s*(\d+)', line)
            if match:
                rush_down = int(match.group(1))
                print(f"   急跌: {rush_down}")
            
            # 状态
            match = re.search(r'状态[:：]\s*([^\s]+)', line)
            if match:
                status = match.group(1)
                print(f"   状态: {status}")
            
            # 差值
            match = re.search(r'差值[:：]\s*(-?\d+)', line)
            if match:
                diff = int(match.group(1))
                print(f"   差值: {diff}")
            
            # 计次
            match = re.search(r'透明标签_计次\s*[=:：]\s*(\d+)', line)
            if match:
                count = int(match.group(1))
                print(f"   计次: {count}")
            
            # 比价最低
            if '比价最低' in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        price_lowest = int(parts[-2])
                        print(f"   比价最低: {price_lowest}")
                    except:
                        pass
            
            # 比价创新高
            if '比价创新高' in line:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        price_newhigh = int(parts[-1])
                        print(f"   比价创新高: {price_newhigh}")
                    except:
                        pass
        
        # 提取日期
        snapshot_date = snapshot_time.split()[0] if ' ' in snapshot_time else snapshot_time
        
        snapshot = {
            'snapshot_date': snapshot_date,
            'snapshot_time': snapshot_time,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': count,
            'status': status,
            'price_lowest': price_lowest,
            'price_newhigh': price_newhigh,
            'count_score_display': '',
            'count_score_type': '',
            'rise_24h_count': 0,
            'fall_24h_count': 0,
            'created_at': None
        }
        
        # 2. 解析币种数据
        print("\n2️⃣ 解析币种数据...")
        coins = []
        
        # 查找币种数据开始位置
        start_index = -1
        for i, line in enumerate(lines):
            if '|币名|' in line or '序号|币名|' in line or '[超级列表框_首页开始]' in line:
                start_index = i + 1
                break
        
        if start_index == -1:
            print("⚠️  未找到币种数据标记")
            # 尝试查找第一个包含多个|的行
            for i, line in enumerate(lines):
                if line.count('|') >= 10:  # 至少10个分隔符
                    start_index = i
                    print(f"   使用备用方法，从第{i+1}行开始")
                    break
        else:
            for i in range(start_index, len(lines)):
                line = lines[i].strip()
                if not line or '透明标签' in line or '[' in line:
                    continue
                
                # 分割数据: 序号|币名|急涨|急跌|更新时间|历史高位|高位时间|距离高位跌幅|24涨幅|排行|当前价格|最高占比|最低占比
                parts = line.split('|')
                if len(parts) < 13:
                    continue
                
                try:
                    symbol = parts[1].strip()
                    if not symbol:
                        continue
                    
                    # 解析数据
                    coin_rush_up = int(parts[2]) if parts[2].strip() else 0
                    coin_rush_down = int(parts[3]) if parts[3].strip() else 0
                    update_time = parts[4].strip()
                    high_price = float(parts[5].replace(',', '')) if parts[5].strip() else 0
                    high_time = parts[6].strip()
                    decline = float(parts[7].replace('%', '').replace('+', '')) if parts[7].strip() else 0
                    change_24h = float(parts[8].replace('%', '').replace('+', '')) if parts[8].strip() else 0
                    rank = parts[9].strip()
                    current_price = float(parts[10].replace(',', '')) if parts[10].strip() else 0
                    ratio1 = float(parts[11].replace('%', '')) if parts[11].strip() else 0  # 最高占比
                    ratio2 = float(parts[12].replace('%', '')) if parts[12].strip() else 0  # 最低占比
                    
                    # 计算优先级
                    priority = manager.calculate_priority(ratio1, ratio2)
                    
                    coin = {
                        'snapshot_time': snapshot_time,
                        'symbol': symbol,
                        'change': '',
                        'rush_up': coin_rush_up,
                        'rush_down': coin_rush_down,
                        'update_time': update_time,
                        'high_price': high_price,
                        'high_time': high_time,
                        'decline': decline,
                        'change_24h': change_24h,
                        'rank': rank,
                        'current_price': current_price,
                        'priority': priority,
                        'ratio1': ratio1,
                        'ratio2': ratio2,
                        'index_order': len(coins) + 1
                    }
                    
                    coins.append(coin)
                    
                except Exception as e:
                    print(f"  ⚠️  解析行失败: {line[:50]}... - {e}")
                    continue
        
        print(f"   解析到 {len(coins)} 个币种")
        
        # 按优先级排序
        coins.sort(key=lambda x: x['priority'])
        
        # 重新设置index_order
        for i, coin in enumerate(coins):
            coin['index_order'] = i + 1
        
        # 3. 保存到JSONL
        print("\n3️⃣ 保存到JSONL...")
        manager.upsert_snapshot(snapshot)
        manager.upsert_coins(coins, snapshot_time)
        
        print("\n" + "=" * 80)
        print(f"✅ 导入完成！快照时间: {snapshot_time}")
        print(f"   快照数据: 急涨{rush_up} 急跌{rush_down} 状态{status}")
        print(f"   币种数量: {len(coins)}")
        print(f"   优先级分布:")
        for i in range(1, 7):
            count_p = sum(1 for c in coins if c['priority'] == i)
            if count_p > 0:
                print(f"     等级{i}: {count_p}个")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # 如果提供了TXT文件路径，解析该文件
        txt_file = sys.argv[1]
        snapshot_time = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(txt_file, 'r', encoding='utf-8') as f:
            txt_content = f.read()
        
        parse_txt_to_jsonl(txt_content, snapshot_time)
    else:
        # 默认执行数据库迁移
        migrate_db_to_jsonl()
