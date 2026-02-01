#!/usr/bin/env python3
"""
数据库自动维护脚本
- 执行 WAL checkpoint (合并WAL文件到主数据库)
- 可选：执行 VACUUM (压缩数据库，回收空间)
- 记录维护日志
- 适合定期执行（建议每6小时或每天）
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "crypto_data.db"
LOG_FILE = BASE_DIR / "db_maintenance.log"

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_file_size(filepath):
    """获取文件大小"""
    try:
        size = os.path.getsize(filepath)
        return size
    except FileNotFoundError:
        return 0

def format_size(bytes_size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def wal_checkpoint(conn):
    """执行 WAL checkpoint"""
    try:
        logging.info("🔄 开始执行 WAL checkpoint (TRUNCATE 模式)...")
        
        # 获取checkpoint前的WAL文件大小
        wal_before = get_file_size(f"{DB_PATH}-wal")
        logging.info(f"  WAL文件大小（checkpoint前）: {format_size(wal_before)}")
        
        # 执行checkpoint
        cursor = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        result = cursor.fetchone()
        
        # 获取checkpoint后的WAL文件大小
        wal_after = get_file_size(f"{DB_PATH}-wal")
        logging.info(f"  WAL文件大小（checkpoint后）: {format_size(wal_after)}")
        
        saved = wal_before - wal_after
        if saved > 0:
            logging.info(f"  ✅ 释放空间: {format_size(saved)}")
        
        logging.info(f"  Checkpoint结果: busy={result[0]}, log={result[1]}, checkpointed={result[2]}")
        return True
        
    except Exception as e:
        logging.error(f"  ❌ WAL checkpoint失败: {e}")
        return False

def vacuum_database(conn):
    """执行 VACUUM (可选，比较耗时)"""
    try:
        logging.info("🗜️  开始执行 VACUUM (数据库压缩)...")
        
        # 获取VACUUM前的数据库大小
        db_before = get_file_size(DB_PATH)
        logging.info(f"  数据库大小（VACUUM前）: {format_size(db_before)}")
        
        # 执行VACUUM
        conn.execute("VACUUM")
        
        # 获取VACUUM后的数据库大小
        db_after = get_file_size(DB_PATH)
        logging.info(f"  数据库大小（VACUUM后）: {format_size(db_after)}")
        
        saved = db_before - db_after
        if saved > 0:
            logging.info(f"  ✅ 释放空间: {format_size(saved)}")
        else:
            logging.info(f"  ℹ️  无空间可回收")
        
        return True
        
    except Exception as e:
        logging.error(f"  ❌ VACUUM失败: {e}")
        return False

def analyze_database(conn):
    """执行 ANALYZE (更新统计信息，优化查询)"""
    try:
        logging.info("📊 开始执行 ANALYZE (更新统计信息)...")
        conn.execute("ANALYZE")
        logging.info("  ✅ ANALYZE完成")
        return True
    except Exception as e:
        logging.error(f"  ❌ ANALYZE失败: {e}")
        return False

def integrity_check(conn):
    """执行完整性检查"""
    try:
        logging.info("🔍 开始执行数据库完整性检查...")
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            logging.info("  ✅ 数据库完整性检查通过")
            return True
        else:
            logging.error(f"  ❌ 数据库完整性检查失败: {result}")
            return False
    except Exception as e:
        logging.error(f"  ❌ 完整性检查失败: {e}")
        return False

def get_db_stats(conn):
    """获取数据库统计信息"""
    try:
        # 获取表数量
        cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        
        # 获取页面大小和页面数
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        
        # 计算数据库大小
        db_size = page_size * page_count
        
        logging.info(f"📈 数据库统计:")
        logging.info(f"  表数量: {table_count}")
        logging.info(f"  页面大小: {page_size} bytes")
        logging.info(f"  页面数量: {page_count}")
        logging.info(f"  理论大小: {format_size(db_size)}")
        
    except Exception as e:
        logging.error(f"获取统计信息失败: {e}")

def main(skip_vacuum=True):
    """
    主函数
    
    Args:
        skip_vacuum: 是否跳过VACUUM操作（默认跳过，因为耗时较长）
    """
    logging.info("="*60)
    logging.info("🛠️  开始数据库自动维护")
    logging.info(f"⏰ 维护时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("="*60)
    
    try:
        # 连接数据库
        logging.info(f"\n📂 连接数据库: {DB_PATH}")
        conn = sqlite3.connect(str(DB_PATH))
        
        # 1. 完整性检查
        logging.info("\n【第1步】完整性检查")
        integrity_ok = integrity_check(conn)
        
        if not integrity_ok:
            logging.error("⚠️  数据库完整性检查失败，跳过维护操作")
            conn.close()
            return 1
        
        # 2. WAL Checkpoint (必须执行)
        logging.info("\n【第2步】WAL Checkpoint")
        wal_checkpoint(conn)
        
        # 3. ANALYZE (更新统计信息)
        logging.info("\n【第3步】ANALYZE")
        analyze_database(conn)
        
        # 4. VACUUM (可选，耗时较长)
        if not skip_vacuum:
            logging.info("\n【第4步】VACUUM")
            vacuum_database(conn)
        else:
            logging.info("\n【第4步】VACUUM (已跳过)")
            logging.info("  ℹ️  如需执行VACUUM，请运行: python3 db_maintenance.py --vacuum")
        
        # 5. 获取数据库统计信息
        logging.info("\n【第5步】统计信息")
        get_db_stats(conn)
        
        # 关闭连接
        conn.close()
        
        logging.info("\n" + "="*60)
        logging.info("✅ 数据库维护完成")
        logging.info("="*60)
        return 0
        
    except Exception as e:
        logging.critical(f"❌ 数据库维护失败: {e}", exc_info=True)
        return 2

if __name__ == "__main__":
    # 检查是否需要执行VACUUM
    skip_vacuum = "--vacuum" not in sys.argv
    
    try:
        exit_code = main(skip_vacuum=skip_vacuum)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logging.warning("\n⚠️  用户中断操作")
        sys.exit(130)
