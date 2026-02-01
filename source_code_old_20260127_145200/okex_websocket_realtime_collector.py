#!/usr/bin/env python3
"""
OKEx WebSocket 实时 K线指标采集器
实时订阅K线数据，动态计算技术指标
目标：尽量匹配欧易官网显示
"""

import asyncio
import websockets
import json
import sqlite3
import talib
import numpy as np
from datetime import datetime
from collections import deque
import sys

# 设置北京时区
import os
os.environ['TZ'] = 'Asia/Shanghai'

# 27个币种（按用户指定顺序）
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# K线数据缓存（用于计算指标）
kline_cache = {
    '5m': {symbol: deque(maxlen=100) for symbol in SYMBOLS},
    '1H': {symbol: deque(maxlen=100) for symbol in SYMBOLS}
}

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 确保表存在
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okex_technical_indicators (
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
            record_time TEXT,
            PRIMARY KEY (symbol, timeframe)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def calculate_indicators(klines):
    """
    计算技术指标
    klines: list of [timestamp, open, high, low, close, volume]
    """
    if len(klines) < 20:
        return None
    
    # 提取数据
    closes = np.array([float(k[4]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])
    
    current_price = closes[-1]
    
    # RSI(14)
    rsi = talib.RSI(closes, timeperiod=14)
    rsi_14 = rsi[-1] if not np.isnan(rsi[-1]) else None
    
    # Parabolic SAR
    sar = talib.SAR(highs, lows, acceleration=0.02, maximum=0.2)
    sar_value = sar[-1] if not np.isnan(sar[-1]) else None
    
    # SAR 位置
    if sar_value:
        sar_position = 'bullish' if current_price > sar_value else 'bearish'
        
        # 计算 SAR 连续周期数
        count = 1
        for i in range(len(sar) - 2, -1, -1):
            if np.isnan(sar[i]):
                break
            prev_position = 'bullish' if closes[i] > sar[i] else 'bearish'
            if prev_position == sar_position:
                count += 1
            else:
                break
        
        sar_count_label = f"{'多头' if sar_position == 'bullish' else '空头'}{count:02d}"
        
        # SAR 象限（相对布林带）
        bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
        
        if not np.isnan(bb_upper[-1]):
            if sar_value > bb_upper[-1]:
                sar_quadrant = 1
            elif sar_value > bb_middle[-1]:
                sar_quadrant = 2
            elif sar_value > bb_lower[-1]:
                sar_quadrant = 3
            else:
                sar_quadrant = 4
        else:
            sar_quadrant = None
    else:
        sar_position = None
        sar_count_label = None
        sar_quadrant = None
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
    bb_upper_val = bb_upper[-1] if not np.isnan(bb_upper[-1]) else None
    bb_middle_val = bb_middle[-1] if not np.isnan(bb_middle[-1]) else None
    bb_lower_val = bb_lower[-1] if not np.isnan(bb_lower[-1]) else None
    
    return {
        'current_price': current_price,
        'rsi_14': rsi_14,
        'sar': sar_value,
        'sar_position': sar_position,
        'sar_quadrant': sar_quadrant,
        'sar_count_label': sar_count_label,
        'bb_upper': bb_upper_val,
        'bb_middle': bb_middle_val,
        'bb_lower': bb_lower_val
    }

def save_indicators(symbol, timeframe, indicators):
    """保存指标到数据库"""
    if not indicators:
        return
    
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    record_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT OR REPLACE INTO okex_technical_indicators
        (symbol, timeframe, current_price, rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
         bb_upper, bb_middle, bb_lower, record_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        symbol, timeframe,
        indicators['current_price'], indicators['rsi_14'],
        indicators['sar'], indicators['sar_position'], indicators['sar_quadrant'],
        indicators['sar_count_label'],
        indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'],
        record_time
    ))
    
    conn.commit()
    conn.close()

async def subscribe_klines(websocket, symbols, timeframe):
    """订阅K线频道"""
    args = [
        {
            "channel": f"candle{timeframe}",
            "instId": symbol
        }
        for symbol in symbols
    ]
    
    subscribe_msg = {
        "op": "subscribe",
        "args": args
    }
    
    await websocket.send(json.dumps(subscribe_msg))
    print(f"📊 已订阅 {len(symbols)} 个币种的 {timeframe} K线")

async def process_kline_message(data):
    """处理K线消息"""
    try:
        arg = data.get('arg', {})
        kline_data = data.get('data', [])
        
        if not kline_data:
            return
        
        channel = arg.get('channel', '')
        symbol = arg.get('instId', '')
        
        # 解析时间周期
        if 'candle5m' in channel:
            timeframe = '5m'
        elif 'candle1H' in channel:
            timeframe = '1H'
        else:
            return
        
        # 更新缓存
        for kline in kline_data:
            # kline: [timestamp, open, high, low, close, volume, ...]
            kline_cache[timeframe][symbol].append(kline[:6])
        
        # 计算指标
        if len(kline_cache[timeframe][symbol]) >= 20:
            indicators = calculate_indicators(list(kline_cache[timeframe][symbol]))
            
            if indicators:
                # 保存到数据库
                save_indicators(symbol, timeframe, indicators)
                
                # 输出日志
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol} ({timeframe}): "
                      f"价格=${indicators['current_price']:.4f}, "
                      f"RSI={indicators['rsi_14']:.2f}, "
                      f"SAR={indicators['sar_count_label']}")
    
    except Exception as e:
        print(f"❌ 处理消息错误: {e}")

async def ws_client():
    """WebSocket 客户端"""
    uri = "wss://ws.okx.com:8443/ws/v5/business"
    
    while True:
        try:
            print(f"\n{'='*80}")
            print(f"🔌 连接 OKEx WebSocket...")
            
            async with websockets.connect(uri, ping_interval=20) as websocket:
                print(f"✅ WebSocket 已连接")
                
                # 订阅所有币种的 5m 和 1H K线
                await subscribe_klines(websocket, SYMBOLS, '5m')
                await subscribe_klines(websocket, SYMBOLS, '1H')
                
                # 持续接收消息
                async for message in websocket:
                    data = json.loads(message)
                    
                    # 跳过非数据消息
                    if 'event' in data:
                        if data['event'] == 'subscribe':
                            print(f"✅ 订阅成功: {data.get('arg', {})}")
                        continue
                    
                    # 处理K线数据
                    await process_kline_message(data)
        
        except Exception as e:
            print(f"❌ WebSocket 错误: {e}")
            print(f"⏰ 5秒后重连...")
            await asyncio.sleep(5)

async def main():
    """主函数"""
    print("=" * 80)
    print("🚀 OKEx WebSocket 实时K线指标采集器")
    print("=" * 80)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"币种数量: {len(SYMBOLS)}")
    print(f"时间周期: 5分钟, 1小时")
    print(f"技术指标: RSI(14), Parabolic SAR, Bollinger Bands(20,2)")
    print(f"数据源: OKEx WebSocket (实时)")
    print("=" * 80)
    
    # 初始化数据库
    init_database()
    
    # 启动 WebSocket 客户端
    await ws_client()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  收到停止信号，正在关闭...")
        sys.exit(0)
