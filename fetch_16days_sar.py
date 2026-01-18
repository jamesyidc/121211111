#!/usr/bin/env python3
"""
获取近16天的SAR数据并保存到JSONL
"""
import sys
import json
import time
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, '/home/user/webapp/source_code')
from okx.MarketData import MarketAPI
from sar_jsonl_manager import SARJSONLManager

# 初始化OKX API
flag = "0"  # 实盘
marketDataAPI = MarketAPI(flag=flag)

# 时区设置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 币种列表
SYMBOLS = [
    'AAVE', 'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'DOGE', 'LINK', 'DOT', 'LTC',
    'UNI', 'NEAR', 'FIL', 'ETC', 'APT', 'HBAR', 'CRV', 'LDO', 'STX', 'CFX',
    'CRO', 'BCH', 'SUI', 'TAO', 'TRX', 'TON', 'XLM'
]

# SAR计算类
class SARCalculator:
    @staticmethod
    def calculate_sar(candles, initial_af=0.02, max_af=0.2):
        """
        计算SAR指标（标准参数）
        initial_af: 0.02
        max_af: 0.2
        """
        if len(candles) < 2:
            return [], []
        
        sar_values = []
        positions = []
        
        # 初始化
        high = float(candles[0][2])
        low = float(candles[0][3])
        close = float(candles[0][4])
        
        # 判断初始趋势
        if close > (high + low) / 2:
            position = 'long'
            sar = low
            ep = high
        else:
            position = 'short'
            sar = high
            ep = low
        
        af = initial_af
        
        sar_values.append(sar)
        positions.append(position)
        
        # 计算后续SAR
        for i in range(1, len(candles)):
            high = float(candles[i][2])
            low = float(candles[i][3])
            close = float(candles[i][4])
            
            # 更新SAR
            sar = sar + af * (ep - sar)
            
            # 检查是否需要反转
            reverse = False
            if position == 'long':
                if low < sar:
                    reverse = True
                    position = 'short'
                    sar = ep
                    ep = low
                    af = initial_af
                else:
                    if high > ep:
                        ep = high
                        af = min(af + initial_af, max_af)
                    # SAR不能高于前两根K线的最低价
                    if i >= 1:
                        sar = min(sar, float(candles[i-1][3]))
                    if i >= 2:
                        sar = min(sar, float(candles[i-2][3]))
            else:  # short
                if high > sar:
                    reverse = True
                    position = 'long'
                    sar = ep
                    ep = high
                    af = initial_af
                else:
                    if low < ep:
                        ep = low
                        af = min(af + initial_af, max_af)
                    # SAR不能低于前两根K线的最高价
                    if i >= 1:
                        sar = max(sar, float(candles[i-1][2]))
                    if i >= 2:
                        sar = max(sar, float(candles[i-2][2]))
            
            sar_values.append(sar)
            positions.append(position)
        
        return sar_values, positions


def fetch_all_candles(symbol, days=16, max_candles=5000):
    """
    获取指定天数的所有K线数据
    
    Args:
        symbol: 币种符号
        days: 天数
        max_candles: 最大K线数量
    
    Returns:
        list: K线数据列表（从旧到新）
    """
    all_candles = []
    batch_count = 0
    max_batches = 20  # 最多20批次
    
    # 首先获取最新的300根
    try:
        result = marketDataAPI.get_candlesticks(
            instId=f"{symbol}-USDT",
            bar="5m",
            limit=300
        )
        
        if result['code'] != '0':
            print(f"  ❌ 获取失败: {result.get('msg', 'Unknown error')}")
            return []
        
        data = result.get('data', [])
        if not data:
            print(f"  ❌ 没有数据")
            return []
        
        # OKX返回的是从最新到最旧，需要反转
        data.reverse()
        all_candles = data
        batch_count += 1
        
        # 获取最旧的时间戳
        oldest_ts = int(data[0][0])
        oldest_time = datetime.fromtimestamp(oldest_ts/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        latest_ts = int(data[-1][0])
        latest_time = datetime.fromtimestamp(latest_ts/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"  批次1: {len(data)} 根 | {oldest_time} -> {latest_time}")
        
        # 计算目标时间戳（16天前）
        target_ts = int((datetime.now(BEIJING_TZ) - timedelta(days=days)).timestamp() * 1000)
        
        # 使用after参数继续获取更早的数据
        while len(all_candles) < max_candles and batch_count < max_batches and oldest_ts > target_ts:
            batch_count += 1
            time.sleep(0.1)  # 避免请求太快
            
            result = marketDataAPI.get_candlesticks(
                instId=f"{symbol}-USDT",
                bar="5m",
                limit=300,
                after=str(oldest_ts)
            )
            
            if result['code'] != '0':
                print(f"  ❌ 批次{batch_count}失败: {result.get('msg', 'Unknown error')}")
                break
            
            data = result.get('data', [])
            if not data:
                print(f"  ✓ 批次{batch_count}: 没有更多数据")
                break
            
            # 反转并添加到前面
            data.reverse()
            oldest_ts_new = int(data[0][0])
            latest_ts_new = int(data[-1][0])
            
            oldest_time = datetime.fromtimestamp(oldest_ts_new/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            latest_time = datetime.fromtimestamp(latest_ts_new/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"  批次{batch_count}: {len(data)} 根 | {oldest_time} -> {latest_time}")
            
            # 添加到前面
            all_candles = data + all_candles
            oldest_ts = oldest_ts_new
            
            # 如果已经到达目标时间，停止
            if oldest_ts <= target_ts:
                print(f"  ✓ 已到达{days}天前")
                break
        
        return all_candles
        
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return []


def process_symbol(symbol):
    """处理单个币种的数据"""
    print(f"\n{'='*60}")
    print(f"处理 {symbol}...")
    print('='*60)
    
    # 1. 获取K线数据
    print("步骤1: 获取K线数据...")
    candles = fetch_all_candles(symbol, days=16)
    if not candles:
        return False
    
    print(f"  ✓ 总计: {len(candles)} 根K线")
    
    # 2. 计算SAR
    print("步骤2: 计算SAR...")
    sar_values, positions = SARCalculator.calculate_sar(candles)
    print(f"  ✓ 计算完成")
    
    # 3. 构建记录并保存
    print("步骤3: 保存到JSONL...")
    manager = SARJSONLManager(symbol)
    
    # 先清空现有数据
    existing_records = manager.read_records()
    print(f"  - 现有数据: {len(existing_records)} 条")
    
    # 用集合去重（基于时间）
    existing_times = {record.get('beijing_time') for record in existing_records}
    
    saved_count = 0
    skipped_count = 0
    
    for i, candle in enumerate(candles):
        timestamp = int(candle[0])
        beijing_time = datetime.fromtimestamp(timestamp/1000, BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 如果这个时间的数据已存在，跳过
        if beijing_time in existing_times:
            skipped_count += 1
            continue
        
        record = {
            'symbol': symbol,
            'timestamp': timestamp,
            'beijing_time': beijing_time,
            'open': round(float(candle[1]), 2),
            'high': round(float(candle[2]), 2),
            'low': round(float(candle[3]), 2),
            'close': round(float(candle[4]), 2),
            'volume': float(candle[5]),
            'sar': round(sar_values[i], 4),
            'position': positions[i],
            'sequence': 1,  # 稍后重新计算
            'duration': 0   # 稍后重新计算
        }
        
        manager.append_record(record)
        saved_count += 1
    
    print(f"  ✓ 新增: {saved_count} 条, 跳过: {skipped_count} 条")
    
    # 4. 重新计算序列号
    print("步骤4: 重新计算序列号...")
    all_records = manager.read_records()
    all_records.reverse()  # 从旧到新排序
    
    for i in range(len(all_records)):
        if i == 0:
            all_records[i]['sequence'] = 1
            all_records[i]['duration'] = 0
        else:
            prev = all_records[i-1]
            curr = all_records[i]
            
            # 解析时间
            prev_time = datetime.strptime(prev['beijing_time'], '%Y-%m-%d %H:%M:%S')
            curr_time = datetime.strptime(curr['beijing_time'], '%Y-%m-%d %H:%M:%S')
            time_diff_minutes = (curr_time - prev_time).total_seconds() / 60
            
            # 判断是否连续（4-6分钟）
            is_continuous = 4 <= time_diff_minutes <= 6
            
            if not is_continuous or prev['position'] != curr['position']:
                # 时间不连续或position变化，重置序列号
                curr['sequence'] = 1
                curr['duration'] = 0
            else:
                # 时间连续且position相同，序列号+1
                curr['sequence'] = prev['sequence'] + 1
                curr['duration'] = curr['sequence'] * 5  # 5分钟 * 序列号
    
    # 5. 保存更新后的数据
    all_records.reverse()  # 恢复最新到最旧
    
    # 手动写入文件
    with open(manager.jsonl_path, 'w', encoding='utf-8') as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # 6. 显示最新状态
    latest = all_records[0]
    print(f"  ✓ 最新: {latest['beijing_time']} {latest['position']} #{latest['sequence']} @ {latest['close']}")
    
    return True


def main():
    """主函数"""
    print("="*60)
    print("开始获取近16天的SAR数据")
    print(f"时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    
    for symbol in SYMBOLS:
        try:
            if process_symbol(symbol):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"\n❌ {symbol} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
    
    print("\n" + "="*60)
    print("处理完成")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print("="*60)


if __name__ == '__main__':
    main()
