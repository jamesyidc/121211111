#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆仓金额数据采集器
每3分钟采集一次1小时和24小时爆仓金额数据
使用北京时间 (UTC+8)
"""

import requests
import sqlite3
import time
import sys
import signal
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('liquidation_amount_collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# API配置
API_1H = "https://api.btc123.fans/bicoin.php?from=1hbaocang"
API_24H = "https://api.btc123.fans/bicoin.php?from=24hbaocang"
API_REALHOLD = "https://api.btc123.fans/bicoin.php?from=realhold"

# PID文件
PID_FILE = Path(__file__).parent / "liquidation_amount_collector.pid"

class LiquidationAmountCollector:
    def __init__(self):
        self.running = False
        self.db_path = 'crypto_data.db'
        
    def get_beijing_time(self):
        """获取北京时间"""
        return datetime.now(BEIJING_TZ)
    
    def fetch_1h_liquidation(self):
        """
        获取1小时爆仓金额
        使用 API 的汇总字段 totalBlastUsd1h（单位：美元）
        """
        try:
            resp = requests.get(API_1H, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if 'data' in data:
                # 优先使用汇总字段 totalBlastUsd1h
                if 'totalBlastUsd1h' in data['data']:
                    total_usd = data['data']['totalBlastUsd1h']  # 单位：美元
                    total_usd_yi = total_usd / 100_000_000  # 转换为亿美元
                    total_usd_wan = total_usd / 10000  # 转换为万美元
                    
                    logger.info(f"✅ 1小时爆仓: ${total_usd:,.2f} = ${total_usd_wan:.2f}万 = ${total_usd_yi:.4f}亿")
                    return total_usd_yi
                else:
                    logger.error(f"❌ 1h API缺少 totalBlastUsd1h 字段")
                    return None
            else:
                logger.error(f"❌ 1h API返回数据格式错误: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取1小时爆仓数据失败: {e}")
            return None
    
    def fetch_24h_liquidation(self):
        """
        获取24小时爆仓金额和人数
        使用 API 的汇总字段 totalBlastUsd24h（单位：美元）和 totalBlastNum24h（单位：人）
        返回: (金额_亿美元, 人数)
        """
        try:
            resp = requests.get(API_24H, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if 'data' in data:
                # 优先使用汇总字段 totalBlastUsd24h
                if 'totalBlastUsd24h' in data['data']:
                    total_usd = data['data']['totalBlastUsd24h']  # 单位：美元
                    total_usd_yi = total_usd / 100_000_000  # 转换为亿美元
                    
                    # 获取爆仓人数
                    total_people = data['data'].get('totalBlastNum24h', 0)  # 单位：人
                    
                    logger.info(f"✅ 24小时爆仓: ${total_usd:,.2f} = ${total_usd_yi:.2f}亿")
                    logger.info(f"✅ 24小时爆仓人数: {total_people:,}人")
                    return (total_usd_yi, total_people)
                else:
                    logger.error(f"❌ 24h API缺少 totalBlastUsd24h 字段")
                    return (None, None)
            else:
                logger.error(f"❌ 24h API返回数据格式错误: {data}")
                return (None, None)
                
        except Exception as e:
            logger.error(f"❌ 获取24小时爆仓数据失败: {e}")
            return (None, None)
    
    def fetch_total_position(self):
        """
        获取全网持仓量
        使用 realhold API，取"全网总计"的amount字段（单位：美元）
        """
        try:
            resp = requests.get(API_REALHOLD, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if 'data' in data and isinstance(data['data'], list):
                # 查找"全网总计"项
                for item in data['data']:
                    if item.get('exchange') == '全网总计':
                        total_usd = item.get('amount', 0)  # 单位：美元
                        total_usd_yi = total_usd / 100_000_000  # 转换为亿美元
                        
                        logger.info(f"✅ 全网持仓: ${total_usd:,.2f} = ${total_usd_yi:.2f}亿美元")
                        return total_usd_yi
                
                logger.error(f"❌ 未找到'全网总计'数据")
                return None
            else:
                logger.error(f"❌ realhold API返回数据格式错误: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取全网持仓数据失败: {e}")
            return None
    
    def update_database(self, hour_1_yi, hour_24_yi, hour_24_people=None, total_position_yi=None):
        """
        插入新记录到数据库
        每次采集都新增一条记录，保留完整历史数据
        参数:
            hour_1_yi: 1小时爆仓金额（亿美元）
            hour_24_yi: 24小时爆仓金额（亿美元）
            hour_24_people: 24小时爆仓人数（人）
            total_position_yi: 全网持仓量（亿美元）
        """
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(self.db_path, timeout=10.0)
                cursor = conn.cursor()
                
                beijing_time = self.get_beijing_time()
                time_str = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
                date_str = beijing_time.strftime('%Y-%m-%d')
                
                # 获取最新记录的其他字段值（用于填充新记录）
                cursor.execute("""
                    SELECT panic_index, hour_24_people, total_position
                    FROM panic_wash_index 
                    ORDER BY id DESC 
                    LIMIT 1
                """)
                
                row = cursor.fetchone()
                
                if row:
                    # 如果本次采集到了新的人数，使用新值；否则使用历史值
                    if hour_24_people is not None:
                        people_count = hour_24_people
                    else:
                        people_count = row[1]
                    # 如果本次采集到了新的持仓量，使用新值；否则使用历史值
                    if total_position_yi is not None:
                        total_position = total_position_yi
                    else:
                        total_position = row[2]
                else:
                    # 如果没有历史记录，使用默认值或采集值
                    people_count = hour_24_people if hour_24_people is not None else 0.0
                    total_position = total_position_yi if total_position_yi is not None else 0.0
                
                # 计算恐慌清洗指数：(万人 / 亿美元) × 100
                # people_count单位是人，需要转换为万人
                if total_position > 0:
                    people_wan = people_count / 10000  # 转换为万人
                    panic_index = (people_wan / total_position) * 100
                else:
                    panic_index = 0.0
                
                # 插入新记录（包含record_date字段）
                cursor.execute("""
                    INSERT INTO panic_wash_index 
                    (record_time, record_date, panic_index, hour_24_people, total_position, hour_1_amount, hour_24_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (time_str, date_str, panic_index, people_count, total_position, hour_1_yi, hour_24_yi))
                
                new_id = cursor.lastrowid
                conn.commit()
                conn.close()
                
                logger.info(f"✅ 新记录已插入数据库 (ID: {new_id})")
                logger.info(f"   记录时间: {time_str}")
                logger.info(f"   1小时爆仓: ${hour_1_yi*10000:.2f}万 (${hour_1_yi:.4f}亿)")
                logger.info(f"   24小时爆仓: ${hour_24_yi:.2f}亿")
                logger.info(f"   24小时爆仓人数: {people_count:,}人 ({people_count/10000:.4f}万人)")
                logger.info(f"   全网持仓: ${total_position:.2f}亿美元")
                logger.info(f"   恐慌清洗指数: {panic_index:.2f}% (= {people_count/10000:.4f}万人 / {total_position:.2f}亿 × 100)")
                return  # 成功后退出
                
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"⚠️  数据库被锁定，{retry_delay}秒后重试 (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"❌ 数据库插入失败: {e}")
                    return
            except Exception as e:
                logger.error(f"❌ 数据库插入失败: {e}")
                return
    
    def collect_once(self):
        """执行一次数据采集"""
        beijing_time = self.get_beijing_time()
        logger.info(f"\n{'='*60}")
        logger.info(f"开始采集数据 - {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        logger.info(f"{'='*60}")
        
        # 获取1小时数据
        hour_1_yi = self.fetch_1h_liquidation()
        time.sleep(1)  # 避免API限流
        
        # 获取24小时数据
        hour_24_yi, hour_24_people = self.fetch_24h_liquidation()
        time.sleep(1)  # 避免API限流
        
        # 获取全网持仓量
        total_position_yi = self.fetch_total_position()
        
        # 如果爆仓数据都成功获取，则更新数据库（人数和持仓量可选）
        if hour_1_yi is not None and hour_24_yi is not None:
            self.update_database(hour_1_yi, hour_24_yi, hour_24_people, total_position_yi)
            logger.info("✅ 本轮采集完成")
        else:
            logger.error("❌ 数据获取不完整，跳过数据库更新")
    
    def start(self):
        """启动采集器（每3分钟一次）"""
        self.running = True
        
        # 写入PID文件
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        logger.info("🚀 爆仓金额采集器启动")
        logger.info(f"📍 使用北京时间 (UTC+8)")
        logger.info(f"⏱️  采集间隔: 3分钟")
        logger.info(f"💾 数据库: {self.db_path}")
        
        try:
            while self.running:
                self.collect_once()
                
                if self.running:
                    logger.info(f"⏳ 等待3分钟后进行下一次采集...\n")
                    time.sleep(180)  # 3分钟 = 180秒
                    
        except KeyboardInterrupt:
            logger.info("\n⚠️  收到停止信号")
        finally:
            self.stop()
    
    def stop(self):
        """停止采集器"""
        self.running = False
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("🛑 采集器已停止")

def signal_handler(signum, frame):
    """处理终止信号"""
    logger.info(f"\n收到信号 {signum}，准备停止...")
    sys.exit(0)

if __name__ == '__main__':
    import os
    import argparse
    
    parser = argparse.ArgumentParser(description='爆仓金额数据采集器')
    parser.add_argument('--once', action='store_true', help='只执行一次采集')
    args = parser.parse_args()
    
    # 注册信号处理
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    collector = LiquidationAmountCollector()
    
    if args.once:
        # 只执行一次
        logger.info("📌 单次执行模式")
        collector.collect_once()
    else:
        # 持续运行
        collector.start()
