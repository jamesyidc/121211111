#!/usr/bin/env python3
"""
Google Drive TXT文件智能检测器 - 完整版
使用嵌入式视图方法，下载TXT后解析并写入JSONL
每30秒检测一次，自动导入最新TXT文件
"""
import requests
import re
import time
import json
from datetime import datetime
import pytz
import sys
import os

# 添加路径
sys.path.insert(0, '/home/user/webapp/source_code')
sys.path.insert(0, '/home/user/webapp')

from gdrive_jsonl_manager import GDriveJSONLManager

# 配置
HOME_DATA_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'  # 首页数据文件夹ID
CHECK_INTERVAL = 30  # 检测间隔（秒）
TIMEOUT_THRESHOLD = 11 * 60  # 超时阈值（秒）= 11分钟
LOG_FILE = "/home/user/webapp/logs/gdrive_final_detector.log"
JSONL_DATA_DIR = "/home/user/webapp/data/gdrive_jsonl"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message):
    """写入日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass

def get_date_folder_id(parent_folder_id, target_date):
    """从父文件夹中获取指定日期文件夹的ID"""
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}#list"
        response = requests.get(embed_url, timeout=30)
        html = response.text
        
        # 查找所有<a>标签
        a_tags = re.findall(r'<a[^>]+>.*?</a>', html, re.DOTALL)
        
        for tag in a_tags:
            if target_date in tag:
                # 提取href中的文件夹ID
                href_match = re.search(r'href="https://drive\.google\.com/drive/folders/([a-zA-Z0-9_-]{33})"', tag)
                if href_match:
                    folder_id = href_match.group(1)
                    log(f"✅ 找到 {target_date} 文件夹ID: {folder_id}")
                    return folder_id
        
        log(f"❌ 未找到 {target_date} 文件夹")
        return None
        
    except Exception as e:
        log(f"❌ 获取日期文件夹ID失败: {e}")
        return None

def get_txt_files_from_folder(folder_id, target_date):
    """从文件夹中获取所有TXT文件列表"""
    try:
        embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
        response = requests.get(embed_url, timeout=30)
        html = response.text
        
        # 查找所有TXT文件名
        txt_pattern = rf'({re.escape(target_date)}_\d{{4}})\.txt'
        txt_files = re.findall(txt_pattern, html)
        unique_files = sorted(set(txt_files), reverse=True)
        
        if not unique_files:
            log(f"❌ 未找到TXT文件")
            return []
        
        log(f"✅ 找到 {len(unique_files)} 个TXT文件")
        
        # 获取每个文件的ID和下载链接
        files_info = []
        for filename in unique_files:
            # 在HTML中查找文件名附近的ID
            file_pattern = rf'{re.escape(filename)}\.txt.*?href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]{{33}})'
            matches = re.findall(file_pattern, html, re.DOTALL)
            
            if not matches:
                # 备用方案：查找任何包含文件名的链接
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
        
        return files_info
        
    except Exception as e:
        log(f"❌ 获取TXT文件列表失败: {e}")
        return []

def check_if_imported_jsonl(snapshot_time):
    """检查JSONL中是否已导入该时间点的数据"""
    try:
        manager = GDriveJSONLManager(JSONL_DATA_DIR)
        snapshots = manager.get_snapshots_by_time(snapshot_time)
        return len(snapshots) > 0
    except Exception as e:
        log(f"❌ 检查失败: {e}")
        return False

def download_file(url):
    """下载文件"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        log(f"❌ 下载失败: {e}")
        return None

def parse_txt_content(content, snapshot_time):
    """解析TXT内容，返回币种快照列表和聚合数据"""
    try:
        # 解码内容
        content_str = content.decode('gbk', errors='ignore') if isinstance(content, bytes) else content
        
        if not content_str or len(content_str) < 100:
            log(f"❌ 文件内容无效或太短")
            return None, None
        
        lines = content_str.split('\n')
        
        # 提取聚合数据（前面的标签行）
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
                        
                        # 解析各字段
                        change_24h = float(parts[2]) if parts[2].strip() else 0.0
                        rush_up = int(parts[3]) if parts[3].strip() else 0
                        rush_down = int(parts[4]) if parts[4].strip() else 0
                        last_price = float(parts[6]) if parts[6].strip() else 0.0
                        high_24h_date = parts[7].strip() if len(parts) > 7 else ''
                        count_value = int(parts[12]) if len(parts) > 12 and parts[12].strip() else 0
                        
                        # 创建快照记录
                        coin_snapshot = {
                            'snapshot_date': snapshot_date,
                            'snapshot_time': snapshot_time,
                            'inst_id': inst_id,
                            'last_price': last_price,
                            'change_24h': change_24h,
                            'rush_up': rush_up,
                            'rush_down': rush_down,
                            'high_24h_date': high_24h_date,
                            'count': count_value,
                            'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        coin_snapshots.append(coin_snapshot)
                        
                    except (ValueError, IndexError) as e:
                        log(f"⚠️  解析行失败: {line[:50]}... - {e}")
                        continue
        
        if not coin_snapshots:
            log(f"❌ 未解析到币种数据")
            return None, None
        
        # 创建聚合数据
        # 注意：count 字段来自"透明标签_计次"标签，不是币种累加
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
            'count': count,  # 来自"透明标签_计次"
            'count_score': count_score,
            'count_score_display': count_score,
            'price_lowest': price_lowest,
            'price_newhigh': price_newhigh,
            'fall_24h_count': fall_24h_count,
            'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        log(f"✅ 解析成功: {len(coin_snapshots)} 个币种, 急涨={rush_up_total}, 急跌={rush_down_total}, 计次={count}")
        
        return coin_snapshots, aggregate_data
        
    except Exception as e:
        log(f"❌ 解析TXT失败: {e}")
        import traceback
        log(traceback.format_exc())
        return None, None

def save_to_jsonl(coin_snapshots, aggregate_data):
    """保存到JSONL文件"""
    try:
        # 保存币种快照
        snapshot_manager = GDriveJSONLManager(JSONL_DATA_DIR)
        snapshot_manager.append_snapshots(coin_snapshots)
        
        # 保存聚合数据到单独的JSONL文件
        aggregate_file = os.path.join(JSONL_DATA_DIR, 'crypto_aggregate.jsonl')
        os.makedirs(JSONL_DATA_DIR, exist_ok=True)
        with open(aggregate_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(aggregate_data, ensure_ascii=False) + '\n')
        
        log(f"✅ 已保存到JSONL: {len(coin_snapshots)} 个币种快照 + 1 条聚合数据")
        return True
        
    except Exception as e:
        log(f"❌ 保存JSONL失败: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def main_loop():
    """主循环"""
    log("=" * 80)
    log("🚀 Google Drive TXT文件智能检测器启动 (完整版 - 支持JSONL)")
    log(f"📂 首页数据文件夹ID: {HOME_DATA_FOLDER_ID}")
    log(f"📁 JSONL数据目录: {JSONL_DATA_DIR}")
    log(f"⏱️  检测间隔: {CHECK_INTERVAL}秒")
    log(f"⏰ 超时阈值: {TIMEOUT_THRESHOLD}秒")
    log("=" * 80)
    
    last_imported_file = None
    last_check_time = None
    
    while True:
        try:
            now = datetime.now(BEIJING_TZ)
            today = now.strftime('%Y-%m-%d')
            
            log("")
            log("-" * 80)
            log(f"🔍 开始检测... ({now.strftime('%Y-%m-%d %H:%M:%S')})")
            
            # 1. 获取今天的文件夹ID
            date_folder_id = get_date_folder_id(HOME_DATA_FOLDER_ID, today)
            if not date_folder_id:
                log(f"⚠️  未找到今天的文件夹，{CHECK_INTERVAL}秒后重试...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 2. 获取文件夹中的TXT文件列表
            txt_files = get_txt_files_from_folder(date_folder_id, today)
            if not txt_files:
                log(f"⚠️  未找到TXT文件，{CHECK_INTERVAL}秒后重试...")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # 3. 获取最新文件
            latest_file = txt_files[0]
            filename = latest_file['filename']
            
            log(f"📄 最新文件: {filename}")
            
            # 4. 检查是否是新文件
            if last_imported_file == filename:
                log(f"✅ 文件未更新，无需重复导入")
            else:
                # 解析时间
                match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                if match:
                    date_part = match.group(1)
                    time_part = match.group(2)
                    snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
                    
                    # 检查是否已导入到JSONL
                    if check_if_imported_jsonl(snapshot_time):
                        log(f"✅ 文件已导入JSONL: {filename}")
                        last_imported_file = filename
                    else:
                        log(f"📥 开始下载新文件: {filename}")
                        content = download_file(latest_file['download_url'])
                        
                        if content:
                            log(f"✅ 下载成功，大小: {len(content)} 字节")
                            
                            # 解析内容
                            coin_snapshots, aggregate_data = parse_txt_content(content, snapshot_time)
                            
                            if coin_snapshots and aggregate_data:
                                # 保存到JSONL
                                if save_to_jsonl(coin_snapshots, aggregate_data):
                                    log(f"✅ 导入成功: {filename}")
                                    last_imported_file = filename
                                else:
                                    log(f"❌ 导入失败: {filename}")
                            else:
                                log(f"❌ 解析失败: {filename}")
            
            # 5. 检查超时
            if last_check_time:
                elapsed = (now - last_check_time).total_seconds()
                if elapsed > TIMEOUT_THRESHOLD:
                    log(f"⚠️  警告：距离上次检测已过 {elapsed/60:.1f} 分钟")
            
            last_check_time = now
            
            # 6. 等待下次检测
            log(f"⏳ {CHECK_INTERVAL}秒后进行下次检测...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            log("")
            log("⚠️  收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 检测过程出错: {e}")
            import traceback
            log(traceback.format_exc())
            log(f"⏳ 60秒后重试...")
            time.sleep(60)

if __name__ == '__main__':
    main_loop()
