#!/usr/bin/env python3
"""
逃顶信号计算器
从SAR斜率数据计算2h和24h逃顶信号数量，并保存到JSONL文件
每分钟运行一次，在服务器端处理，不依赖浏览器缓存
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/escape_signal_calculator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 配置
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
SAR_JSONL_DIR = Path('/home/user/webapp/data/sar_slope_jsonl')
SAR_JSONL_FILE = SAR_JSONL_DIR / 'sar_slope_data.jsonl'
ESCAPE_SIGNAL_DIR = Path('/home/user/webapp/data/escape_signal_jsonl')
ESCAPE_SIGNAL_FILE = ESCAPE_SIGNAL_DIR / 'escape_signal_stats.jsonl'

# 确保目录存在
ESCAPE_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)

def is_topping_signal(record):
    """判断是否为见顶信号"""
    sar_position = record.get('sar_position', '')
    slope_direction = record.get('slope_direction', '')
    sar_quadrant = record.get('sar_quadrant', '')
    
    # 见顶信号：SAR多头，斜率向下，Q1或Q2象限
    return (sar_position == 'bullish' and 
            slope_direction == 'down' and 
            sar_quadrant in ['Q1', 'Q2'])

def load_sar_data_from_jsonl(hours=24):
    """从JSONL加载最近N小时的SAR数据"""
    if not SAR_JSONL_FILE.exists():
        logger.warning(f"⚠️ SAR数据文件不存在: {SAR_JSONL_FILE}")
        return []
    
    cutoff_time = datetime.now(BEIJING_TZ) - timedelta(hours=hours)
    cutoff_timestamp = int(cutoff_time.timestamp())
    
    records = []
    try:
        with open(SAR_JSONL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    timestamp = record.get('timestamp', 0)
                    if timestamp >= cutoff_timestamp:
                        records.append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"❌ 读取SAR数据失败: {e}")
        return []
    
    logger.info(f"📊 加载了 {len(records)} 条最近{hours}小时的SAR数据")
    return records

def calculate_escape_signals():
    """计算逃顶信号"""
    try:
        # 加载最近24小时的数据
        records_24h = load_sar_data_from_jsonl(hours=24)
        if not records_24h:
            logger.warning("⚠️ 没有SAR数据可供计算")
            return None
        
        # 获取当前时间的数据点（最新的）
        now = datetime.now(BEIJING_TZ)
        current_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 按时间分组统计
        time_groups = {}
        for record in records_24h:
            dt_str = record.get('datetime', '')
            if not dt_str:
                continue
            
            # 只保留到分钟
            try:
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
                time_key = dt.strftime('%Y-%m-%d %H:%M')
            except:
                continue
            
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(record)
        
        # 计算每个时间点的见顶信号数量
        time_signal_counts = {}
        for time_key, group_records in time_groups.items():
            # 对每个时间点，统计有多少个币种符合见顶条件
            topping_symbols = set()
            for record in group_records:
                if is_topping_signal(record):
                    symbol = record.get('symbol', '')
                    if symbol:
                        topping_symbols.add(symbol)
            time_signal_counts[time_key] = len(topping_symbols)
        
        # 计算2h信号数量（当前时间点）
        current_time_key = now.strftime('%Y-%m-%d %H:%M')
        signal_2h_count = time_signal_counts.get(current_time_key, 0)
        
        # 计算24h信号总数（所有时间点的最大值）
        signal_24h_count = max(time_signal_counts.values()) if time_signal_counts else 0
        
        # 计算历史最大值
        max_signal_24h = signal_24h_count
        max_signal_2h = signal_2h_count
        
        # 计算涨跌强度等级（简化版，需要从coin_prices获取）
        decline_strength_level = 0
        rise_strength_level = 0
        
        result = {
            'stat_time': current_time_str,
            'signal_24h_count': signal_24h_count,
            'signal_2h_count': signal_2h_count,
            'decline_strength_level': decline_strength_level,
            'rise_strength_level': rise_strength_level,
            'max_signal_24h': max_signal_24h,
            'max_signal_2h': max_signal_2h,
            'created_at': now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        logger.info(f"✅ 计算完成: 2h信号={signal_2h_count}, 24h信号={signal_24h_count}")
        return result
        
    except Exception as e:
        logger.error(f"❌ 计算逃顶信号失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def save_to_jsonl(data):
    """保存到JSONL文件"""
    try:
        with open(ESCAPE_SIGNAL_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
        logger.info(f"✅ 数据已保存到: {ESCAPE_SIGNAL_FILE}")
        return True
    except Exception as e:
        logger.error(f"❌ 保存数据失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🚀 逃顶信号计算器启动")
    logger.info("=" * 60)
    
    interval = 60  # 每60秒运行一次
    
    while True:
        try:
            logger.info(f"⏰ {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')} - 开始计算...")
            
            # 计算逃顶信号
            result = calculate_escape_signals()
            
            if result:
                # 保存到JSONL
                save_to_jsonl(result)
            else:
                logger.warning("⚠️ 计算结果为空，跳过保存")
            
            logger.info(f"😴 等待 {interval} 秒后进行下一次计算...")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号，退出...")
            break
        except Exception as e:
            logger.error(f"❌ 主循环异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(interval)

if __name__ == '__main__':
    main()
