#!/usr/bin/env python3
"""
批量导入Query系统数据 - 从Google Drive TXT文件
"""

import sys
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

import json
import os
import requests
import re
from datetime import datetime
import pytz
from migrate_query_to_jsonl import parse_txt_to_jsonl
from query_jsonl_manager import QueryJSONLManager

def log_message(msg):
    """打印日志"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    timestamp = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")

def get_folder_id_for_date(target_date):
    """获取指定日期的文件夹ID"""
    try:
        config_file = '/home/user/webapp/daily_folder_config.json'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            if config.get('current_date') == target_date:
                return config.get('folder_id')
    except Exception as e:
        log_message(f"⚠️ 读取配置文件失败: {e}")
    return None

def get_txt_files_from_gdrive(folder_id, date_str):
    """从Google Drive获取TXT文件列表"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        log_message(f"📡 访问Google Drive: {url}")
        
        response = requests.get(url, timeout=30)
        content = response.text
        
        # 查找所有TXT文件
        pattern = rf'>{date_str}_(\d{{4}})\.txt<'
        matches = re.findall(pattern, content)
        
        # 排序（从旧到新）
        times_sorted = sorted(matches)
        filenames = [f"{date_str}_{time}.txt" for time in times_sorted]
        
        log_message(f"📂 找到 {len(filenames)} 个TXT文件")
        return filenames
        
    except Exception as e:
        log_message(f"❌ 获取文件列表失败: {e}")
        return []

def download_txt_file(folder_id, filename):
    """下载单个TXT文件内容"""
    try:
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        response = requests.get(url, timeout=30)
        content = response.text
        
        # 查找文件ID
        pattern = rf'data-id="([^"]+)"[^>]*>{re.escape(filename)}<'
        match = re.search(pattern, content)
        
        if not match:
            return None
            
        file_id = match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        file_response = requests.get(download_url, timeout=30)
        file_content = file_response.text
        
        return file_content
        
    except Exception as e:
        log_message(f"❌ 下载文件失败 {filename}: {e}")
        return None

def main():
    """主函数"""
    log_message("=" * 60)
    log_message("🚀 开始批量导入Query系统数据")
    log_message("=" * 60)
    
    # 1. 确定日期
    beijing_tz = pytz.timezone('Asia/Shanghai')
    target_date = datetime.now(beijing_tz).strftime('%Y-%m-%d')
    log_message(f"📅 目标日期: {target_date}")
    
    # 2. 获取文件夹ID
    folder_id = get_folder_id_for_date(target_date)
    if not folder_id:
        log_message(f"❌ 未找到 {target_date} 的文件夹ID")
        return
    
    log_message(f"📁 文件夹ID: {folder_id}")
    
    # 3. 获取TXT文件列表
    txt_files = get_txt_files_from_gdrive(folder_id, target_date)
    if not txt_files:
        log_message("❌ 未找到任何TXT文件")
        return
    
    log_message(f"📋 将导入 {len(txt_files)} 个文件")
    
    # 4. 初始化管理器
    manager = QueryJSONLManager()
    
    # 5. 批量导入
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, filename in enumerate(txt_files, 1):
        try:
            # 从文件名提取时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
            if not time_match:
                log_message(f"⚠️ [{i}/{len(txt_files)}] 跳过无效文件名: {filename}")
                skip_count += 1
                continue
            
            date_part = time_match.group(1)
            time_part = time_match.group(2)
            snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
            
            # 检查是否已存在
            existing = manager.get_snapshot_by_time(snapshot_time)
            if existing:
                log_message(f"⏭️  [{i}/{len(txt_files)}] 跳过已存在: {filename}")
                skip_count += 1
                continue
            
            # 下载文件
            log_message(f"📥 [{i}/{len(txt_files)}] 下载: {filename}")
            content = download_txt_file(folder_id, filename)
            
            if not content:
                log_message(f"❌ [{i}/{len(txt_files)}] 下载失败: {filename}")
                error_count += 1
                continue
            
            # 解析内容
            snapshot_data, currency_data = parse_txt_to_jsonl(content, snapshot_time)
            
            if not snapshot_data:
                log_message(f"❌ [{i}/{len(txt_files)}] 解析失败: {filename}")
                error_count += 1
                continue
            
            # 保存到JSONL
            manager.upsert_snapshot(snapshot_data)
            if currency_data:
                manager.upsert_coins(currency_data, snapshot_time)
            
            log_message(f"✅ [{i}/{len(txt_files)}] 导入成功: {filename} (急涨:{snapshot_data.get('rush_up')}, 急跌:{snapshot_data.get('rush_down')}, 计次:{snapshot_data.get('count')})")
            success_count += 1
            
        except Exception as e:
            log_message(f"❌ [{i}/{len(txt_files)}] 处理出错 {filename}: {e}")
            error_count += 1
            continue
    
    # 6. 统计结果
    log_message("=" * 60)
    log_message("📊 导入统计")
    log_message("=" * 60)
    log_message(f"✅ 成功导入: {success_count}")
    log_message(f"⏭️  跳过重复: {skip_count}")
    log_message(f"❌ 导入失败: {error_count}")
    log_message(f"📂 总文件数: {len(txt_files)}")
    
    # 7. 数据验证
    stats = manager.get_statistics()
    log_message("=" * 60)
    log_message("📈 数据统计")
    log_message("=" * 60)
    log_message(f"总快照数: {stats['total_snapshots']}")
    log_message(f"总币种数: {stats['total_coins']}")
    log_message(f"时间点数: {stats['unique_times']}")
    log_message(f"最新时间: {stats['latest_time']}")
    
    # 8. 显示最新数据
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
