#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级技术指标采集系统
功能：采集并计算5分钟/1小时K线的技术指标（RSI、SAR、MACD等）
数据源：Binance WebSocket/REST API
"""

import sqlite3
import requests
import time
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# Binance API配置
BINANCE_BASE_URL = "https://api.binance.com"
BINANCE_KLINE_ENDPOINT = "/api/v3/klines"

# 监控的币种列表（27个永续合约）
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'DOGEUSDT', 'ADAUSDT', 'SHIBUSDT', 'LINKUSDT', 'AVAXUSDT',
    'DOTUSDT', 'MATICUSDT', 'UNIUSDT', 'LTCUSDT', 'ETCUSDT',
    'XLMUSDT', 'ATOMUSDT', 'ICPUSDT', 'APTUSDT', 'FILUSDT',
    'NEARUSDT', 'ARBUSDT', 'OPUSDT', 'STXUSDT', 'INJUSDT',
    'LDOUSDT', 'VETUSDT', 'OKBUSDT', 'CFXUSDT', 'CRVUSDT'
]

# 数据库表结构
DB_FILE = 'crypto_data.db'

class TechnicalIndicatorsCollector:
    """技术指标采集器"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        
        # 创建5分钟K线表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kline_5m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                close_time INTEGER NOT NULL,
                quote_volume REAL,
                trades INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # 创建1小时K线表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kline_1h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                close_time INTEGER NOT NULL,
                quote_volume REAL,
                trades INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # 创建技术指标表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                rsi_14 REAL,
                rsi_6 REAL,
                sar REAL,
                sar_trend TEXT,
                sar_quadrant INTEGER,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                bb_width REAL,
                atr_14 REAL,
                record_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, record_time)
            )
        ''')
        
        # 创建5分钟统计表（震荡、涨跌）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS kline_5m_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                consecutive_no_new_low INTEGER DEFAULT 0,
                consecutive_low_volatility INTEGER DEFAULT 0,
                avg_change_3bars REAL,
                avg_range_3bars REAL,
                last_new_low_time TIMESTAMP,
                record_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, record_time)
            )
        ''')
        
        # 创建索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_kline_5m_symbol_time ON kline_5m(symbol, timestamp DESC)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_kline_1h_symbol_time ON kline_1h(symbol, timestamp DESC)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_technical_symbol_time ON technical_indicators(symbol, timeframe, record_time DESC)')
        
        self.conn.commit()
        print("✅ 数据库初始化完成")
    
    def fetch_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """
        从Binance获取K线数据
        
        Args:
            symbol: 交易对（如BTCUSDT）
            interval: 时间周期（5m, 1h等）
            limit: 获取数量（默认100）
        
        Returns:
            K线数据列表
        """
        url = f"{BINANCE_BASE_URL}{BINANCE_KLINE_ENDPOINT}"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            klines = response.json()
            return klines
        except Exception as e:
            print(f"❌ 获取{symbol} {interval}K线失败: {e}")
            return []
    
    def save_klines(self, symbol: str, klines: List[List], table: str):
        """
        保存K线数据到数据库
        
        Args:
            symbol: 交易对
            klines: K线数据
            table: 表名（kline_5m或kline_1h）
        """
        if not klines:
            return
        
        for kline in klines:
            try:
                timestamp = kline[0]  # 开盘时间
                open_price = float(kline[1])
                high = float(kline[2])
                low = float(kline[3])
                close = float(kline[4])
                volume = float(kline[5])
                close_time = kline[6]
                quote_volume = float(kline[7])
                trades = int(kline[8])
                
                self.cursor.execute(f'''
                    INSERT OR REPLACE INTO {table} 
                    (symbol, timestamp, open, high, low, close, volume, close_time, quote_volume, trades)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timestamp, open_price, high, low, close, volume, close_time, quote_volume, trades))
            except Exception as e:
                print(f"❌ 保存K线数据失败: {e}")
                continue
        
        self.conn.commit()
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        计算RSI指标
        
        Args:
            prices: 收盘价列表
            period: 周期（默认14）
        
        Returns:
            RSI值（0-100）
        """
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_sar(self, highs: List[float], lows: List[float], 
                     acceleration: float = 0.02, maximum: float = 0.2) -> Tuple[float, str, int]:
        """
        计算SAR指标（抛物线转向）
        
        Args:
            highs: 最高价列表
            lows: 最低价列表
            acceleration: 加速因子
            maximum: 最大加速因子
        
        Returns:
            (SAR值, 趋势方向, 象限)
        """
        if len(highs) < 5 or len(lows) < 5:
            return None, None, None
        
        # 简化版SAR计算
        current_high = highs[-1]
        current_low = lows[-1]
        prev_high = max(highs[-5:])
        prev_low = min(lows[-5:])
        
        # 判断趋势
        if current_high > prev_high:
            sar = prev_low
            trend = "bullish"
        else:
            sar = prev_high
            trend = "bearish"
        
        # 判断象限（相对于当前价格）
        current_price = (current_high + current_low) / 2
        if sar < current_price * 0.95:
            quadrant = 1  # 第一象限（远低于价格）
        elif sar < current_price:
            quadrant = 2  # 第二象限（略低于价格）
        elif sar < current_price * 1.05:
            quadrant = 3  # 第三象限（略高于价格）
        else:
            quadrant = 4  # 第四象限（远高于价格）
        
        return round(sar, 6), trend, quadrant
    
    def calculate_macd(self, prices: List[float], 
                      fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """
        计算MACD指标
        
        Args:
            prices: 收盘价列表
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期
        
        Returns:
            (MACD, Signal, Histogram)
        """
        if len(prices) < slow + signal:
            return None, None, None
        
        prices_series = pd.Series(prices)
        ema_fast = prices_series.ewm(span=fast).mean()
        ema_slow = prices_series.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return round(macd.iloc[-1], 6), round(signal_line.iloc[-1], 6), round(histogram.iloc[-1], 6)
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std: float = 2.0):
        """
        计算布林带指标
        
        Args:
            prices: 收盘价列表
            period: 周期
            std: 标准差倍数
        
        Returns:
            (上轨, 中轨, 下轨, 带宽)
        """
        if len(prices) < period:
            return None, None, None, None
        
        prices_series = pd.Series(prices)
        middle = prices_series.rolling(window=period).mean()
        std_dev = prices_series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = ((upper - lower) / middle * 100)
        
        return (round(upper.iloc[-1], 6), round(middle.iloc[-1], 6), 
                round(lower.iloc[-1], 6), round(width.iloc[-1], 2))
    
    def calculate_atr(self, highs: List[float], lows: List[float], 
                     closes: List[float], period: int = 14) -> float:
        """
        计算ATR指标（真实波幅）
        
        Args:
            highs: 最高价列表
            lows: 最低价列表
            closes: 收盘价列表
            period: 周期
        
        Returns:
            ATR值
        """
        if len(highs) < period + 1:
            return None
        
        tr_list = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)
        
        atr = np.mean(tr_list[-period:])
        return round(atr, 6)
    
    def analyze_5m_stats(self, symbol: str) -> Dict:
        """
        分析5分钟统计数据
        - 连续5个5分钟K线不创新低
        - 连续3个震荡≤0.5%，涨跌<0.25%
        
        Args:
            symbol: 交易对
        
        Returns:
            统计数据字典
        """
        # 获取最近20根5分钟K线
        self.cursor.execute('''
            SELECT high, low, close, timestamp
            FROM kline_5m
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 20
        ''', (symbol,))
        
        rows = self.cursor.fetchall()
        if len(rows) < 10:
            return None
        
        rows.reverse()  # 按时间正序
        
        # 计算连续不创新低
        consecutive_no_new_low = 0
        lowest_price = float('inf')
        
        for i in range(len(rows) - 5, len(rows)):
            low = rows[i][1]
            if low < lowest_price:
                lowest_price = low
                consecutive_no_new_low = 0
            else:
                consecutive_no_new_low += 1
        
        # 计算连续低震荡
        consecutive_low_volatility = 0
        changes = []
        ranges = []
        
        for i in range(-3, 0):
            high = rows[i][0]
            low = rows[i][1]
            close = rows[i][2]
            prev_close = rows[i-1][2]
            
            change = abs((close - prev_close) / prev_close * 100)
            range_pct = (high - low) / low * 100
            
            changes.append(change)
            ranges.append(range_pct)
            
            if range_pct <= 0.5 and change < 0.25:
                consecutive_low_volatility += 1
        
        return {
            'consecutive_no_new_low': consecutive_no_new_low,
            'consecutive_low_volatility': consecutive_low_volatility,
            'avg_change_3bars': round(np.mean(changes), 4),
            'avg_range_3bars': round(np.mean(ranges), 4)
        }
    
    def collect_and_calculate(self, symbol: str):
        """
        采集并计算指定币种的技术指标
        
        Args:
            symbol: 交易对
        """
        now = datetime.now(BEIJING_TZ)
        
        # 1. 获取5分钟K线（最近100根）
        print(f"📊 采集{symbol} 5分钟K线...")
        klines_5m = self.fetch_klines(symbol, '5m', 100)
        if klines_5m:
            self.save_klines(symbol, klines_5m, 'kline_5m')
        
        # 2. 获取1小时K线（最近100根）
        print(f"📊 采集{symbol} 1小时K线...")
        klines_1h = self.fetch_klines(symbol, '1h', 100)
        if klines_1h:
            self.save_klines(symbol, klines_1h, 'kline_1h')
        
        # 3. 计算5分钟技术指标
        if klines_5m and len(klines_5m) >= 30:
            closes_5m = [float(k[4]) for k in klines_5m]
            highs_5m = [float(k[2]) for k in klines_5m]
            lows_5m = [float(k[3]) for k in klines_5m]
            
            rsi_5m = self.calculate_rsi(closes_5m, 14)
            sar_5m, sar_trend_5m, sar_quad_5m = self.calculate_sar(highs_5m, lows_5m)
            macd_5m, signal_5m, hist_5m = self.calculate_macd(closes_5m)
            bb_upper_5m, bb_mid_5m, bb_lower_5m, bb_width_5m = self.calculate_bollinger_bands(closes_5m)
            atr_5m = self.calculate_atr(highs_5m, lows_5m, closes_5m)
            
            # 保存5分钟技术指标
            self.cursor.execute('''
                INSERT OR REPLACE INTO technical_indicators
                (symbol, timeframe, rsi_14, sar, sar_trend, sar_quadrant, 
                 macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower, bb_width, atr_14, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, '5m', rsi_5m, sar_5m, sar_trend_5m, sar_quad_5m,
                  macd_5m, signal_5m, hist_5m, bb_upper_5m, bb_mid_5m, bb_lower_5m, bb_width_5m, atr_5m,
                  now.strftime('%Y-%m-%d %H:%M:%S')))
        
        # 4. 计算1小时技术指标
        if klines_1h and len(klines_1h) >= 30:
            closes_1h = [float(k[4]) for k in klines_1h]
            highs_1h = [float(k[2]) for k in klines_1h]
            lows_1h = [float(k[3]) for k in klines_1h]
            
            rsi_1h = self.calculate_rsi(closes_1h, 14)
            sar_1h, sar_trend_1h, sar_quad_1h = self.calculate_sar(highs_1h, lows_1h)
            macd_1h, signal_1h, hist_1h = self.calculate_macd(closes_1h)
            bb_upper_1h, bb_mid_1h, bb_lower_1h, bb_width_1h = self.calculate_bollinger_bands(closes_1h)
            atr_1h = self.calculate_atr(highs_1h, lows_1h, closes_1h)
            
            # 保存1小时技术指标
            self.cursor.execute('''
                INSERT OR REPLACE INTO technical_indicators
                (symbol, timeframe, rsi_14, sar, sar_trend, sar_quadrant,
                 macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower, bb_width, atr_14, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, '1h', rsi_1h, sar_1h, sar_trend_1h, sar_quad_1h,
                  macd_1h, signal_1h, hist_1h, bb_upper_1h, bb_mid_1h, bb_lower_1h, bb_width_1h, atr_1h,
                  now.strftime('%Y-%m-%d %H:%M:%S')))
        
        # 5. 分析5分钟统计数据
        stats_5m = self.analyze_5m_stats(symbol)
        if stats_5m:
            self.cursor.execute('''
                INSERT OR REPLACE INTO kline_5m_stats
                (symbol, consecutive_no_new_low, consecutive_low_volatility, 
                 avg_change_3bars, avg_range_3bars, record_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, stats_5m['consecutive_no_new_low'], stats_5m['consecutive_low_volatility'],
                  stats_5m['avg_change_3bars'], stats_5m['avg_range_3bars'],
                  now.strftime('%Y-%m-%d %H:%M:%S')))
        
        self.conn.commit()
        print(f"✅ {symbol} 技术指标计算完成")
    
    def run_collection_cycle(self):
        """运行一个完整的采集周期"""
        print(f"\n{'='*60}")
        print(f"🚀 开始采集技术指标 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        success_count = 0
        fail_count = 0
        
        for symbol in SYMBOLS:
            try:
                self.collect_and_calculate(symbol)
                success_count += 1
                time.sleep(0.5)  # 避免API限流
            except Exception as e:
                print(f"❌ {symbol} 采集失败: {e}")
                fail_count += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ 采集周期完成: 成功 {success_count}/{len(SYMBOLS)}, 失败 {fail_count}")
        print(f"{'='*60}\n")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


def main():
    """主函数"""
    collector = TechnicalIndicatorsCollector()
    
    try:
        # 运行一次采集
        collector.run_collection_cycle()
        
        # 可以设置定时任务，每5分钟运行一次
        # while True:
        #     collector.run_collection_cycle()
        #     time.sleep(300)  # 5分钟
        
    except KeyboardInterrupt:
        print("\n⚠️ 收到中断信号，正在退出...")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
    finally:
        collector.close()


if __name__ == '__main__':
    main()
