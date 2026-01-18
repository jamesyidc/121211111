#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
比特币恐慌贪婪指数历史数据采集器
数据源：https://history.btc123.fans/zhishu/
采集频率：每天一次
存储格式：JSONL
"""

import json
import requests
from datetime import datetime
import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/fear_greed_collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# API配置
API_URL = "https://history.btc123.fans/zhishu/api.php"
JSONL_FILE = "/home/user/webapp/data/fear_greed_jsonl/fear_greed_index.jsonl"
TIMEOUT = 10  # 请求超时时间（秒）

def ensure_directory():
    """确保数据目录存在"""
    os.makedirs(os.path.dirname(JSONL_FILE), exist_ok=True)
    logger.info(f"数据目录已准备: {os.path.dirname(JSONL_FILE)}")

def fetch_fear_greed_data():
    """
    从API获取恐慌贪婪指数历史数据
    
    返回:
        list: 包含所有历史数据的列表，每个元素格式：
              {"datetime": "2026-01-16", "value": 49, "result": "正常"}
    """
    try:
        logger.info(f"开始请求API: {API_URL}")
        response = requests.get(API_URL, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        history_data = data.get('data', [])
        
        logger.info(f"✅ API返回成功，数据条数: {len(history_data)}")
        
        if history_data:
            latest = history_data[-1]
            logger.info(f"   最新数据: {latest.get('datetime')} - 指数:{latest.get('value')} - {latest.get('result')}")
        
        return history_data
        
    except requests.exceptions.Timeout:
        logger.error(f"❌ API请求超时 (>{TIMEOUT}秒)")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 未知错误: {e}")
        return None

def load_existing_data():
    """
    加载已存在的JSONL数据
    
    返回:
        dict: 以日期为key的字典，用于快速查找
    """
    if not os.path.exists(JSONL_FILE):
        logger.info("📝 JSONL文件不存在，将创建新文件")
        return {}
    
    existing_data = {}
    try:
        with open(JSONL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line.strip())
                date_key = record.get('datetime') or record.get('date')  # 兼容旧格式
                if date_key:
                    existing_data[date_key] = record
        
        logger.info(f"📥 已加载现有数据: {len(existing_data)} 条")
        return existing_data
        
    except Exception as e:
        logger.error(f"❌ 加载现有数据失败: {e}")
        return {}

def save_to_jsonl(history_data):
    """
    将数据保存到JSONL文件
    
    策略：
    1. 加载已有数据
    2. 只添加新的日期数据或更新当天数据
    3. 按日期排序后重写整个文件
    
    参数:
        history_data: API返回的历史数据列表
    
    返回:
        tuple: (新增数量, 更新数量)
    """
    if not history_data:
        logger.warning("⚠️ 没有数据需要保存")
        return 0, 0
    
    # 加载现有数据
    existing_data = load_existing_data()
    
    # 统计计数
    new_count = 0
    update_count = 0
    
    # 处理新数据
    for item in history_data:
        date = item.get('datetime')
        value = item.get('value')
        result = item.get('result')
        
        if not all([date, value is not None, result]):
            logger.warning(f"⚠️ 数据不完整，跳过: {item}")
            continue
        
        # 构建记录（与旧格式兼容）
        record = {
            'datetime': date,
            'value': int(value),
            'result': result,
            'source': 'https://history.btc123.fans/zhishu/',
            'collect_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 判断是新增还是更新
        if date in existing_data:
            # 如果指数值有变化，则更新
            if existing_data[date]['value'] != record['value']:
                existing_data[date] = record
                update_count += 1
                logger.info(f"🔄 更新数据: {date} - 指数:{value} - {result}")
        else:
            existing_data[date] = record
            new_count += 1
            logger.info(f"➕ 新增数据: {date} - 指数:{value} - {result}")
    
    # 按日期排序
    sorted_data = sorted(existing_data.values(), key=lambda x: x['datetime'])
    
    # 重写文件
    try:
        with open(JSONL_FILE, 'w', encoding='utf-8') as f:
            for record in sorted_data:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.info(f"💾 数据已保存: {JSONL_FILE}")
        logger.info(f"   总计: {len(sorted_data)} 条 (新增:{new_count}, 更新:{update_count})")
        
        return new_count, update_count
        
    except Exception as e:
        logger.error(f"❌ 保存数据失败: {e}")
        return 0, 0

def collect_once():
    """执行一次完整的采集流程"""
    logger.info("=" * 50)
    logger.info("🚀 开始采集恐慌贪婪指数历史数据")
    logger.info("=" * 50)
    
    # 确保目录存在
    ensure_directory()
    
    # 获取数据
    history_data = fetch_fear_greed_data()
    
    if history_data is None:
        logger.error("❌ 采集失败：无法获取数据")
        return False
    
    # 保存数据
    new_count, update_count = save_to_jsonl(history_data)
    
    if new_count > 0 or update_count > 0:
        logger.info(f"✅ 采集成功！新增: {new_count} 条，更新: {update_count} 条")
        return True
    else:
        logger.info("ℹ️ 没有新数据")
        return True

if __name__ == '__main__':
    # 执行一次采集
    success = collect_once()
    sys.exit(0 if success else 1)
