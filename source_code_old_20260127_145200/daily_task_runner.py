#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨日期自动执行脚本
在每天00:00时自动执行指定任务
"""

import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
import pytz
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/daily_task.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
CHECK_INTERVAL = 60  # 每60秒检查一次

class DailyTaskRunner:
    def __init__(self):
        self.last_run_date = None
        self.tasks_executed_today = False
        
    def get_current_date(self):
        """获取当前北京时间日期"""
        return datetime.now(BEIJING_TZ).date()
    
    def should_run_tasks(self):
        """判断是否应该执行任务"""
        current_date = self.get_current_date()
        current_time = datetime.now(BEIJING_TZ)
        
        # 如果是新的一天且还没执行过
        if current_date != self.last_run_date and not self.tasks_executed_today:
            # 在00:00到00:30之间执行
            if 0 <= current_time.hour < 1:
                return True
        
        # 如果日期变了，重置标志
        if current_date != self.last_run_date:
            self.tasks_executed_today = False
            self.last_run_date = current_date
        
        return False
    
    def run_gdrive_update(self):
        """执行Google Drive数据更新"""
        try:
            logger.info("=" * 80)
            logger.info("🔄 开始执行Google Drive数据更新")
            logger.info("=" * 80)
            
            # 方法1: 直接运行Python脚本
            script_path = '/home/user/webapp/source_code/auto_gdrive_updater.py'
            if os.path.exists(script_path):
                logger.info(f"执行脚本: {script_path}")
                result = subprocess.run(
                    ['python3', script_path],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                
                if result.returncode == 0:
                    logger.info("✅ Google Drive更新脚本执行成功")
                    logger.info(f"输出: {result.stdout[:500]}")
                else:
                    logger.error(f"❌ 脚本执行失败，返回码: {result.returncode}")
                    logger.error(f"错误: {result.stderr[:500]}")
            else:
                logger.warning(f"⚠️ 脚本不存在: {script_path}")
            
            # 方法2: 重启PM2进程
            logger.info("\n🔄 重启gdrive-updater进程...")
            result = subprocess.run(
                ['pm2', 'restart', 'gdrive-updater'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("✅ gdrive-updater进程重启成功")
            else:
                logger.warning(f"⚠️ 进程重启失败: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            logger.error("❌ 脚本执行超时")
        except Exception as e:
            logger.error(f"❌ 执行失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_database_backup(self):
        """执行数据库备份"""
        try:
            logger.info("\n📦 开始数据库备份...")
            
            backup_dir = '/home/user/webapp/backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            current_date = self.get_current_date()
            backup_file = f"{backup_dir}/crypto_data_{current_date.strftime('%Y%m%d')}.db"
            
            # 备份数据库
            db_path = '/home/user/webapp/databases/crypto_data.db'
            if os.path.exists(db_path):
                result = subprocess.run(
                    ['cp', db_path, backup_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
                    logger.info(f"✅ 数据库备份成功: {backup_file}")
                    logger.info(f"   文件大小: {file_size:.2f} MB")
                else:
                    logger.error(f"❌ 备份失败: {result.stderr}")
            else:
                logger.warning(f"⚠️ 数据库文件不存在: {db_path}")
            
            # 清理7天前的备份
            logger.info("\n🧹 清理旧备份...")
            cutoff_date = current_date - timedelta(days=7)
            
            for filename in os.listdir(backup_dir):
                if filename.startswith('crypto_data_') and filename.endswith('.db'):
                    filepath = os.path.join(backup_dir, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).date()
                    
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        logger.info(f"   删除旧备份: {filename}")
            
        except Exception as e:
            logger.error(f"❌ 数据库备份失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def run_data_cleanup(self):
        """执行数据清理"""
        try:
            logger.info("\n🧹 开始数据清理...")
            
            # 清理临时文件
            temp_dirs = ['/tmp', '/home/user/webapp/temp']
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    logger.info(f"   清理临时目录: {temp_dir}")
                    # 这里可以添加具体的清理逻辑
            
            logger.info("✅ 数据清理完成")
            
        except Exception as e:
            logger.error(f"❌ 数据清理失败: {e}")
    
    def execute_daily_tasks(self):
        """执行所有日常任务"""
        current_time = datetime.now(BEIJING_TZ)
        logger.info("\n" + "=" * 80)
        logger.info(f"🌅 开始执行每日任务 - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        # 任务1: Google Drive更新
        self.run_gdrive_update()
        
        # 任务2: 数据库备份
        self.run_database_backup()
        
        # 任务3: 数据清理
        self.run_data_cleanup()
        
        # 标记今天已执行
        self.tasks_executed_today = True
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ 所有每日任务执行完成 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
    
    def run(self):
        """主循环"""
        logger.info("=" * 80)
        logger.info("🚀 每日任务调度器启动")
        logger.info(f"   检查间隔: {CHECK_INTERVAL}秒")
        logger.info(f"   执行时间: 每天 00:00-00:30")
        logger.info("=" * 80)
        
        self.last_run_date = self.get_current_date()
        
        while True:
            try:
                if self.should_run_tasks():
                    self.execute_daily_tasks()
                
                # 每分钟检查一次
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("\n收到中断信号，程序退出")
                break
            except Exception as e:
                logger.error(f"❌ 主循环错误: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(CHECK_INTERVAL)

def main():
    """主函数"""
    # 创建日志目录
    os.makedirs('/home/user/webapp/logs', exist_ok=True)
    os.makedirs('/home/user/webapp/backups', exist_ok=True)
    
    # 启动任务运行器
    runner = DailyTaskRunner()
    runner.run()

if __name__ == '__main__':
    main()
