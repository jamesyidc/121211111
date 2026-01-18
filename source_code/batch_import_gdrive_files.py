#!/usr/bin/env python3
"""
批量导入Google Drive历史TXT文件到数据库
用于补充缺失的历史数据
"""
import requests
import re
import sqlite3
from datetime import datetime
import pytz
import json
import sys

# 从gdrive_final_detector导入必要函数
from calculate_count_score import calculate_count_score

# 配置
DB_PATH = "/home/user/webapp/crypto_data.db"
CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(msg):
    """打印日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)

def get_folder_id_for_date(date_str):
    """获取指定日期的文件夹ID"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 检查配置中的日期是否匹配
            if config.get('current_date') == date_str:
                return config.get('folder_id')
            # 如果不匹配，返回None
            return None
    except Exception as e:
        log(f"❌ 读取配置文件失败: {e}")
        return None

def list_txt_files_in_folder(folder_id):
    """列出文件夹中的所有TXT文件"""
    try:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return []
        
        # 提取文件ID和名称
        pattern = r'\["([\w-]+)","([^"]+\.txt)"'
        matches = re.findall(pattern, response.text)
        
        files = []
        for file_id, filename in matches:
            if filename.endswith('.txt') and '2025-12-' in filename:
                files.append({'id': file_id, 'name': filename})
        
        return sorted(files, key=lambda x: x['name'])
    
    except Exception as e:
        log(f"❌ 列出文件失败: {e}")
        return []

def download_file_content(file_id):
    """下载文件内容"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return response.text
        else:
            return None
    
    except Exception as e:
        log(f"❌ 下载文件失败: {e}")
        return None

def parse_content(content, file_timestamp=None):
    """解析TXT文件内容"""
    try:
        data = {}
        
        # 提取快照时间
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        if time_match:
            data['snapshot_time'] = time_match.group(1)
        elif file_timestamp:
            data['snapshot_time'] = file_timestamp
        else:
            return None
        
        # 提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', data['snapshot_time'])
        if date_match:
            data['snapshot_date'] = date_match.group(1)
        else:
            return None
        
        # 提取急涨急跌数据
        rush_up_match = re.search(r'本轮急涨数量[:：]\s*(\d+)', content)
        rush_down_match = re.search(r'本轮急跌数量[:：]\s*(\d+)', content)
        
        data['rush_up'] = int(rush_up_match.group(1)) if rush_up_match else 0
        data['rush_down'] = int(rush_down_match.group(1)) if rush_down_match else 0
        data['diff'] = data['rush_up'] - data['rush_down']
        
        # 提取计次
        count_match = re.search(r'本轮计次[:：]\s*(\d+)', content)
        data['count'] = int(count_match.group(1)) if count_match else 0
        
        # 计算计次得分
        score_result = calculate_count_score(data['count'])
        data['count_score_display'] = score_result['display']
        data['count_score_type'] = score_result['type']
        
        # 提取状态
        status_match = re.search(r'本轮状态[:：]\s*([^\n]+)', content)
        data['status'] = status_match.group(1).strip() if status_match else '震荡无序'
        
        return data
    
    except Exception as e:
        log(f"❌ 解析内容失败: {e}")
        return None

def parse_coin_data(content):
    """解析币种数据"""
    try:
        coins = []
        
        # 查找表格数据
        lines = content.split('\n')
        in_table = False
        index_order = 1
        
        for line in lines:
            line = line.strip()
            
            # 跳过空行和分隔线
            if not line or line.startswith('---') or line.startswith('==='):
                continue
            
            # 检测表格开始
            if '|' in line and ('币种' in line or 'symbol' in line.lower()):
                in_table = True
                continue
            
            # 解析表格行
            if in_table and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                parts = [p for p in parts if p]  # 移除空字符串
                
                if len(parts) >= 4:
                    try:
                        symbol = parts[0]
                        change = float(parts[1].replace('%', '').strip())
                        rush_up = int(parts[2]) if parts[2].isdigit() else 0
                        rush_down = int(parts[3]) if parts[3].isdigit() else 0
                        
                        # 构建币种数据
                        coin = {
                            'symbol': symbol,
                            'index_order': index_order,
                            'change': change,
                            'rush_up': rush_up,
                            'rush_down': rush_down,
                            'update_time': '',
                            'high_price': 0.0,
                            'high_time': '',
                            'decline': 0.0,
                            'change_24h': 0.0,
                            'rank': 0,
                            'current_price': 0.0,
                            'ratio1': 0.0,
                            'ratio2': 0.0,
                            'priority_level': 0
                        }
                        
                        coins.append(coin)
                        index_order += 1
                    
                    except (ValueError, IndexError):
                        continue
        
        return coins
    
    except Exception as e:
        log(f"❌ 解析币种数据失败: {e}")
        return []

def check_exists(cursor, snapshot_time):
    """检查数据是否已存在"""
    cursor.execute("""
        SELECT COUNT(*) FROM crypto_snapshots 
        WHERE snapshot_time = ?
    """, (snapshot_time,))
    return cursor.fetchone()[0] > 0

def import_file_to_database(file_info, folder_id):
    """导入单个文件到数据库"""
    try:
        # 下载文件内容
        content = download_file_content(file_info['id'])
        if not content:
            log(f"   ❌ 无法下载文件: {file_info['name']}")
            return False
        
        # 解析文件内容
        data = parse_content(content)
        if not data:
            log(f"   ❌ 无法解析文件: {file_info['name']}")
            return False
        
        # 连接数据库
        conn = sqlite3.connect(DB_PATH, timeout=30)
        cursor = conn.cursor()
        
        # 检查是否已存在
        if check_exists(cursor, data['snapshot_time']):
            log(f"   ℹ️  数据已存在: {data['snapshot_time']}")
            conn.close()
            return False
        
        # 插入快照数据
        cursor.execute("""
            INSERT INTO crypto_snapshots 
            (snapshot_time, snapshot_date, rush_up, rush_down, diff, count, status, 
             count_score_display, count_score_type, created_at)
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
        
        snapshot_id = cursor.lastrowid
        
        # 解析并插入币种数据
        coins = parse_coin_data(content)
        for coin in coins:
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
        
        conn.commit()
        conn.close()
        
        log(f"   ✅ 成功导入: {data['snapshot_time']} ({len(coins)} 个币种)")
        return True
    
    except Exception as e:
        log(f"   ❌ 导入失败: {e}")
        return False

def batch_import_date(date_str):
    """批量导入指定日期的所有文件"""
    log(f"\n{'='*80}")
    log(f"📅 开始处理日期: {date_str}")
    log(f"{'='*80}")
    
    # 获取文件夹ID
    folder_id = get_folder_id_for_date(date_str)
    if not folder_id:
        log(f"❌ 未找到日期 {date_str} 的文件夹配置")
        return 0
    
    log(f"📂 文件夹ID: {folder_id}")
    
    # 列出所有TXT文件
    files = list_txt_files_in_folder(folder_id)
    if not files:
        log(f"❌ 未找到任何TXT文件")
        return 0
    
    log(f"📄 找到 {len(files)} 个TXT文件")
    
    # 逐个导入
    success_count = 0
    for i, file_info in enumerate(files, 1):
        log(f"\n[{i}/{len(files)}] 处理文件: {file_info['name']}")
        if import_file_to_database(file_info, folder_id):
            success_count += 1
    
    log(f"\n{'='*80}")
    log(f"✅ 完成! 成功导入 {success_count}/{len(files)} 个文件")
    log(f"{'='*80}\n")
    
    return success_count

if __name__ == "__main__":
    log("🚀 批量导入工具启动")
    log("="*80)
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        log("用法: python3 batch_import_gdrive_files.py <日期>")
        log("示例: python3 batch_import_gdrive_files.py 2025-12-26")
        sys.exit(1)
    
    date_str = sys.argv[1]
    
    # 验证日期格式
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        log(f"❌ 无效的日期格式: {date_str}")
        log("正确格式: YYYY-MM-DD (例如: 2025-12-26)")
        sys.exit(1)
    
    # 执行批量导入
    total = batch_import_date(date_str)
    
    log(f"\n🎉 批量导入完成! 共导入 {total} 条记录")
