#!/usr/bin/env python3
"""
OKEx WebSocket 实时 K线指标采集器 (修复版)
启动时加载历史K线，确保SAR计数准确
"""

import asyncio
import websockets
import json
import sqlite3
import talib
import numpy as np
import requests
from datetime import datetime
from collections import deque
import sys

# 设置北京时区
import os
os.environ['TZ'] = 'Asia/Shanghai'

# 27个币种
SYMBOLS = [
    'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP', 
    'SOL-USDT-SWAP', 'LTC-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP',
    'TRX-USDT-SWAP', 'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
    'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP', 'LINK-USDT-SWAP',
    'CRO-USDT-SWAP', 'DOT-USDT-SWAP', 'AAVE-USDT-SWAP', 'UNI-USDT-SWAP',
    'NEAR-USDT-SWAP', 'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
    'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
]

# K线数据缓存
kline_cache = {
    '5m': {symbol: deque(maxlen=100) for symbol in SYMBOLS},
    '1H': {symbol: deque(maxlen=100) for symbol in SYMBOLS}
}

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 保留原表用于存储最新指标（实时查询用）
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
    
    # 新增历史指标表（每根K线一条记录）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS okex_indicators_history (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            current_price REAL,
            rsi_14 REAL,
            sar REAL,
            sar_position TEXT,
            sar_count_label TEXT,
            bb_upper REAL,
            bb_middle REAL,
            bb_lower REAL,
            created_at TEXT,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")

def load_historical_klines(symbol, timeframe):
    """从OKEx API加载历史K线数据"""
    try:
        bar_map = {'5m': '5m', '1H': '1H'}
        bar = bar_map.get(timeframe, '5m')
        
        url = 'https://www.okx.com/api/v5/market/candles'
        params = {
            'instId': symbol,
            'bar': bar,
            'limit': 100
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == '0' and result.get('data'):
                # 数据是从新到旧排序的，需要反转
                klines = list(reversed(result['data']))
                return [[k[0], k[1], k[2], k[3], k[4], k[5]] for k in klines]
    except Exception as e:
        print(f"❌ 加载历史K线失败 {symbol} {timeframe}: {e}")
    
    return []

async def init_kline_cache():
    """初始化K线缓存"""
    print("\n" + "="*80)
    print("📊 正在加载历史K线数据...")
    print("="*80)
    
    total = len(SYMBOLS) * 2
    loaded = 0
    
    for symbol in SYMBOLS:
        for timeframe in ['5m', '1H']:
            klines = load_historical_klines(symbol, timeframe)
            if klines:
                for kline in klines:
                    kline_cache[timeframe][symbol].append(kline[:6])
                loaded += 1
                print(f"✅ [{loaded}/{total}] {symbol} ({timeframe}): {len(klines)} 根K线")
            else:
                print(f"❌ [{loaded+1}/{total}] {symbol} ({timeframe}): 加载失败")
            
            # 避免请求过快
            await asyncio.sleep(0.1)
    
    print("="*80)
    print(f"✅ 历史K线加载完成！成功: {loaded}/{total}")
    print("="*80 + "\n")

def calculate_indicators(klines):
    """计算技术指标"""
    if len(klines) < 20:
        return None
    
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
    
    # SAR 位置和计数
    if sar_value:
        sar_position = 'bullish' if current_price > sar_value else 'bearish'
        
        # 计算连续周期数
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
        
        # SAR 象限
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

def save_kline(symbol, timeframe, kline):
    """保存K线数据到数据库（仅在整点时刻）"""
    try:
        import pytz
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # kline: [timestamp, open, high, low, close, volume]
        timestamp = int(kline[0])
        open_price = float(kline[1])
        high = float(kline[2])
        low = float(kline[3])
        close = float(kline[4])
        volume = float(kline[5])
        
        # 使用北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        created_at = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # 🔥 修复：保存到统一的 okex_kline_ohlc 表
        cursor.execute('''
            INSERT OR REPLACE INTO okex_kline_ohlc
            (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, timeframe, timestamp, open_price, high, low, close, volume, created_at))
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        print(f"❌ 保存K线失败 {symbol} {timeframe}: {e}")
        return False

def save_indicators(symbol, timeframe, indicators, timestamp=None):
    """保存指标到数据库"""
    if not indicators:
        print(f"⚠️  save_indicators: indicators为空，跳过保存")
        return
    
    try:
        import pytz
        conn = sqlite3.connect('crypto_data.db', timeout=30.0)
        cursor = conn.cursor()
        
        # 使用北京时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        record_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存最新指标（用于实时显示）
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
        
        # 如果提供了timestamp，同时保存到历史表
        if timestamp:
            print(f"💾 save_indicators: 保存到历史表 {symbol} {timeframe} timestamp={timestamp}")
            cursor.execute('''
                INSERT OR REPLACE INTO okex_indicators_history
                (symbol, timeframe, timestamp, current_price, rsi_14, sar, sar_position, sar_count_label,
                 bb_upper, bb_middle, bb_lower, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol, timeframe, timestamp,
                indicators['current_price'], indicators['rsi_14'],
                indicators['sar'], indicators['sar_position'], indicators['sar_count_label'],
                indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'],
                record_time
            ))
            print(f"✅ save_indicators: 历史表保存成功")
            
            # 在同一个连接中更新采集器状态表
            update_collector_status_in_transaction(cursor, record_time)
        else:
            print(f"⚠️  save_indicators: timestamp为None，只保存到最新表")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ save_indicators失败: {symbol} {timeframe} - {e}")

def update_collector_status_in_transaction(cursor, collection_time):
    """在现有事务中更新采集器状态表（避免数据库锁定）"""
    try:
        # 确保表存在
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS okex_tv_collector_status (
                id INTEGER PRIMARY KEY,
                last_collect_time TIMESTAMP,
                total_indicators_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            )
        ''')
        
        # 获取总指标数
        cursor.execute('SELECT COUNT(*) FROM okex_indicators_history')
        total_count = cursor.fetchone()[0]
        
        # 更新或插入状态
        cursor.execute('''
            INSERT OR REPLACE INTO okex_tv_collector_status 
            (id, last_collect_time, total_indicators_count, status)
            VALUES (1, ?, ?, 'running')
        ''', (collection_time, total_count))
        
    except Exception as e:
        print(f"❌ 更新collector状态失败: {e}")

async def subscribe_klines(websocket, symbols, timeframe):
    """订阅K线频道"""
    args = [{"channel": f"candle{timeframe}", "instId": symbol} for symbol in symbols]
    
    subscribe_msg = {"op": "subscribe", "args": args}
    
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
        
        # 更新缓存（保留最近100根K线用于SAR计数）
        for kline in kline_data:
            cache = kline_cache[timeframe][symbol]
            new_kline = kline[:6]
            new_timestamp = int(new_kline[0])
            
            # 检查是否是新K线（时间戳变化）
            is_new_kline = False
            if cache and cache[-1][0] == new_kline[0]:
                # 更新最后一根K线（实时更新）
                cache[-1] = new_kline
            else:
                # 添加新K线
                is_new_kline = True
                cache.append(new_kline)
                # 保持缓存大小在100根以内
                if len(cache) > 100:
                    cache.pop(0)
            
            # 检查是否是整点时刻（5分钟或1小时）
            is_on_interval = False
            if timeframe == '5m':
                # 5分钟：检查是否在0,5,10,15...分钟（放宽到前30秒）
                dt = datetime.fromtimestamp(new_timestamp / 1000)
                is_on_interval = (dt.minute % 5 == 0 and dt.second < 30)
                
                # Debug logging for FIL
                if symbol == 'FIL-USDT-SWAP' and is_new_kline:
                    print(f"🔍 FIL新K线: 时间={dt}, is_on_interval={is_on_interval}, minute={dt.minute}, second={dt.second}")
            elif timeframe == '1H':
                # 1小时：检查是否在整点（放宽到前30秒）
                dt = datetime.fromtimestamp(new_timestamp / 1000)
                is_on_interval = (dt.minute == 0 and dt.second < 30)
            
            # 如果是新K线且在整点时刻，保存到数据库
            if is_new_kline and is_on_interval:
                # 保存前一根完整的K线（当前是新K线，保存前一根）
                cache_size = len(cache)
                if symbol == 'FIL-USDT-SWAP' and timeframe == '5m':
                    print(f"🔍 FIL触发保存逻辑: cache_size={cache_size}")
                if cache_size >= 2:
                    prev_kline = cache[-2]
                    prev_timestamp = int(prev_kline[0])
                    
                    # 保存K线数据
                    save_result = save_kline(symbol, timeframe, prev_kline)
                    dt = datetime.fromtimestamp(prev_timestamp / 1000)
                    print(f"💾 [{dt.strftime('%H:%M:%S')}] 已保存 {symbol} ({timeframe}) K线 [save_result={save_result}]")
                    
                    if save_result:
                        # 计算并保存对应的指标数据
                        cache_len = len(cache)
                        print(f"🔍 [{dt.strftime('%H:%M:%S')}] {symbol} ({timeframe}) 开始计算指标 [cache_len={cache_len}]")
                        if cache_len >= 20:
                            hist_indicators = calculate_indicators(list(cache[:-1]))  # 使用前N-1根K线计算
                            if hist_indicators:
                                save_indicators(symbol, timeframe, hist_indicators, prev_timestamp)
                                print(f"📊 [{dt.strftime('%H:%M:%S')}] 已保存 {symbol} ({timeframe}) 指标 [cache:{cache_len}]")
                            else:
                                print(f"⚠️  [{dt.strftime('%H:%M:%S')}] {symbol} ({timeframe}) 指标计算失败 [cache:{cache_len}]")
                        else:
                            print(f"⚠️  [{dt.strftime('%H:%M:%S')}] {symbol} ({timeframe}) cache不足 [cache:{cache_len}, 需要>=20]")
        
        # 计算并保存最新指标（实时更新，同时保存timestamp到历史表）
        if len(kline_cache[timeframe][symbol]) >= 20:
            indicators = calculate_indicators(list(kline_cache[timeframe][symbol]))
            
            if indicators:
                # 获取最新K线的时间戳
                latest_kline = kline_cache[timeframe][symbol][-1]
                latest_timestamp = int(latest_kline[0])
                
                # 保存到数据库（更新最新记录 + 历史记录）
                save_indicators(symbol, timeframe, indicators, latest_timestamp)
                
                # 输出日志（每5分钟输出一次，避免刷屏）
                now = datetime.now()
                if now.minute % 5 == 0 and now.second < 10:  # 在整点后10秒内输出
                    print(f"[{now.strftime('%H:%M:%S')}] {symbol} ({timeframe}): "
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
    print("🚀 OKEx WebSocket 实时K线指标采集器 (修复版)")
    print("=" * 80)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"币种数量: {len(SYMBOLS)}")
    print(f"时间周期: 5分钟, 1小时")
    print(f"技术指标: RSI(14), Parabolic SAR, Bollinger Bands(20,2)")
    print(f"数据源: OKEx WebSocket (实时)")
    print("=" * 80)
    
    # 初始化数据库
    init_database()
    
    # 加载历史K线数据
    await init_kline_cache()
    
    # 启动 WebSocket 客户端
    await ws_client()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  收到停止信号，正在关闭...")
        sys.exit(0)
