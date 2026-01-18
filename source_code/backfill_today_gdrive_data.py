#!/usr/bin/env python3
"""
批量回填今天的Google Drive数据
从Google Drive下载所有TXT文件并导入到JSONL
"""
import requests
import re
import json
import time
import sys
import os
from datetime import datetime
import pytz

# 添加路径
sys.path.insert(0, '/home/user/webapp/source_code')
sys.path.insert(0, '/home/user/webapp')

from gdrive_jsonl_manager import GDriveJSONLManager

# 配置
FOLDER_ID = '1Ndx7uLKmp1c31nDQP4BCC9SObnNJ3cpy'  # 2026-01-18文件夹
TARGET_DATE = '2026-01-18'
JSONL_DATA_DIR = "/home/user/webapp/data/gdrive_jsonl"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_all_txt_files():
    """获取文件夹中的所有TXT文件"""
    print(f"🔍 获取Google Drive文件夹中的TXT文件列表...")
    
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}#list"
        response = requests.get(embed_url, timeout=30)
        html = response.text
        
        # 查找所有TXT文件名和ID
        txt_pattern = rf'({re.escape(TARGET_DATE)}_\d{{4}})\.txt'
        txt_files = re.findall(txt_pattern, html)
        unique_files = sorted(set(txt_files))
        
        # 获取每个文件的ID
        files_info = []
        for filename in unique_files:
            # 在HTML中查找文件名附近的ID
            file_pattern = rf'{re.escape(filename)}\.txt.*?href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]{{33}})'
            matches = re.findall(file_pattern, html, re.DOTALL)
            
            if not matches:
                # 备用方案
                file_pattern2 = rf'{re.escape(filename)}.*?([a-zA-Z0-9_-]{{33}})'
                matches = re.findall(file_pattern2, html)
            
            if matches:
                file_id = matches[0]
                download_url = f'https://drive.google.com/uc?id={file_id}&export=download'
                
                files_info.append({
                    'filename': f'{filename}.txt',
                    'file_id': file_id,
                    'download_url': download_url,
                    'time': filename.split('_')[1]
                })
        
        print(f"✅ 找到 {len(files_info)} 个TXT文件")
        return files_info
        
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        return []

def check_if_imported(snapshot_time):
    """检查JSONL中是否已有该时间点的数据"""
    try:
        manager = GDriveJSONLManager(JSONL_DATA_DIR)
        snapshots = manager.get_snapshots_by_time(snapshot_time)
        return len(snapshots) > 0
    except:
        return False

def download_file(url):
    """下载文件"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return None

def parse_txt_content(content, snapshot_time):
    """解析TXT内容"""
    try:
        # 解码
        content_str = content.decode('gbk', errors='ignore') if isinstance(content, bytes) else content
        
        if not content_str or len(content_str) < 100:
            return None, None
        
        lines = content_str.split('\n')
        
        # 提取聚合数据
        rush_up_total = 0
        rush_down_total = 0
        status = ''
        ratio = ''
        green_count = 0
        green_percent = ''
        count = 0
        count_score = ''
        price_lowest = 0
        price_newhigh = 0
        fall_24h_count = 0
        
        for line in lines:
            line = line.strip()
            if '透明标签_急涨总和' in line:
                match = re.search(r'急涨：(\d+)', line)
                if match:
                    rush_up_total = int(match.group(1))
            elif '透明标签_急跌总和' in line:
                match = re.search(r'急跌：(\d+)', line)
                if match:
                    rush_down_total = int(match.group(1))
            elif '透明标签_五种状态' in line:
                match = re.search(r'状态：(.+?)[\r\n]', line)
                if match:
                    status = match.group(1).strip()
            elif '透明标签_急涨急跌比值' in line:
                match = re.search(r'比值：(.+?)[\r\n]', line)
                if match:
                    ratio = match.group(1).strip()
            elif '透明标签_绿色数量' in line:
                match = re.search(r'绿色数量=(\d+)', line)
                if match:
                    green_count = int(match.group(1))
            elif '透明标签_百分比' in line:
                match = re.search(r'百分比=(.+?)[\r\n]', line)
                if match:
                    green_percent = match.group(1).strip()
            elif '透明标签_计次' in line:
                match = re.search(r'计次=(\d+)', line)
                if match:
                    count = int(match.group(1))
            elif '透明标签_全绿得分' in line:
                match = re.search(r'全绿得分=(.+?)[\r\n]', line)
                if match:
                    count_score = match.group(1).strip()
            elif '透明标签_比价最低得分' in line:
                match = re.search(r'比价最低 (\d+)', line)
                if match:
                    price_lowest = int(match.group(1))
            elif '透明标签_仓位得分' in line:
                match = re.search(r'比价创新高 (\d+)', line)
                if match:
                    price_newhigh = int(match.group(1))
            elif '透明标签_急跌数量' in line:
                match = re.search(r'急跌数量 计次 \d+ (\d+)', line)
                if match:
                    fall_24h_count = int(match.group(1))
        
        # 解析币种数据
        coin_snapshots = []
        in_data_section = False
        
        for line in lines:
            line = line.strip()
            
            if '[超级列表框_首页开始]' in line:
                in_data_section = True
                continue
            elif '[超级列表框_首页结束]' in line:
                break
            
            if in_data_section and '|' in line:
                parts = line.split('|')
                if len(parts) >= 16:
                    try:
                        snapshot_date = snapshot_time.split(' ')[0]
                        inst_id = parts[1].strip()
                        
                        change_24h = float(parts[2]) if parts[2].strip() else 0.0
                        rush_up = int(parts[3]) if parts[3].strip() else 0
                        rush_down = int(parts[4]) if parts[4].strip() else 0
                        last_price = float(parts[6]) if parts[6].strip() else 0.0
                        high_24h_date = parts[7].strip() if len(parts) > 7 else ''
                        
                        coin_snapshot = {
                            'snapshot_date': snapshot_date,
                            'snapshot_time': snapshot_time,
                            'inst_id': inst_id,
                            'last_price': last_price,
                            'change_24h': change_24h,
                            'rush_up': rush_up,
                            'rush_down': rush_down,
                            'high_24h_date': high_24h_date,
                            'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        coin_snapshots.append(coin_snapshot)
                        
                    except (ValueError, IndexError):
                        continue
        
        if not coin_snapshots:
            return None, None
        
        # 聚合数据
        aggregate_data = {
            'snapshot_date': snapshot_time.split(' ')[0],
            'snapshot_time': snapshot_time,
            'rush_up_total': rush_up_total,
            'rush_down_total': rush_down_total,
            'diff': rush_up_total - rush_down_total,
            'status': status,
            'ratio': ratio,
            'green_count': green_count,
            'green_percent': green_percent,
            'count': count,
            'count_score': count_score,
            'price_lowest': price_lowest,
            'price_newhigh': price_newhigh,
            'fall_24h_count': fall_24h_count,
            'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return coin_snapshots, aggregate_data
        
    except Exception as e:
        print(f"  ❌ 解析失败: {e}")
        return None, None

def save_to_jsonl(coin_snapshots, aggregate_data):
    """保存到JSONL"""
    try:
        # 保存币种快照
        snapshot_manager = GDriveJSONLManager(JSONL_DATA_DIR)
        snapshot_manager.append_snapshots(coin_snapshots)
        
        # 保存聚合数据
        aggregate_file = os.path.join(JSONL_DATA_DIR, 'crypto_aggregate.jsonl')
        os.makedirs(JSONL_DATA_DIR, exist_ok=True)
        with open(aggregate_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(aggregate_data, ensure_ascii=False) + '\n')
        
        return True
        
    except Exception as e:
        print(f"  ❌ 保存失败: {e}")
        return False

def main():
    """主函数"""
    print("="*80)
    print(f"🔄 批量回填 {TARGET_DATE} 的Google Drive数据")
    print("="*80)
    print()
    
    # 1. 获取所有文件
    files = get_all_txt_files()
    if not files:
        print("❌ 没有找到文件")
        return
    
    print()
    print(f"📊 开始处理 {len(files)} 个文件...")
    print()
    
    # 2. 批量处理
    success_count = 0
    skip_count = 0
    error_count = 0
    
    for i, file_info in enumerate(files, 1):
        filename = file_info['filename']
        time_part = file_info['time']
        snapshot_time = f"{TARGET_DATE} {time_part[:2]}:{time_part[2:]}:00"
        
        # 进度显示
        print(f"[{i:3d}/{len(files)}] {filename} ...", end=' ')
        
        # 检查是否已导入
        if check_if_imported(snapshot_time):
            print("✓ 已存在，跳过")
            skip_count += 1
            continue
        
        # 下载
        content = download_file(file_info['download_url'])
        if not content:
            print("✗ 下载失败")
            error_count += 1
            continue
        
        # 解析
        coin_snapshots, aggregate_data = parse_txt_content(content, snapshot_time)
        if not coin_snapshots or not aggregate_data:
            print("✗ 解析失败")
            error_count += 1
            continue
        
        # 保存
        if save_to_jsonl(coin_snapshots, aggregate_data):
            print(f"✓ 成功 ({len(coin_snapshots)} 币种)")
            success_count += 1
        else:
            print("✗ 保存失败")
            error_count += 1
        
        # 避免请求过快
        if i % 10 == 0:
            time.sleep(1)
    
    print()
    print("="*80)
    print("📊 处理完成统计")
    print("="*80)
    print(f"✅ 成功导入: {success_count} 个文件")
    print(f"⏭️  已存在跳过: {skip_count} 个文件")
    print(f"❌ 失败: {error_count} 个文件")
    print(f"📁 总计: {len(files)} 个文件")
    print("="*80)

if __name__ == '__main__':
    main()
