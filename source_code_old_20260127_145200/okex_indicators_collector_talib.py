#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策-K线指标系统（TA-Lib精确计算版本）
功能：获取OKEx K线数据，使用TA-Lib库精确计算技术指标
数据源：OKEx Perpetual Futures K-line API + TA-Lib计算
北京时间为准
"""

import sqlite3
import requests
import time
import json
from datetime import datetime
import pytz
import numpy as np
from typing import Dict, List, Optional
import talib

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

class OKExTALibCollector:
    """OKEx技术指标采集器（TA-Lib精确计算版本）"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        
        # 使用现有的表结构
        # okex_kline_5m, okex_kline_1h, okex_technical_indicators 已存在
        
        print("✅ Database initialized (using existing tables)")
    
    def fetch_okex_klines(self, symbol: str, bar: str = '5m', limit: int = 100) -> Optional[List]:
        """
        从OKEx获取K线数据
        
        Args:
            symbol: 币种代码（如 BTC-USDT-SWAP）
            bar: K线周期（5m, 1H）
            limit: 获取数量（最多100）
        
        Returns:
            K线数据列表，失败返回None
        """
        url = f"{OKEX_BASE_URL}{OKEX_CANDLES_ENDPOINT}"
        params = {
            'instId': symbol,
            'bar': bar,
            'limit': str(limit)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') == '0' and data.get('data'):
                return data['data']
            else:
                print(f"❌ OKEx API error for {symbol}: {data.get('msg', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching {symbol} klines: {str(e)}")
            return None
    
    def calculate_indicators_with_talib(self, klines: List) -> Optional[Dict]:
        """
        使用TA-Lib精确计算技术指标
        
        Args:
            klines: OKEx K线数据（倒序，最新在前）
        
        Returns:
            技术指标字典
        """
        if not klines or len(klines) < 30:
            return None
        
        # 反转数据（TA-Lib需要正序，最旧在前）
        klines = list(reversed(klines))
        
        # 提取OHLC数据
        closes = np.array([float(k[4]) for k in klines])
        highs = np.array([float(k[2]) for k in klines])
        lows = np.array([float(k[3]) for k in klines])
        
        try:
            # 计算 RSI(14)
            rsi = talib.RSI(closes, timeperiod=14)
            
            # 计算 Parabolic SAR
            sar = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
            
            # 计算 Bollinger Bands (20, 2)
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                closes, 
                timeperiod=20, 
                nbdevup=2, 
                nbdevdn=2, 
                matype=0
            )
            
            # 获取最新值（最后一个非NaN值）
            current_price = closes[-1]
            rsi_value = rsi[-1] if not np.isnan(rsi[-1]) else None
            sar_value = sar[-1] if not np.isnan(sar[-1]) else None
            bb_upper_value = bb_upper[-1] if not np.isnan(bb_upper[-1]) else None
            bb_middle_value = bb_middle[-1] if not np.isnan(bb_middle[-1]) else None
            bb_lower_value = bb_lower[-1] if not np.isnan(bb_lower[-1]) else None
            
            # SAR多空判断
            sar_position = None
            if sar_value:
                sar_position = 'bullish' if current_price > sar_value else 'bearish'
            
            # SAR象限判断（相对于布林带）
            sar_quadrant = None
            if sar_value and bb_upper_value and bb_middle_value and bb_lower_value:
                if sar_value > bb_upper_value:
                    sar_quadrant = 1
                elif sar_value > bb_middle_value:
                    sar_quadrant = 2
                elif sar_value > bb_lower_value:
                    sar_quadrant = 3
                else:
                    sar_quadrant = 4
            
            # 计算SAR连续多空期数（向前回溯）
            sar_count = 0
            if sar_position:
                # 从最新往前数，计算连续相同方向的期数
                for i in range(len(closes) - 1, -1, -1):
                    if not np.isnan(sar[i]):
                        current_position = 'bullish' if closes[i] > sar[i] else 'bearish'
                        if current_position == sar_position:
                            sar_count += 1
                        else:
                            break
            
            return {
                'current_price': current_price,
                'rsi_14': rsi_value,
                'sar': sar_value,
                'sar_position': sar_position,
                'sar_quadrant': sar_quadrant,
                'sar_count': sar_count,
                'bb_upper': bb_upper_value,
                'bb_middle': bb_middle_value,
                'bb_lower': bb_lower_value
            }
            
        except Exception as e:
            print(f"❌ Error calculating indicators: {str(e)}")
            return None
    
    def save_kline_to_db(self, symbol: str, klines: List, timeframe: str):
        """保存K线数据到数据库"""
        table_name = 'okex_kline_5m' if timeframe == '5m' else 'okex_kline_1h'
        
        for kline in klines:
            timestamp = int(kline[0])
            open_price = float(kline[1])
            high = float(kline[2])
            low = float(kline[3])
            close = float(kline[4])
            volume = float(kline[5])
            vol_currency = float(kline[6]) if len(kline) > 6 else None
            
            # 计算振幅和涨跌幅（仅5分钟）
            amplitude = None
            change_pct = None
            if timeframe == '5m':
                amplitude = ((high - low) / low * 100) if low > 0 else 0
                change_pct = ((close - open_price) / open_price * 100) if open_price > 0 else 0
            
            try:
                if timeframe == '5m':
                    self.cursor.execute(f'''
                        INSERT OR REPLACE INTO {table_name}
                        (symbol, timestamp, open, high, low, close, volume, vol_currency, amplitude, change_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, timestamp, open_price, high, low, close, volume, vol_currency, amplitude, change_pct))
                else:
                    self.cursor.execute(f'''
                        INSERT OR REPLACE INTO {table_name}
                        (symbol, timestamp, open, high, low, close, volume, vol_currency)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, timestamp, open_price, high, low, close, volume, vol_currency))
            except Exception as e:
                print(f"❌ Error saving kline: {str(e)}")
        
        self.conn.commit()
    
    def save_indicator_to_db(self, symbol: str, timeframe: str, indicators: Dict, record_time: str):
        """保存技术指标到数据库"""
        try:
            # 生成SAR计数标签
            sar_count_label = None
            if indicators.get('sar_position') and indicators.get('sar_count'):
                position_cn = '多头' if indicators['sar_position'] == 'bullish' else '空头'
                sar_count_label = f"{position_cn}{indicators['sar_count']:02d}"  # 例如：多头05, 空头12
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO okex_technical_indicators
                (symbol, timeframe, current_price, rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
                 bb_upper, bb_middle, bb_lower, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe,
                indicators['current_price'],
                indicators['rsi_14'],
                indicators['sar'],
                indicators['sar_position'],
                indicators['sar_quadrant'],
                sar_count_label,
                indicators['bb_upper'],
                indicators['bb_middle'],
                indicators['bb_lower'],
                record_time
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error saving indicator: {str(e)}")
            return False
    
    def collect_symbol_indicators(self, symbol: str):
        """采集单个币种的技术指标"""
        beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📊 {symbol}")
        
        success_count = 0
        
        for timeframe, bar in [('5m', '5m'), ('1h', '1H')]:
            # 获取K线数据
            klines = self.fetch_okex_klines(symbol, bar, limit=100)
            if not klines:
                print(f"  ❌ {timeframe} - Failed to fetch klines")
                continue
            
            # 保存K线数据
            self.save_kline_to_db(symbol, klines, timeframe)
            
            # 使用TA-Lib计算指标
            indicators = self.calculate_indicators_with_talib(klines)
            if not indicators:
                print(f"  ❌ {timeframe} - Failed to calculate indicators")
                continue
            
            # 保存指标
            if self.save_indicator_to_db(symbol, timeframe, indicators, beijing_time):
                print(f"  ✅ {timeframe}: Price=${indicators['current_price']:.2f}, "
                      f"RSI={indicators['rsi_14']:.1f}, "
                      f"SAR={indicators['sar']:.4f} [{indicators['sar_position']}]")
                success_count += 1
            
            # 延迟避免请求过快
            time.sleep(0.5)
        
        return success_count
    
    def collect_all_indicators(self):
        """采集所有币种的技术指标"""
        beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*70}")
        print(f"开始采集 OKEx 技术指标（TA-Lib精确计算版）")
        print(f"采集时间: {beijing_time}")
        print(f"币种数量: {len(SYMBOLS)}")
        print(f"计算方式: TA-Lib库（与专业交易平台算法一致）")
        print(f"{'='*70}\n")
        
        total_success = 0
        total_fail = 0
        
        for symbol in SYMBOLS:
            success_count = self.collect_symbol_indicators(symbol)
            total_success += success_count
            total_fail += (2 - success_count)  # 每个币种2个周期
        
        print(f"\n{'='*70}")
        print(f"采集完成:")
        print(f"  成功: {total_success} 个指标")
        print(f"  失败: {total_fail} 个")
        print(f"  数据库: {DB_FILE}")
        print(f"{'='*70}\n")
        
        return total_success, total_fail
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

def main():
    """主函数"""
    print("="*70)
    print("OKEx K线指标系统 - TA-Lib精确计算版")
    print("数据源: OKEx K-line API")
    print("计算方式: TA-Lib库精确计算（与交易所算法一致）")
    print("="*70)
    
    collector = OKExTALibCollector()
    
    try:
        # 执行一次完整采集
        total_success, total_fail = collector.collect_all_indicators()
        
        print(f"\n✅ 采集完成: {total_success}个指标已保存到数据库")
        print(f"   使用TA-Lib精确计算，确保与专业交易平台数据一致")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  采集被用户中断")
    except Exception as e:
        print(f"\n\n❌ 采集过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close()
        print("\n✅ 采集器已关闭")

if __name__ == "__main__":
    main()
