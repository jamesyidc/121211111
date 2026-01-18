#!/usr/bin/env python3
"""
自动Google Drive数据更新器 V2
使用公开链接访问，不需要OAuth认证
每10分钟自动检查并导入最新的TXT文件
"""
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from gdrive_public_reader import GDrivePublicReader
from manual_import_txt import import_txt_file

# 配置
HOME_DATA_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"  # 首页数据文件夹ID
CHECK_INTERVAL = 600  # 10分钟检查一次
DB_PATH = "/home/user/webapp/databases/crypto_data.db"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/auto_gdrive_updater_v2.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def download_file(url: str, save_path: str) -> bool:
    """下载文件"""
    import requests
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return False


def check_and_import_latest():
    """检查并导入最新文件"""
    try:
        # 获取今天的日期
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"检查日期: {today}")
        
        # 创建读取器
        reader = GDrivePublicReader(HOME_DATA_FOLDER_ID)
        
        # 获取最新的TXT文件
        latest_file = reader.get_latest_txt_file(today)
        
        if not latest_file:
            logger.warning(f"未找到 {today} 的文件")
            
            # 尝试获取最新可用日期的文件
            date_folders = reader.find_date_folders()
            if date_folders:
                latest_date = date_folders[0]
                logger.info(f"尝试获取最新可用日期的文件: {latest_date}")
                latest_file = reader.get_latest_txt_file(latest_date)
        
        if not latest_file:
            logger.warning("未找到任何文件")
            return
        
        filename = latest_file['filename']
        download_url = latest_file['download_url']
        
        # 检查是否已导入
        if is_already_imported(filename):
            logger.info(f"文件已导入: {filename}")
            return
        
        # 下载文件
        temp_dir = Path("/home/user/webapp/data/gdrive_temp")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        temp_file = temp_dir / filename
        logger.info(f"下载文件: {filename}")
        
        if not download_file(download_url, str(temp_file)):
            logger.error(f"下载失败: {filename}")
            return
        
        # 导入数据库
        logger.info(f"导入数据库: {filename}")
        success = import_txt_file(str(temp_file), DB_PATH)
        
        if success:
            logger.info(f"✅ 成功导入: {filename}")
            # 删除临时文件
            temp_file.unlink()
        else:
            logger.error(f"❌ 导入失败: {filename}")
        
    except Exception as e:
        logger.error(f"检查更新时出错: {e}", exc_info=True)


def is_already_imported(filename: str) -> bool:
    """检查文件是否已导入"""
    import sqlite3
    import re
    
    try:
        # 从文件名解析时间: YYYY-MM-DD_HHMM.txt
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
        if not match:
            return False
        
        date_part = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        
        # 构造时间戳
        timestamp_str = f"{date_part} {hour}:{minute}:00"
        
        # 查询数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查是否存在该时间点的数据
        cursor.execute(
            "SELECT COUNT(*) FROM escape_signal_stats WHERE stat_time = ?",
            (timestamp_str,)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception as e:
        logger.error(f"检查文件是否已导入时出错: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 启动自动Google Drive数据更新器 V2")
    logger.info(f"   首页数据文件夹ID: {HOME_DATA_FOLDER_ID}")
    logger.info(f"   检查间隔: {CHECK_INTERVAL} 秒 ({CHECK_INTERVAL // 60} 分钟)")
    logger.info(f"   数据库路径: {DB_PATH}")
    logger.info("=" * 60)
    
    # 立即执行一次
    logger.info("立即执行首次检查...")
    check_and_import_latest()
    
    # 定时循环
    while True:
        try:
            next_check = datetime.now().timestamp() + CHECK_INTERVAL
            next_check_time = datetime.fromtimestamp(next_check).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"下次检查时间: {next_check_time} ({CHECK_INTERVAL // 60}分钟后)")
            
            time.sleep(CHECK_INTERVAL)
            
            logger.info("-" * 60)
            logger.info("开始检查更新...")
            check_and_import_latest()
            
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在退出...")
            break
        except Exception as e:
            logger.error(f"主循环出错: {e}", exc_info=True)
            logger.info("等待60秒后重试...")
            time.sleep(60)


if __name__ == '__main__':
    main()
