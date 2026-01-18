#!/usr/bin/env python3
"""
SAR斜率系统 V2.0
功能：
1. 记录每个币种的5分钟SAR数据（近7天）
2. 判断多空状态和持续时间
3. 计算SAR变化率和平均值
4. 异常预警（偏离平均值30%以上）
5. 标记最高点和最低点
"""
import sqlite3
import requests
import time
from datetime import datetime, timedelta
import pytz

# 配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/sar_slope_data.db'

# 27个币种列表
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
]

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # SAR数据表 - 每个币种单独存储
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sar_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            kline_time TEXT NOT NULL,
            open_price REAL NOT NULL,
            high_price REAL NOT NULL,
            low_price REAL NOT NULL,
            close_price REAL NOT NULL,
            sar_value REAL NOT NULL,
            position TEXT NOT NULL,
            position_sequence INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        )
    ''')
    
    # SAR变化率统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sar_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            position TEXT NOT NULL,
            sequence_start INTEGER NOT NULL,
            sequence_end INTEGER NOT NULL,
            start_sar REAL NOT NULL,
            end_sar REAL NOT NULL,
            change_value REAL NOT NULL,
            change_percent REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # SAR平均值统计表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sar_averages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            position TEXT NOT NULL,
            avg_type TEXT NOT NULL,
            avg_value REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, position, avg_type)
        )
    ''')
    
    # SAR异常预警表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sar_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            position TEXT NOT NULL,
            sequence_num INTEGER NOT NULL,
            sar_value REAL NOT NULL,
            change_percent REAL NOT NULL,
            avg_value REAL NOT NULL,
            deviation_percent REAL NOT NULL,
            alert_type TEXT NOT NULL,
            kline_time TEXT NOT NULL,
            is_extreme_point INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sar_data_symbol_time ON sar_data(symbol, timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sar_changes_symbol ON sar_changes(symbol, position)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sar_alerts_symbol ON sar_alerts(symbol, created_at DESC)')
    
    conn.commit()
    conn.close()
    print("✓ 数据库初始化完成")

def fetch_kline_data(symbol, limit=600):
    """
    获取K线数据
    limit=600 表示 600根5分钟K线 = 50小时数据（大于48小时要求）
    """
    url = f"https://www.okx.com/api/v5/market/candles"
    params = {
        'instId': f'{symbol}-USDT-SWAP',
        'bar': '5m',
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            klines = data['data']
            klines.reverse()  # 从旧到新排序
            return klines
        return None
    except Exception as e:
        print(f"✗ 获取{symbol} K线数据失败: {e}")
        return None

def calculate_sar(klines, acceleration=0.02, maximum=0.2):
    """
    计算SAR指标
    返回: [(timestamp, open, high, low, close, sar, position), ...]
    """
    if not klines or len(klines) < 2:
        return []
    
    results = []
    
    # 初始化
    sar = float(klines[0][3])  # 初始SAR = 第一根K线的low
    ep = float(klines[0][2])   # 极值点 = 第一根K线的high
    af = acceleration          # 加速因子
    is_long = True            # 假设初始为多头
    
    for i, kline in enumerate(klines):
        timestamp = int(kline[0])
        open_price = float(kline[1])
        high = float(kline[2])
        low = float(kline[3])
        close = float(kline[4])
        
        # 判断position：SAR < 开盘价 = 多头，SAR > 开盘价 = 空头
        if i == 0:
            position = 'long' if sar < open_price else 'short'
        else:
            position = 'long' if sar < open_price else 'short'
        
        # 记录结果
        kline_time = datetime.fromtimestamp(timestamp/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        results.append((timestamp, open_price, high, low, close, sar, position, kline_time))
        
        # 计算下一个SAR
        if i < len(klines) - 1:
            # 更新SAR
            sar = sar + af * (ep - sar)
            
            # 检查是否转势
            next_high = float(klines[i+1][2])
            next_low = float(klines[i+1][3])
            
            if is_long:
                if next_low < sar:  # 多转空
                    is_long = False
                    sar = ep
                    ep = next_low
                    af = acceleration
                else:
                    if next_high > ep:
                        ep = next_high
                        af = min(af + acceleration, maximum)
            else:
                if next_high > sar:  # 空转多
                    is_long = True
                    sar = ep
                    ep = next_high
                    af = acceleration
                else:
                    if next_low < ep:
                        ep = next_low
                        af = min(af + acceleration, maximum)
    
    return results

def assign_position_sequence(sar_results):
    """
    分配position_sequence（多01, 多02... 空01, 空02...）
    """
    if not sar_results:
        return []
    
    results_with_seq = []
    current_position = sar_results[0][6]
    sequence = 1
    
    for item in sar_results:
        timestamp, open_p, high, low, close, sar, position, kline_time = item
        
        # 检查是否转势
        if position != current_position:
            current_position = position
            sequence = 1
        
        results_with_seq.append((timestamp, open_p, high, low, close, sar, position, sequence, kline_time))
        sequence += 1
    
    return results_with_seq

def save_sar_data(symbol, sar_data_with_seq):
    """保存SAR数据到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved_count = 0
    for item in sar_data_with_seq:
        timestamp, open_p, high, low, close, sar, position, seq, kline_time = item
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO sar_data 
                (symbol, timestamp, kline_time, open_price, high_price, low_price, 
                 close_price, sar_value, position, position_sequence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, timestamp, kline_time, open_p, high, low, close, sar, position, seq))
            saved_count += 1
        except Exception as e:
            print(f"✗ 保存{symbol}数据失败: {e}")
    
    conn.commit()
    conn.close()
    return saved_count

def calculate_changes_and_averages(symbol):
    """
    计算SAR变化率和平均值
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 获取最新的一段连续position数据
    cursor.execute('''
        SELECT timestamp, sar_value, position, position_sequence, kline_time
        FROM sar_data
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 200
    ''', (symbol,))
    
    rows = cursor.fetchall()
    if len(rows) < 2:
        conn.close()
        return
    
    rows.reverse()  # 从旧到新
    
    # 按position分组
    for position_type in ['long', 'short']:
        position_data = [(r[1], r[3], r[4]) for r in rows if r[2] == position_type]
        
        if len(position_data) < 2:
            continue
        
        # 计算每一步的变化
        changes = []
        for i in range(len(position_data) - 1):
            start_sar = position_data[i][0]
            end_sar = position_data[i+1][0]
            start_seq = position_data[i][1]
            end_seq = position_data[i+1][1]
            
            change_value = abs(end_sar - start_sar)
            change_percent = (change_value / start_sar * 100) if start_sar != 0 else 0
            
            changes.append({
                'start_seq': start_seq,
                'end_seq': end_seq,
                'start_sar': start_sar,
                'end_sar': end_sar,
                'change_value': change_value,
                'change_percent': change_percent
            })
            
            # 保存变化率
            cursor.execute('''
                INSERT INTO sar_changes 
                (symbol, position, sequence_start, sequence_end, start_sar, end_sar, 
                 change_value, change_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, position_type, start_seq, end_seq, start_sar, end_sar, 
                  change_value, change_percent))
        
        # 计算平均值（当天、3天、7天、15天）
        if changes:
            # 当天平均值（最近12个变化 = 1小时）
            recent_12 = changes[-12:] if len(changes) >= 12 else changes
            avg_1day = sum(c['change_percent'] for c in recent_12) / len(recent_12)
            
            # 3天平均值（最近36个变化）
            recent_36 = changes[-36:] if len(changes) >= 36 else changes
            avg_3day = sum(c['change_percent'] for c in recent_36) / len(recent_36)
            
            # 7天平均值（最近84个变化）
            recent_84 = changes[-84:] if len(changes) >= 84 else changes
            avg_7day = sum(c['change_percent'] for c in recent_84) / len(recent_84)
            
            # 15天平均值（所有数据）
            avg_15day = sum(c['change_percent'] for c in changes) / len(changes)
            
            # 保存平均值
            for avg_type, avg_val, sample in [
                ('1day', avg_1day, len(recent_12)),
                ('3day', avg_3day, len(recent_36)),
                ('7day', avg_7day, len(recent_84)),
                ('15day', avg_15day, len(changes))
            ]:
                cursor.execute('''
                    INSERT OR REPLACE INTO sar_averages
                    (symbol, position, avg_type, avg_value, sample_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (symbol, position_type, avg_type, avg_val, sample))
            
            # 检查异常（偏离平均值30%以上）
            check_anomalies(cursor, symbol, position_type, changes, avg_3day, position_data)
    
    conn.commit()
    conn.close()

def check_anomalies(cursor, symbol, position_type, changes, avg_value, position_data):
    """
    检查异常并标记极值点
    偏离3天平均值30%以上为异常
    """
    if not changes or avg_value == 0:
        return
    
    for change in changes[-20:]:  # 只检查最近20个变化
        deviation = abs(change['change_percent'] - avg_value) / avg_value * 100
        
        if deviation >= 30:  # 偏离30%以上
            alert_type = 'high' if change['change_percent'] > avg_value else 'low'
            
            # 判断是否为极值点
            is_extreme = 0
            if alert_type == 'high' and change['change_percent'] == max(c['change_percent'] for c in changes[-20:]):
                is_extreme = 1  # 最高点
            elif alert_type == 'low' and change['change_percent'] == min(c['change_percent'] for c in changes[-20:]):
                is_extreme = 1  # 最低点
            
            # 获取对应的kline_time
            kline_time = next((pd[2] for pd in position_data if pd[1] == change['end_seq']), '')
            
            cursor.execute('''
                INSERT INTO sar_alerts
                (symbol, position, sequence_num, sar_value, change_percent, 
                 avg_value, deviation_percent, alert_type, kline_time, is_extreme_point)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, position_type, change['end_seq'], change['end_sar'], 
                  change['change_percent'], avg_value, deviation, alert_type, kline_time, is_extreme))

def cleanup_old_data():
    """清理7天前的数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    seven_days_ago = int((datetime.now(BEIJING_TZ) - timedelta(days=7)).timestamp() * 1000)
    
    cursor.execute('DELETE FROM sar_data WHERE timestamp < ?', (seven_days_ago,))
    deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    if deleted > 0:
        print(f"✓ 清理了 {deleted} 条7天前的数据")

def collect_all_symbols():
    """采集所有币种的SAR数据"""
    print("\n" + "="*80)
    print("SAR斜率系统 V2.0 - 数据采集")
    print("="*80)
    
    init_database()
    
    success_count = 0
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n[{i}/{len(SYMBOLS)}] 处理 {symbol}...")
        
        # 获取K线数据
        klines = fetch_kline_data(symbol, limit=600)
        if not klines:
            continue
        
        # 计算SAR
        sar_results = calculate_sar(klines)
        if not sar_results:
            continue
        
        # 分配序列号
        sar_with_seq = assign_position_sequence(sar_results)
        
        # 保存数据
        saved = save_sar_data(symbol, sar_with_seq)
        print(f"  ✓ 保存了 {saved} 条数据")
        
        # 计算变化率和平均值
        calculate_changes_and_averages(symbol)
        print(f"  ✓ 完成变化率分析")
        
        success_count += 1
        time.sleep(0.5)  # 避免请求过快
    
    # 清理旧数据
    cleanup_old_data()
    
    print("\n" + "="*80)
    print(f"✅ 采集完成！成功处理 {success_count}/{len(SYMBOLS)} 个币种")
    print("="*80)

if __name__ == '__main__':
    collect_all_symbols()
