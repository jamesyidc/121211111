#!/usr/bin/env python3
"""
加密货币指数采集器
- 27个币种加权指数
- 起始点数: 1000点
- 5分钟K线数据
- 从CoinGecko API获取价格（避免OKX限流）
"""

import sqlite3
import requests
import time
import json
from datetime import datetime, timedelta
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/crypto_index_collector.log'),
        logging.StreamHandler()
    ]
)

# CoinGecko API（免费，无需密钥）
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# 27个币种及其权重
COIN_WEIGHTS = {
    'bitcoin': 0.10,      # BTC 10%
    'ethereum': 0.07,     # ETH 7%
    'ripple': 0.0332,     # XRP 3.32%
    'binancecoin': 0.0332,  # BNB 3.32%
    'solana': 0.0332,     # SOL 3.32%
    'litecoin': 0.0332,   # LTC 3.32%
    'dogecoin': 0.0332,   # DOGE 3.32%
    'sui': 0.0332,        # SUI 3.32%
    'tron': 0.0332,       # TRX 3.32%
    'the-open-network': 0.0332,  # TON 3.32%
    'ethereum-classic': 0.0332,  # ETC 3.32%
    'bitcoin-cash': 0.0332,      # BCH 3.32%
    'hedera-hashgraph': 0.0332,  # HBAR 3.32%
    'stellar': 0.0332,    # XLM 3.32%
    'filecoin': 0.0332,   # FIL 3.32%
    'chainlink': 0.0332,  # LINK 3.32%
    'crypto-com-chain': 0.0332,  # CRO 3.32%
    'polkadot': 0.0332,   # DOT 3.32%
    'aave': 0.0332,       # AAVE 3.32%
    'uniswap': 0.0332,    # UNI 3.32%
    'near': 0.0332,       # NEAR 3.32%
    'aptos': 0.0332,      # APT 3.32%
    'conflux-token': 0.0332,     # CFX 3.32%
    'curve-dao-token': 0.0332,   # CRV 3.32%
    'stacks': 0.0332,     # STX 3.32%
    'lido-dao': 0.0332,   # LDO 3.32%
    'bittensor': 0.0332   # TAO 3.32%
}

# 起始点数
BASE_INDEX = 1000.0

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class CryptoIndexCollector:
    def __init__(self):
        self.db_path = '/home/user/webapp/crypto_data.db'
        self.init_database()
        self.base_prices = None  # 基准价格（首次采集时的价格）
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建指数K线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_index_klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                index_value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp)
            )
        ''')
        
        # 创建基准价格表（用于计算指数变化）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_index_base_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL UNIQUE,
                base_price REAL NOT NULL,
                weight REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建指数位置表（用于存储4h/12h/24h/48h平均位置）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_index_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL UNIQUE,
                position_4h REAL DEFAULT 50.0,
                position_12h REAL DEFAULT 50.0,
                position_24h REAL DEFAULT 50.0,
                position_48h REAL DEFAULT 50.0,
                index_value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("✅ 数据库初始化完成")
    
    def fetch_prices(self):
        """从 OKX API 获取所有币种的当前价格（永续合约）"""
        try:
            # 币种映射：CoinGecko ID -> OKX永续合约symbol
            symbol_mapping = {
                'bitcoin': 'BTC-USDT-SWAP',
                'ethereum': 'ETH-USDT-SWAP',
                'ripple': 'XRP-USDT-SWAP',
                'binancecoin': 'BNB-USDT-SWAP',
                'solana': 'SOL-USDT-SWAP',
                'litecoin': 'LTC-USDT-SWAP',
                'dogecoin': 'DOGE-USDT-SWAP',
                'sui': 'SUI-USDT-SWAP',
                'tron': 'TRX-USDT-SWAP',
                'the-open-network': 'TON-USDT-SWAP',
                'ethereum-classic': 'ETC-USDT-SWAP',
                'bitcoin-cash': 'BCH-USDT-SWAP',
                'hedera-hashgraph': 'HBAR-USDT-SWAP',
                'stellar': 'XLM-USDT-SWAP',
                'filecoin': 'FIL-USDT-SWAP',
                'chainlink': 'LINK-USDT-SWAP',
                'crypto-com-chain': 'CRO-USDT-SWAP',
                'polkadot': 'DOT-USDT-SWAP',
                'aave': 'AAVE-USDT-SWAP',
                'uniswap': 'UNI-USDT-SWAP',
                'near': 'NEAR-USDT-SWAP',
                'aptos': 'APT-USDT-SWAP',
                'conflux-token': 'CFX-USDT-SWAP',
                'curve-dao-token': 'CRV-USDT-SWAP',
                'stacks': 'STX-USDT-SWAP',
                'lido-dao': 'LDO-USDT-SWAP',
                'bittensor': 'TAO-USDT-SWAP'
            }
            
            # 从OKX API逐个获取价格（使用ticker接口）
            prices = {}
            for coin_id, okx_symbol in symbol_mapping.items():
                try:
                    url = f'https://www.okx.com/api/v5/market/ticker?instId={okx_symbol}'
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data['code'] == '0' and data['data']:
                        # OKX ticker返回格式: {'data': [{'last': '89000', ...}]}
                        last_price = float(data['data'][0]['last'])
                        prices[coin_id] = last_price
                    else:
                        logging.warning(f"⚠️  {coin_id} OKX API返回错误: {data.get('msg')}")
                        
                except Exception as e:
                    logging.warning(f"⚠️  获取 {coin_id} 价格失败: {str(e)}")
                    continue
            
            logging.info(f"✅ 成功获取 {len(prices)}/27 个币种价格（从 OKX API）")
            return prices if len(prices) > 0 else None
            
        except Exception as e:
            logging.error(f"❌ 获取价格失败: {str(e)}")
            return None
    
    def load_base_prices(self):
        """加载今日基准价格（北京时间0点）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取今天的日期（北京时间）
        beijing_now = datetime.now(BEIJING_TZ)
        today_date = beijing_now.date().isoformat()
        
        # 币种ID到symbol的映射（用于查询daily_baseline_prices表）
        coin_to_symbol = {
            'bitcoin': 'BTCUSDT',
            'ethereum': 'ETHUSDT',
            'ripple': 'XRPUSDT',
            'binancecoin': 'BNBUSDT',
            'solana': 'SOLUSDT',
            'litecoin': 'LTCUSDT',
            'dogecoin': 'DOGEUSDT',
            'sui': 'SUIUSDT',
            'tron': 'TRXUSDT',
            'the-open-network': 'TONUSDT',
            'ethereum-classic': 'ETCUSDT',
            'bitcoin-cash': 'BCHUSDT',
            'hedera-hashgraph': 'HBARUSDT',
            'stellar': 'XLMUSDT',
            'filecoin': 'FILUSDT',
            'chainlink': 'LINKUSDT',
            'crypto-com-chain': 'CROUSDT',
            'polkadot': 'DOTUSDT',
            'aave': 'AAVEUSDT',
            'uniswap': 'UNIUSDT',
            'near': 'NEARUSDT',
            'aptos': 'APTUSDT',
            'conflux-token': 'CFXUSDT',
            'curve-dao-token': 'CRVUSDT',
            'stacks': 'STXUSDT',
            'lido-dao': 'LDOUSDT',
            'bittensor': 'TAOUSDT'
        }
        
        # 从daily_baseline_prices表读取今日基准价格
        base_prices = {}
        for coin_id, symbol in coin_to_symbol.items():
            cursor.execute('''
                SELECT baseline_price FROM daily_baseline_prices
                WHERE symbol = ? AND baseline_date = ?
            ''', (symbol, today_date))
            row = cursor.fetchone()
            if row:
                base_prices[coin_id] = row[0]
        
        conn.close()
        
        if base_prices:
            logging.info(f"✅ 加载今日基准价格（{today_date}）: {len(base_prices)} 个币种")
            return base_prices
        else:
            logging.warning(f"⚠️  未找到今日基准价格，尝试从crypto_index_base_prices加载")
            # 回退：从旧表加载
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT coin_id, base_price FROM crypto_index_base_prices")
            rows = cursor.fetchall()
            conn.close()
            if rows:
                return {row[0]: row[1] for row in rows}
            return None
    
    def save_base_prices(self, prices):
        """保存今日基准价格（北京时间0点）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取今天的日期（北京时间）
        beijing_now = datetime.now(BEIJING_TZ)
        today_date = beijing_now.date().isoformat()
        baseline_time = beijing_now.strftime('%Y-%m-%d 00:00:00')
        
        # 币种ID到symbol的映射
        coin_to_symbol = {
            'bitcoin': 'BTCUSDT',
            'ethereum': 'ETHUSDT',
            'ripple': 'XRPUSDT',
            'binancecoin': 'BNBUSDT',
            'solana': 'SOLUSDT',
            'litecoin': 'LTCUSDT',
            'dogecoin': 'DOGEUSDT',
            'sui': 'SUIUSDT',
            'tron': 'TRXUSDT',
            'the-open-network': 'TONUSDT',
            'ethereum-classic': 'ETCUSDT',
            'bitcoin-cash': 'BCHUSDT',
            'hedera-hashgraph': 'HBARUSDT',
            'stellar': 'XLMUSDT',
            'filecoin': 'FILUSDT',
            'chainlink': 'LINKUSDT',
            'crypto-com-chain': 'CROUSDT',
            'polkadot': 'DOTUSDT',
            'aave': 'AAVEUSDT',
            'uniswap': 'UNIUSDT',
            'near': 'NEARUSDT',
            'aptos': 'APTUSDT',
            'conflux-token': 'CFXUSDT',
            'curve-dao-token': 'CRVUSDT',
            'stacks': 'STXUSDT',
            'lido-dao': 'LDOUSDT',
            'bittensor': 'TAOUSDT'
        }
        
        # 保存到daily_baseline_prices表
        count = 0
        for coin_id, price in prices.items():
            symbol = coin_to_symbol.get(coin_id)
            if symbol:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO daily_baseline_prices 
                        (symbol, baseline_date, baseline_price, baseline_time)
                        VALUES (?, ?, ?, ?)
                    ''', (symbol, today_date, price, baseline_time))
                    count += 1
                except Exception as e:
                    logging.warning(f"⚠️  保存 {symbol} 基准价格失败: {e}")
        
        # 同时保存到crypto_index_base_prices表（用于向后兼容）
        for coin_id, price in prices.items():
            weight = COIN_WEIGHTS.get(coin_id, 0)
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_index_base_prices (coin_id, base_price, weight)
                VALUES (?, ?, ?)
            ''', (coin_id, price, weight))
        
        conn.commit()
        conn.close()
        logging.info(f"✅ 保存今日基准价格（{today_date}）: {count} 个币种")
    
    def calculate_index(self, current_prices, base_prices):
        """
        计算加权指数
        
        公式: Index = BASE_INDEX * Σ(weight_i * (current_price_i / base_price_i))
        """
        if not current_prices or not base_prices:
            return None
        
        weighted_sum = 0.0
        for coin_id, weight in COIN_WEIGHTS.items():
            if coin_id in current_prices and coin_id in base_prices:
                price_ratio = current_prices[coin_id] / base_prices[coin_id]
                weighted_sum += weight * price_ratio
        
        index_value = BASE_INDEX * weighted_sum
        return round(index_value, 2)
    
    def collect_kline_data(self):
        """采集5分钟K线数据 - 在5分钟内采集多个点计算真实OHLC"""
        try:
            # 每次都重新加载基准价格（确保使用最新的每日基准）
            self.base_prices = self.load_base_prices()
            
            if self.base_prices is None:
                # 首次运行，设置当前价格为基准价格
                current_prices = self.fetch_prices()
                if not current_prices or len(current_prices) < 20:
                    logging.error(f"❌ 价格数据不足: {len(current_prices) if current_prices else 0}/27")
                    return False
                self.save_base_prices(current_prices)
                self.base_prices = current_prices
                logging.info("🎯 首次运行，设置基准价格")
            
            # 在5分钟内采集多个数据点（每30秒采集一次，共10个点）
            index_values = []
            for i in range(10):
                current_prices = self.fetch_prices()
                if current_prices and len(current_prices) >= 20:
                    index_value = self.calculate_index(current_prices, self.base_prices)
                    if index_value:
                        index_values.append(index_value)
                
                if i < 9:  # 最后一次不需要等待
                    time.sleep(30)  # 等待30秒
            
            if not index_values:
                logging.error("❌ 未能采集到有效的指数数据")
                return False
            
            # 计算OHLC
            open_price = index_values[0]      # 开盘价：第一个值
            close_price = index_values[-1]    # 收盘价：最后一个值
            high_price = max(index_values)     # 最高价：最大值
            low_price = min(index_values)      # 最低价：最小值
            index_value = close_price           # 指数值使用收盘价
            
            # 生成时间戳（对齐到5分钟）
            now = datetime.now(BEIJING_TZ)
            timestamp = now.strftime('%Y-%m-%d %H:%M:00')
            
            # 保存K线数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_index_klines 
                (timestamp, open_price, high_price, low_price, close_price, index_value)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, open_price, high_price, low_price, close_price, index_value))
            
            conn.commit()
            
            # 计算并保存平均位置
            self.calculate_average_positions(cursor, timestamp, index_value)
            
            conn.commit()
            conn.close()
            
            logging.info(f"✅ 指数K线采集成功: {timestamp} | O:{open_price:.2f} H:{high_price:.2f} L:{low_price:.2f} C:{close_price:.2f}")
            return True
            
        except Exception as e:
            logging.error(f"❌ 采集K线数据失败: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def calculate_average_positions(self, cursor, timestamp, current_value):
        """
        计算4小时、12小时、24小时、48小时的平均位置
        
        位置 = (当前值 - 周期最低) / (周期最高 - 周期最低) * 100
        """
        try:
            periods = {
                '4h': 4 * 12,    # 4小时 = 48个5分钟K线
                '12h': 12 * 12,  # 12小时 = 144个5分钟K线
                '24h': 24 * 12,  # 24小时 = 288个5分钟K线
                '48h': 48 * 12   # 48小时 = 576个5分钟K线
            }
            
            positions = {}
            for period_name, kline_count in periods.items():
                # 获取周期内的最高价和最低价
                cursor.execute('''
                    SELECT MAX(high_price), MIN(low_price)
                    FROM (
                        SELECT high_price, low_price
                        FROM crypto_index_klines
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                ''', (kline_count,))
                
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    period_high = row[0]
                    period_low = row[1]
                    
                    if period_high > period_low:
                        position = ((current_value - period_low) / (period_high - period_low)) * 100
                        positions[period_name] = round(position, 2)
                    else:
                        positions[period_name] = 50.0  # 如果最高=最低，默认50%
                else:
                    positions[period_name] = 50.0  # 数据不足，默认50%
            
            # 保存到数据库
            cursor.execute('''
                INSERT OR REPLACE INTO crypto_index_positions
                (timestamp, position_4h, position_12h, position_24h, position_48h, index_value)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, positions.get('4h', 50.0), positions.get('12h', 50.0),
                  positions.get('24h', 50.0), positions.get('48h', 50.0), current_value))
            
            logging.info(f"📊 平均位置: 4h={positions.get('4h', 50.0):.1f}% 12h={positions.get('12h', 50.0):.1f}% 24h={positions.get('24h', 50.0):.1f}% 48h={positions.get('48h', 50.0):.1f}%")
            
        except Exception as e:
            logging.error(f"❌ 计算平均位置失败: {str(e)}")
    
    def run_daemon(self, interval=300):
        """
        守护进程模式运行
        
        参数:
            interval: 采集间隔（秒），默认300秒=5分钟
        """
        logging.info(f"🚀 加密货币指数采集器启动，采集间隔: {interval}秒 (5分钟)")
        
        # 首次采集
        logging.info("📊 执行首次指数采集...")
        self.collect_kline_data()
        
        # 定期采集
        while True:
            try:
                time.sleep(interval)
                logging.info("📊 开始采集指数数据...")
                self.collect_kline_data()
                
            except KeyboardInterrupt:
                logging.info("⏹️  收到停止信号，退出采集器")
                break
            except Exception as e:
                logging.error(f"❌ 采集过程出错: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟再继续


if __name__ == '__main__':
    collector = CryptoIndexCollector()
    collector.run_daemon(interval=300)  # 5分钟=300秒
