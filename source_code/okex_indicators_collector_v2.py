#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策-K线指标系统 V2（使用专业技术指标库）
功能：从OKEx获取K线数据，使用pandas_ta精确计算技术指标
数据源：OKEx永续合约API
时间：北京时间（Asia/Shanghai）
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import pandas_ta as ta
from typing import Dict, List, Tuple, Optional

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# OKEx API配置
OKEX_BASE_URL = "https://www.okx.com"
OKEX_CANDLES_ENDPOINT = "/api/v5/market/candles"

# 监控的币种列表（27个永续合约）
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# 数据库配置
DB_FILE = 'crypto_data.db'

class OKExIndicatorsCollectorV2:
    """OKEx技术指标采集器 V2 - 使用pandas_ta专业库"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化数据库表（使用现有表结构）"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        print("✅ 数据库连接成功")
    
    def fetch_okex_candles(self, inst_id: str, bar: str, limit: int = 100) -> List[List]:
        """
        从OKEx获取K线数据
        
        Args:
            inst_id: 合约ID（如BTC-USDT-SWAP）
            bar: K线周期（5m, 1H等）
            limit: 获取数量
        
        Returns:
            K线数据列表
        """
        url = f"{OKEX_BASE_URL}{OKEX_CANDLES_ENDPOINT}"
        params = {
            'instId': inst_id,
            'bar': bar,
            'limit': str(limit)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0':
                return data.get('data', [])
            else:
                print(f"❌ OKEx API错误: {data.get('msg', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"❌ 获取{inst_id} {bar}K线失败: {e}")
            return []
    
    def calculate_technical_indicators(self, candles: List[List]) -> Dict:
        """
        使用pandas_ta计算技术指标
        
        Args:
            candles: OKEx K线数据 [timestamp, open, high, low, close, vol, volCcy]
        
        Returns:
            包含所有技术指标的字典
        """
        if not candles or len(candles) < 20:
            return None
        
        # 将K线数据转换为DataFrame（注意OKEx返回的是从新到旧，需要反转）
        candles.reverse()  # 从旧到新排序
        
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy'])
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms', utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert(BEIJING_TZ)  # 转换为北京时间
        
        # 转换为数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # 使用pandas_ta计算技术指标
        # 1. RSI (14周期)
        df['rsi_14'] = ta.rsi(df['close'], length=14)
        
        # 2. SAR (抛物线转向)
        sar = ta.psar(df['high'], df['low'], df['close'])
        df['sar'] = sar['PSARl_0.02_0.2'].fillna(sar['PSARs_0.02_0.2'])  # 合并long和short
        df['sar_long'] = sar['PSARl_0.02_0.2']  # SAR在下方（多头）
        df['sar_short'] = sar['PSARs_0.02_0.2']  # SAR在上方（空头）
        
        # 3. 布林带 (20周期, 2倍标准差)
        bbands = ta.bbands(df['close'], length=20, std=2)
        df['bb_upper'] = bbands['BBU_20_2.0']
        df['bb_middle'] = bbands['BBM_20_2.0']
        df['bb_lower'] = bbands['BBL_20_2.0']
        
        # 获取最新一根K线的指标
        latest = df.iloc[-1]
        
        # 判断SAR多空
        if pd.notna(latest['sar_long']):
            sar_position = 'bullish'  # SAR在下方，多头
            sar_value = latest['sar_long']
        elif pd.notna(latest['sar_short']):
            sar_position = 'bearish'  # SAR在上方，空头
            sar_value = latest['sar_short']
        else:
            sar_position = None
            sar_value = latest['sar']
        
        # 判断SAR象限（相对布林带）
        if pd.notna(sar_value) and pd.notna(latest['bb_upper']) and pd.notna(latest['bb_middle']) and pd.notna(latest['bb_lower']):
            if sar_value > latest['bb_upper']:
                sar_quadrant = 1
            elif sar_value > latest['bb_middle']:
                sar_quadrant = 2
            elif sar_value > latest['bb_lower']:
                sar_quadrant = 3
            else:
                sar_quadrant = 4
        else:
            sar_quadrant = None
        
        # 计算连续SAR位置数量
        consecutive_count = self.calculate_consecutive_sar(df, sar_position)
        
        # 计算5分钟振幅和涨跌幅
        amplitude = ((latest['high'] - latest['low']) / latest['low'] * 100) if latest['low'] > 0 else 0
        change_pct = ((latest['close'] - latest['open']) / latest['open'] * 100) if latest['open'] > 0 else 0
        
        return {
            'timestamp': latest['timestamp'],
            'current_price': latest['close'],
            'rsi_14': latest['rsi_14'] if pd.notna(latest['rsi_14']) else None,
            'sar': sar_value if pd.notna(sar_value) else None,
            'sar_position': sar_position,
            'sar_quadrant': sar_quadrant,
            'sar_count': consecutive_count,
            'bb_upper': latest['bb_upper'] if pd.notna(latest['bb_upper']) else None,
            'bb_middle': latest['bb_middle'] if pd.notna(latest['bb_middle']) else None,
            'bb_lower': latest['bb_lower'] if pd.notna(latest['bb_lower']) else None,
            'amplitude': round(amplitude, 4),
            'change_pct': round(change_pct, 4),
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'close': latest['close'],
            'volume': latest['volume']
        }
    
    def calculate_consecutive_sar(self, df: pd.DataFrame, current_position: str) -> int:
        """
        计算连续相同SAR位置的K线数量
        
        Args:
            df: 包含SAR数据的DataFrame
            current_position: 当前SAR位置（bullish/bearish）
        
        Returns:
            连续计数
        """
        if current_position is None:
            return 1
        
        count = 0
        # 从最后一根K线向前遍历
        for i in range(len(df) - 1, -1, -1):
            row = df.iloc[i]
            
            # 判断该K线的SAR位置
            if pd.notna(row['sar_long']):
                pos = 'bullish'
            elif pd.notna(row['sar_short']):
                pos = 'bearish'
            else:
                pos = None
            
            if pos == current_position:
                count += 1
            else:
                break
        
        return max(1, count)
    
    def save_kline_5m(self, symbol: str, candle_data: Dict):
        """保存5分钟K线数据"""
        timestamp_ms = int(candle_data['timestamp'].timestamp() * 1000)
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO okex_kline_5m 
            (symbol, timestamp, open, high, low, close, volume, vol_currency, amplitude, change_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, timestamp_ms, candle_data['open'], candle_data['high'], 
              candle_data['low'], candle_data['close'], candle_data['volume'], 
              0, candle_data['amplitude'], candle_data['change_pct']))
    
    def save_technical_indicators(self, symbol: str, timeframe: str, indicators: Dict):
        """保存技术指标数据"""
        position_label = "空头" if indicators['sar_position'] == 'bearish' else "多头"
        count_label = f"{position_label}{indicators['sar_count']:02d}"
        
        beijing_time = indicators['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        self.cursor.execute('''
            INSERT OR REPLACE INTO okex_technical_indicators
            (symbol, timeframe, current_price, rsi_14, sar, sar_position, sar_quadrant,
             sar_count_label, bb_upper, bb_middle, bb_lower, record_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, timeframe, indicators['current_price'], indicators['rsi_14'], 
              indicators['sar'], indicators['sar_position'], indicators['sar_quadrant'],
              count_label, indicators['bb_upper'], indicators['bb_middle'], 
              indicators['bb_lower'], beijing_time))
    
    def collect_symbol(self, symbol: str):
        """采集单个币种的数据"""
        print(f"📊 采集{symbol}...")
        
        # 1. 获取5分钟K线
        candles_5m = self.fetch_okex_candles(symbol, '5m', 100)
        if candles_5m and len(candles_5m) >= 20:
            indicators_5m = self.calculate_technical_indicators(candles_5m.copy())
            if indicators_5m:
                self.save_kline_5m(symbol, indicators_5m)
                self.save_technical_indicators(symbol, '5m', indicators_5m)
                print(f"   ✅ 5m: RSI={indicators_5m['rsi_14']:.2f} SAR={indicators_5m['sar_position']} 计数={indicators_5m['sar_count']}")
        
        # 2. 获取1小时K线
        candles_1h = self.fetch_okex_candles(symbol, '1H', 100)
        if candles_1h and len(candles_1h) >= 20:
            indicators_1h = self.calculate_technical_indicators(candles_1h.copy())
            if indicators_1h:
                self.save_technical_indicators(symbol, '1h', indicators_1h)
                print(f"   ✅ 1h: RSI={indicators_1h['rsi_14']:.2f} SAR={indicators_1h['sar_position']} 计数={indicators_1h['sar_count']}")
        
        self.conn.commit()
        print(f"✅ {symbol} 采集完成\n")
    
    def run_collection(self):
        """运行完整采集周期"""
        print(f"\n{'='*70}")
        print(f"🚀 OKEx K线指标采集系统 V2 - 使用pandas_ta专业计算")
        print(f"⏰ 开始时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        print(f"📊 币种数量: {len(SYMBOLS)}个")
        print(f"{'='*70}\n")
        
        success = 0
        failed = 0
        
        for symbol in SYMBOLS:
            try:
                self.collect_symbol(symbol)
                success += 1
                time.sleep(0.3)  # 避免API限流
            except Exception as e:
                print(f"❌ {symbol} 失败: {e}\n")
                failed += 1
        
        print(f"\n{'='*70}")
        print(f"✅ 采集完成: 成功 {success}/{len(SYMBOLS)}, 失败 {failed}")
        print(f"⏰ 完成时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
        print(f"{'='*70}\n")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.commit()
            self.conn.close()


def main():
    """主函数"""
    collector = OKExIndicatorsCollectorV2()
    try:
        collector.run_collection()
    except KeyboardInterrupt:
        print("\n⚠️ 收到中断信号")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close()


if __name__ == '__main__':
    main()
