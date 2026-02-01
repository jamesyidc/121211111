#!/usr/bin/env python3
"""
SAR斜率JSONL数据采集器
每1分钟从API获取数据并存入JSONL文件
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')
sys.path.insert(0, '/home/user/webapp')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/sar_slope_jsonl_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置
API_URL = 'http://localhost:5000/api/sar-slope/latest'
JSONL_DIR = '/home/user/webapp/data/sar_slope_jsonl'
JSONL_FILE = os.path.join(JSONL_DIR, 'sar_slope_data.jsonl')
SUMMARY_FILE = os.path.join(JSONL_DIR, 'sar_slope_summary.jsonl')
COLLECTION_INTERVAL = 60  # 每60秒（1分钟）采集一次

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


def ensure_directory():
    """确保数据目录存在"""
    os.makedirs(JSONL_DIR, exist_ok=True)
    logger.info(f"✅ 数据目录已就绪: {JSONL_DIR}")


def fetch_sar_slope_data():
    """从API获取SAR斜率数据"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if not data.get('success'):
            logger.warning(f"⚠️ API返回失败: {data.get('message', 'Unknown error')}")
            return None
        
        return data
    
    except requests.exceptions.Timeout:
        logger.error("❌ API请求超时")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析失败: {e}")
        return None


def save_to_jsonl(data, timestamp):
    """保存数据到JSONL文件"""
    try:
        # 保存详细数据（每个币种一行）
        with open(JSONL_FILE, 'a', encoding='utf-8') as f:
            for coin_data in data.get('data', []):
                record = {
                    'timestamp': timestamp,
                    'collection_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
                    **coin_data
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        # 保存汇总数据
        stats = data.get('stats', {})
        
        # 计算偏多比>80%和偏空比>80%的数量
        bullish_80_count = 0
        bearish_80_count = 0
        bullish_coins = []
        bearish_coins = []
        
        for coin_data in data.get('data', []):
            slope_value = coin_data.get('slope_value', 0) or 0
            position = coin_data.get('sar_position', '')
            symbol = coin_data.get('symbol', '')
            
            if position == 'bullish' and slope_value > 0.8:
                bullish_80_count += 1
                bullish_coins.append({
                    'symbol': symbol,
                    'slope': slope_value
                })
            
            if position == 'bearish' and slope_value < -0.8:
                bearish_80_count += 1
                bearish_coins.append({
                    'symbol': symbol,
                    'slope': abs(slope_value)
                })
        
        summary = {
            'timestamp': timestamp,
            'collection_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'total_symbols': stats.get('total_symbols', 0),
            'bullish_count': stats.get('bullish_count', 0),
            'bearish_count': stats.get('bearish_count', 0),
            'bullish_80_plus_count': bullish_80_count,
            'bearish_80_plus_count': bearish_80_count,
            'bullish_80_plus_coins': bullish_coins,
            'bearish_80_plus_coins': bearish_coins,
            'data_count': len(data.get('data', []))
        }
        
        with open(SUMMARY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(summary, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 数据已保存: {len(data.get('data', []))} 条记录")
        logger.info(f"   偏多比>80%: {bullish_80_count}, 偏空比>80%: {bearish_80_count}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 保存数据失败: {e}")
        return False


def cleanup_old_data(days=7):
    """清理旧数据（保留最近N天）"""
    try:
        cutoff_time = time.time() - (days * 86400)
        
        for filename in [JSONL_FILE, SUMMARY_FILE]:
            if not os.path.exists(filename):
                continue
            
            temp_file = filename + '.tmp'
            kept_count = 0
            removed_count = 0
            
            with open(filename, 'r', encoding='utf-8') as infile:
                with open(temp_file, 'w', encoding='utf-8') as outfile:
                    for line in infile:
                        try:
                            record = json.loads(line)
                            record_time = record.get('timestamp', 0)
                            
                            if record_time >= cutoff_time:
                                outfile.write(line)
                                kept_count += 1
                            else:
                                removed_count += 1
                        except:
                            continue
            
            os.replace(temp_file, filename)
            
            if removed_count > 0:
                logger.info(f"🗑️ {os.path.basename(filename)}: 保留 {kept_count} 条，删除 {removed_count} 条旧记录")
    
    except Exception as e:
        logger.error(f"❌ 清理旧数据失败: {e}")


def collect_once():
    """执行一次数据采集"""
    logger.info("=" * 60)
    logger.info("🚀 开始采集SAR斜率数据...")
    
    timestamp = time.time()
    
    # 获取数据
    data = fetch_sar_slope_data()
    if not data:
        logger.warning("⚠️ 本次采集失败，跳过")
        return False
    
    # 保存数据
    success = save_to_jsonl(data, timestamp)
    
    if success:
        logger.info(f"✅ 采集成功！时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    
    return success


def run_daemon():
    """守护进程模式运行"""
    logger.info("=" * 60)
    logger.info("🔥 SAR斜率JSONL数据采集器启动")
    logger.info(f"📡 API地址: {API_URL}")
    logger.info(f"💾 数据目录: {JSONL_DIR}")
    logger.info(f"⏰ 采集间隔: {COLLECTION_INTERVAL} 秒")
    logger.info("=" * 60)
    
    ensure_directory()
    
    # 记录启动次数
    collection_count = 0
    last_cleanup_time = time.time()
    
    while True:
        try:
            # 执行采集
            success = collect_once()
            collection_count += 1
            
            # 每小时清理一次旧数据
            if time.time() - last_cleanup_time > 3600:
                logger.info("🧹 执行数据清理...")
                cleanup_old_data(days=7)
                last_cleanup_time = time.time()
            
            # 等待下一次采集
            logger.info(f"⏳ 等待 {COLLECTION_INTERVAL} 秒后进行下一次采集... (已采集 {collection_count} 次)")
            time.sleep(COLLECTION_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("\n👋 收到停止信号，正在退出...")
            break
        except Exception as e:
            logger.error(f"❌ 采集过程出错: {e}")
            logger.info(f"⏳ 等待 {COLLECTION_INTERVAL} 秒后重试...")
            time.sleep(COLLECTION_INTERVAL)


if __name__ == '__main__':
    run_daemon()
