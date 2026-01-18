#!/usr/bin/env python3
"""
SAR数据实时更新脚本 - 使用正确的数据库结构
从OKEx获取最新5分钟K线数据并计算SAR指标，更新到 sar_raw_data 表
"""
import sqlite3
import requests
import time
from datetime import datetime
import json

# 配置
DB_PATH = 'databases/sar_slope_data.db'
SYMBOLS = [
    'AAVE', 'CRV', 'XRP', 'SUI', 'HBAR', 'DOT', 'NEAR', 'APT', 'TAO', 'LDO',
    'BTC', 'ETH', 'BNB', 'SOL', 'LTC', 'DOGE', 'TRX', 'TON', 'ETC', 'BCH',
    'XLM', 'FIL', 'LINK', 'CRO', 'UNI', 'CFX', 'STX'
]

class SARCalculator:
    """SAR指标计算器"""
    def __init__(self, af_start=0.02, af_max=0.2):
        self.af_start = af_start
        self.af_max = af_max
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.sar = None
        self.ep = None
        self.af = self.af_start
        self.position = None
        self.position_sequence = 0
        self.position_start_time = None
    
    def calculate_batch(self, klines):
        """批量计算SAR（用于初始化）"""
        results = []
        self.reset()
        
        for i, k in enumerate(klines):
            if i == 0:
                # 第一根K线，初始化
                self.sar = k['low']
                self.ep = k['high']
                self.position = 'long'
                self.position_sequence = 1
                self.position_start_time = k['timestamp']
            else:
                # 计算新的SAR值
                prev_k = klines[i-1]
                self._update_sar(k, prev_k)
            
            # 计算持续时间（分钟）
            duration = (k['timestamp'] - self.position_start_time) // (60 * 1000)
            
            results.append({
                'symbol': k.get('symbol', ''),
                'timestamp': k['timestamp'],
                'kline_time': datetime.fromtimestamp(k['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'open_price': k['open'],
                'high_price': k['high'],
                'low_price': k['low'],
                'close_price': k['close'],
                'sar_value': self.sar,
                'position': self.position,
                'position_sequence': self.position_sequence,
                'duration_minutes': duration
            })
        
        return results
    
    def _update_sar(self, current_k, prev_k):
        """更新SAR值"""
        if self.position == 'long':
            # 多头模式
            new_sar = self.sar + self.af * (self.ep - self.sar)
            new_sar = min(new_sar, prev_k['low'])
            
            # 检查是否反转为空头
            if current_k['low'] < new_sar:
                # 反转
                self.position = 'short'
                self.sar = self.ep  # SAR变为之前的极值点
                self.ep = current_k['low']
                self.af = self.af_start
                self.position_sequence = 1
                self.position_start_time = current_k['timestamp']
            else:
                # 继续多头
                self.sar = new_sar
                self.position_sequence += 1
                # 更新极值点和加速因子
                if current_k['high'] > self.ep:
                    self.ep = current_k['high']
                    self.af = min(self.af + self.af_start, self.af_max)
        else:
            # 空头模式
            new_sar = self.sar + self.af * (self.ep - self.sar)
            new_sar = max(new_sar, prev_k['high'])
            
            # 检查是否反转为多头
            if current_k['high'] > new_sar:
                # 反转
                self.position = 'long'
                self.sar = self.ep  # SAR变为之前的极值点
                self.ep = current_k['high']
                self.af = self.af_start
                self.position_sequence = 1
                self.position_start_time = current_k['timestamp']
            else:
                # 继续空头
                self.sar = new_sar
                self.position_sequence += 1
                # 更新极值点和加速因子
                if current_k['low'] < self.ep:
                    self.ep = current_k['low']
                    self.af = min(self.af + self.af_start, self.af_max)

def get_okex_klines(symbol, bar='5m', limit=100):
    """从OKEx获取K线数据"""
    try:
        instId = f"{symbol}-USDT-SWAP"
        url = f"https://www.okx.com/api/v5/market/candles?instId={instId}&bar={bar}&limit={limit}"
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('code') != '0':
            return None, f"API错误 - {data.get('msg')}"
        
        klines = data.get('data', [])
        if not klines:
            return None, "无数据"
        
        # 解析K线数据（OKEx返回的数据是逆序的，需要反转）
        parsed_klines = []
        for k in reversed(klines):
            parsed_klines.append({
                'timestamp': int(k[0]),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            })
        
        return parsed_klines, None
        
    except Exception as e:
        return None, str(e)

def get_last_sar_state(conn, symbol):
    """获取币种的最后SAR状态"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sar_value, position, position_sequence, timestamp
        FROM sar_raw_data
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (symbol,))
    
    result = cursor.fetchone()
    if result:
        return {
            'sar': result[0],
            'position': result[1],
            'sequence': result[2],
            'timestamp': result[3]
        }
    return None

def update_symbol_data(symbol, conn, full_update=False):
    """更新单个币种的SAR数据"""
    try:
        # 获取K线数据
        limit = 100 if full_update else 10
        klines, error = get_okex_klines(symbol, bar='5m', limit=limit)
        
        if error:
            return False, f"获取数据失败: {error}"
        
        # 添加symbol到每个kline
        for k in klines:
            k['symbol'] = symbol
        
        # 检查数据库中最后的时间戳
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(timestamp) FROM sar_raw_data WHERE symbol = ?
        """, (symbol,))
        last_ts = cursor.fetchone()[0]
        
        # 过滤出新数据
        if last_ts:
            new_klines = [k for k in klines if k['timestamp'] > last_ts]
            if not new_klines:
                return True, "数据已是最新"
            
            # 获取最后的SAR状态
            last_state = get_last_sar_state(conn, symbol)
            if not last_state:
                # 如果没有历史状态，需要全量计算
                new_klines = klines
                last_state = None
        else:
            # 没有历史数据，全量计算
            new_klines = klines
            last_state = None
        
        # 计算SAR
        calculator = SARCalculator()
        
        if last_state:
            # 从上次状态继续计算
            calculator.sar = last_state['sar']
            calculator.position = last_state['position']
            calculator.position_sequence = last_state['sequence']
            calculator.position_start_time = last_state['timestamp']
            
            # 需要前一根K线来计算
            prev_klines = [k for k in klines if k['timestamp'] <= last_ts]
            if prev_klines:
                # 计算新数据
                results = []
                for i, k in enumerate(new_klines):
                    prev_k = prev_klines[-1] if i == 0 else new_klines[i-1]
                    calculator._update_sar(k, prev_k)
                    
                    duration = (k['timestamp'] - calculator.position_start_time) // (60 * 1000)
                    results.append({
                        'symbol': symbol,
                        'timestamp': k['timestamp'],
                        'kline_time': datetime.fromtimestamp(k['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                        'open_price': k['open'],
                        'high_price': k['high'],
                        'low_price': k['low'],
                        'close_price': k['close'],
                        'sar_value': calculator.sar,
                        'position': calculator.position,
                        'position_sequence': calculator.position_sequence,
                        'duration_minutes': duration
                    })
            else:
                # 重新全量计算
                results = calculator.calculate_batch(new_klines)
        else:
            # 全量计算
            results = calculator.calculate_batch(new_klines)
        
        # 插入数据库
        for record in results:
            cursor.execute("""
                INSERT OR REPLACE INTO sar_raw_data
                (symbol, timestamp, kline_time, open_price, high_price, low_price, close_price,
                 sar_value, position, position_sequence, duration_minutes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                record['symbol'], record['timestamp'], record['kline_time'],
                record['open_price'], record['high_price'], record['low_price'], record['close_price'],
                record['sar_value'], record['position'], record['position_sequence'],
                record['duration_minutes']
            ))
        
        # 更新系统状态表
        if results:
            latest = results[-1]
            cursor.execute("""
                INSERT OR REPLACE INTO system_status
                (symbol, last_update_time, last_kline_time, total_klines, 
                 current_position, current_sequence, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
            """, (
                symbol, latest['timestamp'], latest['kline_time'],
                len(results), latest['position'], latest['position_sequence']
            ))
        
        conn.commit()
        
        latest_time = results[-1]['kline_time'] if results else ''
        return True, f"新增 {len(results)} 条记录 | 最新: {latest_time}"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"更新失败: {e}"

def main():
    """主函数"""
    print(f"\n{'='*80}")
    print(f"  SAR数据实时更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    conn = sqlite3.connect(DB_PATH)
    
    success_count = 0
    failed_count = 0
    results = []
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"[{i:2d}/{len(SYMBOLS)}] {symbol:6s}: ", end='', flush=True)
        
        success, message = update_symbol_data(symbol, conn)
        
        if success:
            print(f"✓ {message}")
            success_count += 1
        else:
            print(f"✗ {message}")
            failed_count += 1
        
        results.append({
            'symbol': symbol,
            'success': success,
            'message': message
        })
        
        # 避免请求过快
        if i < len(SYMBOLS):
            time.sleep(0.3)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"  更新完成: 成功 {success_count}/{len(SYMBOLS)} | 失败 {failed_count}")
    print(f"{'='*80}\n")
    
    # 显示数据库统计
    print("数据库统计:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT symbol, COUNT(*) as count, 
               MAX(kline_time) as latest_time,
               current_position, current_sequence
        FROM sar_raw_data
        LEFT JOIN system_status USING (symbol)
        GROUP BY symbol
        ORDER BY symbol
    """)
    
    print(f"{'币种':<8} {'记录数':>8} {'最新时间':<20} {'当前':<6} {'序列':>4}")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"{row[0]:<8} {row[1]:>8,} {row[2] or 'N/A':<20} {row[3] or 'N/A':<6} {row[4] or 0:>4}")
    
    conn.close()

if __name__ == '__main__':
    main()
