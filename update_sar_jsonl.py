#!/usr/bin/env python3
"""
SAR数据实时更新脚本 (JSONL版本)
- 从OKEx获取最新5分钟K线数据
- 计算SAR指标
- 保存到JSONL文件
- 所有时间使用北京时间
"""
import requests
import time
from datetime import datetime
import pytz
from sar_jsonl_manager import SARJSONLManager, BEIJING_TZ, ALL_SYMBOLS

# SAR计算器
class SARCalculator:
    """SAR指标计算器"""
    def __init__(self, af_start=0.02, af_max=0.2):
        self.af_start = af_start
        self.af_max = af_max
        self.reset()
    
    def reset(self):
        self.sar = None
        self.ep = None
        self.af = self.af_start
        self.position = None
        self.position_sequence = 0
        self.position_start_time = None
    
    def load_state(self, last_record):
        """从上一条记录加载状态"""
        self.sar = last_record['sar']
        self.position = last_record['position']
        self.position_sequence = last_record['sequence']
        self.position_start_time = last_record['timestamp']
        
        # EP需要根据历史数据重建，这里简化处理
        if self.position == 'long':
            self.ep = last_record['high']
        else:
            self.ep = last_record['low']
    
    def calculate_next(self, prev_k, current_k):
        """计算下一根K线的SAR"""
        if self.position == 'long':
            new_sar = self.sar + self.af * (self.ep - self.sar)
            new_sar = min(new_sar, prev_k['low'])
            
            if current_k['low'] < new_sar:
                # 转为空头
                self.position = 'short'
                self.sar = self.ep
                self.ep = current_k['low']
                self.af = self.af_start
                self.position_sequence = 1
                self.position_start_time = current_k['timestamp']
            else:
                # 继续多头
                self.sar = new_sar
                self.position_sequence += 1
                if current_k['high'] > self.ep:
                    self.ep = current_k['high']
                    self.af = min(self.af + self.af_start, self.af_max)
        else:
            # 空头模式
            new_sar = self.sar + self.af * (self.ep - self.sar)
            new_sar = max(new_sar, prev_k['high'])
            
            if current_k['high'] > new_sar:
                # 转为多头
                self.position = 'long'
                self.sar = self.ep
                self.ep = current_k['high']
                self.af = self.af_start
                self.position_sequence = 1
                self.position_start_time = current_k['timestamp']
            else:
                # 继续空头
                self.sar = new_sar
                self.position_sequence += 1
                if current_k['low'] < self.ep:
                    self.ep = current_k['low']
                    self.af = min(self.af + self.af_start, self.af_max)
        
        # 计算持续时间
        duration = (current_k['timestamp'] - self.position_start_time) // (60 * 1000)
        
        return {
            'symbol': current_k['symbol'],
            'timestamp': current_k['timestamp'],
            'beijing_time': datetime.fromtimestamp(current_k['timestamp'] / 1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'open': current_k['open'],
            'high': current_k['high'],
            'low': current_k['low'],
            'close': current_k['close'],
            'sar': self.sar,
            'position': self.position,
            'sequence': self.position_sequence,
            'duration_minutes': duration
        }


def get_okex_klines(symbol, bar='5m', limit=10):
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
                'volume': float(k[5]),
                'symbol': symbol
            })
        
        return parsed_klines, None
        
    except Exception as e:
        return None, str(e)


def update_symbol_data(symbol, manager):
    """更新单个币种的SAR数据"""
    try:
        # 获取最新K线数据
        klines, error = get_okex_klines(symbol, bar='5m', limit=10)
        
        if error:
            return False, f"获取数据失败: {error}"
        
        # 获取现有数据的最后记录
        last_record = manager.get_latest_record(symbol)
        
        if not last_record:
            # 如果没有历史数据，返回提示需要初始化
            return False, "无历史数据，需要初始化"
        
        last_timestamp = last_record['timestamp']
        
        # 过滤出新K线
        new_klines = [k for k in klines if k['timestamp'] > last_timestamp]
        
        if not new_klines:
            return True, "数据已是最新"
        
        # 加载SAR状态
        calculator = SARCalculator()
        calculator.load_state(last_record)
        
        # 计算新数据
        new_records = []
        prev_k = {
            'timestamp': last_record['timestamp'],
            'open': last_record['open'],
            'high': last_record['high'],
            'low': last_record['low'],
            'close': last_record['close']
        }
        
        for k in new_klines:
            record = calculator.calculate_next(prev_k, k)
            new_records.append(record)
            prev_k = k
        
        # 保存新记录
        count = manager.append_records(symbol, new_records)
        
        if count > 0:
            latest = new_records[-1]
            return True, f"新增 {count} 条 | 最新: {latest['beijing_time']} (北京时间)"
        else:
            return True, "无新数据"
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"更新失败: {e}"


def main():
    """主函数"""
    print(f"\n{'='*80}")
    print(f"  SAR数据实时更新 (JSONL) - {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    print(f"{'='*80}\n")
    
    manager = SARJSONLManager()
    
    success_count = 0
    failed_count = 0
    results = []
    
    for i, symbol in enumerate(ALL_SYMBOLS, 1):
        print(f"[{i:2d}/{len(ALL_SYMBOLS)}] {symbol:6s}: ", end='', flush=True)
        
        success, message = update_symbol_data(symbol, manager)
        
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
        if i < len(ALL_SYMBOLS):
            time.sleep(0.3)
    
    print(f"\n{'='*80}")
    print(f"  更新完成: 成功 {success_count}/{len(ALL_SYMBOLS)} | 失败 {failed_count}")
    print(f"{'='*80}\n")
    
    # 显示统计
    print("📊 数据统计:\n")
    status_list = manager.get_all_symbols_status()
    
    print(f"{'币种':<8} {'记录数':>8} {'最新时间 (北京)':<20} {'当前':<6} {'序列':>4}")
    print("-" * 60)
    for status in status_list[:10]:  # 只显示前10个
        print(f"{status['symbol']:<8} {status['total_klines']:>8,} "
              f"{status['last_kline_time']:<20} "
              f"{status['current_position']:<6} {status['current_sequence']:>4}")
    
    if len(status_list) > 10:
        print(f"... 还有 {len(status_list) - 10} 个币种")


if __name__ == '__main__':
    main()
