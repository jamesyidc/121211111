#!/usr/bin/env python3
"""
加密货币指数采集器
- 27个币种加权指数
- 起始点数: 1000点
- 5分钟K线数据
- 从CoinGecko API获取价格（免费，无限流）
- 支持4小时、12小时、24小时、48小时平均位置计算
"""

import requests
import time
import json
import sys
import os
from datetime import datetime, timedelta
import logging
import pytz

# 添加source_code到路径
sys.path.insert(0, os.path.dirname(__file__))
from crypto_index_jsonl_manager import CryptoIndexJSONLManager

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
        """初始化采集器"""
        self.manager = CryptoIndexJSONLManager()
        logging.info('✅ JSONL管理器初始化完成')
        self.base_prices = None  # 基准价格（首次采集时的价格）
    
    def fetch_prices_from_coingecko(self):
        """
        从CoinGecko API获取所有币种的当前价格
        
        优点：
        - 免费，无需API密钥
        - 无限流限制
        - 一次请求获取所有币种价格
        """
        try:
            # 构建币种ID列表
            coin_ids = ','.join(COIN_WEIGHTS.keys())
            
            # 请求参数
            params = {
                'ids': coin_ids,
                'vs_currencies': 'usd',
                'precision': '8'  # 8位小数精度
            }
            
            # 发送请求
            response = requests.get(COINGECKO_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 解析价格数据
            prices = {}
            for coin_id in COIN_WEIGHTS.keys():
                if coin_id in data and 'usd' in data[coin_id]:
                    prices[coin_id] = float(data[coin_id]['usd'])
            
            if len(prices) >= 20:  # 至少要有20个币种的价格
                logging.info(f"✅ 成功获取 {len(prices)}/27 个币种价格（CoinGecko API）")
                return prices
            else:
                logging.warning(f"⚠️  价格数据不足: {len(prices)}/27")
                return None
            
        except Exception as e:
            logging.error(f"❌ 获取CoinGecko价格失败: {str(e)}")
            return None
    
    def load_base_prices(self):
        """加载基准价格从JSONL"""
        base_prices = self.manager.get_base_prices()
        if base_prices:
            logging.info(f"✅ 加载基准价格: {len(base_prices)} 个币种")
            return base_prices
        return None
    
    def save_base_prices(self, prices):
        """保存基准价格到JSONL"""
        for coin_id, price in prices.items():
            self.manager.set_base_price(coin_id, price)
        logging.info(f"💾 保存基准价格: {len(prices)} 个币种")
    
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
    
    def calculate_average_positions(self, timestamp, current_value):
        """
        计算4小时、12小时、24小时、48小时的平均位置
        
        位置 = (当前值 - 周期最低) / (周期最高 - 周期最低) * 100
        
        返回: {
            'position_4h': 75.5,
            'position_12h': 62.3,
            'position_24h': 58.1,
            'position_48h': 55.2
        }
        """
        try:
            periods = {
                'position_4h': 4,     # 4小时
                'position_12h': 12,   # 12小时
                'position_24h': 24,   # 24小时
                'position_48h': 48    # 48小时
            }
            
            positions = {}
            now = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            
            for position_name, hours in periods.items():
                # 计算时间范围
                start_time = now - timedelta(hours=hours)
                start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                
                # 获取周期内的K线数据
                klines = self.manager.get_klines_by_time_range(start_time_str, timestamp)
                
                if len(klines) >= 2:  # 至少需要2个数据点
                    # 找出周期内的最高价和最低价
                    period_high = max([k['high_price'] for k in klines])
                    period_low = min([k['low_price'] for k in klines])
                    
                    if period_high > period_low:
                        # 计算当前位置
                        position = ((current_value - period_low) / (period_high - period_low)) * 100
                        positions[position_name] = round(position, 2)
                    else:
                        positions[position_name] = 50.0  # 如果最高=最低，默认50%
                else:
                    positions[position_name] = 50.0  # 数据不足，默认50%
            
            logging.info(f"📊 平均位置: 4h={positions.get('position_4h', 50.0):.1f}% "
                        f"12h={positions.get('position_12h', 50.0):.1f}% "
                        f"24h={positions.get('position_24h', 50.0):.1f}% "
                        f"48h={positions.get('position_48h', 50.0):.1f}%")
            
            return positions
            
        except Exception as e:
            logging.error(f"❌ 计算平均位置失败: {str(e)}")
            return {
                'position_4h': 50.0,
                'position_12h': 50.0,
                'position_24h': 50.0,
                'position_48h': 50.0
            }
    
    def collect_kline_data(self):
        """采集5分钟K线数据 - 在5分钟内采集多个点计算真实OHLC"""
        try:
            # 每次都重新加载基准价格（确保使用最新的每日基准）
            self.base_prices = self.load_base_prices()
            
            if self.base_prices is None:
                # 首次运行，设置当前价格为基准价格
                current_prices = self.fetch_prices_from_coingecko()
                if not current_prices or len(current_prices) < 20:
                    logging.error(f"❌ 价格数据不足: {len(current_prices) if current_prices else 0}/27")
                    return False
                self.save_base_prices(current_prices)
                self.base_prices = current_prices
                logging.info("🎯 首次运行，设置基准价格")
            
            # 在5分钟内采集多个数据点（每30秒采集一次，共10个点）
            index_values = []
            for i in range(10):
                current_prices = self.fetch_prices_from_coingecko()
                if current_prices and len(current_prices) >= 20:
                    index_value = self.calculate_index(current_prices, self.base_prices)
                    if index_value:
                        index_values.append(index_value)
                        logging.info(f"   📈 采样点 {i+1}/10: {index_value:.2f}")
                
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
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 计算平均位置
            positions = self.calculate_average_positions(timestamp, close_price)
            
            # 保存K线数据到JSONL
            kline_data = {
                'timestamp': timestamp,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'index_value': index_value,
                'position_4h': positions.get('position_4h', 50.0),
                'position_12h': positions.get('position_12h', 50.0),
                'position_24h': positions.get('position_24h', 50.0),
                'position_48h': positions.get('position_48h', 50.0)
            }
            
            self.manager.save_kline(kline_data)
            
            logging.info(f"✅ 指数K线采集成功: {timestamp}")
            logging.info(f"   📊 OHLC: O:{open_price:.2f} H:{high_price:.2f} L:{low_price:.2f} C:{close_price:.2f}")
            logging.info(f"   📍 位置: 4h={positions.get('position_4h', 50.0):.1f}% "
                        f"12h={positions.get('position_12h', 50.0):.1f}% "
                        f"24h={positions.get('position_24h', 50.0):.1f}% "
                        f"48h={positions.get('position_48h', 50.0):.1f}%")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 采集K线数据失败: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def run_daemon(self, interval=300):
        """
        守护进程模式运行
        
        参数:
            interval: 采集间隔（秒），默认300秒=5分钟
        """
        logging.info(f"🚀 加密货币指数采集器启动")
        logging.info(f"   ⏱️  采集间隔: {interval}秒 (5分钟)")
        logging.info(f"   💱 数据源: CoinGecko API（免费，无限流）")
        logging.info(f"   📊 监控币种: 27个")
        logging.info(f"   📈 基准点数: {BASE_INDEX}")
        
        # 首次采集
        logging.info("📊 执行首次指数采集...")
        self.collect_kline_data()
        
        # 定期采集
        while True:
            try:
                time.sleep(interval)
                logging.info("=" * 60)
                logging.info("📊 开始新一轮指数采集...")
                self.collect_kline_data()
                
            except KeyboardInterrupt:
                logging.info("⏹️  收到停止信号，退出采集器")
                break
            except Exception as e:
                logging.error(f"❌ 采集过程出错: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                time.sleep(60)  # 出错后等待1分钟再继续


if __name__ == '__main__':
    collector = CryptoIndexCollector()
    collector.run_daemon(interval=300)  # 5分钟=300秒
