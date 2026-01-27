#!/usr/bin/env python3
"""
SAR斜率系统采集守护进程
功能：
1. 每5分钟自动采集一次所有27个币种的最新SAR数据
2. 自动计算变化率、平均值和异常检测
3. 保持7天的历史数据
4. 记录运行日志
"""

import time
import logging
from datetime import datetime
import pytz
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入主系统模块
from sar_slope_system_complete import (
    collect_symbol_data, 
    cleanup_old_data,
    SYMBOLS,
    BEIJING_TZ
)

# 配置日志
LOG_DIR = '/home/user/webapp/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/sar_slope_collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 采集间隔（秒）
COLLECTION_INTERVAL = 5 * 60  # 5分钟

def collect_all_symbols_daemon():
    """采集所有币种的数据（守护进程版本）"""
    logger.info("="*80)
    logger.info("SAR斜率系统采集守护进程 - 开始运行")
    logger.info(f"采集间隔: {COLLECTION_INTERVAL} 秒 (5分钟)")
    logger.info(f"币种数量: {len(SYMBOLS)} 个")
    logger.info("="*80)
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        try:
            logger.info(f"[{i}/{len(SYMBOLS)}] 采集 {symbol}...")
            
            if collect_symbol_data(symbol):
                success_count += 1
                logger.info(f"  ✓ {symbol} 采集成功")
            else:
                fail_count += 1
                logger.warning(f"  ✗ {symbol} 采集失败")
        
        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ {symbol} 采集异常: {e}")
        
        # 避免请求过快
        if i < len(SYMBOLS):
            time.sleep(0.5)
    
    # 清理旧数据
    try:
        deleted = cleanup_old_data()
        logger.info(f"✓ 清理了 {deleted} 条超过7天的旧数据")
    except Exception as e:
        logger.error(f"✗ 清理旧数据失败: {e}")
    
    # 输出统计
    logger.info("="*80)
    logger.info(f"本次采集完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    logger.info("="*80)
    
    return success_count, fail_count

def main():
    """主循环"""
    logger.info("SAR斜率系统采集守护进程启动")
    logger.info(f"进程ID: {os.getpid()}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"日志目录: {LOG_DIR}")
    
    cycle_count = 0
    total_success = 0
    total_fail = 0
    
    try:
        while True:
            cycle_count += 1
            current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"\n{'='*80}")
            logger.info(f"第 {cycle_count} 次采集 - {current_time}")
            logger.info(f"{'='*80}")
            
            # 执行采集
            success, fail = collect_all_symbols_daemon()
            total_success += success
            total_fail += fail
            
            # 输出累计统计
            logger.info(f"\n累计统计:")
            logger.info(f"  总采集次数: {cycle_count}")
            logger.info(f"  总成功次数: {total_success}")
            logger.info(f"  总失败次数: {total_fail}")
            logger.info(f"  成功率: {total_success/(total_success+total_fail)*100:.2f}%")
            
            # 等待下一次采集
            next_time = datetime.now(BEIJING_TZ)
            next_time = next_time.replace(second=0, microsecond=0)
            
            # 计算到下一个5分钟整点的时间
            minutes = next_time.minute
            next_minutes = ((minutes // 5) + 1) * 5
            if next_minutes >= 60:
                next_time = next_time.replace(hour=(next_time.hour + 1) % 24, minute=0)
            else:
                next_time = next_time.replace(minute=next_minutes)
            
            wait_seconds = (next_time - datetime.now(BEIJING_TZ)).total_seconds()
            if wait_seconds > 0:
                logger.info(f"\n等待 {wait_seconds:.0f} 秒到下一个5分钟整点 ({next_time.strftime('%H:%M:%S')})...")
                time.sleep(wait_seconds)
            else:
                logger.info(f"\n等待 {COLLECTION_INTERVAL} 秒到下一次采集...")
                time.sleep(COLLECTION_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n收到停止信号，正在退出...")
        logger.info(f"总共完成 {cycle_count} 次采集")
        logger.info(f"成功: {total_success}, 失败: {total_fail}")
    
    except Exception as e:
        logger.error(f"守护进程异常: {e}", exc_info=True)
        raise
    
    finally:
        logger.info("SAR斜率系统采集守护进程已停止")

if __name__ == '__main__':
    main()
