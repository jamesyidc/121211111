#!/usr/bin/env python3
"""
Google Drive TXT文件更新检测器 - 独立功能模块

功能：
1. 持续监控Google Drive上的TXT文件
2. 检测文件内容的时间戳变化
3. 发现新数据时立即触发导入
4. 提供清晰的日志输出

使用方法：
    python3 gdrive_txt_detector.py
"""

import time
import requests
import re
from datetime import datetime
import pytz
import logging
import sys

# ============================================================================
# 配置区域
# ============================================================================

# Google Drive文件ID
GOOGLE_DRIVE_FILE_ID = "1eyYiU6lU8n7SwWUvFtm_kUIvaZI0SO4U"

# 检查间隔（秒）
CHECK_INTERVAL_SECONDS = 30

# 时区设置
TIMEZONE = pytz.timezone('Asia/Shanghai')

# 日志配置
LOG_FILE = '/home/user/webapp/gdrive_txt_detector.log'
LOG_LEVEL = logging.INFO

# ============================================================================
# 日志设置
# ============================================================================

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# 核心功能类
# ============================================================================

class GoogleDriveTxtDetector:
    """Google Drive TXT文件更新检测器"""
    
    def __init__(self, file_id, check_interval=30):
        self.file_id = file_id
        self.check_interval = check_interval
        self.last_known_timestamp = None
        self.check_count = 0
        
    def download_file(self):
        """下载Google Drive文件内容"""
        try:
            url = f"https://drive.google.com/uc?export=download&id={self.file_id}"
            
            # 防缓存headers
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"下载失败: HTTP {response.status_code}")
                return None
            
            # 验证是否为TXT文件
            content = response.text
            if '透明标签' not in content:
                logger.error("文件格式不正确")
                return None
            
            return content
            
        except Exception as e:
            logger.error(f"下载异常: {e}")
            return None
    
    def extract_timestamp(self, content):
        """从文件内容中提取时间戳"""
        try:
            timestamps = re.findall(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', content)
            if not timestamps:
                return None
            
            date_str, time_str = timestamps[0]
            timestamp = f"{date_str} {time_str}"
            return timestamp
            
        except Exception as e:
            logger.error(f"提取时间戳失败: {e}")
            return None
    
    def check_for_update(self):
        """检查文件是否有更新"""
        self.check_count += 1
        now = datetime.now(TIMEZONE)
        
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"检查 #{self.check_count} | {now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 1. 下载文件
        content = self.download_file()
        if not content:
            logger.warning("⚠️  下载失败，跳过本次检查")
            return False
        
        # 2. 提取时间戳
        current_timestamp = self.extract_timestamp(content)
        if not current_timestamp:
            logger.warning("⚠️  无法提取时间戳")
            return False
        
        logger.info(f"📄 文件时间戳: {current_timestamp}")
        
        # 3. 检查是否为新数据
        if self.last_known_timestamp is None:
            # 第一次运行
            self.last_known_timestamp = current_timestamp
            logger.info(f"🆕 初始化: 记录基准时间戳")
            return False
        
        if current_timestamp != self.last_known_timestamp:
            # 发现新数据!
            logger.info(f"")
            logger.info(f"🎉🎉🎉 检测到新数据更新! 🎉🎉🎉")
            logger.info(f"")
            logger.info(f"旧时间戳: {self.last_known_timestamp}")
            logger.info(f"新时间戳: {current_timestamp}")
            logger.info(f"")
            
            # 更新记录
            old_timestamp = self.last_known_timestamp
            self.last_known_timestamp = current_timestamp
            
            # 返回更新信息
            return {
                'old_timestamp': old_timestamp,
                'new_timestamp': current_timestamp,
                'content': content
            }
        else:
            # 没有更新
            file_time = TIMEZONE.localize(datetime.strptime(current_timestamp, '%Y-%m-%d %H:%M:%S'))
            delay_minutes = (now - file_time).total_seconds() / 60
            
            if delay_minutes > 20:
                logger.warning(f"⏰ 数据延迟 {delay_minutes:.0f} 分钟")
            else:
                logger.info(f"✓ 数据正常 (延迟 {delay_minutes:.0f} 分钟)")
            
            return False
    
    def run(self):
        """主运行循环"""
        logger.info("=" * 80)
        logger.info("🚀 Google Drive TXT文件更新检测器")
        logger.info("=" * 80)
        logger.info(f"文件ID: {self.file_id}")
        logger.info(f"检查间隔: {self.check_interval} 秒")
        logger.info(f"时区: {TIMEZONE}")
        logger.info(f"日志文件: {LOG_FILE}")
        logger.info("=" * 80)
        logger.info("")
        
        # 立即执行第一次检查
        self.check_for_update()
        
        # 持续监控循环
        while True:
            try:
                time.sleep(self.check_interval)
                
                result = self.check_for_update()
                
                if result:
                    # 发现新数据，触发回调
                    self.on_new_data_detected(result)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("=" * 80)
                logger.info("👋 收到停止信号，正在退出...")
                logger.info("=" * 80)
                break
            except Exception as e:
                logger.error(f"❌ 异常: {e}")
                logger.info("等待10秒后继续...")
                time.sleep(10)
    
    def on_new_data_detected(self, result):
        """新数据检测回调函数"""
        logger.info("=" * 80)
        logger.info("📢 触发新数据处理流程")
        logger.info("=" * 80)
        logger.info(f"请执行导入命令:")
        logger.info(f"  python3 import_latest_txt.py")
        logger.info("")
        logger.info(f"或者手动调用导入模块")
        logger.info("=" * 80)
        logger.info("")

# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主函数"""
    detector = GoogleDriveTxtDetector(
        file_id=GOOGLE_DRIVE_FILE_ID,
        check_interval=CHECK_INTERVAL_SECONDS
    )
    
    detector.run()

if __name__ == '__main__':
    main()
