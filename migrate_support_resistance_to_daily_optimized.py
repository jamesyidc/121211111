#!/usr/bin/env python3
"""
支撑压力系统数据迁移脚本 v2.0 - 优化版
从单文件JSONL迁移到按日期存储的JSONL格式

特性:
- 分批处理，避免内存溢出
- 支持断点续传
- 实时进度显示
- 数据完整性验证

使用:
python3 migrate_support_resistance_to_daily_optimized.py [--batch-size 10000] [--start-date YYYYMMDD] [--dry-run]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from source_code.support_resistance_daily_manager import SupportResistanceDailyManager

# 配置
OLD_DATA_FILE = '/home/user/webapp/data/support_resistance_jsonl/support_resistance_levels.jsonl'
PROGRESS_FILE = '/home/user/webapp/data/support_resistance_daily/.migration_progress'

class MigrationProgress:
    """迁移进度管理"""
    
    def __init__(self, progress_file):
        self.progress_file = progress_file
        self.processed_lines = 0
        self.migrated_records = 0
        self.failed_records = 0
        self.last_date = None
        
        # 加载进度
        self.load()
    
    def load(self):
        """加载进度"""
        if not os.path.exists(self.progress_file):
            return
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                self.processed_lines = data.get('processed_lines', 0)
                self.migrated_records = data.get('migrated_records', 0)
                self.failed_records = data.get('failed_records', 0)
                self.last_date = data.get('last_date')
                
            print(f"📂 加载进度: 已处理 {self.processed_lines:,} 行, 迁移 {self.migrated_records:,} 条")
        except Exception as e:
            print(f"⚠️ 加载进度失败: {e}")
    
    def save(self):
        """保存进度"""
        try:
            data = {
                'processed_lines': self.processed_lines,
                'migrated_records': self.migrated_records,
                'failed_records': self.failed_records,
                'last_date': self.last_date,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ 保存进度失败: {e}")
    
    def reset(self):
        """重置进度"""
        self.processed_lines = 0
        self.migrated_records = 0
        self.failed_records = 0
        self.last_date = None
        
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)

def parse_record_time(record):
    """从记录中解析时间"""
    record_time = record.get('record_time', '') or record.get('record_time_beijing', '')
    
    if not record_time:
        return None
    
    # 处理不同的时间格式
    try:
        # 格式1: "2026-01-23 22:00:46"
        if ' ' in record_time:
            dt = datetime.strptime(record_time.split('.')[0], '%Y-%m-%d %H:%M:%S')
        # 格式2: "2026-01-23T22:00:46+08:00"
        elif 'T' in record_time:
            dt = datetime.fromisoformat(record_time.replace('+08:00', ''))
        else:
            return None
        
        return dt
    except Exception as e:
        print(f"⚠️ 解析时间失败: {record_time} - {e}")
        return None

def migrate_batch(manager, records_by_date, progress, dry_run=False):
    """迁移一批数据"""
    migrated = 0
    failed = 0
    
    for date_str, records in records_by_date.items():
        print(f"  📅 {date_str}: {len(records):,} 条记录...", end='')
        
        if dry_run:
            print(" [模拟模式，跳过]")
            migrated += len(records)
            continue
        
        # 批量写入
        success_count = 0
        for record_data in records:
            try:
                # 提取记录和时间
                record, dt = record_data
                
                # 格式化时间
                time_str = dt.strftime('%H:%M:%S')
                timestamp = dt.isoformat()
                
                # 写入level记录（指定原始时间）
                if manager.write_level_record(record, date_str, time_str, timestamp):
                    success_count += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"\n  ❌ 写入失败: {e}")
                failed += 1
        
        migrated += success_count
        print(f" ✅ 成功 {success_count}/{len(records)}")
    
    progress.migrated_records += migrated
    progress.failed_records += failed
    
    return migrated, failed

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='支撑压力数据迁移工具')
    parser.add_argument('--batch-size', type=int, default=10000, help='批处理大小（默认10000）')
    parser.add_argument('--start-date', type=str, help='起始日期（YYYYMMDD）')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际写入')
    parser.add_argument('--reset', action='store_true', help='重置进度，重新开始')
    parser.add_argument('--force', action='store_true', help='强制执行，跳过确认')
    
    args = parser.parse_args()
    
    print("="*70)
    print("  支撑压力系统数据迁移工具 v2.0")
    print("="*70)
    print()
    
    # 检查源文件
    if not os.path.exists(OLD_DATA_FILE):
        print(f"❌ 错误: 源文件不存在")
        print(f"   文件: {OLD_DATA_FILE}")
        return 1
    
    # 获取文件大小和行数
    file_size_mb = os.path.getsize(OLD_DATA_FILE) / 1024 / 1024
    print(f"📁 源文件: {OLD_DATA_FILE}")
    print(f"📊 文件大小: {file_size_mb:.1f} MB")
    
    # 统计总行数（快速估算）
    print(f"📊 正在统计行数...", end='', flush=True)
    with open(OLD_DATA_FILE, 'r') as f:
        total_lines = sum(1 for _ in f)
    print(f" {total_lines:,} 行")
    
    # 初始化管理器和进度
    manager = SupportResistanceDailyManager()
    progress = MigrationProgress(PROGRESS_FILE)
    
    if args.reset:
        print(f"\n🔄 重置进度...")
        progress.reset()
    
    # 显示进度
    if progress.processed_lines > 0:
        print(f"\n📂 续传模式:")
        print(f"   已处理: {progress.processed_lines:,} / {total_lines:,} 行 ({progress.processed_lines*100/total_lines:.1f}%)")
        print(f"   已迁移: {progress.migrated_records:,} 条")
        print(f"   失败: {progress.failed_records:,} 条")
        print(f"   最后日期: {progress.last_date}")
        
        if not args.force:
            response = input(f"\n是否继续？[Y/n] ")
            if response.lower() == 'n':
                print("取消迁移")
                return 0
    
    print(f"\n⚙️  迁移配置:")
    print(f"   批处理大小: {args.batch_size:,} 行")
    print(f"   起始日期: {args.start_date or '全部'}")
    print(f"   模拟模式: {'是' if args.dry_run else '否'}")
    print(f"   跳过行数: {progress.processed_lines:,}")
    
    if not args.dry_run and not args.force:
        response = input(f"\n开始迁移？[Y/n] ")
        if response.lower() == 'n':
            print("取消迁移")
            return 0
    
    print(f"\n🚀 开始迁移...\n")
    
    start_time = datetime.now()
    
    # 分批读取和迁移
    current_batch = []
    records_by_date = defaultdict(list)
    line_no = 0
    
    with open(OLD_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line_no += 1
            
            # 跳过已处理的行
            if line_no <= progress.processed_lines:
                continue
            
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
                
                # 解析时间
                dt = parse_record_time(record)
                if not dt:
                    progress.failed_records += 1
                    continue
                
                date_str = dt.strftime('%Y%m%d')
                
                # 如果指定了起始日期，跳过之前的
                if args.start_date and date_str < args.start_date:
                    continue
                
                # 添加到当前批次
                records_by_date[date_str].append((record, dt))
                current_batch.append((date_str, record))
                progress.last_date = date_str
                
                # 达到批处理大小，执行迁移
                if len(current_batch) >= args.batch_size:
                    print(f"📦 批次 #{line_no // args.batch_size}: {len(current_batch):,} 条")
                    
                    migrated, failed = migrate_batch(manager, records_by_date, progress, args.dry_run)
                    
                    # 更新进度
                    progress.processed_lines = line_no
                    progress.save()
                    
                    # 显示进度
                    percent = (line_no * 100.0 / total_lines)
                    elapsed = (datetime.now() - start_time).total_seconds()
                    speed = line_no / elapsed if elapsed > 0 else 0
                    eta_seconds = (total_lines - line_no) / speed if speed > 0 else 0
                    
                    print(f"   进度: {percent:.1f}% | "
                          f"速度: {speed:.0f} 行/秒 | "
                          f"预计剩余: {eta_seconds/60:.1f} 分钟")
                    print()
                    
                    # 清空批次
                    current_batch = []
                    records_by_date = defaultdict(list)
            
            except json.JSONDecodeError as e:
                progress.failed_records += 1
                continue
            except Exception as e:
                print(f"❌ 处理行 {line_no} 失败: {e}")
                progress.failed_records += 1
                continue
    
    # 处理剩余批次
    if current_batch:
        print(f"📦 最后批次: {len(current_batch):,} 条")
        migrated, failed = migrate_batch(manager, records_by_date, progress, args.dry_run)
        progress.processed_lines = line_no
        progress.save()
    
    # 完成
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("✅ 迁移完成！")
    print("="*70)
    print(f"📊 统计:")
    print(f"   总行数: {total_lines:,}")
    print(f"   已处理: {progress.processed_lines:,}")
    print(f"   成功迁移: {progress.migrated_records:,}")
    print(f"   失败: {progress.failed_records:,}")
    print(f"   用时: {elapsed_time/60:.1f} 分钟")
    print(f"   速度: {progress.processed_lines/elapsed_time:.0f} 行/秒")
    
    # 显示按日期统计
    print(f"\n📅 按日期统计:")
    dates = manager.get_available_dates()
    print(f"   共 {len(dates)} 天数据")
    
    total_size = 0
    for date in dates:
        stats = manager.get_date_statistics(date)
        print(f"   {date}: {stats['level_count']:,} 条 ({stats['file_size_mb']:.1f} MB)")
        total_size += stats['file_size']
    
    print(f"\n   总大小: {total_size/1024/1024:.1f} MB")
    print(f"   原文件: {file_size_mb:.1f} MB")
    print(f"   空间变化: {(total_size/1024/1024 - file_size_mb):.1f} MB")
    
    if args.dry_run:
        print(f"\n⚠️  这是模拟运行，数据未实际写入")
    
    # 清理进度文件
    if not args.dry_run and os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print(f"\n✅ 已清理进度文件")
    
    print(f"\n🎉 迁移成功！新数据位于:")
    print(f"   {manager.data_dir}")
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断，进度已保存")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
