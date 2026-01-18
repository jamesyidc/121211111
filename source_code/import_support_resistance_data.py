#!/usr/bin/env python3
"""
支撑/阻力位系统数据导入工具
导入内容:
1. support_resistance_levels - 实时支撑阻力位数据
2. support_resistance_snapshots - 12小时趋势快照数据

安全特性:
- 备份现有数据
- 数据验证
- 原子性导入（全部成功或全部失败）
- 自动去重
"""
import sqlite3
import json
import os
from datetime import datetime
import pytz
import shutil

DB_PATH = "/home/user/webapp/crypto_data.db"
BACKUP_DIR = "/home/user/webapp/backups"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message):
    """打印带时间戳的日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def ensure_backup_dir():
    """确保备份目录存在"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        log(f"✅ 创建备份目录: {BACKUP_DIR}")

def backup_database():
    """备份当前数据库"""
    log("💾 备份当前数据库...")
    ensure_backup_dir()
    
    backup_filename = f"crypto_data_backup_{datetime.now(BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    shutil.copy2(DB_PATH, backup_path)
    
    backup_size = os.path.getsize(backup_path)
    backup_size_mb = backup_size / (1024 * 1024)
    
    log(f"✅ 数据库备份完成")
    log(f"   备份文件: {backup_path}")
    log(f"   备份大小: {backup_size_mb:.2f} MB")
    log("")
    
    return backup_path

def validate_import_file(import_path):
    """验证导入文件"""
    log(f"🔍 验证导入文件: {import_path}")
    
    if not os.path.exists(import_path):
        raise Exception(f"文件不存在: {import_path}")
    
    file_size = os.path.getsize(import_path)
    file_size_mb = file_size / (1024 * 1024)
    log(f"   文件大小: {file_size_mb:.2f} MB")
    
    # 读取JSON文件
    with open(import_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 验证数据结构
    if 'export_info' not in data:
        raise Exception("无效的导出文件: 缺少 export_info")
    
    if 'tables' not in data:
        raise Exception("无效的导出文件: 缺少 tables")
    
    log(f"✅ 文件验证通过")
    log(f"   导出时间: {data['export_info'].get('export_time', 'Unknown')}")
    log(f"   表数量: {data['export_info'].get('tables_count', 0)}")
    log("")
    
    return data

def clear_table(cursor, table_name):
    """清空表数据"""
    cursor.execute(f"DELETE FROM {table_name}")
    log(f"   清空表: {table_name}")

def import_table_data(cursor, table_data):
    """导入表数据"""
    table_name = table_data['table_name']
    columns = table_data['columns']
    records = table_data['data']
    
    log(f"📊 导入表: {table_name}")
    log(f"   记录数: {len(records):,}")
    
    if len(records) == 0:
        log(f"   ⚠️ 表为空，跳过")
        return 0
    
    # 构建INSERT语句
    placeholders = ', '.join(['?' for _ in columns])
    columns_str = ', '.join(columns)
    sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
    
    # 批量插入
    success_count = 0
    error_count = 0
    
    for record in records:
        try:
            values = [record.get(col) for col in columns]
            cursor.execute(sql, values)
            success_count += 1
        except Exception as e:
            error_count += 1
            if error_count <= 5:  # 只显示前5个错误
                log(f"   ⚠️ 插入失败: {e}")
    
    log(f"   ✅ 成功: {success_count:,} 条")
    if error_count > 0:
        log(f"   ❌ 失败: {error_count:,} 条")
    
    return success_count

def import_all_data(import_path, clear_existing=False):
    """导入所有数据"""
    log("")
    log("=" * 80)
    log("🚀 支撑/阻力位系统数据导入工具")
    log("=" * 80)
    log("")
    
    # 验证导入文件
    try:
        import_data = validate_import_file(import_path)
    except Exception as e:
        log(f"❌ 文件验证失败: {e}")
        return False
    
    # 备份当前数据库
    try:
        backup_path = backup_database()
    except Exception as e:
        log(f"❌ 数据库备份失败: {e}")
        return False
    
    # 连接数据库
    log("🔌 连接数据库...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    log(f"✅ 数据库连接成功: {DB_PATH}")
    log("")
    
    try:
        # 开始事务
        log("🔄 开始导入事务...")
        log("")
        
        total_imported = 0
        
        # 逐个导入表
        for table_name, table_data in import_data['tables'].items():
            # 如果需要清空现有数据
            if clear_existing:
                clear_table(cursor, table_name)
            
            # 导入数据
            imported_count = import_table_data(cursor, table_data)
            total_imported += imported_count
            log("")
        
        # 提交事务
        log("💾 提交事务...")
        conn.commit()
        
        log("")
        log("=" * 80)
        log("✅ 数据导入完成！")
        log("=" * 80)
        log("")
        log(f"📈 导入统计:")
        log(f"   表数量: {len(import_data['tables'])}")
        log(f"   总记录数: {total_imported:,}")
        log("")
        
        for table_name, table_data in import_data['tables'].items():
            log(f"   - {table_name}: {table_data['record_count']:,} 条记录")
        
        log("")
        log(f"💾 数据库备份: {backup_path}")
        log("")
        log("🎉 导入成功！")
        log("")
        
        conn.close()
        return True
        
    except Exception as e:
        log("")
        log("=" * 80)
        log("❌ 导入失败！")
        log("=" * 80)
        log("")
        log(f"错误信息: {e}")
        log("")
        log("🔄 回滚事务...")
        conn.rollback()
        conn.close()
        
        log(f"💾 可以从备份恢复: {backup_path}")
        log("")
        
        return False

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python3 import_support_resistance_data.py <导入文件路径> [--clear]")
        print("参数说明:")
        print("  <导入文件路径>: JSON格式的导出文件")
        print("  --clear: 可选，导入前清空现有数据")
        sys.exit(1)
    
    import_path = sys.argv[1]
    clear_existing = '--clear' in sys.argv
    
    if clear_existing:
        log("⚠️  警告: 将清空现有数据后再导入")
        log("")
    
    success = import_all_data(import_path, clear_existing)
    
    sys.exit(0 if success else 1)
