#!/usr/bin/env python3
"""
OKX交易数据JSONL管理器
管理OKX 27币种涨跌数据的存储
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class OKXTradingJSONLManager:
    """OKX交易数据JSONL管理器"""
    
    def __init__(self):
        self.data_dir = Path('/home/user/webapp/data/okx_trading_jsonl')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_file = self.data_dir / 'okx_day_change.jsonl'
        self.timezone = pytz.timezone('Asia/Shanghai')
    
    def save_day_change(self, total_change, average_change, day_changes, 
                       success_count, failed_count, record_time=None):
        """
        保存当日涨跌数据
        :param record_time: 记录时间(datetime对象),如果为None则使用当前时间
        """
        try:
            if record_time is None:
                now = datetime.now(self.timezone)
            else:
                now = record_time
            
            record = {
                'record_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp': int(now.timestamp()),
                'total_change': round(total_change, 4),
                'average_change': round(average_change, 4),
                'day_changes': day_changes,
                'success_count': success_count,
                'failed_count': failed_count,
                'total_symbols': 27
            }
            
            # 写入JSONL文件
            with open(self.jsonl_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}", exc_info=True)
            return False
    
    def get_latest_records(self, limit=1440):
        """
        获取最新的记录(默认24小时,每分钟一条,共1440条)
        """
        try:
            if not self.jsonl_file.exists():
                return []
            
            records = []
            with open(self.jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            # 返回最后limit条记录
            return records[-limit:] if len(records) > limit else records
            
        except Exception as e:
            logger.error(f"❌ 读取数据失败: {e}", exc_info=True)
            return []
    
    def get_records_by_timerange(self, start_time, end_time):
        """
        获取指定时间范围的记录
        :param start_time: 开始时间戳(秒)
        :param end_time: 结束时间戳(秒)
        """
        try:
            if not self.jsonl_file.exists():
                return []
            
            records = []
            with open(self.jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        timestamp = record.get('timestamp', 0)
                        if start_time <= timestamp <= end_time:
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            return records
            
        except Exception as e:
            logger.error(f"❌ 读取数据失败: {e}", exc_info=True)
            return []
