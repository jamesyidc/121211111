#!/usr/bin/env python3
"""
支撑阻力系统数据迁移脚本
将现有的单文件JSONL数据迁移到按日期分文件的新格式

迁移步骤:
1. 读取 support_resistance_levels.jsonl
2. 读取 support_resistance_snapshots.jsonl
3. 按日期分组
4. 写入新的按日期文件
"""

import os
import sys
import json
import pytz
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')
from support_resistance_daily_manager import SupportResistanceDailyManager

# 旧数据目录
OLD_DATA_DIR = '/home/user/webapp/data/support_resistance_jsonl'
OLD_LEVELS_FILE = os.path.join(OLD_DATA_DIR, 'support_resistance_levels.jsonl')
OLD_SNAPSHOTS_FILE = os.path.join(OLD_DATA_DIR, 'support_resistance_snapshots.jsonl')

# 新数据目录
NEW_DATA_DIR = '/home/user/webapp/data/support_resistance_daily'

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def parse_datetime(datetime_str: str) -> tuple:
    """
    解析日期时间字符串，返回(date_str, time_str, timestamp)
    
    支持的格式:
    - "2026-01-24 19:30:35"
    - "2026-01-24T19:30:35+08:00"
    """
    try:
        # 尝试带时区的ISO格式
        if 'T' in datetime_str and ('+' in datetime_str or 'Z' in datetime_str):
            dt = datetime.fromisoformat(datetime_str)
            # 转换到北京时区
            if dt.tzinfo is None:
                dt = BEIJING_TZ.localize(dt)
            else:
                dt = dt.astimezone(BEIJING_TZ)
        else:
            # 简单格式 "YYYY-MM-DD HH:MM:SS"
            dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            dt = BEIJING_TZ.localize(dt)
        
        date_str = dt.strftime('%Y%m%d')
        time_str = dt.strftime('%H:%M:%S')
        timestamp = dt.isoformat()
        
        return date_str, time_str, timestamp
        
    except Exception as e:
        print(f"⚠️ 解析日期时间失败: {datetime_str}, 错误: {e}")
        return None, None, None

def migrate_levels(manager: SupportResistanceDailyManager) -> Dict:
    """迁移levels数据"""
    print("\n=== 迁移 Levels 数据 ===")
    
    if not os.path.exists(OLD_LEVELS_FILE):
        print(f"⚠️ 文件不存在: {OLD_LEVELS_FILE}")
        return {"success": False, "error": "文件不存在"}
    
    # 按日期分组
    records_by_date = defaultdict(list)
    total_records = 0
    failed_records = 0
    
    print(f"📖 读取文件: {OLD_LEVELS_FILE}")
    
    with open(OLD_LEVELS_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                total_records += 1
                
                # 提取时间字段
                record_time = record.get('record_time') or record.get('record_time_beijing')
                
                if not record_time:
                    print(f"⚠️ 行 {line_num}: 缺少时间字段")
                    failed_records += 1
                    continue
                
                # 解析日期时间
                date_str, time_str, timestamp = parse_datetime(record_time)
                
                if not date_str:
                    failed_records += 1
                    continue
                
                # 构建新格式记录
                new_record = {
                    "type": "level",
                    "timestamp": timestamp,
                    "date": date_str,
                    "time": time_str,
                    "data": record
                }
                
                records_by_date[date_str].append(new_record)
                
                if total_records % 100000 == 0:
                    print(f"   已处理 {total_records:,} 条记录...")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ 行 {line_num}: JSON解析失败 - {e}")
                failed_records += 1
                continue
            except Exception as e:
                print(f"⚠️ 行 {line_num}: 处理失败 - {e}")
                failed_records += 1
                continue
    
    print(f"\n📊 读取完成:")
    print(f"   总记录数: {total_records:,}")
    print(f"   失败记录: {failed_records:,}")
    print(f"   成功记录: {total_records - failed_records:,}")
    print(f"   日期数量: {len(records_by_date)}")
    
    # 写入新文件
    print(f"\n💾 写入新文件到: {NEW_DATA_DIR}")
    
    written_dates = []
    written_records = 0
    
    for date_str in sorted(records_by_date.keys()):
        records = records_by_date[date_str]
        file_path = manager.get_file_path(date_str)
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    written_records += 1
            
            written_dates.append(date_str)
            print(f"   ✅ {date_str}: {len(records):,} 条记录")
            
        except Exception as e:
            print(f"   ❌ {date_str}: 写入失败 - {e}")
    
    print(f"\n✅ Levels迁移完成:")
    print(f"   写入日期: {len(written_dates)}")
    print(f"   写入记录: {written_records:,}")
    
    return {
        "success": True,
        "total_records": total_records,
        "failed_records": failed_records,
        "written_records": written_records,
        "dates": written_dates
    }

def migrate_snapshots(manager: SupportResistanceDailyManager) -> Dict:
    """迁移snapshots数据"""
    print("\n=== 迁移 Snapshots 数据 ===")
    
    if not os.path.exists(OLD_SNAPSHOTS_FILE):
        print(f"⚠️ 文件不存在: {OLD_SNAPSHOTS_FILE}")
        return {"success": False, "error": "文件不存在"}
    
    # 按日期分组
    records_by_date = defaultdict(list)
    total_records = 0
    failed_records = 0
    
    print(f"📖 读取文件: {OLD_SNAPSHOTS_FILE}")
    
    with open(OLD_SNAPSHOTS_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                total_records += 1
                
                # 提取时间字段
                snapshot_time = record.get('snapshot_time') or record.get('snapshot_time_beijing')
                
                if not snapshot_time:
                    print(f"⚠️ 行 {line_num}: 缺少时间字段")
                    failed_records += 1
                    continue
                
                # 解析日期时间
                date_str, time_str, timestamp = parse_datetime(snapshot_time)
                
                if not date_str:
                    failed_records += 1
                    continue
                
                # 构建新格式记录
                new_record = {
                    "type": "snapshot",
                    "timestamp": timestamp,
                    "date": date_str,
                    "time": time_str,
                    "data": record
                }
                
                records_by_date[date_str].append(new_record)
                
                if total_records % 5000 == 0:
                    print(f"   已处理 {total_records:,} 条记录...")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ 行 {line_num}: JSON解析失败 - {e}")
                failed_records += 1
                continue
            except Exception as e:
                print(f"⚠️ 行 {line_num}: 处理失败 - {e}")
                failed_records += 1
                continue
    
    print(f"\n📊 读取完成:")
    print(f"   总记录数: {total_records:,}")
    print(f"   失败记录: {failed_records:,}")
    print(f"   成功记录: {total_records - failed_records:,}")
    print(f"   日期数量: {len(records_by_date)}")
    
    # 写入新文件
    print(f"\n💾 写入新文件到: {NEW_DATA_DIR}")
    
    written_dates = []
    written_records = 0
    
    for date_str in sorted(records_by_date.keys()):
        records = records_by_date[date_str]
        file_path = manager.get_file_path(date_str)
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    written_records += 1
            
            written_dates.append(date_str)
            print(f"   ✅ {date_str}: {len(records):,} 条记录")
            
        except Exception as e:
            print(f"   ❌ {date_str}: 写入失败 - {e}")
    
    print(f"\n✅ Snapshots迁移完成:")
    print(f"   写入日期: {len(written_dates)}")
    print(f"   写入记录: {written_records:,}")
    
    return {
        "success": True,
        "total_records": total_records,
        "failed_records": failed_records,
        "written_records": written_records,
        "dates": written_dates
    }

def verify_migration(manager: SupportResistanceDailyManager):
    """验证迁移结果"""
    print("\n=== 验证迁移结果 ===")
    
    dates = manager.get_available_dates()
    
    print(f"\n📅 可用日期: {len(dates)} 个")
    print(f"   最早: {dates[0] if dates else 'N/A'}")
    print(f"   最新: {dates[-1] if dates else 'N/A'}")
    
    total_size = 0
    total_records = 0
    total_levels = 0
    total_snapshots = 0
    
    print(f"\n📊 各日期统计:")
    print(f"{'日期':<12} {'文件大小':>12} {'总记录':>10} {'Levels':>10} {'Snapshots':>10}")
    print("-" * 60)
    
    for date_str in dates:
        stats = manager.get_date_statistics(date_str)
        
        if stats['exists']:
            total_size += stats['file_size']
            total_records += stats['total_records']
            total_levels += stats['level_count']
            total_snapshots += stats['snapshot_count']
            
            print(f"{date_str:<12} {stats['file_size_mb']:>10.2f} MB "
                  f"{stats['total_records']:>10,} {stats['level_count']:>10,} "
                  f"{stats['snapshot_count']:>10,}")
    
    print("-" * 60)
    print(f"{'总计':<12} {total_size/1024/1024:>10.2f} MB "
          f"{total_records:>10,} {total_levels:>10,} {total_snapshots:>10,}")
    
    print(f"\n✅ 验证完成！")

def backup_old_data():
    """备份旧数据"""
    print("\n=== 备份旧数据 ===")
    
    backup_dir = f"{OLD_DATA_DIR}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        # 备份levels文件
        if os.path.exists(OLD_LEVELS_FILE):
            import shutil
            backup_file = os.path.join(backup_dir, 'support_resistance_levels.jsonl')
            shutil.copy2(OLD_LEVELS_FILE, backup_file)
            print(f"✅ 已备份: {OLD_LEVELS_FILE}")
            print(f"   -> {backup_file}")
        
        # 备份snapshots文件
        if os.path.exists(OLD_SNAPSHOTS_FILE):
            import shutil
            backup_file = os.path.join(backup_dir, 'support_resistance_snapshots.jsonl')
            shutil.copy2(OLD_SNAPSHOTS_FILE, backup_file)
            print(f"✅ 已备份: {OLD_SNAPSHOTS_FILE}")
            print(f"   -> {backup_file}")
        
        print(f"\n✅ 备份完成: {backup_dir}")
        return True
        
    except Exception as e:
        print(f"❌ 备份失败: {e}")
        return False

def main():
    """主函数"""
    print("╔" + "═" * 60 + "╗")
    print("║" + " " * 60 + "║")
    print("║" + "支撑阻力系统数据迁移".center(60) + "║")
    print("║" + "单文件JSONL -> 按日期分文件".center(60) + "║")
    print("║" + " " * 60 + "║")
    print("╚" + "═" * 60 + "╝")
    
    # 初始化管理器
    manager = SupportResistanceDailyManager(NEW_DATA_DIR)
    
    print(f"\n📁 旧数据目录: {OLD_DATA_DIR}")
    print(f"📁 新数据目录: {NEW_DATA_DIR}")
    
    # 确认是否继续
    print("\n⚠️  警告: 此操作将迁移所有历史数据到新格式")
    response = input("是否继续？ (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ 已取消迁移")
        return
    
    # 备份旧数据
    print("\n步骤1: 备份旧数据")
    if not backup_old_data():
        print("❌ 备份失败，终止迁移")
        return
    
    # 迁移levels
    print("\n步骤2: 迁移Levels数据")
    levels_result = migrate_levels(manager)
    
    if not levels_result.get('success'):
        print("❌ Levels迁移失败")
        return
    
    # 迁移snapshots
    print("\n步骤3: 迁移Snapshots数据")
    snapshots_result = migrate_snapshots(manager)
    
    if not snapshots_result.get('success'):
        print("❌ Snapshots迁移失败")
        return
    
    # 验证迁移结果
    print("\n步骤4: 验证迁移结果")
    verify_migration(manager)
    
    # 总结
    print("\n" + "=" * 60)
    print("迁移总结".center(60))
    print("=" * 60)
    print(f"\n✅ Levels:")
    print(f"   总记录: {levels_result['total_records']:,}")
    print(f"   成功: {levels_result['written_records']:,}")
    print(f"   失败: {levels_result['failed_records']:,}")
    
    print(f"\n✅ Snapshots:")
    print(f"   总记录: {snapshots_result['total_records']:,}")
    print(f"   成功: {snapshots_result['written_records']:,}")
    print(f"   失败: {snapshots_result['failed_records']:,}")
    
    print(f"\n✅ 迁移完成！新数据目录: {NEW_DATA_DIR}")
    
    print("\n💡 后续步骤:")
    print("   1. 验证新数据是否正确")
    print("   2. 更新采集器使用新的管理器")
    print("   3. 更新API路由读取新格式数据")
    print("   4. 确认无误后可删除旧数据文件")

if __name__ == '__main__':
    main()
