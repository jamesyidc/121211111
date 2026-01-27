#!/usr/bin/env python3
"""
磁盘空间监控脚本
- 检查磁盘使用率，当超过80%时发出告警
- 检查关键文件大小（WAL文件、日志目录等）
- 自动记录到日志文件
- 可配置告警阈值
"""

import os
import sys
import shutil
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "crypto_data.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = BASE_DIR / "disk_monitor.log"

# 告警阈值
DISK_WARNING_THRESHOLD = 80  # 磁盘使用率告警阈值 (%)
DISK_CRITICAL_THRESHOLD = 90  # 磁盘使用率严重告警阈值 (%)
WAL_WARNING_SIZE = 100 * 1024 * 1024  # WAL文件告警大小 (100MB)
LOG_DIR_WARNING_SIZE = 500 * 1024 * 1024  # 日志目录告警大小 (500MB)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_disk_usage():
    """获取磁盘使用情况"""
    usage = shutil.disk_usage("/")
    used_percent = (usage.used / usage.total) * 100
    return {
        'total_gb': usage.total / (1024**3),
        'used_gb': usage.used / (1024**3),
        'free_gb': usage.free / (1024**3),
        'used_percent': used_percent
    }

def get_file_size(filepath):
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(filepath)
    except FileNotFoundError:
        return 0

def get_dir_size(dirpath):
    """获取目录大小（字节）"""
    total = 0
    try:
        for entry in os.scandir(dirpath):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    except Exception as e:
        logging.error(f"获取目录大小失败 {dirpath}: {e}")
    return total

def format_size(bytes_size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def check_wal_file():
    """检查WAL文件大小"""
    wal_file = f"{DB_PATH}-wal"
    wal_size = get_file_size(wal_file)
    
    status = "✅ 正常"
    if wal_size > WAL_WARNING_SIZE:
        status = "⚠️ 警告"
        logging.warning(f"WAL文件过大: {format_size(wal_size)} (阈值: {format_size(WAL_WARNING_SIZE)})")
        
    return {
        'path': wal_file,
        'size': wal_size,
        'formatted': format_size(wal_size),
        'status': status,
        'warning': wal_size > WAL_WARNING_SIZE
    }

def check_log_dir():
    """检查日志目录大小"""
    log_size = get_dir_size(LOG_DIR)
    
    status = "✅ 正常"
    if log_size > LOG_DIR_WARNING_SIZE:
        status = "⚠️ 警告"
        logging.warning(f"日志目录过大: {format_size(log_size)} (阈值: {format_size(LOG_DIR_WARNING_SIZE)})")
        
    return {
        'path': str(LOG_DIR),
        'size': log_size,
        'formatted': format_size(log_size),
        'status': status,
        'warning': log_size > LOG_DIR_WARNING_SIZE
    }

def check_db_files():
    """检查数据库文件大小"""
    db_main = get_file_size(DB_PATH)
    db_wal = get_file_size(f"{DB_PATH}-wal")
    db_shm = get_file_size(f"{DB_PATH}-shm")
    
    return {
        'main': {'size': db_main, 'formatted': format_size(db_main)},
        'wal': {'size': db_wal, 'formatted': format_size(db_wal)},
        'shm': {'size': db_shm, 'formatted': format_size(db_shm)},
        'total': {'size': db_main + db_wal + db_shm, 'formatted': format_size(db_main + db_wal + db_shm)}
    }

def auto_cleanup_if_needed(disk_info, wal_info, log_info):
    """如果磁盘使用率过高，自动执行清理"""
    actions_taken = []
    
    # 如果磁盘使用率 >= 85%，自动清理
    if disk_info['used_percent'] >= 85:
        logging.warning(f"🔴 磁盘使用率 {disk_info['used_percent']:.1f}% >= 85%，开始自动清理...")
        
        # 1. 执行WAL checkpoint
        if wal_info['size'] > 10 * 1024 * 1024:  # WAL > 10MB
            try:
                logging.info("执行 WAL checkpoint...")
                conn = sqlite3.connect(str(DB_PATH))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
                actions_taken.append("✅ WAL checkpoint完成")
                logging.info("✅ WAL checkpoint完成")
            except Exception as e:
                logging.error(f"❌ WAL checkpoint失败: {e}")
                actions_taken.append(f"❌ WAL checkpoint失败: {e}")
        
        # 2. 清理旧日志
        if log_info['size'] > 100 * 1024 * 1024:  # 日志 > 100MB
            try:
                logging.info("清理7天前的日志...")
                os.system(f"find {LOG_DIR} -name '*.log' -mtime +7 -delete")
                actions_taken.append("✅ 清理旧日志完成")
                logging.info("✅ 清理旧日志完成")
            except Exception as e:
                logging.error(f"❌ 清理日志失败: {e}")
                actions_taken.append(f"❌ 清理日志失败: {e}")
    
    return actions_taken

def main():
    """主函数"""
    logging.info("="*60)
    logging.info("🔍 开始磁盘空间监控检查")
    logging.info("="*60)
    
    # 1. 检查磁盘使用率
    disk_info = get_disk_usage()
    logging.info(f"\n📊 磁盘使用情况:")
    logging.info(f"  总容量: {disk_info['total_gb']:.2f} GB")
    logging.info(f"  已使用: {disk_info['used_gb']:.2f} GB ({disk_info['used_percent']:.1f}%)")
    logging.info(f"  可用空间: {disk_info['free_gb']:.2f} GB")
    
    disk_status = "✅ 正常"
    if disk_info['used_percent'] >= DISK_CRITICAL_THRESHOLD:
        disk_status = "🔴 严重告警"
        logging.critical(f"🔴 磁盘使用率 {disk_info['used_percent']:.1f}% >= {DISK_CRITICAL_THRESHOLD}% (严重告警阈值)")
    elif disk_info['used_percent'] >= DISK_WARNING_THRESHOLD:
        disk_status = "⚠️ 警告"
        logging.warning(f"⚠️ 磁盘使用率 {disk_info['used_percent']:.1f}% >= {DISK_WARNING_THRESHOLD}% (告警阈值)")
    
    logging.info(f"  状态: {disk_status}")
    
    # 2. 检查WAL文件
    wal_info = check_wal_file()
    logging.info(f"\n📄 WAL文件检查:")
    logging.info(f"  大小: {wal_info['formatted']}")
    logging.info(f"  状态: {wal_info['status']}")
    
    # 3. 检查日志目录
    log_info = check_log_dir()
    logging.info(f"\n📁 日志目录检查:")
    logging.info(f"  大小: {log_info['formatted']}")
    logging.info(f"  状态: {log_info['status']}")
    
    # 4. 检查数据库文件
    db_info = check_db_files()
    logging.info(f"\n💾 数据库文件:")
    logging.info(f"  主文件: {db_info['main']['formatted']}")
    logging.info(f"  WAL文件: {db_info['wal']['formatted']}")
    logging.info(f"  SHM文件: {db_info['shm']['formatted']}")
    logging.info(f"  总计: {db_info['total']['formatted']}")
    
    # 5. 自动清理（如果需要）
    actions = auto_cleanup_if_needed(disk_info, wal_info, log_info)
    if actions:
        logging.info(f"\n🔧 自动清理操作:")
        for action in actions:
            logging.info(f"  {action}")
    
    # 6. 总结
    logging.info(f"\n" + "="*60)
    has_warnings = (
        disk_info['used_percent'] >= DISK_WARNING_THRESHOLD or 
        wal_info['warning'] or 
        log_info['warning']
    )
    
    if has_warnings:
        logging.warning("⚠️ 发现告警项，请关注！")
        return 1
    else:
        logging.info("✅ 所有检查通过，系统健康")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logging.critical(f"❌ 监控脚本执行失败: {e}", exc_info=True)
        sys.exit(2)
