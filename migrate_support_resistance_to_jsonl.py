#!/usr/bin/env python3
"""
支撑压力线系统数据迁移工具
功能：将 SQLite 数据库迁移到 JSONL 格式
时区：统一使用北京时间 (UTC+8)
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 配置
DB_PATH = '/home/user/webapp/databases/support_resistance.db'
OUTPUT_DIR = '/home/user/webapp/data/support_resistance_jsonl'

# 需要迁移的表
TABLES_TO_MIGRATE = [
    'support_resistance_levels',
    'support_resistance_snapshots',
    'daily_baseline_prices',
    'okex_kline_ohlc'
]


def ensure_dir(directory: str):
    """确保目录存在"""
    os.makedirs(directory, exist_ok=True)


def convert_timestamp_to_beijing(ts_value: Any) -> str:
    """
    转换时间戳为北京时间字符串
    
    支持格式:
    - Unix 时间戳（秒）
    - Unix 时间戳（毫秒）
    - ISO 格式字符串
    - SQLite TIMESTAMP 字符串
    """
    if ts_value is None:
        return None
    
    try:
        # 如果是数字（时间戳）
        if isinstance(ts_value, (int, float)):
            # 判断是秒还是毫秒
            if ts_value > 10000000000:  # 毫秒时间戳
                dt = datetime.fromtimestamp(ts_value / 1000, tz=BEIJING_TZ)
            else:  # 秒时间戳
                dt = datetime.fromtimestamp(ts_value, tz=BEIJING_TZ)
            
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果是字符串
        if isinstance(ts_value, str):
            # 尝试解析常见格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(ts_value, fmt)
                    # 假设数据库存储的是 UTC 时间或本地时间
                    # 转换为北京时间
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    
                    beijing_dt = dt.astimezone(BEIJING_TZ)
                    return beijing_dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            
            # 如果都解析失败，返回原值
            return ts_value
        
        return str(ts_value)
        
    except Exception as e:
        print(f"  ⚠️  时间转换失败: {ts_value} -> {e}")
        return str(ts_value) if ts_value else None


def export_table_to_jsonl(conn: sqlite3.Connection, table_name: str, output_dir: str) -> int:
    """
    导出单个表到 JSONL 文件
    
    返回：导出的记录数
    """
    try:
        cursor = conn.cursor()
        
        # 获取表结构
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]
        
        # 识别时间字段
        time_columns = []
        for col in columns_info:
            col_name = col[1].lower()
            col_type = col[2].lower()
            
            if any(keyword in col_name for keyword in ['time', 'date', 'timestamp', 'created', 'updated']):
                time_columns.append(col[1])
            elif 'timestamp' in col_type or 'datetime' in col_type:
                time_columns.append(col[1])
        
        print(f"  时间字段: {time_columns if time_columns else '无'}")
        
        # 读取所有数据
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"  ⚠️  表为空，跳过")
            return 0
        
        # 写入 JSONL 文件
        output_file = os.path.join(output_dir, f"{table_name}.jsonl")
        record_count = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for row in rows:
                record = {}
                
                for i, col_name in enumerate(column_names):
                    value = row[i]
                    
                    # 转换时间字段
                    if col_name in time_columns and value is not None:
                        beijing_time = convert_timestamp_to_beijing(value)
                        record[col_name] = value  # 保留原始值
                        record[f"{col_name}_beijing"] = beijing_time  # 添加北京时间
                    else:
                        record[col_name] = value
                
                # 写入 JSON 行
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
                record_count += 1
        
        print(f"  ✅ 导出成功: {record_count:,} 条记录")
        print(f"  📁 文件: {output_file}")
        
        return record_count
        
    except Exception as e:
        print(f"  ❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """主函数"""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     📦 支撑压力线系统 - SQLite → JSONL 迁移工具             ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # 检查数据库
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        return
    
    print(f"📊 数据库: {DB_PATH}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print()
    
    # 创建输出目录
    ensure_dir(OUTPUT_DIR)
    
    # 连接数据库
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        print("✅ 数据库连接成功\n")
        
        # 获取所有表
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📋 数据库中的所有表 ({len(all_tables)}):")
        for table in all_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            marker = "✓" if table in TABLES_TO_MIGRATE else " "
            print(f"  [{marker}] {table:40s} {count:>10,} 条")
        print()
        
        # 开始迁移
        print("="*60)
        print("开始迁移...")
        print("="*60)
        print()
        
        total_records = 0
        migrated_tables = 0
        
        for table_name in TABLES_TO_MIGRATE:
            if table_name not in all_tables:
                print(f"⚠️  表不存在: {table_name}")
                print()
                continue
            
            # 获取记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            
            print(f"📊 表: {table_name}")
            print(f"  记录数: {count:,}")
            
            if count == 0:
                print(f"  ⚠️  表为空，跳过")
                print()
                continue
            
            # 导出
            exported = export_table_to_jsonl(conn, table_name, OUTPUT_DIR)
            
            if exported > 0:
                total_records += exported
                migrated_tables += 1
            
            print()
        
        conn.close()
        
        # 生成汇总报告
        print("="*60)
        print("迁移完成!")
        print("="*60)
        print()
        print(f"✅ 成功迁移表数: {migrated_tables}/{len(TABLES_TO_MIGRATE)}")
        print(f"✅ 总记录数: {total_records:,}")
        print(f"✅ 输出目录: {OUTPUT_DIR}")
        print()
        
        # 显示生成的文件
        print("📁 生成的 JSONL 文件:")
        jsonl_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.jsonl')])
        
        for jsonl_file in jsonl_files:
            file_path = os.path.join(OUTPUT_DIR, jsonl_file)
            file_size = os.path.getsize(file_path)
            
            # 统计行数
            with open(file_path, 'r') as f:
                line_count = sum(1 for _ in f)
            
            # 格式化文件大小
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            
            print(f"  • {jsonl_file:45s} {line_count:>10,} 条  {size_str:>10s}")
        
        print()
        print("🎉 迁移完成！所有数据已转换为 JSONL 格式")
        print("🕐 时区: 北京时间 (UTC+8)")
        print()
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
