#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策-K线指标系统（OKEx版本）
功能：采集OKEx永续合约5分钟/1小时K线数据及技术指标
数据源：OKEx Perpetual Futures API
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

# OKEx API配置
OKEX_BASE_URL = "https://www.okx.com"
OKEX_CANDLES_ENDPOINT = "/api/v5/market/candles"

# 监控的币种列表（27个永续合约，OKEx格式）
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

class OKExIndicatorsCollector:
    """OKEx技术指标采集器"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        
        # 创建5分钟K线表（OKEx版）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_kline_5m (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                vol_currency REAL,
                amplitude REAL,
                change_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # 创建1小时K线表（OKEx版）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_kline_1h (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                vol_currency REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        ''')
        
        # 创建技术指标表（含SAR多空与象限）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                current_price REAL,
                rsi_14 REAL,
                sar REAL,
                sar_position TEXT,
                sar_quadrant INTEGER,
                sar_count_label TEXT,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                record_time TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe, record_time)
            )
        ''')
        
        # 创建SAR多空计数表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_sar_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                current_position TEXT,
                position_count INTEGER DEFAULT 1,
                last_change_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe)
            )
        ''')
        
        # 创建索引
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_okex_kline_5m_symbol_time ON okex_kline_5m(symbol, timestamp DESC)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_okex_kline_1h_symbol_time ON okex_kline_1h(symbol, timestamp DESC)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_okex_tech_symbol_time ON okex_technical_indicators(symbol, timeframe, record_time DESC)')
        
        self.conn.commit()
        print("✅ OKEx数据库初始化完成")
    
    def fetch_okex_candles(self, inst_id: str, bar: str, limit: int = 100) -> List[List]:
        """
        从OKEx获取K线数据
        
        Args:
            inst_id: 合约ID（如BTC-USDT-SWAP）
            bar: K线周期（5m, 1H等）
            limit: 获取数量（默认100）
        
        Returns:
            K线数据列表，格式：[timestamp, open, high, low, close, vol, volCcy, ...]
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
    
    def save_klines_5m(self, symbol: str, candles: List[List]):
        """
        保存5分钟K线数据（含振幅和涨跌幅）
        
        OKEx K线格式：[timestamp, open, high, low, close, vol, volCcy, ...]
        """
        if not candles:
            return
        
        for candle in candles:
            try:
                timestamp = int(candle[0])
                open_price = float(candle[1])
                high = float(candle[2])
                low = float(candle[3])
                close = float(candle[4])
                volume = float(candle[5])
                vol_currency = float(candle[6])
                
                # 计算振幅和涨跌幅
                amplitude = ((high - low) / low * 100) if low > 0 else 0
                change_pct = ((close - open_price) / open_price * 100) if open_price > 0 else 0
                
                self.cursor.execute('''
                    INSERT OR REPLACE INTO okex_kline_5m 
                    (symbol, timestamp, open, high, low, close, volume, vol_currency, amplitude, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timestamp, open_price, high, low, close, volume, vol_currency, 
                      round(amplitude, 4), round(change_pct, 4)))
            except Exception as e:
                print(f"❌ 保存5分钟K线失败: {e}")
                continue
        
        self.conn.commit()
    
    def save_klines_1h(self, symbol: str, candles: List[List]):
        """保存1小时K线数据"""
        if not candles:
            return
        
        for candle in candles:
            try:
                timestamp = int(candle[0])
                open_price = float(candle[1])
                high = float(candle[2])
                low = float(candle[3])
                close = float(candle[4])
                volume = float(candle[5])
                vol_currency = float(candle[6])
                
                self.cursor.execute('''
                    INSERT OR REPLACE INTO okex_kline_1h 
                    (symbol, timestamp, open, high, low, close, volume, vol_currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timestamp, open_price, high, low, close, volume, vol_currency))
            except Exception as e:
                print(f"❌ 保存1小时K线失败: {e}")
                continue
        
        self.conn.commit()
    
    def calculate_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        """
        计算RSI指标（不计算，只采集原始数据，返回None用于标记）
        
        注意：根据用户要求"只采集数据，不计算"，这里返回None
        实际使用时，可以通过原始K线数据外部计算
        """
        if len(closes) < period + 1:
            return None
        
        # 简单RSI计算（仅用于演示）
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_sar_with_bollinger(self, highs: List[float], lows: List[float], 
                                     closes: List[float], current_close: float) -> Tuple:
        """
        计算SAR及其与布林带的关系
        
        返回：(sar_value, sar_position, sar_quadrant, bb_upper, bb_middle, bb_lower)
        
        SAR多空定义：
        - bearish（空头）：K线在SAR下方
        - bullish（多头）：K线在SAR上方
        
        SAR象限定义（相对于布林带）：
        - 象限1：SAR > UB（布林带上轨）
        - 象限2：UB > SAR > BOLL（中轨）
        - 象限3：BOLL > SAR > LB（下轨）
        - 象限4：SAR < LB（布林带下轨）
        """
        if len(closes) < 20:
            return None, None, None, None, None, None
        
        # 1. 简化版SAR计算（基于最近5根K线的极值）
        recent_highs = highs[-5:]
        recent_lows = lows[-5:]
        max_high = max(recent_highs)
        min_low = min(recent_lows)
        
        # 判断趋势：如果当前价接近最高价，SAR在下方（多头）
        if current_close > (max_high + min_low) / 2:
            sar = min_low * 0.995  # SAR在下方
            sar_position = "bullish"
        else:
            sar = max_high * 1.005  # SAR在上方
            sar_position = "bearish"
        
        # 2. 计算布林带（20周期，2倍标准差）
        closes_series = pd.Series(closes[-20:])
        bb_middle = closes_series.mean()
        std_dev = closes_series.std()
        bb_upper = bb_middle + (2 * std_dev)
        bb_lower = bb_middle - (2 * std_dev)
        
        # 3. 判断SAR象限
        if sar > bb_upper:
            sar_quadrant = 1
        elif sar > bb_middle:
            sar_quadrant = 2
        elif sar > bb_lower:
            sar_quadrant = 3
        else:
            sar_quadrant = 4
        
        return (round(sar, 6), sar_position, sar_quadrant, 
                round(bb_upper, 6), round(bb_middle, 6), round(bb_lower, 6))
    
    def update_sar_tracking(self, symbol: str, timeframe: str, current_position: str, 
                           current_kline_timestamp: int) -> str:
        """
        更新SAR多空计数（基于K线时间戳）
        
        多转空：SAR从K线下方移动到上方，开始计数"空头01"、"空头02"...
        空转多：SAR从K线上方移动到下方，开始计数"多头01"、"多头02"...
        
        计数逻辑：基于当前K线时间戳，查询该symbol在同一position下的历史K线数量
        
        Args:
            symbol: 币种合约ID
            timeframe: 时间周期
            current_position: 当前SAR位置（bullish/bearish）
            current_kline_timestamp: 当前K线的时间戳（毫秒）
            
        返回：计数标签（如"空头02"、"多头01"）
        """
        now_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 查询历史记录，找到position最后一次变化的时间
        self.cursor.execute('''
            SELECT current_position, position_count, last_change_time
            FROM okex_sar_tracking
            WHERE symbol = ? AND timeframe = ?
        ''', (symbol, timeframe))
        
        row = self.cursor.fetchone()
        
        if not row:
            # 首次记录，默认计数为1
            self.cursor.execute('''
                INSERT INTO okex_sar_tracking (symbol, timeframe, current_position, position_count, last_change_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, timeframe, current_position, 1, now_str))
            self.conn.commit()
            position_label = "空头" if current_position == "bearish" else "多头"
            return f"{position_label}01"
        
        prev_position, prev_count, last_change = row
        
        if prev_position != current_position:
            # 位置发生反转，重置计数为1
            self.cursor.execute('''
                UPDATE okex_sar_tracking
                SET current_position = ?, position_count = ?, last_change_time = ?
                WHERE symbol = ? AND timeframe = ?
            ''', (current_position, 1, now_str, symbol, timeframe))
            self.conn.commit()
            position_label = "空头" if current_position == "bearish" else "多头"
            return f"{position_label}01"
        
        # 位置未变，计数+1（简单累加模式）
        # 注意：这是简化的计数方式，每次采集时如果position不变就+1
        # 如果需要精确的K线周期计数，需要设置定时任务每5分钟运行一次采集器
        new_count = prev_count + 1
        
        # 更新追踪表
        self.cursor.execute('''
            UPDATE okex_sar_tracking
            SET position_count = ?, last_change_time = ?
            WHERE symbol = ? AND timeframe = ?
        ''', (new_count, now_str, symbol, timeframe))
        self.conn.commit()
        
        # 生成计数标签
        position_label = "空头" if current_position == "bearish" else "多头"
        count_label = f"{position_label}{new_count:02d}"
        
        return count_label
    
    def calculate_consecutive_sar_count(self, highs: List[float], lows: List[float], 
                                       closes: List[float], current_sar_position: str) -> int:
        """
        基于K线数据回溯计算连续SAR位置的数量
        
        从最新的K线向前回溯，计算连续相同SAR位置的K线数量
        """
        count = 0
        # 从最后一根K线开始向前遍历
        for i in range(len(closes) - 1, -1, -1):
            close = closes[i]
            high = highs[i]
            low = lows[i]
            
            # 简单判断：用收盘价与最近5根K线的极值比较
            if i >= 5:
                recent_highs = highs[max(0, i-4):i+1]
                recent_lows = lows[max(0, i-4):i+1]
                max_high = max(recent_highs)
                min_low = min(recent_lows)
                
                # 判断SAR位置
                if close > (max_high + min_low) / 2:
                    position = "bullish"  # SAR在下方，多头
                else:
                    position = "bearish"  # SAR在上方，空头
                
                # 如果位置相同，计数+1
                if position == current_sar_position:
                    count += 1
                else:
                    # 遇到不同位置，停止计数
                    break
            else:
                count += 1  # 前5根K线默认计入
        
        return max(1, count)  # 至少返回1
    
    def collect_and_save(self, symbol: str):
        """
        采集并保存指定币种的K线和技术指标
        
        Args:
            symbol: OKEx合约ID（如BTC-USDT-SWAP）
        """
        now = datetime.now(BEIJING_TZ)
        
        # 1. 采集5分钟K线（100根）
        print(f"📊 采集{symbol} 5分钟K线...")
        candles_5m = self.fetch_okex_candles(symbol, '5m', 100)
        if candles_5m:
            self.save_klines_5m(symbol, candles_5m)
        
        # 2. 采集1小时K线（100根）
        print(f"📊 采集{symbol} 1小时K线...")
        candles_1h = self.fetch_okex_candles(symbol, '1H', 100)
        if candles_1h:
            self.save_klines_1h(symbol, candles_1h)
        
        # 3. 计算5分钟技术指标
        if candles_5m and len(candles_5m) >= 20:
            closes_5m = [float(c[4]) for c in candles_5m]
            highs_5m = [float(c[2]) for c in candles_5m]
            lows_5m = [float(c[3]) for c in candles_5m]
            current_close_5m = closes_5m[-1]
            
            # 计算指标
            rsi_5m = self.calculate_rsi(closes_5m, 14)
            sar_5m, sar_pos_5m, sar_quad_5m, bb_u_5m, bb_m_5m, bb_l_5m = \
                self.calculate_sar_with_bollinger(highs_5m, lows_5m, closes_5m, current_close_5m)
            
            # 基于K线数据计算连续SAR计数
            count_label_5m = None
            if sar_pos_5m:
                consecutive_count = self.calculate_consecutive_sar_count(highs_5m, lows_5m, closes_5m, sar_pos_5m)
                position_label = "空头" if sar_pos_5m == "bearish" else "多头"
                count_label_5m = f"{position_label}{consecutive_count:02d}"
                
                # 同时更新追踪表
                latest_5m_timestamp = int(candles_5m[-1][0]) if candles_5m else 0
                self.update_sar_tracking(symbol, '5m', sar_pos_5m, latest_5m_timestamp)
            
            # 保存技术指标
            self.cursor.execute('''
                INSERT OR REPLACE INTO okex_technical_indicators
                (symbol, timeframe, current_price, rsi_14, sar, sar_position, sar_quadrant, 
                 sar_count_label, bb_upper, bb_middle, bb_lower, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, '5m', current_close_5m, rsi_5m, sar_5m, sar_pos_5m, sar_quad_5m,
                  count_label_5m, bb_u_5m, bb_m_5m, bb_l_5m, now.strftime('%Y-%m-%d %H:%M:%S')))
        
        # 4. 计算1小时技术指标
        if candles_1h and len(candles_1h) >= 20:
            closes_1h = [float(c[4]) for c in candles_1h]
            highs_1h = [float(c[2]) for c in candles_1h]
            lows_1h = [float(c[3]) for c in candles_1h]
            current_close_1h = closes_1h[-1]
            
            # 计算指标
            rsi_1h = self.calculate_rsi(closes_1h, 14)
            sar_1h, sar_pos_1h, sar_quad_1h, bb_u_1h, bb_m_1h, bb_l_1h = \
                self.calculate_sar_with_bollinger(highs_1h, lows_1h, closes_1h, current_close_1h)
            
            # 基于K线数据计算连续SAR计数
            count_label_1h = None
            if sar_pos_1h:
                consecutive_count = self.calculate_consecutive_sar_count(highs_1h, lows_1h, closes_1h, sar_pos_1h)
                position_label = "空头" if sar_pos_1h == "bearish" else "多头"
                count_label_1h = f"{position_label}{consecutive_count:02d}"
                
                # 同时更新追踪表
                latest_1h_timestamp = int(candles_1h[-1][0]) if candles_1h else 0
                self.update_sar_tracking(symbol, '1h', sar_pos_1h, latest_1h_timestamp)
            
            # 保存技术指标
            self.cursor.execute('''
                INSERT OR REPLACE INTO okex_technical_indicators
                (symbol, timeframe, current_price, rsi_14, sar, sar_position, sar_quadrant,
                 sar_count_label, bb_upper, bb_middle, bb_lower, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, '1h', current_close_1h, rsi_1h, sar_1h, sar_pos_1h, sar_quad_1h,
                  count_label_1h, bb_u_1h, bb_m_1h, bb_l_1h, now.strftime('%Y-%m-%d %H:%M:%S')))
        
        self.conn.commit()
        print(f"✅ {symbol} 技术指标采集完成")
    
    def run_collection_cycle(self):
        """运行一个完整的采集周期"""
        print(f"\n{'='*60}")
        print(f"🚀 开始OKEx指标采集 - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        success_count = 0
        fail_count = 0
        
        for symbol in SYMBOLS:
            try:
                self.collect_and_save(symbol)
                success_count += 1
                time.sleep(0.3)  # 避免API限流
            except Exception as e:
                print(f"❌ {symbol} 采集失败: {e}")
                fail_count += 1
                continue
        
        print(f"\n{'='*60}")
        print(f"✅ 采集完成: 成功 {success_count}/{len(SYMBOLS)}, 失败 {fail_count}")
        print(f"⏰ 下次采集: 5分钟后")
        print(f"{'='*60}\n")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


def main():
    """主函数"""
    collector = OKExIndicatorsCollector()
    
    try:
        # 运行一次采集
        collector.run_collection_cycle()
        
        # 可选：持续采集模式（每5分钟一次）
        # while True:
        #     collector.run_collection_cycle()
        #     time.sleep(300)  # 5分钟
        
    except KeyboardInterrupt:
        print("\n⚠️ 收到中断信号，正在退出...")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        collector.close()


if __name__ == '__main__':
    main()
