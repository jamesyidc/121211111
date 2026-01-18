#!/usr/bin/env python3
"""
SAR JSONL 采集器
功能：
1. 每5分钟自动采集一次所有27个币种的最新SAR数据
2. 将数据保存到 JSONL 文件
3. 保持30天的历史数据
4. 计算并维护序列号和持续时间
5. 记录运行日志
"""

import time
import logging
import sys
import os
import json
import okx.MarketData as MarketData
from datetime import datetime, timedelta
import pytz

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入SAR JSONL管理器
from sar_jsonl_manager import SARJSONLManager

# 配置日志
LOG_DIR = '/home/user/webapp/logs'
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(f'{LOG_DIR}/sar_jsonl_collector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 27个币种
SYMBOLS = [
    'AAVE', 'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'DOGE', 'LINK', 'DOT', 'LTC', 
    'UNI', 'NEAR', 'FIL', 'ETC', 'APT', 'HBAR', 'CRV', 'LDO', 'STX', 'CFX', 
    'CRO', 'BCH', 'SUI', 'TAO', 'TRX', 'TON', 'XLM'
]

# OKX API初始化
flag = "0"  # 实盘: 0, 模拟盘: 1
marketDataAPI = MarketData.MarketAPI(flag=flag)

# 采集间隔（秒）
COLLECTION_INTERVAL = 5 * 60  # 5分钟

class SARCalculator:
    """SAR计算器（简化版）"""
    
    @staticmethod
    def calculate_sar(candles, initial_af=0.02, max_af=0.2):
        """
        计算抛物线SAR指标
        
        参数:
        - candles: K线数据列表，每个元素包含 [timestamp, o, h, l, c, vol]
        - initial_af: 初始加速因子，默认0.02（标准参数）
        - max_af: 最大加速因子，默认0.2（标准参数）
        
        返回:
        - sar_values: SAR值列表
        - positions: 仓位列表（'long' 或 'short'）
        
        注意：参数已调整为OKX的SAR配置，确保计算结果与OKX图表一致
        """
        if len(candles) < 2:
            return [], []
        
        sar_values = []
        positions = []
        
        # 初始化
        high = float(candles[0][2])
        low = float(candles[0][3])
        position = 'long' if float(candles[0][4]) > float(candles[0][1]) else 'short'
        sar = low if position == 'long' else high
        ep = high if position == 'long' else low
        af = initial_af
        
        sar_values.append(sar)
        positions.append(position)
        
        # 遍历K线计算SAR
        for i in range(1, len(candles)):
            prev_sar = sar
            prev_position = position
            prev_ep = ep
            prev_af = af
            
            high = float(candles[i][2])
            low = float(candles[i][3])
            close = float(candles[i][4])
            
            # 计算新的SAR
            sar = prev_sar + prev_af * (prev_ep - prev_sar)
            
            # 检查是否反转
            if prev_position == 'long':
                if low < sar:
                    # 多转空
                    position = 'short'
                    sar = prev_ep
                    ep = low
                    af = initial_af
                else:
                    position = 'long'
                    if high > prev_ep:
                        ep = high
                        af = min(prev_af + initial_af, max_af)
                    else:
                        ep = prev_ep
                        af = prev_af
                    # 确保SAR不高于前两根K线的最低价
                    sar = min(sar, float(candles[i-1][3]))
                    if i > 1:
                        sar = min(sar, float(candles[i-2][3]))
            else:  # short
                if high > sar:
                    # 空转多
                    position = 'long'
                    sar = prev_ep
                    ep = high
                    af = initial_af
                else:
                    position = 'short'
                    if low < prev_ep:
                        ep = low
                        af = min(prev_af + initial_af, max_af)
                    else:
                        ep = prev_ep
                        af = prev_af
                    # 确保SAR不低于前两根K线的最高价
                    sar = max(sar, float(candles[i-1][2]))
                    if i > 1:
                        sar = max(sar, float(candles[i-2][2]))
            
            sar_values.append(sar)
            positions.append(position)
        
        return sar_values, positions


def fetch_kline_data(symbol, limit=100):
    """
    获取K线数据
    
    参数:
    - symbol: 币种代码，如 'BTC'
    - limit: 获取的K线数量，默认100
    
    返回:
    - candles: K线数据列表
    """
    try:
        inst_id = f"{symbol}-USDT"
        bar = "5m"  # 5分钟K线
        
        # 获取K线数据
        result = marketDataAPI.get_candlesticks(
            instId=inst_id,
            bar=bar,
            limit=str(limit)
        )
        
        if result['code'] == '0' and result['data']:
            # 数据格式: [timestamp, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            # 按时间正序排列（OKX返回的是倒序）
            candles = result['data'][::-1]
            return candles
        else:
            logger.error(f"获取{symbol}的K线数据失败: {result}")
            return None
            
    except Exception as e:
        logger.error(f"获取{symbol}的K线数据异常: {e}")
        return None


def collect_symbol_sar_data(symbol):
    """
    采集单个币种的SAR数据并保存到JSONL
    
    参数:
    - symbol: 币种代码，如 'BTC'
    
    返回:
    - bool: 是否成功
    """
    try:
        # 1. 获取K线数据
        candles = fetch_kline_data(symbol, limit=100)
        if not candles:
            logger.warning(f"{symbol}: 无法获取K线数据")
            return False
        
        # 2. 计算SAR
        calculator = SARCalculator()
        sar_values, positions = calculator.calculate_sar(candles)
        
        if not sar_values:
            logger.warning(f"{symbol}: SAR计算失败")
            return False
        
        # 3. 获取最新的已确认K线数据（confirm=1）
        # OKX返回的数据是按时间倒序的，经过[::-1]反转后变成正序
        # 最后一根K线(confirm=0)可能还在形成中，我们需要获取已确认的K线
        latest_confirmed_idx = -1
        for i in range(len(candles) - 1, -1, -1):
            # candles的数据格式: [timestamp, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            if len(candles[i]) >= 9 and candles[i][8] == '1':
                latest_confirmed_idx = i
                break
        
        if latest_confirmed_idx == -1:
            # 没有找到已确认的K线，使用最后一根
            latest_confirmed_idx = -1
        
        latest_candle = candles[latest_confirmed_idx]
        latest_sar = sar_values[latest_confirmed_idx]
        latest_position = positions[latest_confirmed_idx]
        
        # 解析数据
        timestamp = int(latest_candle[0])
        open_price = float(latest_candle[1])
        high_price = float(latest_candle[2])
        low_price = float(latest_candle[3])
        close_price = float(latest_candle[4])
        
        # 转换为北京时间
        dt = datetime.fromtimestamp(timestamp / 1000, tz=BEIJING_TZ)
        beijing_time = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 4. 初始化JSONL管理器
        manager = SARJSONLManager(symbol)
        
        # 5. 检查是否已经采集过这条数据
        current_status = manager.get_latest_status()
        if current_status and current_status.get('last_update_time') == beijing_time:
            # 这条数据已经存在，跳过
            logger.info(f"{symbol}: 数据已存在 - {beijing_time}")
            return True
        
        # 6. 获取当前序列信息
        # 确定序列号和持续时间
        if current_status:
            last_position = current_status['current_position']
            last_sequence = current_status['current_sequence']
            last_update_time = current_status.get('last_update_time', '')
            
            # 检查时间连续性：只有相邻的5分钟K线才能延续序列号
            # 时间差应该恰好是5分钟（300秒），允许±1分钟的误差
            is_continuous = False
            if last_update_time:
                try:
                    last_dt = datetime.strptime(last_update_time, '%Y-%m-%d %H:%M:%S')
                    curr_dt = datetime.strptime(beijing_time, '%Y-%m-%d %H:%M:%S')
                    time_diff_minutes = (curr_dt - last_dt).total_seconds() / 60
                    # 时间差在4-6分钟之间认为是连续的
                    is_continuous = 4 <= time_diff_minutes <= 6
                except:
                    is_continuous = False
            
            if not is_continuous:
                # 数据不连续（时间跳跃），重置序列号为1
                sequence = 1
                duration_minutes = 0
            elif last_position == latest_position:
                # 同一个position且数据连续，序列号+1
                sequence = last_sequence + 1
                # 计算持续时间（分钟）
                all_records = manager.read_records()
                duration_minutes = sum(1 for r in all_records if r.get('position') == latest_position and r.get('sequence') >= sequence) * 5
            else:
                # position反转，序列号重置为1
                sequence = 1
                duration_minutes = 0
        else:
            # 第一次采集
            sequence = 1
            duration_minutes = 0
        
        # 6. 构建新记录
        new_record = {
            'symbol': symbol,
            'timestamp': timestamp,
            'beijing_time': beijing_time,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'sar': latest_sar,
            'position': latest_position,
            'sequence': sequence,
            'duration_minutes': duration_minutes
        }
        
        # 7. 保存到JSONL
        if manager.append_record(new_record):
            logger.info(f"{symbol}: ✓ 保存成功 - {latest_position} #{sequence} - 价格: {close_price}, SAR: {latest_sar:.4f}, 持续: {duration_minutes}分钟")
            return True
        else:
            logger.error(f"{symbol}: ✗ 保存失败")
            return False
        
    except Exception as e:
        logger.error(f"{symbol}: 采集异常 - {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def cleanup_old_jsonl_data():
    """清理超过30天的JSONL数据"""
    logger.info("开始清理旧数据...")
    total_deleted = 0
    
    for symbol in SYMBOLS:
        try:
            manager = SARJSONLManager(symbol)
            deleted = manager.cleanup_old_data(days=30)
            if deleted > 0:
                logger.info(f"  {symbol}: 清理了 {deleted} 条旧数据")
                total_deleted += deleted
        except Exception as e:
            logger.error(f"  {symbol}: 清理失败 - {e}")
    
    logger.info(f"✓ 总共清理了 {total_deleted} 条超过30天的旧数据")
    return total_deleted


def collect_all_symbols():
    """采集所有币种的数据"""
    logger.info("="*80)
    logger.info("SAR JSONL 采集器 - 开始运行")
    logger.info(f"采集时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"币种数量: {len(SYMBOLS)} 个")
    logger.info("="*80)
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(SYMBOLS, 1):
        try:
            logger.info(f"[{i}/{len(SYMBOLS)}] 采集 {symbol}...")
            
            if collect_symbol_sar_data(symbol):
                success_count += 1
            else:
                fail_count += 1
        
        except Exception as e:
            fail_count += 1
            logger.error(f"  ✗ {symbol} 采集异常: {e}")
        
        # 避免请求过快
        if i < len(SYMBOLS):
            time.sleep(0.5)
    
    # 每次采集后清理旧数据
    try:
        cleanup_old_jsonl_data()
    except Exception as e:
        logger.error(f"清理旧数据失败: {e}")
    
    # 输出统计
    logger.info("="*80)
    logger.info(f"本次采集完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    logger.info("="*80)
    
    return success_count, fail_count


def main():
    """主循环 - 延迟5分钟采集策略"""
    logger.info("SAR JSONL 采集器启动")
    logger.info(f"进程ID: {os.getpid()}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"日志目录: {LOG_DIR}")
    logger.info(f"采集间隔: {COLLECTION_INTERVAL} 秒 (5分钟)")
    logger.info(f"⚠️  采集策略: 延迟5分钟采集（等K线完全形成后再采集）")
    logger.info(f"    例如: 18:05的K线 → 18:10采集")
    logger.info(f"          18:10的K线 → 18:15采集")
    
    cycle_count = 0
    total_success = 0
    total_fail = 0
    
    # 🔥 首次启动：延迟5分钟后再开始第一次采集
    logger.info("\n" + "="*80)
    logger.info("⏰ 首次启动延迟策略:")
    now = datetime.now(BEIJING_TZ)
    logger.info(f"   当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 计算需要等待到下一个5分钟边界后5分钟
    # 例如：当前17:58 → 等到18:05（下一个5分钟边界）
    minutes = now.minute
    next_5min_mark = ((minutes // 5) + 1) * 5
    if next_5min_mark >= 60:
        next_time = now.replace(hour=(now.hour + 1) % 24, minute=0, second=0, microsecond=0)
    else:
        next_time = now.replace(minute=next_5min_mark, second=0, microsecond=0)
    
    # 再延迟5分钟（等K线完成）
    next_time = next_time + timedelta(minutes=5)
    
    wait_seconds = (next_time - now).total_seconds()
    logger.info(f"   首次采集时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   等待时长: {wait_seconds:.0f} 秒 ({wait_seconds/60:.1f} 分钟)")
    logger.info(f"   说明: 等到 {(next_time - timedelta(minutes=5)).strftime('%H:%M')} 的K线完全形成")
    logger.info("="*80 + "\n")
    
    time.sleep(wait_seconds)
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"第 {cycle_count} 次采集开始")
            logger.info(f"{'='*80}\n")
            
            success, fail = collect_all_symbols()
            total_success += success
            total_fail += fail
            
            # 输出总体统计
            logger.info(f"\n{'='*80}")
            logger.info(f"采集器统计信息:")
            logger.info(f"  总采集次数: {cycle_count}")
            logger.info(f"  总成功次数: {total_success}")
            logger.info(f"  总失败次数: {total_fail}")
            logger.info(f"  成功率: {total_success/(total_success+total_fail)*100:.2f}%")
            logger.info(f"{'='*80}\n")
            
            # 等待下一次采集（5分钟）
            next_time = datetime.now(BEIJING_TZ) + timedelta(seconds=COLLECTION_INTERVAL)
            current_kline_time = next_time - timedelta(minutes=5)
            logger.info(f"下次采集时间: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  → 将采集 {current_kline_time.strftime('%H:%M')} 的K线数据")
            logger.info(f"等待 {COLLECTION_INTERVAL} 秒...\n")
            
            time.sleep(COLLECTION_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n收到中断信号，采集器停止")
        logger.info(f"总采集次数: {cycle_count}")
        logger.info(f"总成功: {total_success}, 总失败: {total_fail}")
    
    except Exception as e:
        logger.error(f"采集器异常退出: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == '__main__':
    main()
