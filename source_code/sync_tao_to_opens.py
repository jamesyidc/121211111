#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将TAO锚点单同步到position_opens表
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def sync_tao_to_position_opens():
    """同步TAO锚点单到position_opens表"""
    
    # TAO锚点单信息（从图片中获取）
    inst_id = "TAO-USDT-SWAP"
    pos_side = "short"
    open_price = 627.3898  # 开仓价
    open_size = 1.0  # 仓位大小（假设为1）
    is_anchor = 1  # 标记为锚点单
    
    conn = sqlite3.connect('/home/user/webapp/trading_decision.db')
    cursor = conn.cursor()
    
    # 检查是否已存在
    cursor.execute("""
        SELECT id FROM position_opens 
        WHERE inst_id = ? AND pos_side = ? AND is_anchor = 1
    """, (inst_id, pos_side))
    
    existing = cursor.fetchone()
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    if existing:
        print(f"❌ TAO锚点单已存在于 position_opens 表")
        return False
    
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
        
        conn.commit()
        print(f"✅ TAO锚点单已添加到 position_opens 表")
        print(f"   币种: {inst_id}")
        print(f"   方向: {pos_side}")
        print(f"   开仓价: {open_price}")
        print(f"   仓位: {open_size}")
        print(f"   时间: {timestamp}")
        
        # 验证
        cursor.execute("""
            SELECT id, inst_id, pos_side, open_price, open_size, is_anchor
            FROM position_opens 
            WHERE inst_id = ? AND is_anchor = 1
        """, (inst_id,))
        
        result = cursor.fetchone()
        if result:
            print(f"\n✅ 验证成功:")
            print(f"   ID: {result[0]}")
            print(f"   币种: {result[1]}")
            print(f"   方向: {result[2]}")
            print(f"   开仓价: {result[3]}")
            print(f"   仓位: {result[4]}")
            print(f"   锚点: {result[5]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 插入失败: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == '__main__':
    try:
        if sync_tao_to_position_opens():
            print("\n✅ TAO锚点单同步完成！现在应该可以在交易管理页面看到了。")
        else:
            print("\n⚠️ 同步未完成")
    except Exception as e:
        print(f"\n❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
