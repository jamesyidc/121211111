#!/usr/bin/env python3
"""
快速批量导入Query数据 - 使用gdrive_detector的download函数
"""

import sys
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

import json
import re
from datetime import datetime
import pytz
from gdrive_detector_jsonl import download_txt_file, get_txt_files
from migrate_query_to_jsonl import parse_txt_to_jsonl
from query_jsonl_manager import QueryJSONLManager

def log_message(msg):
    beijing_tz = pytz.timezone('Asia/Shanghai')
    timestamp = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def main():
    log_message("=" * 60)
    log_message("🚀 开始批量导入Query数据")
    log_message("=" * 60)
    
    # 1. 读取配置
    with open('/home/user/webapp/daily_folder_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    folder_id = config.get('folder_id')
    current_date = config.get('current_date')
    
    log_message(f"📅 日期: {current_date}")
    log_message(f"📁 文件夹ID: {folder_id}")
    
    # 2. 获取文件列表
    log_message("📡 获取文件列表...")
    result = get_txt_files(folder_id, current_date)
    
    if not result or len(result) < 1:
        log_message("❌ 获取文件列表失败")
        return
    
    file_list = result[0] if isinstance(result, tuple) else result
    log_message(f"📂 找到 {len(file_list)} 个文件")
    
    # 3. 初始化管理器
    manager = QueryJSONLManager()
    
    # 4. 批量导入
    success_count = 0
    skip_count = 0
    error_count = 0
    
    # 按时间从旧到新排序
    sorted_files = sorted(file_list)
    
    for i, filename in enumerate(sorted_files, 1):
        try:
            # 提取时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
            if not time_match:
                log_message(f"⏭️  [{i}/{len(sorted_files)}] 跳过无效文件名: {filename}")
                skip_count += 1
                continue
            
            date_part = time_match.group(1)
            time_part = time_match.group(2)
            snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
            
            # 检查是否已存在
            existing = manager.get_snapshot_by_time(snapshot_time)
            if existing:
                skip_count += 1
                if i % 10 == 0:
                    log_message(f"⏭️  [{i}/{len(sorted_files)}] 跳过已存在")
                continue
            
            # 下载文件
            if i % 10 == 1 or success_count < 5:
                log_message(f"📥 [{i}/{len(sorted_files)}] 下载: {filename}")
            
            result = download_txt_file(folder_id, filename)
            
            # download_txt_file返回 (content, error) 元组
            if isinstance(result, tuple):
                content, error = result
            else:
                content, error = result, None
            
            if not content or error:
                error_count += 1
                log_message(f"❌ [{i}/{len(sorted_files)}] 下载失败: {filename} - {error}")
                continue
            
            # 解析内容
            snapshot_data, currency_data = parse_txt_to_jsonl(content, snapshot_time)
            
            if not snapshot_data:
                error_count += 1
                log_message(f"❌ [{i}/{len(sorted_files)}] 解析失败: {filename}")
                continue
            
            # 保存到JSONL
            manager.upsert_snapshot(snapshot_data)
            if currency_data:
                manager.upsert_coins(currency_data, snapshot_time)
            
            success_count += 1
            
            # 显示详细信息（前5个和每10个）
            if success_count <= 5 or i % 10 == 0:
                log_message(
                    f"✅ [{i}/{len(sorted_files)}] {filename} "
                    f"(急涨:{snapshot_data.get('rush_up')}, "
                    f"急跌:{snapshot_data.get('rush_down')}, "
                    f"计次:{snapshot_data.get('count')})"
                )
            elif i % 5 == 0:
                log_message(f"  进度: {i}/{len(sorted_files)} ({int(i/len(sorted_files)*100)}%)")
                
        except Exception as e:
            error_count += 1
            log_message(f"❌ [{i}/{len(sorted_files)}] 错误 {filename}: {e}")
            continue
    
    # 5. 统计结果
    log_message("=" * 60)
    log_message("📊 导入统计")
    log_message("=" * 60)
    log_message(f"✅ 成功导入: {success_count}")
    log_message(f"⏭️  跳过重复: {skip_count}")
    log_message(f"❌ 导入失败: {error_count}")
    log_message(f"📂 总文件数: {len(sorted_files)}")
    
    # 6. 数据验证
    stats = manager.get_statistics()
    log_message("=" * 60)
    log_message("📈 数据统计")
    log_message("=" * 60)
    log_message(f"总快照数: {stats['total_snapshots']}")
    log_message(f"总币种数: {stats['total_coins']}")
    log_message(f"时间点数: {stats['unique_times']}")
    log_message(f"最新时间: {stats['latest_time']}")
    
    # 7. 显示最新数据
    latest = manager.get_latest_snapshot()
    if latest:
        log_message("=" * 60)
        log_message("🔥 最新快照数据")
        log_message("=" * 60)
        log_message(f"时间: {latest.get('snapshot_time')}")
        log_message(f"急涨: {latest.get('rush_up')}")
        log_message(f"急跌: {latest.get('rush_down')}")
        log_message(f"差值: {latest.get('diff')}")
        log_message(f"计次: {latest.get('count')}")
        log_message(f"比值: {latest.get('ratio', 0)}")
        log_message(f"状态: {latest.get('status')}")
    
    log_message("=" * 60)
    log_message("🎉 批量导入完成！")
    log_message("=" * 60)

if __name__ == "__main__":
    main()
