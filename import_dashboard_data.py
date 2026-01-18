#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动导入首页监控数据
从Google Drive TXT文件中提取透明标签数据并存入JSONL
"""
import sys
sys.path.insert(0, '/home/user/webapp')

import json
from datetime import datetime
import pytz
from source_code.dashboard_jsonl_manager import DashboardJSONLManager
from source_code.txt_dashboard_extractor import extract_dashboard_data
from gdrive_detector_jsonl import get_txt_files, download_txt_file, load_config

def import_latest_dashboard_data():
    """导入最新的首页监控数据"""
    
    print('='*60)
    print('🚀 开始导入首页监控数据')
    print('='*60)
    
    try:
        # 1. 加载配置
        config = load_config()
        folder_id = config.get('folder_id')
        date_str = config.get('current_date', datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d'))
        
        if not folder_id:
            print('❌ 配置中没有文件夹ID')
            return False
        
        print(f'\n📁 文件夹信息:')
        print(f'   日期: {date_str}')
        print(f'   ID: {folder_id}')
        
        # 2. 获取TXT文件列表
        print(f'\n📄 获取TXT文件列表...')
        txt_files = get_txt_files(folder_id, date_str)
        
        if not txt_files:
            print(f'❌ 未找到TXT文件')
            return False
        
        print(f'✅ 找到 {len(txt_files)} 个文件')
        
        # 3. 获取最新的文件
        if isinstance(txt_files, list) and len(txt_files) > 0:
            latest_file = txt_files[0]
        else:
            print(f'❌ TXT文件列表格式错误')
            return False
        
        print(f'\n📥 下载最新文件: {latest_file}')
        
        # 4. 下载文件内容
        content = download_txt_file(folder_id, latest_file)
        
        if isinstance(content, tuple):
            content, error = content
            if error:
                print(f'❌ 下载失败: {error}')
                return False
        
        if not content or len(content) < 100:
            print(f'❌ 文件内容为空或太短')
            return False
        
        print(f'✅ 下载成功，文件大小: {len(content)} 字符')
        
        # 5. 解析快照时间
        time_part = latest_file.replace(f'{date_str}_', '').replace('.txt', '')
        hour = time_part[:2]
        minute = time_part[2:]
        snapshot_time = f'{date_str} {hour}:{minute}:00'
        
        print(f'\n📊 快照时间: {snapshot_time}')
        
        # 6. 提取透明标签数据
        print(f'\n🔍 提取透明标签数据...')
        dashboard_data = extract_dashboard_data(content, snapshot_time)
        
        if not dashboard_data:
            print(f'❌ 数据提取失败')
            return False
        
        print(f'✅ 数据提取成功')
        print(f'\n关键数据:')
        print(f'   急涨: {dashboard_data.get("rush_up")}')
        print(f'   急跌: {dashboard_data.get("rush_down")}')
        print(f'   计次: {dashboard_data.get("count")}')
        print(f'   差值: {dashboard_data.get("diff")}')
        print(f'   比值: {dashboard_data.get("ratio")}')
        print(f'   状态: {dashboard_data.get("status")}')
        
        # 7. 保存到JSONL
        print(f'\n💾 保存到JSONL...')
        manager = DashboardJSONLManager()
        manager.upsert_snapshot(dashboard_data)
        
        print(f'✅ 保存成功')
        
        # 8. 验证
        print(f'\n✅ 验证数据...')
        latest = manager.get_latest_snapshot()
        
        if latest:
            print(f'   最新快照时间: {latest.get("snapshot_time")}')
            print(f'   急涨: {latest.get("rush_up")}, 急跌: {latest.get("rush_down")}, 计次: {latest.get("count")}')
        
        # 9. 统计
        stats = manager.get_statistics()
        print(f'\n📊 数据统计:')
        print(f'   总快照数: {stats["total_snapshots"]}')
        print(f'   最新时间: {stats["latest_time"]}')
        
        print(f'\n' + '='*60)
        print(f'✅ 导入完成!')
        print(f'='*60)
        
        return True
        
    except Exception as e:
        print(f'\n❌ 导入失败: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = import_latest_dashboard_data()
    sys.exit(0 if success else 1)
