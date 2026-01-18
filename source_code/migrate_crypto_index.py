#!/usr/bin/env python3
"""
Crypto Index 数据库迁移脚本
- 为 position_system 表添加 symbol 字段
- 确保 crypto_index_collector 可以正常运行
"""

import sqlite3
import os

DB_PATH = '/home/user/webapp/crypto_data.db'

def migrate():
    """执行数据库迁移"""
    print("=" * 80)
    print("Crypto Index 数据库迁移")
    print("=" * 80)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. 检查 position_system 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='position_system'")
        if not cursor.fetchone():
            print("⚠️  position_system 表不存在，跳过迁移")
            return True
        
        # 2. 检查 symbol 字段是否已存在
        cursor.execute("PRAGMA table_info(position_system)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'symbol' in columns:
            print("✅ symbol 字段已存在，无需迁移")
            return True
        
        # 3. 添加 symbol 字段
        print("\n📝 添加 symbol 字段...")
        cursor.execute("ALTER TABLE position_system ADD COLUMN symbol TEXT DEFAULT 'BTC-USDT-SWAP'")
        conn.commit()
        print("✅ 成功添加 symbol 字段")
        
        # 4. 验证
        cursor.execute("PRAGMA table_info(position_system)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("\n验证表结构:")
        for col in columns:
            print(f"  - {col}")
        
        if 'symbol' in columns:
            print("\n✅ 迁移成功！")
            return True
        else:
            print("\n❌ 迁移失败：symbol 字段未添加")
            return False
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
