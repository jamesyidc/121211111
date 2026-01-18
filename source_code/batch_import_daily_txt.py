#!/usr/bin/env python3
"""
批量导入当天所有TXT文件数据
按照时间顺序将当天所有TXT文件的数据补充导入到数据库中
"""
import requests
import re
import sqlite3
from datetime import datetime
import pytz
import json
import sys
import time
from bs4 import BeautifulSoup

# 导入计次得分计算函数
from calculate_count_score import calculate_count_score

# 配置
DB_PATH = "/home/user/webapp/crypto_data.db"
CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message, prefix=""):
    """打印带时间戳的日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{prefix}[{timestamp}] {message}", flush=True)

def get_folder_config():
    """从配置文件读取文件夹信息"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config
    except Exception as e:
        log(f"❌ 无法读取配置文件: {e}")
        return None

def get_all_txt_files(folder_id, target_date):
    """获取指定文件夹中所有的TXT文件信息"""
    log(f"📂 正在扫描文件夹: {folder_id}")
    log(f"📅 目标日期: {target_date}")
    
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        file_list = []
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            filename = link.get_text(strip=True)
            
            # 检查是否是.txt文件
            if filename.endswith('.txt'):
                # 提取file ID
                if '/file/d/' in href:
                    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', href)
                    if match:
                        file_id = match.group(1)
                        
                        # 检查文件名格式: YYYY-MM-DD_HHMM.txt
                        time_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                        if time_match:
                            file_date = time_match.group(1)
                            time_str = time_match.group(2)
                            
                            # 只获取目标日期的文件
                            if file_date == target_date:
                                file_list.append({
                                    'filename': filename,
                                    'file_id': file_id,
                                    'date': file_date,
                                    'time': time_str,
                                    'sort_key': f"{file_date}_{time_str}"
                                })
        
        # 按时间排序
        file_list.sort(key=lambda x: x['sort_key'])
        
        log(f"✅ 找到 {len(file_list)} 个TXT文件")
        if file_list:
            log(f"   最早: {file_list[0]['filename']}")
            log(f"   最晚: {file_list[-1]['filename']}")
        
        return file_list
        
    except Exception as e:
        log(f"❌ 扫描文件夹失败: {e}")
        import traceback
        log(f"错误详情: {traceback.format_exc()}")
        return []

def download_txt_content(file_id):
    """下载TXT文件内容"""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except Exception as e:
        log(f"   ❌ 下载失败: {e}")
        return None

def parse_content(content):
    """解析TXT文件内容"""
    try:
        # 提取时间戳
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', content)
        if not timestamp_match:
            return None
        
        date_str, time_str = timestamp_match.groups()
        timestamp = f"{date_str} {time_str}"
        
        # 解析为datetime对象（只保留到分钟）
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        snapshot_time = dt.strftime('%Y-%m-%d %H:%M:00')
        snapshot_date = dt.strftime('%Y-%m-%d')
        
        # 提取急涨急跌数据（兼容新旧格式）
        rush_up_match = re.search(r'透明标签_急涨总和=急涨[:：](\d+)', content)
        if not rush_up_match:
            rush_up_match = re.search(r'本轮急涨.*?(\d+)/', content)
        
        rush_down_match = re.search(r'透明标签_急跌总和=急跌[:：](\d+)', content)
        if not rush_down_match:
            rush_down_match = re.search(r'本轮急跌.*?(\d+)/', content)
        
        rush_up = int(rush_up_match.group(1)) if rush_up_match else 0
        rush_down = int(rush_down_match.group(1)) if rush_down_match else 0
        
        # 提取计次和状态（兼容新旧格式）
        count_match = re.search(r'透明标签_计次=(\d+)', content)
        if not count_match:
            count_match = re.search(r'计次[:：](\d+)', content)
        
        status_match = re.search(r'透明标签_五种状态=状态[:：]([^\r\n]+)', content)
        if not status_match:
            status_match = re.search(r'[★☆]+\s*\|\s*([^\n]+)', content)
        
        count = int(count_match.group(1)) if count_match else 0
        status = status_match.group(1).strip() if status_match else ""
        
        # 自动计算计次得分
        count_score_display, count_score_type = calculate_count_score(snapshot_time, count)
        
        # 计算diff = rush_up - rush_down
        diff = rush_up - rush_down
        
        return {
            'snapshot_time': snapshot_time,
            'snapshot_date': snapshot_date,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': count,
            'status': status,
            'count_score_display': count_score_display,
            'count_score_type': count_score_type,
            'file_timestamp': timestamp
        }
        
    except Exception as e:
        log(f"   ❌ 解析内容失败: {e}")
        return None

def parse_coin_data(content):
    """解析币种详细数据"""
    try:
        coins = []
        lines = content.split('\n')
        
        # 查找币种数据区域（在[超级列表框_首页开始]之后）
        in_coin_section = False
        for line in lines:
            if '[超级列表框_首页开始]' in line:
                in_coin_section = True
                continue
            
            if '[超级列表框_首页结束]' in line:
                break
            
            if in_coin_section and '|' in line:
                parts = line.strip().split('|')
                if len(parts) >= 15:
                    try:
                        index = int(parts[0])
                        
                        # 解析最高占比和最低占比
                        ratio1_str = parts[14] if len(parts) > 14 else '0%'
                        ratio2_str = parts[15] if len(parts) > 15 else '0%'
                        
                        # 移除百分号并转换为浮点数
                        try:
                            max_ratio = float(ratio1_str.rstrip('%')) if ratio1_str else 0
                            min_ratio = float(ratio2_str.rstrip('%')) if ratio2_str else 0
                        except:
                            max_ratio = 0
                            min_ratio = 0
                        
                        # 根据最高占比和最低占比计算优先级等级
                        if max_ratio > 90 and min_ratio > 120:
                            priority_level = '等级1'
                        elif max_ratio > 80 and min_ratio > 120:
                            priority_level = '等级2'
                        elif max_ratio > 90 and min_ratio > 110:
                            priority_level = '等级3'
                        elif max_ratio > 70 and min_ratio > 120:
                            priority_level = '等级4'
                        elif max_ratio > 80 and min_ratio > 110:
                            priority_level = '等级5'
                        else:
                            priority_level = '等级6'
                        
                        coin = {
                            'index_order': index,
                            'symbol': parts[1],
                            'change': float(parts[2]) if parts[2] else 0,
                            'rush_up': int(parts[3]) if parts[3] else 0,
                            'rush_down': int(parts[4]) if parts[4] else 0,
                            'update_time': parts[5],
                            'high_price': float(parts[6]) if parts[6] else 0,
                            'high_time': parts[7],
                            'decline': float(parts[8]) if parts[8] else 0,
                            'change_24h': float(parts[9]) if parts[9] else 0,
                            'rank': int(parts[12]) if parts[12] else 0,
                            'current_price': float(parts[13]) if parts[13] else 0,
                            'ratio1': ratio1_str,
                            'ratio2': ratio2_str,
                            'priority_level': priority_level
                        }
                        coins.append(coin)
                    except (ValueError, IndexError):
                        continue
        
        return coins
        
    except Exception as e:
        log(f"   ❌ 解析币种数据失败: {e}")
        return []

def check_if_exists(cursor, snapshot_time):
    """检查数据是否已存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM crypto_snapshots 
        WHERE snapshot_time = ?
    """, (snapshot_time,))
    return cursor.fetchone()[0] > 0

def import_to_database(data, content, conn, cursor):
    """导入数据到数据库"""
    try:
        # 检查数据是否已存在
        if check_if_exists(cursor, data['snapshot_time']):
            return 'exists'
        
        # 验证数据有效性：rush_up和rush_down不能同时为0
        if data['rush_up'] == 0 and data['rush_down'] == 0:
            return 'invalid'
        
        # 插入新数据到crypto_snapshots
        cursor.execute("""
            INSERT INTO crypto_snapshots 
            (snapshot_time, snapshot_date, rush_up, rush_down, diff, count, status, count_score_display, count_score_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+8 hours'))
        """, (
            data['snapshot_time'],
            data['snapshot_date'],
            data['rush_up'],
            data['rush_down'],
            data['diff'],
            data['count'],
            data['status'],
            data['count_score_display'],
            data['count_score_type']
        ))
        
        # 获取刚插入的snapshot_id
        snapshot_id = cursor.lastrowid
        
        # 解析并导入币种数据
        coins = parse_coin_data(content)
        coin_count = 0
        
        if coins:
            for coin in coins:
                try:
                    cursor.execute("""
                        INSERT INTO crypto_coin_data 
                        (snapshot_id, snapshot_time, symbol, index_order, change, rush_up, rush_down, 
                         update_time, high_price, high_time, decline, change_24h, rank, current_price, 
                         ratio1, ratio2, priority_level, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+8 hours'))
                    """, (
                        snapshot_id,
                        data['snapshot_time'],
                        coin['symbol'],
                        coin['index_order'],
                        coin['change'],
                        coin['rush_up'],
                        coin['rush_down'],
                        coin['update_time'],
                        coin['high_price'],
                        coin['high_time'],
                        coin['decline'],
                        coin['change_24h'],
                        coin['rank'],
                        coin['current_price'],
                        coin['ratio1'],
                        coin['ratio2'],
                        coin['priority_level']
                    ))
                    coin_count += 1
                except:
                    continue
        
        conn.commit()
        return 'success'
        
    except Exception as e:
        log(f"   ❌ 数据库操作失败: {e}")
        return 'error'

def main():
    """主函数"""
    log("")
    log("=" * 80)
    log("🚀 批量导入当天所有TXT文件数据")
    log("=" * 80)
    log("")
    
    # 读取配置
    config = get_folder_config()
    if not config:
        log("❌ 无法读取配置文件，退出")
        return
    
    folder_id = config.get('folder_id')
    target_date = config.get('current_date')
    
    if not folder_id or not target_date:
        log("❌ 配置文件缺少必要信息，退出")
        return
    
    log(f"📂 文件夹ID: {folder_id}")
    log(f"📅 目标日期: {target_date}")
    log("")
    
    # 获取所有TXT文件
    log("步骤1: 扫描文件夹中的所有TXT文件...")
    file_list = get_all_txt_files(folder_id, target_date)
    
    if not file_list:
        log("❌ 未找到任何TXT文件")
        return
    
    log("")
    log(f"✅ 共找到 {len(file_list)} 个文件")
    log("")
    
    # 连接数据库
    log("步骤2: 连接数据库...")
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        log(f"✅ 数据库连接成功: {DB_PATH}")
    except Exception as e:
        log(f"❌ 数据库连接失败: {e}")
        return
    
    log("")
    log("步骤3: 开始批量导入...")
    log("=" * 80)
    log("")
    
    # 统计
    total = len(file_list)
    success_count = 0
    exists_count = 0
    invalid_count = 0
    error_count = 0
    
    # 逐个处理文件
    for idx, file_info in enumerate(file_list, 1):
        filename = file_info['filename']
        file_id = file_info['file_id']
        
        log(f"[{idx}/{total}] 处理: {filename}")
        
        # 下载内容
        content = download_txt_content(file_id)
        if not content:
            log(f"   ❌ 下载失败，跳过")
            error_count += 1
            continue
        
        # 解析内容
        data = parse_content(content)
        if not data:
            log(f"   ❌ 解析失败，跳过")
            error_count += 1
            continue
        
        # 导入数据库
        result = import_to_database(data, content, conn, cursor)
        
        if result == 'success':
            log(f"   ✅ 成功导入: {data['snapshot_time']} | 急涨:{data['rush_up']} 急跌:{data['rush_down']} | 计次:{data['count']} {data['count_score_display']}")
            success_count += 1
        elif result == 'exists':
            log(f"   ℹ️  已存在: {data['snapshot_time']}")
            exists_count += 1
        elif result == 'invalid':
            log(f"   ⚠️  无效数据: {data['snapshot_time']} (急涨和急跌均为0)")
            invalid_count += 1
        else:
            log(f"   ❌ 导入失败")
            error_count += 1
        
        log("")
        
        # 每处理10个文件休息0.5秒，避免请求过快
        if idx % 10 == 0:
            time.sleep(0.5)
    
    # 关闭数据库
    conn.close()
    
    # 输出统计结果
    log("=" * 80)
    log("📊 批量导入完成！")
    log("=" * 80)
    log("")
    log(f"📈 统计结果:")
    log(f"   总文件数: {total}")
    log(f"   ✅ 成功导入: {success_count}")
    log(f"   ℹ️  已存在: {exists_count}")
    log(f"   ⚠️  无效数据: {invalid_count}")
    log(f"   ❌ 失败: {error_count}")
    log("")
    
    if success_count > 0:
        log(f"🎉 成功补充导入 {success_count} 条新数据到数据库！")
    else:
        log(f"ℹ️  所有数据均已存在，无需导入")
    
    log("")
    log("=" * 80)

if __name__ == '__main__':
    main()
