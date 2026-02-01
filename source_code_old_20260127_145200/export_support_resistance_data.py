#!/usr/bin/env python3
"""
支撑/阻力位系统数据导出工具
导出内容:
1. support_resistance_levels - 实时支撑阻力位数据（抄底信号、逃顶信号）
2. support_resistance_snapshots - 12小时趋势快照数据

导出格式: JSON（包含完整数据和元数据）
"""
import sqlite3
import json
import os
from datetime import datetime
import pytz

DB_PATH = "/home/user/webapp/crypto_data.db"
EXPORT_DIR = "/home/user/webapp/exports"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message):
    """打印带时间戳的日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def ensure_export_dir():
    """确保导出目录存在"""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        log(f"✅ 创建导出目录: {EXPORT_DIR}")

def export_table_data(cursor, table_name):
    """导出指定表的所有数据"""
    log(f"📊 开始导出表: {table_name}")
    
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    columns = [col[1] for col in columns_info]
    
    log(f"   字段数: {len(columns)}")
    
    # 获取所有数据
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    log(f"   记录数: {len(rows)}")
    
    # 转换为字典列表
    data = []
    for row in rows:
        record = {}
        for i, value in enumerate(row):
            record[columns[i]] = value
        data.append(record)
    
    return {
        'table_name': table_name,
        'columns': columns,
        'record_count': len(rows),
        'data': data
    }

def export_all_data():
    """导出所有支撑阻力位数据"""
    log("")
    log("=" * 80)
    log("🚀 支撑/阻力位系统数据导出工具")
    log("=" * 80)
    log("")
    
    # 确保导出目录存在
    ensure_export_dir()
    
    # 连接数据库
    log("🔌 连接数据库...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    log(f"✅ 数据库连接成功: {DB_PATH}")
    log("")
    
    # 导出的表列表
    tables_to_export = [
        'support_resistance_levels',
        'support_resistance_snapshots'
    ]
    
    export_data = {
        'export_info': {
            'export_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'export_timestamp': datetime.now(BEIJING_TZ).timestamp(),
            'database_path': DB_PATH,
            'tables_count': len(tables_to_export),
            'version': '1.0'
        },
        'tables': {}
    }
    
    total_records = 0
    
    # 逐个导出表
    for table_name in tables_to_export:
        try:
            table_data = export_table_data(cursor, table_name)
            export_data['tables'][table_name] = table_data
            total_records += table_data['record_count']
            log(f"✅ 表 {table_name} 导出成功")
            log("")
        except Exception as e:
            log(f"❌ 表 {table_name} 导出失败: {e}")
            log("")
    
    conn.close()
    
    # 生成导出文件名
    export_filename = f"support_resistance_backup_{datetime.now(BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}.json"
    export_path = os.path.join(EXPORT_DIR, export_filename)
    
    # 保存为JSON文件
    log("💾 保存导出数据...")
    with open(export_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    # 获取文件大小
    file_size = os.path.getsize(export_path)
    file_size_mb = file_size / (1024 * 1024)
    
    log("")
    log("=" * 80)
    log("✅ 数据导出完成！")
    log("=" * 80)
    log("")
    log(f"📁 导出文件: {export_path}")
    log(f"📊 文件大小: {file_size_mb:.2f} MB ({file_size:,} bytes)")
    log(f"📈 导出统计:")
    log(f"   表数量: {len(tables_to_export)}")
    log(f"   总记录数: {total_records:,}")
    log("")
    
    for table_name, table_data in export_data['tables'].items():
        log(f"   - {table_name}: {table_data['record_count']:,} 条记录")
    
    log("")
    log("🎉 导出成功！")
    log("")
    
    return export_path

if __name__ == '__main__':
    export_all_data()
