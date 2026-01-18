#!/usr/bin/env python3
"""
更新锚定系统极值记录
根据用户提供的最新极值数据更新数据库
"""
import sqlite3
from datetime import datetime
from pytz import timezone

BEIJING_TZ = timezone('Asia/Shanghai')

# 最新极值数据（从用户提供的数据整理）
EXTREME_DATA = {
    'CFX': {
        'long': {'max_profit': 182.59, 'max_loss': -21.18},
        'short': {'max_profit': 99.73, 'max_loss': -44.53}
    },
    'FIL': {
        'long': {'max_profit': 241.57, 'max_loss': -23.66},
        'short': {'max_profit': 117.87, 'max_loss': -18.45}
    },
    'CRO': {
        'long': {'max_profit': 202.57, 'max_loss': -10.06},
        'short': {'max_profit': 103.63, 'max_loss': -28.44}
    },
    'UNI': {
        'long': {'max_profit': 83.42, 'max_loss': -14.39},
        'short': {'max_profit': 112.15, 'max_loss': -32.27}
    },
    'CRV': {
        'long': {'max_profit': 173.59, 'max_loss': -12.05},
        'short': {'max_profit': 92.06, 'max_loss': -64.12}
    },
    'LDO': {
        'long': {'max_profit': 177.0, 'max_loss': -18.41},
        'short': {'max_profit': 95.38, 'max_loss': -25.72}
    },
    'STX': {
        'long': {'max_profit': 658.28, 'max_loss': -24.29},
        'short': {'max_profit': 98.89, 'max_loss': -60.23}
    },
    'BCH': {
        'long': {'max_profit': 15.12, 'max_loss': -8.67},
        'short': {'max_profit': 59.28, 'max_loss': -35.66}
    },
    'SOL': {
        'long': {'max_profit': 53.59, 'max_loss': None},
        'short': {'max_profit': 44.36, 'max_loss': None}
    },
    'XLM': {
        'long': {'max_profit': 231.42, 'max_loss': -11.52},
        'short': {'max_profit': 126.7, 'max_loss': -28.79}
    },
    'TAO': {
        'long': {'max_profit': 44.7, 'max_loss': None},
        'short': {'max_profit': 87.04, 'max_loss': -15.35}
    },
    'APT': {
        'long': {'max_profit': 132.7, 'max_loss': -24.49},
        'short': {'max_profit': 115.12, 'max_loss': -41.29}
    },
    'TON': {
        'long': {'max_profit': 27.07, 'max_loss': -20.64},
        'short': {'max_profit': 108.0, 'max_loss': -85.45}
    },
    'HBAR': {
        'long': {'max_profit': 75.24, 'max_loss': None},
        'short': {'max_profit': 137.35, 'max_loss': -23.23}
    },
    'XRP': {
        'long': {'max_profit': 56.3, 'max_loss': -2.0},
        'short': {'max_profit': 135.15, 'max_loss': None}
    },
    'NEAR': {
        'long': {'max_profit': 120.0, 'max_loss': -15.6},
        'short': {'max_profit': 76.48, 'max_loss': None}
    },
    'TRX': {
        'long': {'max_profit': 18.87, 'max_loss': None},
        'short': {'max_profit': 16.69, 'max_loss': -5.58}
    },
    'DOT': {
        'long': {'max_profit': 303.0, 'max_loss': -18.62},
        'short': {'max_profit': 74.79, 'max_loss': -70.48}
    },
    'BNB': {
        'long': {'max_profit': None, 'max_loss': None},
        'short': {'max_profit': 27.74, 'max_loss': -16.61}
    },
    'LINK': {
        'long': {'max_profit': 71.0, 'max_loss': -0.45},
        'short': {'max_profit': 73.76, 'max_loss': -19.23}
    },
    'DOGE': {
        'long': {'max_profit': 67.0, 'max_loss': None},
        'short': {'max_profit': 114.0, 'max_loss': None}
    },
    'SUI': {
        'long': {'max_profit': 68.0, 'max_loss': -14.42},
        'short': {'max_profit': 2.94, 'max_loss': -9.57}
    },
    'AAVE': {
        'long': {'max_profit': 234.61, 'max_loss': -12.73},
        'short': {'max_profit': 62.28, 'max_loss': None}
    }
}

def update_extreme_records():
    """更新极值记录"""
    db_path = 'databases/anchor_system.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    updated_count = 0
    inserted_count = 0
    
    print("="*60)
    print("开始更新极值记录")
    print("="*60)
    
    for symbol, directions in EXTREME_DATA.items():
        inst_id = f"{symbol}-USDT-SWAP"
        
        for direction, extremes in directions.items():
            pos_side = 'long' if direction == 'long' else 'short'
            
            # 处理最大盈利
            if extremes['max_profit'] is not None:
                profit_rate = extremes['max_profit']
                
                # 检查是否存在记录
                cursor.execute('''
                    SELECT id, profit_rate FROM anchor_real_profit_records
                    WHERE inst_id = ? AND pos_side = ? AND record_type = 'max_profit'
                ''', (inst_id, pos_side))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有记录
                    cursor.execute('''
                        UPDATE anchor_real_profit_records
                        SET profit_rate = ?, timestamp = ?, updated_at = ?
                        WHERE id = ?
                    ''', (profit_rate, now, now, existing[0]))
                    updated_count += 1
                    print(f"✅ 更新 {inst_id} {pos_side} max_profit: {profit_rate}%")
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO anchor_real_profit_records
                        (inst_id, pos_side, record_type, profit_rate, timestamp, created_at, updated_at)
                        VALUES (?, ?, 'max_profit', ?, ?, ?, ?)
                    ''', (inst_id, pos_side, profit_rate, now, now, now))
                    inserted_count += 1
                    print(f"➕ 新增 {inst_id} {pos_side} max_profit: {profit_rate}%")
            
            # 处理最大亏损
            if extremes['max_loss'] is not None:
                loss_rate = extremes['max_loss']
                
                # 检查是否存在记录
                cursor.execute('''
                    SELECT id, profit_rate FROM anchor_real_profit_records
                    WHERE inst_id = ? AND pos_side = ? AND record_type = 'max_loss'
                ''', (inst_id, pos_side))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有记录
                    cursor.execute('''
                        UPDATE anchor_real_profit_records
                        SET profit_rate = ?, timestamp = ?, updated_at = ?
                        WHERE id = ?
                    ''', (loss_rate, now, now, existing[0]))
                    updated_count += 1
                    print(f"✅ 更新 {inst_id} {pos_side} max_loss: {loss_rate}%")
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO anchor_real_profit_records
                        (inst_id, pos_side, record_type, profit_rate, timestamp, created_at, updated_at)
                        VALUES (?, ?, 'max_loss', ?, ?, ?, ?)
                    ''', (inst_id, pos_side, loss_rate, now, now, now))
                    inserted_count += 1
                    print(f"➕ 新增 {inst_id} {pos_side} max_loss: {loss_rate}%")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*60)
    print("更新完成")
    print("="*60)
    print(f"更新记录数: {updated_count}")
    print(f"新增记录数: {inserted_count}")
    print(f"总处理数: {updated_count + inserted_count}")
    print("="*60)

if __name__ == '__main__':
    update_extreme_records()
