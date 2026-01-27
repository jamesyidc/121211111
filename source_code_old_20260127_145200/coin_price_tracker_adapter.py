#!/usr/bin/env python3
"""
Coin Price Tracker 数据适配器
将 coin_prices_30min.jsonl 的数据格式转换为 OKX Day Change API 所需的格式
用于在 escape-signal-history 页面中显示27币涨跌幅数据
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class CoinPriceTrackerAdapter:
    """Coin Price Tracker 数据适配器"""
    
    def __init__(self):
        self.data_file = Path('/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl')
        self.timezone = pytz.timezone('Asia/Shanghai')
        self.coins = [
            'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
            'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT', 'AAVE', 'UNI',
            'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
        ]
    
    def get_latest_records(self, limit=1440):
        """
        获取最新的记录
        将 coin_prices_30min.jsonl 格式转换为 okx_day_change API 格式
        
        coin_prices格式:
        {
            "timestamp": 1767455200,
            "collect_time": "2026-01-04 00:00:00",
            "base_date": "2026-01-04",
            "coins": {
                "BTC": {"base_price": 90012.70, "current_price": 91065.00, "change_pct": 1.17},
                ...
            }
        }
        
        转换为okx_day_change格式:
        {
            "record_time": "2026-01-04 00:00:00",
            "timestamp": 1767455200,
            "total_change": 42.60,  # 27个币的涨跌幅总和
            "average_change": 1.58,  # 平均涨跌幅
            "day_changes": {...},  # 每个币的涨跌幅
            "success_count": 27,
            "failed_count": 0,
            "total_symbols": 27
        }
        """
        try:
            if not self.data_file.exists():
                logger.warning(f"数据文件不存在: {self.data_file}")
                return []
            
            records = []
            with open(self.data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        
                        # 计算27币涨跌幅总和
                        total_change = 0.0
                        day_changes = {}
                        success_count = 0
                        failed_count = 0
                        
                        # 支持两种字段名: 'coins' 和 'day_changes'
                        source_field = 'day_changes' if 'day_changes' in record else 'coins'
                        
                        for coin in self.coins:
                            if coin in record.get(source_field, {}):
                                coin_data = record[source_field][coin]
                                change_pct = coin_data.get('change_pct', 0.0)
                                total_change += change_pct
                                day_changes[coin] = change_pct
                                
                                if coin_data.get('current_price', 0) > 0:
                                    success_count += 1
                                else:
                                    failed_count += 1
                            else:
                                day_changes[coin] = 0.0
                                failed_count += 1
                        
                        # 计算平均涨跌幅
                        average_change = total_change / 27 if success_count > 0 else 0.0
                        
                        # 转换为OKX格式
                        converted_record = {
                            'record_time': record['collect_time'],
                            'timestamp': record['timestamp'],
                            'total_change': round(total_change, 4),
                            'average_change': round(average_change, 4),
                            'day_changes': day_changes,
                            'success_count': success_count,
                            'failed_count': failed_count,
                            'total_symbols': 27
                        }
                        
                        records.append(converted_record)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON解析失败: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"记录转换失败: {e}")
                        continue
            
            # 返回最后limit条记录
            result = records[-limit:] if len(records) > limit else records
            logger.info(f"✅ 加载了 {len(result)} 条记录 (总共 {len(records)} 条)")
            return result
            
        except Exception as e:
            logger.error(f"❌ 读取数据失败: {e}", exc_info=True)
            return []
    
    def get_records_by_time_range(self, start_time, end_time):
        """
        根据时间范围获取记录
        :param start_time: 开始时间(Unix timestamp 秒)
        :param end_time: 结束时间(Unix timestamp 秒)
        """
        try:
            if not self.data_file.exists():
                return []
            
            records = []
            with open(self.data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        
                        # 检查时间范围
                        if start_time <= record['timestamp'] <= end_time:
                            # 支持两种字段名: 'coins' 和 'day_changes'
                            source_field = 'day_changes' if 'day_changes' in record else 'coins'
                            
                            # 计算27币涨跌幅总和
                            total_change = sum(
                                record[source_field][coin].get('change_pct', 0.0) 
                                for coin in self.coins 
                                if coin in record.get(source_field, {})
                            )
                            
                            # 统计成功/失败
                            success_count = sum(
                                1 for coin in self.coins 
                                if coin in record.get(source_field, {}) and record[source_field][coin].get('current_price', 0) > 0
                            )
                            failed_count = 27 - success_count
                            
                            # 转换格式
                            day_changes = {
                                coin: record.get(source_field, {}).get(coin, {}).get('change_pct', 0.0)
                                for coin in self.coins
                            }
                            
                            average_change = total_change / 27 if success_count > 0 else 0.0
                            
                            converted_record = {
                                'record_time': record['collect_time'],
                                'timestamp': record['timestamp'],
                                'total_change': round(total_change, 4),
                                'average_change': round(average_change, 4),
                                'day_changes': day_changes,
                                'success_count': success_count,
                                'failed_count': failed_count,
                                'total_symbols': 27
                            }
                            
                            records.append(converted_record)
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        continue
            
            logger.info(f"✅ 时间范围查询: {len(records)} 条记录")
            return records
            
        except Exception as e:
            logger.error(f"❌ 时间范围查询失败: {e}", exc_info=True)
            return []

# 便捷函数
def get_coin_tracker_data(limit=1440):
    """获取coin price tracker数据的便捷函数"""
    adapter = CoinPriceTrackerAdapter()
    return adapter.get_latest_records(limit=limit)

def get_coin_tracker_data_by_time(start_time, end_time):
    """根据时间范围获取数据的便捷函数"""
    adapter = CoinPriceTrackerAdapter()
    return adapter.get_records_by_time_range(start_time, end_time)
