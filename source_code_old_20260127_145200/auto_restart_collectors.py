#!/usr/bin/env python3
"""
自动监控和重启数据采集器
当发现采集器停止或数据延迟超过阈值时自动重启
"""

import subprocess
import sqlite3
import time
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 定义采集器配置
COLLECTORS = [
    {
        'name': '持仓系统采集器',
        'script': 'position_system_collector.py',
        'table': 'position_system',
        'time_field': 'record_time',
        'max_delay_minutes': 10
    },
    {
        'name': 'V1V2采集器',
        'script': 'v1v2_collector.py',
        'table': 'crypto_coin_data',
        'time_field': 'update_time',
        'max_delay_minutes': 5
    },
    {
        'name': '价格速度采集器',
        'script': 'price_speed_collector.py',
        'table': None,  # 没有稳定的表
        'time_field': None,
        'max_delay_minutes': 5
    },
    {
        'name': '价格对比采集器',
        'script': 'price_comparison_collector.py',
        'table': 'price_comparison',
        'time_field': 'update_time',
        'max_delay_minutes': 10
    },
    {
        'name': '加密指数采集器',
        'script': 'crypto_index_collector.py',
        'table': 'crypto_index_klines',
        'time_field': 'timestamp',
        'max_delay_minutes': 10
    }
]

def is_process_running(script_name):
    """检查进程是否运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', script_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"检查进程失败: {e}")
        return False

def get_last_update_time(table, time_field):
    """获取数据库表的最后更新时间"""
    if not table or not time_field:
        return None
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX({time_field}) FROM {table}")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result:
            # 解析时间（假设是UTC+8）
            return datetime.strptime(result, '%Y-%m-%d %H:%M:%S')
        return None
    except Exception as e:
        logging.error(f"查询数据库失败 ({table}.{time_field}): {e}")
        return None

def restart_collector(script_name, collector_name):
    """重启采集器"""
    logging.warning(f"🔄 准备重启: {collector_name}")
    
    # 先杀掉旧进程
    try:
        subprocess.run(['pkill', '-f', script_name])
        time.sleep(2)
    except Exception as e:
        logging.error(f"停止进程失败: {e}")
    
    # 启动新进程
    try:
        log_name = script_name.replace('.py', '.log')
        subprocess.Popen(
            ['nohup', 'python3', script_name],
            stdout=open(f'logs/{log_name}', 'a'),
            stderr=subprocess.STDOUT,
            cwd='/home/user/webapp'
        )
        logging.info(f"✅ {collector_name} 已重启")
        return True
    except Exception as e:
        logging.error(f"启动进程失败: {e}")
        return False

def check_and_restart():
    """检查所有采集器并在需要时重启"""
    logging.info("=" * 60)
    logging.info("🔍 开始检查采集器状态...")
    
    restarted_count = 0
    
    for collector in COLLECTORS:
        name = collector['name']
        script = collector['script']
        table = collector['table']
        time_field = collector['time_field']
        max_delay = collector['max_delay_minutes']
        
        # 检查进程是否运行
        if not is_process_running(script):
            logging.warning(f"❌ {name} 进程未运行")
            if restart_collector(script, name):
                restarted_count += 1
            continue
        
        # 检查数据延迟（如果有表）
        if table and time_field:
            last_update = get_last_update_time(table, time_field)
            if last_update:
                now = datetime.now()
                delay = (now - last_update).total_seconds() / 60
                
                if delay > max_delay:
                    logging.warning(
                        f"⚠️  {name} 数据延迟 {delay:.1f} 分钟 "
                        f"(阈值: {max_delay} 分钟)"
                    )
                    if restart_collector(script, name):
                        restarted_count += 1
                else:
                    logging.info(f"✅ {name} 运行正常 (延迟 {delay:.1f} 分钟)")
            else:
                logging.warning(f"⚠️  {name} 无法获取最后更新时间")
        else:
            logging.info(f"✅ {name} 进程运行中")
    
    if restarted_count > 0:
        logging.info(f"🔄 已重启 {restarted_count} 个采集器")
    else:
        logging.info("✅ 所有采集器运行正常")
    
    logging.info("=" * 60)

if __name__ == '__main__':
    logging.info("🚀 自动监控脚本启动")
    logging.info("每5分钟检查一次采集器状态...")
    
    while True:
        try:
            check_and_restart()
            time.sleep(300)  # 等待5分钟
        except KeyboardInterrupt:
            logging.info("⏹️  监控脚本已停止")
            break
        except Exception as e:
            logging.error(f"监控脚本出错: {e}")
            time.sleep(60)  # 出错后等待1分钟再试
