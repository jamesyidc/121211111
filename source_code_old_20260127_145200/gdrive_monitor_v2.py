#!/usr/bin/env python3
"""
Google Drive TXT文件监控器 V2
动态查找共享文件夹中的最新文件并自动导入
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
        logging.FileHandler('/home/user/webapp/gdrive_monitor_v2.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 配置
FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 共享文件夹
DB_PATH = '/home/user/webapp/crypto_data.db'
CHECK_INTERVAL = 300  # 5分钟 (更频繁检查)
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_latest_filename():
    """获取当前时间对应的最新文件名"""
    now = datetime.now(BEIJING_TZ)
    date_str = now.strftime('%Y-%m-%d')
    
    # 计算最近的10分钟整数倍时间
    minute = (now.minute // 10) * 10
    time_str = f"{now.hour:02d}{minute:02d}"
    
    filename = f"{date_str}_{time_str}.txt"
    logger.info(f"目标文件名: {filename}")
    return filename

def find_file_in_folder(filename):
    """在共享文件夹中查找文件并获取下载链接"""
    try:
        folder_url = f"https://drive.google.com/embeddedfolderview?id={FOLDER_ID}"
        logger.info(f"检查文件夹: {folder_url}")
        
        response = requests.get(folder_url, timeout=30)
        if response.status_code != 200:
            logger.error(f"无法访问文件夹: HTTP {response.status_code}")
            return None
        
        content = response.text
        
        # 检查文件是否存在
        if filename not in content:
            logger.warning(f"文件夹中未找到文件: {filename}")
            return None
        
        logger.info(f"✓ 找到文件: {filename}")
        
        # 尝试提取文件ID (使用多种模式)
        patterns = [
            rf'uc\?id=([a-zA-Z0-9_-]+).*?{re.escape(filename)}',
            rf'{re.escape(filename)}.*?uc\?id=([a-zA-Z0-9_-]+)',
            rf'id=([a-zA-Z0-9_-]+).*?{re.escape(filename)}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            if matches:
                file_id = matches[0]
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                logger.info(f"✓ 找到文件ID: {file_id}")
                return download_url
        
        logger.warning(f"无法提取文件ID: {filename}")
        return None
        
    except Exception as e:
        logger.error(f"查找文件失败: {e}")
        return None

def download_file_content(url):
    """下载文件内容"""
    try:
        logger.info(f"正在下载: {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"下载失败: HTTP {response.status_code}")
            return None
        
        content = response.text
        
        # 验证内容
        if '透明标签' not in content or 'BTC' not in content:
            logger.error("文件内容无效")
            return None
        
        logger.info(f"✓ 下载成功: {len(response.content)} 字节")
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
        
        data = {
            'snapshot_time': snapshot_time,
            'snapshot_date': date_str,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'count_score_display': count_score_display,
            'status': status
        }
        
        logger.info(f"✓ 解析成功: {snapshot_time} | 计次:{count} {count_score_display} | {status}")
        return data
        
    except Exception as e:
        logger.error(f"解析失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
            
            logger.info(f"✓ 更新记录: {data['snapshot_time']}")
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
            
            logger.info(f"✓ 插入新记录: {data['snapshot_time']}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_and_import():
    """检查并导入最新数据"""
    logger.info("="*60)
    logger.info(f"开始检查新数据... [北京时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}]")
    
    # 1. 确定文件名
    filename = get_latest_filename()
    
    # 2. 查找文件
    download_url = find_file_in_folder(filename)
    if not download_url:
        logger.warning(f"未找到文件: {filename}")
        # 尝试前一个时间点的文件
        now = datetime.now(BEIJING_TZ)
        prev_minute = ((now.minute - 10) // 10) * 10
        if prev_minute < 0:
            prev_minute = 50
            prev_hour = now.hour - 1
        else:
            prev_hour = now.hour
        
        prev_filename = f"{now.strftime('%Y-%m-%d')}_{prev_hour:02d}{prev_minute:02d}.txt"
        logger.info(f"尝试前一个时间点: {prev_filename}")
        download_url = find_file_in_folder(prev_filename)
        
        if not download_url:
            logger.error("找不到可用的文件,跳过本次检查")
            return False
    
    # 3. 下载
    content = download_file_content(download_url)
    if not content:
        logger.error("下载失败,跳过本次检查")
        return False
    
    # 4. 解析
    data = parse_data(content)
    if not data:
        logger.error("解析失败,跳过本次检查")
        return False
    
    # 5. 导入
    success = import_to_database(data)
    
    if success:
        logger.info("✓ 数据导入成功")
    else:
        logger.error("✗ 数据导入失败")
    
    return success

def main():
    """主循环"""
    logger.info("="*60)
    logger.info("Google Drive监控器 V2 启动")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒 ({CHECK_INTERVAL//60}分钟)")
    logger.info(f"文件夹ID: {FOLDER_ID}")
    logger.info(f"数据库: {DB_PATH}")
    logger.info("="*60)
    
    # 立即执行第一次检查
    check_and_import()
    
    # 循环检查
    while True:
        try:
            logger.info(f"\n⏰ 等待 {CHECK_INTERVAL//60} 分钟后下次检查...")
            time.sleep(CHECK_INTERVAL)
            
            check_and_import()
            
        except KeyboardInterrupt:
            logger.info("\n收到停止信号,正在退出...")
            break
        except Exception as e:
            logger.error(f"发生错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("等待下次检查...")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == '__main__':
    main()
