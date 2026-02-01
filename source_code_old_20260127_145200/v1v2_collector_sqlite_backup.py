#!/usr/bin/env python3
"""
V1V2成交额数据采集器
每30秒从OKEx获取27个币种的5分钟成交额数据
"""
import requests
import sqlite3
import time
import logging
from datetime import datetime
import pytz
import json
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('v1v2_collector.log'),
        logging.StreamHandler()
    ]
)

# 默认的27个币种配置及其V1V2阈值
DEFAULT_COINS_CONFIG = {
    'BTC': {'v1': 200000, 'v2': 100000},
    'ETH': {'v1': 1300000, 'v2': 500000},
    'XRP': {'v1': 200000, 'v2': 87000},
    'SOL': {'v1': 351620, 'v2': 246380},
    'BNB': {'v1': 2388300, 'v2': 1737500},
    'LTC': {'v1': 50000, 'v2': 15000},
    'DOGE': {'v1': 150000, 'v2': 60000},
    'SUI': {'v1': 2000000, 'v2': 800000},
    'TRX': {'v1': 13280, 'v2': 6022},
    'TON': {'v1': 350000, 'v2': 200000},
    'ETC': {'v1': 12000, 'v2': 2000},
    'BCH': {'v1': 103500, 'v2': 50000},
    'HBAR': {'v1': 103500, 'v2': 40000},
    'XLM': {'v1': 103500, 'v2': 30000},
    'FIL': {'v1': 5003500, 'v2': 3700000},
    'ADA': {'v1': 67210, 'v2': 44230},
    'LINK': {'v1': 280000, 'v2': 200000},
    'CRO': {'v1': 100000, 'v2': 40000},
    'DOT': {'v1': 300000, 'v2': 250000},
    'UNI': {'v1': 140000, 'v2': 100000},
    'NEAR': {'v1': 100000, 'v2': 50000},
    'APT': {'v1': 300000, 'v2': 200000},
    'CFX': {'v1': 300000, 'v2': 250000},
    'CRV': {'v1': 1500000, 'v2': 1000000},
    'STX': {'v1': 50000, 'v2': 30000},
    'LDO': {'v1': 1000000, 'v2': 600000},
    'TAO': {'v1': 300000, 'v2': 180000}
}

# 全局变量存储当前配置
COINS_CONFIG = DEFAULT_COINS_CONFIG.copy()

DB_FILE = 'v1v2_data.db'
SETTINGS_FILE = 'v1v2_settings.json'
SETTINGS_UPDATED_FLAG = '.v1v2_settings_updated'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def load_settings():
    """从设置文件加载配置"""
    global COINS_CONFIG
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                COINS_CONFIG = json.load(f)
            logging.info('✅ 从设置文件加载配置成功')
            return True
        else:
            COINS_CONFIG = DEFAULT_COINS_CONFIG.copy()
            logging.info('⚠️ 设置文件不存在，使用默认配置')
            return False
    except Exception as e:
        logging.error(f'❌ 加载设置文件失败: {str(e)}，使用默认配置')
        COINS_CONFIG = DEFAULT_COINS_CONFIG.copy()
        return False

def check_settings_updated():
    """检查设置是否已更新"""
    if os.path.exists(SETTINGS_UPDATED_FLAG):
        try:
            os.remove(SETTINGS_UPDATED_FLAG)
            load_settings()
            logging.info('🔄 检测到设置更新，已重新加载配置')
            return True
        except Exception as e:
            logging.error(f'❌ 处理设置更新失败: {str(e)}')
    return False

def init_database():
    """初始化数据库,为每个币种创建独立的表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for symbol in COINS_CONFIG.keys():
        table_name = f'volume_{symbol.lower()}'
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                collect_time TEXT NOT NULL,
                volume REAL NOT NULL,
                v1_threshold REAL NOT NULL,
                v2_threshold REAL NOT NULL,
                level TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引加速查询
        cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp 
            ON {table_name}(timestamp DESC)
        ''')
    
    conn.commit()
    conn.close()
    logging.info('✅ 数据库初始化完成')

def fetch_volume_from_okex(symbol):
    """
    从OKEx获取5分钟K线的成交额
    返回最新的5分钟成交额(USDT)
    """
    try:
        # OKEx API - 获取5分钟K线数据
        url = 'https://www.okx.com/api/v5/market/candles'
        params = {
            'instId': f'{symbol}-USDT-SWAP',
            'bar': '5m',
            'limit': '1'  # 只获取最新一根K线
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data['code'] == '0' and data['data']:
            # K线数据格式: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
            # volCcyQuote 是以报价货币(USDT)计价的成交量
            candle = data['data'][0]
            volume_usdt = float(candle[7])  # volCcyQuote - USDT成交额
            timestamp = int(candle[0])  # 时间戳(毫秒)
            
            logging.info(f'✅ {symbol}: 成交额 ${volume_usdt:,.2f} USDT')
            return volume_usdt, timestamp
        else:
            logging.warning(f'⚠️ {symbol}: API返回错误 - {data}')
            return None, None
            
    except Exception as e:
        logging.error(f'❌ {symbol}: 获取数据失败 - {str(e)}')
        return None, None

def determine_level(volume, v1, v2):
    """
    判断成交额级别
    规则: 大于V1则只显示V1,不显示V2
    """
    if volume >= v1:
        return 'V1'
    elif volume >= v2:
        return 'V2'
    else:
        return 'NONE'

def save_to_database(symbol, volume, timestamp, v1, v2, level):
    """保存数据到对应币种的表（使用UPSERT避免重复记录）"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        table_name = f'volume_{symbol.lower()}'
        
        # 转换时间戳为北京时间
        dt = datetime.fromtimestamp(timestamp / 1000, tz=BEIJING_TZ)
        collect_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 先检查是否已存在该时间戳的记录
        cursor.execute(f'''
            SELECT id FROM {table_name}
            WHERE timestamp = ?
        ''', (timestamp,))
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute(f'''
                UPDATE {table_name}
                SET volume = ?, v1_threshold = ?, v2_threshold = ?, level = ?, created_at = CURRENT_TIMESTAMP
                WHERE timestamp = ?
            ''', (volume, v1, v2, level, timestamp))
            logging.info(f'🔄 {symbol}: 数据已更新 - {level} (${volume:,.2f})')
        else:
            # 插入新记录
            cursor.execute(f'''
                INSERT INTO {table_name} 
                (timestamp, collect_time, volume, v1_threshold, v2_threshold, level)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, collect_time, volume, v1, v2, level))
            logging.info(f'💾 {symbol}: 数据已保存 - {level} (${volume:,.2f})')
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logging.error(f'❌ {symbol}: 保存数据失败 - {str(e)}')
        return False

def collect_all_coins():
    """采集所有币种的数据"""
    logging.info('=' * 60)
    logging.info('🔄 开始新一轮数据采集')
    
    success_count = 0
    retry_count = 0
    max_retries = 3  # 最多重试3次
    
    for symbol, thresholds in COINS_CONFIG.items():
        volume, timestamp = fetch_volume_from_okex(symbol)
        
        # 如果成交额为0，重试最多max_retries次
        retry_attempts = 0
        while (volume is not None and volume == 0) and retry_attempts < max_retries:
            retry_attempts += 1
            retry_count += 1
            logging.warning(f'⚠️ {symbol}: 成交额为0，第{retry_attempts}次重试...')
            time.sleep(2)  # 等待2秒后重试
            volume, timestamp = fetch_volume_from_okex(symbol)
        
        # 最终验证：只有当volume不为None、不为0时才保存
        if volume is not None and timestamp is not None and volume > 0:
            v1 = thresholds['v1']
            v2 = thresholds['v2']
            level = determine_level(volume, v1, v2)
            
            if save_to_database(symbol, volume, timestamp, v1, v2, level):
                success_count += 1
        elif volume == 0:
            logging.error(f'❌ {symbol}: 成交额仍为0，已重试{retry_attempts}次，跳过本次保存')
        
        # 避免请求过快
        time.sleep(0.5)
    
    if retry_count > 0:
        logging.info(f'🔄 本轮共重试 {retry_count} 次（成交额为0）')
    logging.info(f'✅ 本轮采集完成: {success_count}/{len(COINS_CONFIG)} 成功')
    logging.info('=' * 60)
    
    return success_count

def cleanup_old_data(days=7):
    """清理N天前的旧数据"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cutoff_time = int((time.time() - days * 86400) * 1000)
        
        for symbol in COINS_CONFIG.keys():
            table_name = f'volume_{symbol.lower()}'
            cursor.execute(f'''
                DELETE FROM {table_name} 
                WHERE timestamp < ?
            ''', (cutoff_time,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logging.info(f'🧹 清理了 {deleted} 条旧数据 (>{days}天)')
        
    except Exception as e:
        logging.error(f'❌ 清理数据失败: {str(e)}')

def main():
    """主程序"""
    logging.info('🚀 V1V2成交额采集器启动')
    
    # 加载设置
    load_settings()
    
    logging.info(f'📊 监控币种: {len(COINS_CONFIG)} 个')
    logging.info(f'⏰ 采集间隔: 30 秒')
    logging.info(f'📈 K线周期: 5 分钟')
    
    # 初始化数据库
    init_database()
    
    # 首次采集
    collect_all_coins()
    
    # 定时采集循环
    cycle = 1
    while True:
        try:
            # 等待30秒
            time.sleep(30)
            
            cycle += 1
            logging.info(f'\n🔄 第 {cycle} 轮采集')
            
            # 检查设置是否更新
            check_settings_updated()
            
            # 采集数据
            collect_all_coins()
            
            # 每小时清理一次旧数据
            if cycle % 120 == 0:  # 120 * 30秒 = 1小时
                cleanup_old_data(days=7)
                
        except KeyboardInterrupt:
            logging.info('\n⛔ 收到停止信号,采集器退出')
            break
        except Exception as e:
            logging.error(f'❌ 采集循环出错: {str(e)}')
            time.sleep(30)

if __name__ == '__main__':
    main()
