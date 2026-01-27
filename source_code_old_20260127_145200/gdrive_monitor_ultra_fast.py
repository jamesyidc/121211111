#!/usr/bin/env python3
"""
Google Drive TXT文件超快速监控器
每30秒检查一次，确保第一时间检测到新文件
"""
import time
import requests
import re
import sqlite3
from datetime import datetime
import pytz
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/gdrive_monitor_ultra_fast.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 配置
FILE_ID = "1eyYiU6lU8n7SwWUvFtm_kUIvaZI0SO4U"
DB_PATH = '/home/user/webapp/crypto_data.db'
CHECK_INTERVAL = 30  # 30秒检查一次
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def download_latest_file():
    """下载最新文件内容"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={FILE_ID}"
        
        # 添加防缓存header
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"下载失败: HTTP {response.status_code}")
            return None
        
        content = response.text
        
        # 验证内容
        if '透明标签' not in content or 'BTC' not in content:
            logger.error("文件内容无效")
            return None
        
        return content
        
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return None

def parse_data(content):
    """解析TXT文件数据"""
    try:
        # 提取时间戳
        timestamps = re.findall(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', content)
        if not timestamps:
            logger.error("未找到时间戳")
            return None
        
        date_str, time_str = timestamps[0]
        hour = int(time_str.split(':')[0])
        minute = int(time_str.split(':')[1])
        snapshot_time = f"{date_str} {hour:02d}:{minute:02d}:00"
        
        # 提取数据
        rush_up = int(re.search(r'急涨：(\d+)', content).group(1))
        rush_down = int(re.search(r'急跌：(\d+)', content).group(1))
        count = int(re.search(r'透明标签_计次=(\d+)', content).group(1))
        status_match = re.search(r'透明标签_五种状态=(.+)', content)
        status = status_match.group(1).strip().replace('状态：', '').split('\r')[0] if status_match else '未知'
        
        # 计算计次得分
        if hour >= 18:  # 18:00-23:59
            if count <= 3:
                count_score_display = "★★★★★"
            elif count <= 5:
                count_score_display = "★★★★"
            elif count <= 8:
                count_score_display = "★★★"
            elif count <= 12:
                count_score_display = "★★"
            elif count <= 20:
                count_score_display = "★"
            else:
                count_score_display = "---"
        else:  # Before 18:00
            if count <= 10:
                count_score_display = "☆---"
            elif count <= 20:
                count_score_display = "☆☆"
            elif count <= 30:
                count_score_display = "☆☆☆"
            else:
                count_score_display = "---"
        
        return {
            'snapshot_time': snapshot_time,
            'snapshot_date': date_str,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'count_score_display': count_score_display,
            'status': status
        }
        
    except Exception as e:
        logger.error(f"解析失败: {e}")
        return None

def import_to_database(data):
    """导入数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("SELECT id FROM crypto_snapshots WHERE snapshot_time = ?", 
                      (data['snapshot_time'],))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE crypto_snapshots SET
                    rush_up = ?, rush_down = ?,
                    count = ?, count_score_display = ?,
                    status = ?
                WHERE snapshot_time = ?
            """, (data['rush_up'], data['rush_down'],
                  data['count'], data['count_score_display'],
                  data['status'], data['snapshot_time']))
            
            logger.info(f"更新: {data['snapshot_time']}")
            return False  # 不是新数据
        else:
            # 插入新记录
            cursor.execute("""
                INSERT INTO crypto_snapshots 
                (snapshot_time, snapshot_date, rush_up, rush_down, 
                 count, count_score_display, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data['snapshot_time'], data['snapshot_date'],
                  data['rush_up'], data['rush_down'],
                  data['count'], data['count_score_display'],
                  data['status']))
            
            logger.info(f"🎉 新数据! {data['snapshot_time']} | 计次:{data['count']} {data['count_score_display']} | {data['status']}")
            conn.commit()
            conn.close()
            return True  # 是新数据
        
        conn.commit()
        conn.close()
        return False
        
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        return False

def check_and_import():
    """检查并导入最新数据"""
    now = datetime.now(BEIJING_TZ)
    
    # 1. 下载
    content = download_latest_file()
    if not content:
        return False
    
    # 2. 解析
    data = parse_data(content)
    if not data:
        return False
    
    # 计算延迟
    file_time = BEIJING_TZ.localize(datetime.strptime(data['snapshot_time'], '%Y-%m-%d %H:%M:%S'))
    delay = (now - file_time).total_seconds() / 60
    
    # 3. 导入
    is_new = import_to_database(data)
    
    if is_new:
        logger.info(f"✓ 新数据已导入!")
    else:
        if delay > 20:
            logger.warning(f"⏰ 数据延迟 {delay:.0f} 分钟 (最新: {data['snapshot_time']})")
    
    return is_new

def main():
    """主循环"""
    logger.info("="*60)
    logger.info("🚀 Google Drive 超快速监控器启动")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info(f"文件ID: {FILE_ID}")
    logger.info(f"数据库: {DB_PATH}")
    logger.info("="*60)
    
    # 立即执行第一次检查
    check_and_import()
    
    # 循环检查
    check_count = 1
    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            check_count += 1
            
            logger.info(f"[检查 #{check_count}] {datetime.now(BEIJING_TZ).strftime('%H:%M:%S')}")
            check_and_import()
            
        except KeyboardInterrupt:
            logger.info("\n收到停止信号,正在退出...")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()
