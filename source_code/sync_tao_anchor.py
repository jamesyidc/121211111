#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动同步TAO锚点单到anchor_monitors表
"""

import sqlite3
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def sync_tao_anchor():
    """同步TAO锚点单"""
    
    # 从图片中看到的TAO信息
    # TAO-USDT-SWAP, 开仓价 627.3898, 当前价 620.5
    
    inst_id = "TAO-USDT-SWAP"
    pos_side = "short"  # 根据图片，应该是做空
    pos_size = 1.0  # 假设仓位为1
    avg_price = 627.3898  # 开仓价
    mark_price = 620.5  # 当前价格
    
    # 计算收益率（空单）
    profit_rate = ((avg_price - mark_price) / avg_price) * 100
    
    # 连接anchor_system.db
    conn = sqlite3.connect('/home/user/webapp/anchor_system.db')
    cursor = conn.cursor()
    
    # 检查是否已存在
    cursor.execute("""
        SELECT id FROM anchor_monitors 
        WHERE inst_id = ? AND pos_side = ?
    """, (inst_id, pos_side))
    
    existing = cursor.fetchone()
    
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    if existing:
        # 更新
        cursor.execute("""
            UPDATE anchor_monitors
            SET pos_size = ?, avg_price = ?, mark_price = ?, 
                profit_rate = ?, timestamp = ?, created_at = ?
            WHERE inst_id = ? AND pos_side = ?
        """, (pos_size, avg_price, mark_price, profit_rate, 
              timestamp, timestamp, inst_id, pos_side))
        print(f"✅ 更新TAO锚点单: {inst_id} {pos_side}")
    else:
        # 插入
        cursor.execute("""
            INSERT INTO anchor_monitors (
                inst_id, pos_side, pos_size, avg_price, mark_price,
                upl, upl_ratio, margin, leverage, profit_rate,
                alert_type, alert_sent, timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inst_id, pos_side, pos_size, avg_price, mark_price,
            0.0,  # upl
            profit_rate,  # upl_ratio
            pos_size * avg_price,  # margin
            1.0,  # leverage
            profit_rate,  # profit_rate
            '',  # alert_type
            0,  # alert_sent
            timestamp,
            timestamp
        ))
        print(f"✅ 创建TAO锚点单: {inst_id} {pos_side}")
        print(f"   开仓价: {avg_price}")
        print(f"   当前价: {mark_price}")
        print(f"   收益率: {profit_rate:.2f}%")
    
    conn.commit()
    
    # 验证
    cursor.execute("""
        SELECT inst_id, pos_side, pos_size, avg_price, mark_price, profit_rate
        FROM anchor_monitors 
        WHERE inst_id = ?
    """, (inst_id,))
    
    result = cursor.fetchone()
    if result:
        print(f"\n✅ TAO锚点单已同步:")
        print(f"   币种: {result[0]}")
        print(f"   方向: {result[1]}")
        print(f"   仓位: {result[2]}")
        print(f"   开仓价: {result[3]}")
        print(f"   当前价: {result[4]}")
        print(f"   收益率: {result[5]:.2f}%")
    
    conn.close()
    return True

if __name__ == '__main__':
    try:
        sync_tao_anchor()
        print("\n✅ TAO锚点单同步完成！")
    except Exception as e:
        print(f"\n❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
