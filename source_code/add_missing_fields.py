#!/usr/bin/env python3
"""
为 stats_history 表添加缺失的字段
"""
import sqlite3

def add_missing_fields():
    """添加缺失的字段到数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    print('=== 添加缺失字段到 stats_history 表 ===')
    print()
    
    # 要添加的字段
    fields_to_add = [
        ('difference', 'TEXT', '差值 (急涨-急跌)'),
        ('price_lowest', 'TEXT', '比价最低'),
        ('price_new_high', 'TEXT', '比价创新高')
    ]
    
    for field_name, field_type, description in fields_to_add:
        try:
            cursor.execute(f'ALTER TABLE stats_history ADD COLUMN {field_name} {field_type}')
            print(f'✅ 添加字段: {field_name} ({description})')
        except Exception as e:
            if 'duplicate column name' in str(e):
                print(f'⏭️  字段已存在: {field_name}')
            else:
                print(f'❌ 添加字段失败 {field_name}: {e}')
    
    conn.commit()
    
    # 验证字段
    print()
    print('=== 验证表结构 ===')
    cursor.execute('PRAGMA table_info(stats_history)')
    columns = cursor.fetchall()
    
    for col in columns:
        print(f'  {col[1]}: {col[2]}')
    
    conn.close()
    print()
    print('✅ 完成')

if __name__ == '__main__':
    add_missing_fields()
