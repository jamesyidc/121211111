#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策-K线指标系统（TradingView直接获取版本）
功能：直接从TradingView获取OKEx永续合约的技术指标（不进行本地计算）
数据源：TradingView API (OKX Exchange)
北京时间为准
"""

import sqlite3
import time
import json
from datetime import datetime
import pytz
from typing import Dict, List, Optional
from tradingview_ta import TA_Handler, Interval

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

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

class OKExTVIndicatorsCollector:
    """OKEx技术指标采集器（TradingView版本 - 直接获取，不计算）"""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        
        # 创建技术指标表（TradingView直接获取版）
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_tv_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                current_price REAL,
                rsi_14 REAL,
                sar REAL,
                bb_upper REAL,
                bb_middle REAL,
                bb_lower REAL,
                ema_10 REAL,
                ema_20 REAL,
                recommendation TEXT,
                buy_signals INTEGER,
                sell_signals INTEGER,
                neutral_signals INTEGER,
                record_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timeframe)
            )
        ''')
        
        # 创建采集状态表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_tv_collector_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_collect_time TIMESTAMP,
                total_indicators_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'stopped'
            )
        ''')
        
        # 初始化状态记录
        self.cursor.execute('''
            INSERT OR IGNORE INTO okex_tv_collector_status (id, status)
            VALUES (1, 'stopped')
        ''')
        
        self.conn.commit()
        print("✅ Database initialized for TradingView indicators")
    
    def convert_symbol_to_tv_format(self, symbol: str) -> str:
        """
        转换币种格式：BTC-USDT-SWAP -> BTCUSDT.P
        TradingView OKX交易所使用 .P 后缀表示永续合约
        """
        base = symbol.replace('-USDT-SWAP', '')
        return f"{base}USDT.P"
    
    def fetch_indicators_from_tradingview(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        直接从TradingView获取技术指标
        
        Args:
            symbol: 币种代码（如 BTC-USDT-SWAP）
            timeframe: 时间周期（5m 或 1h）
        
        Returns:
            包含技术指标的字典，失败返回None
        """
        tv_symbol = self.convert_symbol_to_tv_format(symbol)
        
        # 转换时间周期
        interval_map = {
            '5m': Interval.INTERVAL_5_MINUTES,
            '1h': Interval.INTERVAL_1_HOUR,
        }
        
        try:
            handler = TA_Handler(
                symbol=tv_symbol,
                exchange="OKX",
                screener="crypto",
                interval=interval_map.get(timeframe, Interval.INTERVAL_5_MINUTES)
            )
            
            # 直接获取分析结果（不进行本地计算）
            analysis = handler.get_analysis()
            indicators = analysis.indicators
            summary = analysis.summary
            
            # 获取北京时间
            beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # 组织数据
            result = {
                'symbol': symbol,
                'tv_symbol': tv_symbol,
                'timeframe': timeframe,
                'current_price': indicators.get('close'),
                'rsi_14': indicators.get('RSI'),
                'sar': indicators.get('P.SAR'),  # TradingView的SAR指标
                'bb_upper': indicators.get('BB.upper'),
                'bb_middle': indicators.get('BB.middle'),
                'bb_lower': indicators.get('BB.lower'),
                'ema_10': indicators.get('EMA10'),
                'ema_20': indicators.get('EMA20'),
                'recommendation': summary.get('RECOMMENDATION'),
                'buy_signals': summary.get('BUY', 0),
                'sell_signals': summary.get('SELL', 0),
                'neutral_signals': summary.get('NEUTRAL', 0),
                'record_time': beijing_time
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Error fetching {symbol} ({timeframe}) from TradingView: {str(e)}")
            return None
    
    def save_indicator_to_db(self, indicator_data: Dict):
        """保存技术指标数据到数据库"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO okex_tv_indicators 
                (symbol, timeframe, current_price, rsi_14, sar, 
                 bb_upper, bb_middle, bb_lower, ema_10, ema_20,
                 recommendation, buy_signals, sell_signals, neutral_signals, record_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                indicator_data['symbol'],
                indicator_data['timeframe'],
                indicator_data['current_price'],
                indicator_data['rsi_14'],
                indicator_data['sar'],
                indicator_data['bb_upper'],
                indicator_data['bb_middle'],
                indicator_data['bb_lower'],
                indicator_data['ema_10'],
                indicator_data['ema_20'],
                indicator_data['recommendation'],
                indicator_data['buy_signals'],
                indicator_data['sell_signals'],
                indicator_data['neutral_signals'],
                indicator_data['record_time']
            ))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Error saving indicator: {str(e)}")
            return False
    
    def collect_all_indicators(self):
        """采集所有币种的技术指标"""
        beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{'='*70}")
        print(f"开始采集 OKEx 技术指标（TradingView直接获取版）")
        print(f"采集时间: {beijing_time}")
        print(f"币种数量: {len(SYMBOLS)}")
        print(f"{'='*70}\n")
        
        # 更新采集状态为运行中
        self.cursor.execute('''
            UPDATE okex_tv_collector_status 
            SET status = 'running', last_collect_time = ?
            WHERE id = 1
        ''', (beijing_time,))
        self.conn.commit()
        
        success_count = 0
        fail_count = 0
        
        for symbol in SYMBOLS:
            print(f"📊 采集 {symbol}...")
            
            # 采集5分钟和1小时指标
            for timeframe in ['5m', '1h']:
                indicator_data = self.fetch_indicators_from_tradingview(symbol, timeframe)
                
                if indicator_data:
                    if self.save_indicator_to_db(indicator_data):
                        print(f"  ✅ {timeframe} 指标保存成功")
                        print(f"     价格: ${indicator_data['current_price']}")
                        if indicator_data['rsi_14']:
                            print(f"     RSI(14): {indicator_data['rsi_14']:.2f}")
                        if indicator_data['bb_lower'] and indicator_data['bb_upper']:
                            bb_mid = indicator_data['bb_middle'] if indicator_data['bb_middle'] else (indicator_data['bb_lower'] + indicator_data['bb_upper']) / 2
                            print(f"     BB: [{indicator_data['bb_lower']:.4f}, {bb_mid:.4f}, {indicator_data['bb_upper']:.4f}]")
                        if indicator_data['sar']:
                            print(f"     SAR: {indicator_data['sar']:.4f}")
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    fail_count += 1
                
                # 避免请求过快 (TradingView有速率限制)
                time.sleep(3)  # 增加延迟到3秒
            
            print()
        
        # 更新采集统计
        self.cursor.execute('''
            UPDATE okex_tv_collector_status 
            SET total_indicators_count = ?
            WHERE id = 1
        ''', (success_count,))
        self.conn.commit()
        
        print(f"\n{'='*70}")
        print(f"采集完成:")
        print(f"  成功: {success_count} 个指标")
        print(f"  失败: {fail_count} 个")
        print(f"{'='*70}\n")
    
    def get_collector_status(self) -> Dict:
        """获取采集器状态"""
        self.cursor.execute('''
            SELECT last_collect_time, total_indicators_count, status
            FROM okex_tv_collector_status
            WHERE id = 1
        ''')
        
        row = self.cursor.fetchone()
        if row:
            return {
                'last_collect_time': row[0],
                'total_indicators_count': row[1],
                'status': row[2]
            }
        return {
            'last_collect_time': None,
            'total_indicators_count': 0,
            'status': 'stopped'
        }
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

def main():
    """主函数"""
    print("="*70)
    print("OKEx K线指标系统 - TradingView直接获取版")
    print("数据源: TradingView (OKX Exchange)")
    print("特点: 直接获取技术指标，不进行本地计算")
    print("="*70)
    
    collector = OKExTVIndicatorsCollector()
    
    try:
        # 执行一次完整采集
        collector.collect_all_indicators()
        
        # 显示采集状态
        status = collector.get_collector_status()
        print(f"\n当前采集器状态:")
        print(f"  状态: {status['status']}")
        print(f"  上次采集时间: {status['last_collect_time']}")
        print(f"  已采集指标数: {status['total_indicators_count']}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  采集被用户中断")
    except Exception as e:
        print(f"\n\n❌ 采集过程出错: {str(e)}")
    finally:
        collector.close()
        print("\n✅ 采集器已关闭")

if __name__ == "__main__":
    main()
