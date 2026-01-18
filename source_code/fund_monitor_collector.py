#!/usr/bin/env python3
"""
资金监控系统数据采集器
- 每5分钟采集27个币种的成交量数据（从OKEx）
- 计算15分钟、30分钟、60分钟的聚合成交量
- 与过去3天平均量能对比，检测异常波动（>20%，可配置）
- 数据与V1V2系统共享OKEx数据源
"""
import requests
import sqlite3
import time
import logging
from datetime import datetime, timedelta
import pytz
import json
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fund_monitor_collector.log'),
        logging.StreamHandler()
    ]
)

# 27个监控币种
COINS = [
    'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
]

DB_FILE = 'fund_monitor.db'
CONFIG_FILE = 'fund_monitor_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 默认配置
DEFAULT_CONFIG = {
    'threshold_percentage': 20.0,  # 异常波动阈值百分比
    'lookback_days': 3,  # 回看天数
    'collection_interval': 300  # 采集间隔（秒），默认5分钟
}

# 全局配置
CONFIG = DEFAULT_CONFIG.copy()

def load_config():
    """加载配置"""
    global CONFIG
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                CONFIG.update(user_config)
            logging.info(f'✅ 配置加载成功: 阈值={CONFIG["threshold_percentage"]}%, 回看={CONFIG["lookback_days"]}天')
        else:
            # 创建默认配置文件
            save_config()
            logging.info('⚠️ 使用默认配置并创建配置文件')
    except Exception as e:
        logging.error(f'❌ 加载配置失败: {str(e)}，使用默认配置')
        CONFIG = DEFAULT_CONFIG.copy()

def save_config():
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=2)
        logging.info('✅ 配置保存成功')
    except Exception as e:
        logging.error(f'❌ 配置保存失败: {str(e)}')

def init_database():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 5分钟原始数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_monitor_5min (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            collect_time TEXT NOT NULL,
            volume REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp)
        )
    ''')
    
    # 聚合数据表（15/30/60分钟）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_monitor_aggregated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            collect_time TEXT NOT NULL,
            interval_type TEXT NOT NULL,
            volume REAL NOT NULL,
            avg_3day REAL,
            deviation_percent REAL,
            is_abnormal INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, timestamp, interval_type)
        )
    ''')
    
    # 配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fund_monitor_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value REAL NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认配置
    cursor.execute('''
        INSERT OR IGNORE INTO fund_monitor_config (key, value, description)
        VALUES ('threshold_percentage', 20.0, '异常波动阈值百分比')
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_5min_symbol_time ON fund_monitor_5min(symbol, timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agg_symbol_time ON fund_monitor_aggregated(symbol, timestamp DESC, interval_type)')
    
    conn.commit()
    conn.close()
    logging.info('✅ 数据库初始化完成')

def fetch_volume_from_okex(symbol):
    """
    从OKEx获取5分钟K线的成交量数据
    返回: (timestamp, volume_usdt) 或 (None, None)
    """
    try:
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
            # K线数据: [timestamp, open, high, low, close, volume, volCcy, volCcyQuote, confirm]
            # volCcyQuote(索引7) 是USDT成交额
            candle = data['data'][0]
            timestamp = int(candle[0])  # 毫秒时间戳
            volume_usdt = float(candle[7])  # USDT成交额
            
            logging.info(f'✅ {symbol}: Vol=${volume_usdt:,.2f} USDT')
            return timestamp, volume_usdt
        else:
            logging.warning(f'⚠️ {symbol}: API返回无数据 - {data}')
            return None, None
            
    except requests.exceptions.Timeout:
        logging.error(f'❌ {symbol}: 请求超时')
        return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f'❌ {symbol}: 网络错误 - {str(e)}')
        return None, None
    except Exception as e:
        logging.error(f'❌ {symbol}: 数据解析错误 - {str(e)}')
        return None, None

def store_5min_data(conn, symbol, timestamp, volume):
    """存储5分钟原始数据"""
    cursor = conn.cursor()
    collect_time = datetime.fromtimestamp(timestamp / 1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO fund_monitor_5min 
            (symbol, timestamp, collect_time, volume)
            VALUES (?, ?, ?, ?)
        ''', (symbol, timestamp, collect_time, volume))
        return True
    except Exception as e:
        logging.error(f'❌ {symbol}: 存储5分钟数据失败 - {str(e)}')
        return False

def calculate_aggregated_volume(conn, symbol, timestamp, interval_minutes):
    """
    计算聚合成交量（15/30/60分钟）
    从当前时间戳向前回溯指定分钟数
    """
    cursor = conn.cursor()
    
    # 计算时间范围（毫秒）
    lookback_ms = interval_minutes * 60 * 1000
    start_timestamp = timestamp - lookback_ms + 1  # +1避免包含边界外的数据
    
    # 查询该时间段内的5分钟数据
    cursor.execute('''
        SELECT SUM(volume) 
        FROM fund_monitor_5min
        WHERE symbol = ? 
        AND timestamp > ? 
        AND timestamp <= ?
    ''', (symbol, start_timestamp, timestamp))
    
    result = cursor.fetchone()
    total_volume = result[0] if result[0] is not None else 0.0
    
    return total_volume

def calculate_3day_average(conn, symbol, timestamp, interval_minutes):
    """
    计算过去3天该时间段的平均成交量
    例如：当前是15分钟数据，则计算过去3天同一时刻的15分钟平均量
    """
    cursor = conn.cursor()
    
    # 3天前的时间戳
    three_days_ago = timestamp - (3 * 24 * 60 * 60 * 1000)
    
    # 查询过去3天的聚合数据
    cursor.execute('''
        SELECT AVG(volume)
        FROM fund_monitor_aggregated
        WHERE symbol = ?
        AND interval_type = ?
        AND timestamp > ?
        AND timestamp < ?
    ''', (symbol, f'{interval_minutes}min', three_days_ago, timestamp))
    
    result = cursor.fetchone()
    avg_volume = result[0] if result[0] is not None else None
    
    return avg_volume

def store_abnormal_history(conn, symbol, timestamp, interval_minutes, volume, avg_3day, deviation_percent):
    """
    记录异常数据到历史表
    """
    cursor = conn.cursor()
    collect_time = datetime.fromtimestamp(timestamp / 1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    collect_date = datetime.fromtimestamp(timestamp / 1000, BEIJING_TZ).strftime('%Y-%m-%d')
    interval_type = f'{interval_minutes}min'
    
    # 判断偏差类型
    deviation_type = 'surge' if deviation_percent > 0 else 'drop'
    
    # 判断严重程度
    abs_deviation = abs(deviation_percent)
    if abs_deviation >= 50:
        severity = 'critical'  # 严重
    elif abs_deviation >= 30:
        severity = 'high'  # 高
    else:
        severity = 'medium'  # 中等
    
    try:
        cursor.execute('''
            INSERT INTO fund_monitor_abnormal_history
            (symbol, interval_type, timestamp, collect_time, collect_date, 
             volume, avg_3day, deviation_percent, deviation_type, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, interval_type, timestamp, collect_time, collect_date,
              volume, avg_3day, deviation_percent, deviation_type, severity))
        return True
    except Exception as e:
        logging.error(f'❌ {symbol}: 记录异常历史失败 - {str(e)}')
        return False

def store_aggregated_data(conn, symbol, timestamp, interval_minutes, volume):
    """
    存储聚合数据并检测异常
    """
    cursor = conn.cursor()
    collect_time = datetime.fromtimestamp(timestamp / 1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    interval_type = f'{interval_minutes}min'
    
    # 计算3天平均
    avg_3day = calculate_3day_average(conn, symbol, timestamp, interval_minutes)
    
    # 计算偏差百分比和异常标记
    deviation_percent = None
    is_abnormal = 0
    
    if avg_3day is not None and avg_3day > 0:
        deviation_percent = ((volume - avg_3day) / avg_3day) * 100
        # 检查是否超过阈值
        if abs(deviation_percent) >= CONFIG['threshold_percentage']:
            is_abnormal = 1
            logging.warning(f'🚨 {symbol} {interval_type}: 异常波动 {deviation_percent:+.2f}% (当前={volume:,.0f}, 3日均={avg_3day:,.0f})')
            
            # 记录到异常历史表
            store_abnormal_history(conn, symbol, timestamp, interval_minutes, volume, avg_3day, deviation_percent)
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO fund_monitor_aggregated
            (symbol, timestamp, collect_time, interval_type, volume, avg_3day, deviation_percent, is_abnormal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, timestamp, collect_time, interval_type, volume, avg_3day, deviation_percent, is_abnormal))
        return True
    except Exception as e:
        logging.error(f'❌ {symbol}: 存储聚合数据失败 - {str(e)}')
        return False

def collect_and_process():
    """采集数据并处理"""
    conn = sqlite3.connect(DB_FILE)
    
    logging.info('='*60)
    logging.info(f'开始采集 - {datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")}')
    
    success_count = 0
    fail_count = 0
    
    for symbol in COINS:
        # 1. 从OKEx获取5分钟数据
        timestamp, volume = fetch_volume_from_okex(symbol)
        
        if timestamp is None or volume is None:
            fail_count += 1
            continue
        
        # 2. 存储5分钟原始数据
        if store_5min_data(conn, symbol, timestamp, volume):
            success_count += 1
        else:
            fail_count += 1
            continue
        
        # 3. 计算并存储聚合数据（15/30/60分钟）
        for interval_min in [15, 30, 60]:
            agg_volume = calculate_aggregated_volume(conn, symbol, timestamp, interval_min)
            store_aggregated_data(conn, symbol, timestamp, interval_min, agg_volume)
    
    conn.commit()
    conn.close()
    
    logging.info(f'采集完成: 成功={success_count}, 失败={fail_count}')
    logging.info('='*60)

def main():
    """主函数"""
    logging.info('🚀 资金监控系统采集器启动')
    logging.info(f'监控币种: {len(COINS)}个 - {", ".join(COINS)}')
    
    # 加载配置
    load_config()
    logging.info(f'配置: 阈值={CONFIG["threshold_percentage"]}%, 回看={CONFIG["lookback_days"]}天, 间隔={CONFIG["collection_interval"]}秒')
    
    # 初始化数据库
    init_database()
    
    # 首次立即采集
    try:
        collect_and_process()
    except Exception as e:
        logging.error(f'❌ 首次采集失败: {str(e)}')
    
    # 定时采集循环
    logging.info(f'⏰ 开始定时采集（间隔={CONFIG["collection_interval"]}秒）')
    
    while True:
        try:
            time.sleep(CONFIG['collection_interval'])
            
            # 重新加载配置（支持热更新）
            load_config()
            
            # 采集数据
            collect_and_process()
            
        except KeyboardInterrupt:
            logging.info('👋 收到停止信号，退出采集器')
            break
        except Exception as e:
            logging.error(f'❌ 采集过程出错: {str(e)}')
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == '__main__':
    main()
