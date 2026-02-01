#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将TAO锚点单同步到position_opens表 - 增强版
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/trading_decision.db'

def sync_tao_to_position_opens():
    """同步TAO锚点单到position_opens表"""
    
    # TAO锚点单信息（从图片中获取）
    inst_id = "TAO-USDT-SWAP"
    pos_side = "short"
    open_price = 627.3898  # 开仓价
    open_size = 1.0  # 仓位大小
    is_anchor = 1  # 标记为锚点单
    
    print(f"数据库路径: {DB_PATH}")
    print(f"开始同步 {inst_id}")
    
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 先检查表结构
    cursor.execute("PRAGMA table_info(position_opens)")
    columns = cursor.fetchall()
    print(f"\nposition_opens表结构:")
    for col in columns:
        print(f"  {col[1]} {col[2]}")
    
    # 检查是否已存在
    cursor.execute("""
        SELECT id, is_anchor FROM position_opens 
        WHERE inst_id = ? AND pos_side = ?
    """, (inst_id, pos_side))
    
    existing = cursor.fetchall()
    if existing:
        print(f"\n发现 {len(existing)} 条已有记录:")
        for row in existing:
            print(f"  ID:{row[0]}, is_anchor:{row[1]}")
        
        # 删除旧记录
        cursor.execute("""
            DELETE FROM position_opens
            WHERE inst_id = ? AND pos_side = ?
        """, (inst_id, pos_side))
        conn.commit()
        print(f"✅ 已删除 {cursor.rowcount} 条旧记录")
    
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    # 插入锚点单开仓记录
    try:
        cursor.execute("""
            INSERT INTO position_opens (
                inst_id, pos_side, open_price, open_size, open_percent,
                granularity, total_positions, is_anchor, 
                timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inst_id, 
            pos_side, 
            open_price, 
            open_size,
            100.0,  # open_percent
            0.0,    # granularity (锚点单不用颗粒度)
            0,      # total_positions
            is_anchor,
            timestamp,
            timestamp
        ))
        
        inserted_id = cursor.lastrowid
        conn.commit()
        print(f"\n✅ TAO锚点单已添加到 position_opens 表")
        print(f"   插入ID: {inserted_id}")
        print(f"   币种: {inst_id}")
        print(f"   方向: {pos_side}")
        print(f"   开仓价: {open_price}")
        print(f"   仓位: {open_size}")
        print(f"   is_anchor: {is_anchor}")
        print(f"   时间: {timestamp}")
        
        # 验证插入
        cursor.execute("""
            SELECT id, inst_id, pos_side, open_price, open_size, is_anchor, created_at
            FROM position_opens 
            WHERE id = ?
        """, (inserted_id,))
        
        result = cursor.fetchone()
        if result:
            print(f"\n✅ 验证成功 - 记录已存在:")
            print(f"   ID: {result[0]}")
            print(f"   币种: {result[1]}")
            print(f"   方向: {result[2]}")
            print(f"   开仓价: {result[3]}")
            print(f"   仓位: {result[4]}")
            print(f"   is_anchor: {result[5]}")
            print(f"   created_at: {result[6]}")
        else:
            print(f"\n❌ 验证失败 - 记录不存在！")
        
        # 再次检查所有锚点单
        cursor.execute("""
            SELECT COUNT(*) FROM position_opens WHERE is_anchor = 1
        """)
        anchor_count = cursor.fetchone()[0]
        print(f"\n当前锚点单总数: {anchor_count}")
        
        cursor.execute("""
            SELECT inst_id FROM position_opens WHERE is_anchor = 1 ORDER BY created_at DESC LIMIT 5
        """)
        print("最近5个锚点单:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}")
        
        conn.close()
        return True, inserted_id
        
    except Exception as e:
        print(f"\n❌ 插入失败: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        conn.close()
        return False, None

if __name__ == '__main__':
    try:
        success, insert_id = sync_tao_to_position_opens()
        if success:
            print(f"\n✅ TAO锚点单同步完成！(ID: {insert_id})")
            print("现在应该可以在交易管理页面看到了。")
        else:
            print("\n⚠️ 同步未完成")
    except Exception as e:
        print(f"\n❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
