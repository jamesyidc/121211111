#!/usr/bin/env python3
"""
批量导入今天所有 TXT 文件到 crypto_snapshots 数据库
"""

import requests
import re
import sqlite3
from datetime import datetime
import pytz
import sys

# 配置
FOLDER_ID = "1sCHpLo3BdxjXmeW9mo30Gijpzkux0eNm"
TODAY_STR = "2026-01-05"
DB_PATH = "/home/user/webapp/databases/crypto_data.db"

def log_message(msg):
    """输出日志消息"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    timestamp = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")
    sys.stdout.flush()

def get_today_files():
    """获取今天所有的 TXT 文件"""
    log_message("📂 获取今天的 TXT 文件列表...")
    
    url = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}"
    response = requests.get(url, timeout=15)
    content = response.text
    
    # 查找所有 TXT 文件
    entries = re.findall(r'id="entry-([A-Za-z0-9_-]+)".*?<div class="flip-entry-title">([^<]+)</div>', content, re.DOTALL)
    
    # 筛选今天的 TXT 文件
    today_files = []
    for file_id, filename in entries:
        if filename.endswith('.txt') and TODAY_STR in filename:
            today_files.append((filename, file_id))
    
    # 按时间排序
    today_files.sort()
    
    log_message(f"✅ 找到 {len(today_files)} 个文件")
    return today_files

def download_txt_file(file_id, filename):
    """下载 TXT 文件内容"""
    try:
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, timeout=30)
        
        if response.status_code == 200:
            return response.text, None
        else:
            return None, f"HTTP {response.status_code}"
    except Exception as e:
        return None, str(e)

def parse_txt_content(content, snapshot_time):
    """解析 TXT 文件内容"""
    try:
        records = []
        lines = content.strip().split('\n')
        
        # 找到数据开始标记
        start_index = -1
        for i, line in enumerate(lines):
            if '[超级列表框_首页开始]' in line or '[超级列表框_首页开始]' in line.strip('\r'):
                start_index = i + 1
                break
        
        if start_index == -1:
            start_index = 0
        
        # 解析每一行
        for line in lines[start_index:]:
            line = line.strip().strip('\r')
            
            if not line or line.startswith('#') or line.startswith('透明标签') or '[' in line:
                continue
            
            # 使用管道符分割
            parts = line.split('|')
            
            if len(parts) >= 14:
                try:
                    inst_id = parts[1].strip()
                    if not inst_id:
                        continue
                    
                    # 添加USDT后缀
                    if not inst_id.endswith('USDT'):
                        inst_id = f"{inst_id}USDT"
                    
                    rush_up = int(parts[3].strip()) if parts[3].strip() else 0
                    rush_down = int(parts[4].strip()) if parts[4].strip() else 0
                    last_price = float(parts[6].strip())
                    change_24h = float(parts[8].strip())
                    vol_24h = float(parts[13].strip())
                    count = int(parts[12].strip()) if parts[12].strip() else 0
                    
                    diff = rush_up - rush_down
                    
                    if diff > 0:
                        status = '上涨'
                    elif diff < 0:
                        status = '下跌'
                    else:
                        status = '震荡'
                    
                    record = {
                        'inst_id': inst_id,
                        'last_price': last_price,
                        'rush_up': rush_up,
                        'rush_down': rush_down,
                        'diff': diff,
                        'count': count,
                        'status': status,
                        'vol_24h': vol_24h,
                        'change_24h': change_24h,
                        'snapshot_time': snapshot_time,
                        'snapshot_date': snapshot_time.split()[0]
                    }
                    records.append(record)
                    
                except (ValueError, IndexError):
                    continue
        
        return records, None
    except Exception as e:
        return [], str(e)

def save_to_database(records):
    """保存数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        inserted = 0
        skipped = 0
        
        for record in records:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO crypto_snapshots 
                    (snapshot_date, snapshot_time, inst_id, last_price, vol_24h,
                     rush_up, rush_down, diff, count, status, change_24h)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['snapshot_date'], record['snapshot_time'], record['inst_id'],
                    record['last_price'], record['vol_24h'], record['rush_up'],
                    record['rush_down'], record['diff'], record['count'],
                    record['status'], record.get('change_24h', 0)
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
            except Exception as e:
                log_message(f"  ⚠️ 插入失败 {record['inst_id']}: {e}")
        
        conn.commit()
        conn.close()
        
        return inserted, skipped, None
    except Exception as e:
        return 0, 0, str(e)

def main():
    """主函数"""
    log_message("=" * 60)
    log_message("🚀 开始批量导入今天所有 TXT 文件")
    log_message("=" * 60)
    
    # 获取文件列表
    try:
        files = get_today_files()
    except Exception as e:
        log_message(f"❌ 获取文件列表失败: {e}")
        return
    
    if not files:
        log_message("⚠️ 没有找到文件")
        return
    
    # 统计
    total_files = len(files)
    processed_files = 0
    failed_files = 0
    total_records = 0
    total_inserted = 0
    total_skipped = 0
    
    log_message(f"\n开始处理 {total_files} 个文件...")
    log_message("")
    
    # 处理每个文件
    for i, (filename, file_id) in enumerate(files, 1):
        log_message(f"[{i}/{total_files}] 📥 处理: {filename}")
        
        # 从文件名提取时间
        # 格式: 2026-01-05_1538.txt -> 2026-01-05 15:38:00
        try:
            date_part, time_part = filename.replace('.txt', '').split('_')
            hour = time_part[:2]
            minute = time_part[2:]
            snapshot_time = f"{date_part} {hour}:{minute}:00"
        except:
            log_message(f"  ⚠️ 无法解析时间，跳过")
            failed_files += 1
            continue
        
        # 下载文件
        content, error = download_txt_file(file_id, filename)
        if error:
            log_message(f"  ❌ 下载失败: {error}")
            failed_files += 1
            continue
        
        # 解析内容
        records, error = parse_txt_content(content, snapshot_time)
        if error:
            log_message(f"  ❌ 解析失败: {error}")
            failed_files += 1
            continue
        
        if not records:
            log_message(f"  ⚠️ 没有解析到数据")
            failed_files += 1
            continue
        
        # 保存到数据库
        inserted, skipped, error = save_to_database(records)
        if error:
            log_message(f"  ❌ 保存失败: {error}")
            failed_files += 1
            continue
        
        processed_files += 1
        total_records += len(records)
        total_inserted += inserted
        total_skipped += skipped
        
        log_message(f"  ✅ 完成: {len(records)} 条记录，插入 {inserted} 条，跳过 {skipped} 条")
    
    # 最终统计
    log_message("")
    log_message("=" * 60)
    log_message("📊 导入完成")
    log_message("=" * 60)
    log_message(f"总文件数: {total_files}")
    log_message(f"成功处理: {processed_files}")
    log_message(f"失败: {failed_files}")
    log_message(f"总记录数: {total_records}")
    log_message(f"插入记录: {total_inserted}")
    log_message(f"跳过记录: {total_skipped}")
    log_message("=" * 60)

if __name__ == "__main__":
    main()
