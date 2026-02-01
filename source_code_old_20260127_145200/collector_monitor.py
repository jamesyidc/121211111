#!/usr/bin/env python3
"""
采集器监控脚本
定期检查各个采集器的运行状态，如果发现数据停止更新则自动重启
"""
import sqlite3
import subprocess
from datetime import datetime, timedelta
import pytz
import logging
import time
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collector_monitor.log'),
        logging.StreamHandler()
    ]
)

beijing_tz = pytz.timezone('Asia/Shanghai')

def check_v1v2_collector():
    """检查V1V2采集器状态"""
    try:
        conn = sqlite3.connect('v1v2_data.db')
        cursor = conn.cursor()
        
        # 检查 BTC 表的最新数据
        cursor.execute("""
            SELECT timestamp, collect_time 
            FROM volume_btc 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logging.warning("❌ V1V2采集器: 数据库无数据")
            return False, 0
        
        ts, collect_time = row
        data_time = datetime.fromtimestamp(ts / 1000, tz=beijing_tz)
        now = datetime.now(beijing_tz)
        delay_minutes = (now - data_time).total_seconds() / 60
        
        logging.info(f"✅ V1V2采集器: 最新数据时间 {data_time.strftime('%H:%M:%S')}, 延迟 {delay_minutes:.1f}分钟")
        
        # 如果延迟超过10分钟，认为有问题
        if delay_minutes > 10:
            logging.warning(f"⚠️  V1V2采集器: 数据延迟 {delay_minutes:.1f}分钟，超过阈值(10分钟)")
            return False, delay_minutes
        
        return True, delay_minutes
        
    except Exception as e:
        logging.error(f"❌ V1V2采集器检查失败: {e}")
        return False, 0

def check_support_resistance_collector():
    """检查支撑压力线采集器状态"""
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 检查最新数据
        cursor.execute("""
            SELECT record_time 
            FROM support_resistance_levels 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logging.warning("❌ 支撑压力线采集器: 数据库无数据")
            return False, 0
        
        record_time = row[0]
        data_time = datetime.strptime(record_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=beijing_tz)
        now = datetime.now(beijing_tz)
        delay_minutes = (now - data_time).total_seconds() / 60
        
        logging.info(f"✅ 支撑压力线采集器: 最新数据时间 {data_time.strftime('%H:%M:%S')}, 延迟 {delay_minutes:.1f}分钟")
        
        # 如果延迟超过10分钟，认为有问题
        if delay_minutes > 10:
            logging.warning(f"⚠️  支撑压力线采集器: 数据延迟 {delay_minutes:.1f}分钟，超过阈值(10分钟)")
            return False, delay_minutes
        
        return True, delay_minutes
        
    except Exception as e:
        logging.error(f"❌ 支撑压力线采集器检查失败: {e}")
        return False, 0

def restart_collector(collector_name):
    """重启指定的采集器"""
    try:
        logging.info(f"🔄 正在重启 {collector_name}...")
        result = subprocess.run(
            ['pm2', 'restart', collector_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logging.info(f"✅ {collector_name} 重启成功")
            return True
        else:
            logging.error(f"❌ {collector_name} 重启失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"❌ 重启 {collector_name} 失败: {e}")
        return False

def check_position_system_collector():
    """检查位置系统采集器状态"""
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 检查最新数据
        cursor.execute("""
            SELECT record_time 
            FROM position_system 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logging.warning("❌ 位置系统采集器: 数据库无数据")
            return False, 0
        
        record_time = row[0]
        data_time = datetime.strptime(record_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=beijing_tz)
        now = datetime.now(beijing_tz)
        delay_minutes = (now - data_time).total_seconds() / 60
        
        logging.info(f"✅ 位置系统采集器: 最新数据时间 {data_time.strftime('%H:%M:%S')}, 延迟 {delay_minutes:.1f}分钟")
        
        # 如果延迟超过10分钟，认为有问题
        if delay_minutes > 10:
            logging.warning(f"⚠️  位置系统采集器: 数据延迟 {delay_minutes:.1f}分钟，超过阈值(10分钟)")
            return False, delay_minutes
        
        return True, delay_minutes
        
    except Exception as e:
        logging.error(f"❌ 位置系统采集器检查失败: {e}")
        return False, 0

def check_crypto_index_collector():
    """检查加密货币指数采集器状态"""
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 检查最新数据（timestamp字段是文本格式）
        cursor.execute("""
            SELECT timestamp 
            FROM crypto_index_klines 
            ORDER BY id DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logging.warning("❌ 加密货币指数采集器: 数据库无数据")
            return False, 0
        
        timestamp_str = row[0]
        data_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=beijing_tz)
        now = datetime.now(beijing_tz)
        delay_minutes = (now - data_time).total_seconds() / 60
        
        logging.info(f"✅ 加密货币指数采集器: 最新数据时间 {data_time.strftime('%H:%M:%S')}, 延迟 {delay_minutes:.1f}分钟")
        
        # 如果延迟超过10分钟，认为有问题
        if delay_minutes > 10:
            logging.warning(f"⚠️  加密货币指数采集器: 数据延迟 {delay_minutes:.1f}分钟，超过阈值(10分钟)")
            return False, delay_minutes
        
        return True, delay_minutes
        
    except Exception as e:
        logging.error(f"❌ 加密货币指数采集器检查失败: {e}")
        return False, 0

def monitor_collectors():
    """监控所有采集器"""
    logging.info("=" * 60)
    logging.info("🔍 开始监控采集器状态")
    
    now = datetime.now(beijing_tz)
    logging.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查 V1V2 采集器
    v1v2_ok, v1v2_delay = check_v1v2_collector()
    if not v1v2_ok:
        logging.warning("🚨 V1V2采集器需要重启")
        restart_collector('v1v2-collector')
    
    # 检查支撑压力线采集器
    sr_ok, sr_delay = check_support_resistance_collector()
    if not sr_ok:
        logging.warning("🚨 支撑压力线采集器需要重启")
        restart_collector('support-resistance-collector')
    
    # 检查位置系统采集器
    pos_ok, pos_delay = check_position_system_collector()
    if not pos_ok:
        logging.warning("🚨 位置系统采集器需要重启")
        restart_collector('position-system-collector')
    
    # 检查加密货币指数采集器
    crypto_ok, crypto_delay = check_crypto_index_collector()
    if not crypto_ok:
        logging.warning("🚨 加密货币指数采集器需要重启")
        restart_collector('crypto-index-collector')
    
    logging.info("=" * 60)
    logging.info("")

def main():
    """主函数"""
    logging.info("🚀 采集器监控脚本启动")
    
    while True:
        try:
            monitor_collectors()
            # 每5分钟检查一次
            time.sleep(300)
        except KeyboardInterrupt:
            logging.info("👋 监控脚本停止")
            break
        except Exception as e:
            logging.error(f"❌ 监控循环出错: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
