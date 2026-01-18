#!/usr/bin/env python3
"""
Google Drive TXT文件监控器 - 更新版
监控"首页数据"文件夹中的TXT文件
共享链接: https://drive.google.com/drive/folders/1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH?usp=sharing
"""
import time
import requests
import re
import sqlite3
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import json

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/gdrive_monitor_updated.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 配置 - 使用新的共享链接
PARENT_FOLDER_ID = "1U5VjRis2FYnBJvtR_8mmPrmFcJCMPGrH"  # 爷爷文件夹
TARGET_FOLDER_NAME = "首页数据"  # 要监控的子文件夹名称
DB_PATH = '/home/user/webapp/crypto_data.db'
CHECK_INTERVAL = 600  # 10分钟

def get_folder_contents(folder_id):
    """获取Google Drive文件夹内容"""
    try:
        # 使用Google Drive API的公开访问方式
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"访问文件夹失败: HTTP {response.status_code}")
            return None
        
        # 从HTML中提取文件列表数据
        html = response.text
        
        # 查找包含文件信息的JavaScript数据
        # Google Drive会在页面中嵌入JSON数据
        pattern = r'window\[\'_DRIVE_ivd\'\]\s*=\s*\'([^\']+)\''
        match = re.search(pattern, html)
        
        if match:
            logger.info("找到Drive数据")
            return match.group(1)
        
        logger.warning("未找到文件列表数据，尝试其他方法")
        return None
        
    except Exception as e:
        logger.error(f"获取文件夹内容失败: {e}")
        return None

def find_homepage_data_folder(parent_folder_id):
    """在父文件夹中查找'首页数据'子文件夹"""
    try:
        logger.info(f"搜索'首页数据'文件夹，父文件夹ID: {parent_folder_id}")
        
        # 尝试通过API获取子文件夹
        # 由于是公开共享，我们可以尝试列出文件夹
        url = f"https://www.googleapis.com/drive/v3/files"
        params = {
            'q': f"'{parent_folder_id}' in parents and name='{TARGET_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder'",
            'key': 'AIzaSyDummyKey'  # 公开访问不需要真实key，但需要尝试
        }
        
        # 由于可能没有API key，我们使用备用方案
        # 直接尝试已知的可能文件夹ID模式
        logger.info("使用备用方案：尝试常见的文件夹结构")
        
        return None
        
    except Exception as e:
        logger.error(f"查找'首页数据'文件夹失败: {e}")
        return None

def download_file_by_id(file_id):
    """通过文件ID下载文件内容"""
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"下载文件失败: HTTP {response.status_code}")
            return None
        
        content = response.text
        
        # 验证内容格式
        if '透明标签' in content or 'BTC' in content or '急涨' in content:
            logger.info("✅ 成功下载并验证文件内容")
            return content
        else:
            logger.warning("文件内容格式不符合预期")
            return None
        
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return None

def parse_data(content):
    """解析TXT文件数据"""
    try:
        # 提取日期和时间
        # 先尝试提取完整日期时间
        date_time_pattern = r'(2025-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})'
        matches = re.findall(date_time_pattern, content)
        
        if not matches:
            logger.error("未找到日期时间戳")
            return None
        
        date_str = matches[0][0]
        time_str = matches[0][1]
        hour = int(time_str.split(':')[0])
        minute = int(time_str.split(':')[1])
        
        snapshot_time = f"{date_str} {hour:02d}:{minute:02d}:00"
        snapshot_date = date_str
        
        logger.info(f"解析时间: {snapshot_time}")
        
        # 提取数据
        rush_up = int(re.search(r'急涨[：:]\s*(\d+)', content).group(1))
        rush_down = int(re.search(r'急跌[：:]\s*(\d+)', content).group(1))
        count = int(re.search(r'透明标签_计次\s*[=＝]\s*(\d+)', content).group(1))
        status_match = re.search(r'透明标签_五种状态\s*[=＝]\s*(.+?)(?:\n|$)', content)
        status = status_match.group(1).strip().replace('状态：', '').replace('状态:', '') if status_match else "未知"
        
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
            'snapshot_date': snapshot_date,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'count': count,
            'count_score_display': count_score_display,
            'status': status
        }
        
        logger.info(f"✅ 解析数据成功: {data}")
        return data
        
    except Exception as e:
        logger.error(f"解析数据失败: {e}")
        logger.error(f"内容前500字符: {content[:500]}")
        return None

def save_to_database(data):
    """保存数据到数据库"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM homepage_realtime_data 
            WHERE snapshot_time = ?
        """, (data['snapshot_time'],))
        
        if cursor.fetchone():
            logger.info(f"数据已存在: {data['snapshot_time']}")
            conn.close()
            return False
        
        # 插入新数据
        cursor.execute("""
            INSERT INTO homepage_realtime_data 
            (snapshot_time, snapshot_date, rush_up, rush_down, count, count_score_display, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['snapshot_time'],
            data['snapshot_date'],
            data['rush_up'],
            data['rush_down'],
            data['count'],
            data['count_score_display'],
            data['status'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ 数据保存成功: {data['snapshot_time']}")
        return True
        
    except Exception as e:
        logger.error(f"保存数据失败: {e}")
        return False

def monitor_loop():
    """主监控循环"""
    logger.info("="*80)
    logger.info("🚀 Google Drive TXT监控器启动")
    logger.info(f"父文件夹ID: {PARENT_FOLDER_ID}")
    logger.info(f"目标文件夹: {TARGET_FOLDER_NAME}")
    logger.info(f"检查间隔: {CHECK_INTERVAL}秒")
    logger.info("="*80)
    
    consecutive_failures = 0
    
    while True:
        try:
            logger.info("\n" + "="*80)
            logger.info(f"开始检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("="*80)
            
            # TODO: 实现文件夹遍历和文件查找逻辑
            # 由于Google Drive公开API有限制，这里需要手动配置文件ID
            # 或者使用OAuth认证
            
            logger.info("⚠️  当前版本需要手动配置文件ID")
            logger.info("请提供'首页数据'文件夹中最新TXT文件的ID")
            
            # 暂时使用旧的文件ID进行测试
            # 用户需要提供新的文件ID
            
            consecutive_failures += 1
            
            if consecutive_failures >= 3:
                logger.warning(f"连续失败{consecutive_failures}次，等待下一个周期")
            
            logger.info(f"等待{CHECK_INTERVAL}秒后继续...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("\n收到中断信号，停止监控")
            break
        except Exception as e:
            logger.error(f"监控循环异常: {e}")
            time.sleep(60)

if __name__ == "__main__":
    monitor_loop()
