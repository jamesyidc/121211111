#!/usr/bin/env python3
"""
获取所有采集器的运行状态
"""
import subprocess
import sqlite3
from datetime import datetime, timedelta
import pytz
import json

def check_process_running(process_name):
    """检查进程是否运行"""
    try:
        result = subprocess.run(
            f"ps aux | grep '[p]ython.*{process_name}'",
            shell=True,
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
    except:
        return False

def get_latest_data_time(table_name, time_column='created_at', db_name='crypto_data.db'):
    """获取表中最新数据的时间"""
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute(f"SELECT {time_column} FROM {table_name} ORDER BY {time_column} DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        return None

def calculate_delay_minutes(last_time_str):
    """计算延迟分钟数"""
    if not last_time_str:
        return None
    try:
        utc_tz = pytz.utc
        beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 尝试解析时间
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']:
            try:
                # 去掉毫秒部分
                time_str = last_time_str.split('.')[0]
                last_time = datetime.strptime(time_str, fmt)
                
                # 当前UTC时间
                now_utc = datetime.now(utc_tz)
                
                # 先假设是UTC时间
                last_time_utc = utc_tz.localize(last_time)
                delay = (now_utc - last_time_utc).total_seconds() / 60
                
                # 如果延迟是负数（未来时间），说明存储的是北京时间
                if delay < -60:  # 负数超过1小时，说明时区理解错了
                    last_time_beijing = beijing_tz.localize(last_time)
                    last_time_utc = last_time_beijing.astimezone(utc_tz)
                    delay = (now_utc - last_time_utc).total_seconds() / 60
                
                return round(delay, 2)
            except:
                continue
        return None
    except:
        return None

def get_all_collectors_status():
    """获取所有采集器状态"""
    
    collectors = [
        {
            'name': 'Google Drive 检测器',
            'process': 'gdrive_final_detector.py',
            'table': 'crypto_snapshots',
            'time_column': 'created_at',
            'description': 'Google Drive TXT文件监控',
            'interval': '30秒'
        },
        {
            'name': '恐慌清洗指数采集',
            'process': 'panic_wash_collector.py',
            'table': 'panic_wash_index',
            'time_column': 'created_at',
            'description': '恐慌清洗指数数据采集',
            'interval': '5分钟'
        },
        {
            'name': '交易信号采集',
            'process': 'signal_collector.py',
            'table': 'trading_signals',
            'time_column': 'created_at',
            'description': '做多做空交易信号采集',
            'interval': '5分钟'
        },
        {
            'name': '持仓系统采集',
            'process': 'position_system_collector.py',
            'table': 'position_system',
            'time_column': 'created_at',
            'description': '持仓数据采集',
            'interval': '5分钟'
        },
        {
            'name': '价格速度采集',
            'process': 'price_speed_collector.py',
            'table': 'latest_price_speed',
            'time_column': 'timestamp',
            'description': '价格变化速度监控',
            'interval': '30秒',
            'db_name': 'price_speed_data.db'
        },
        {
            'name': 'V1V2 采集',
            'process': 'v1v2_collector.py',
            'table': 'volume_btc',  # 使用BTC表作为代表检查
            'time_column': 'created_at',
            'description': 'V1V2信号数据采集',
            'interval': '1分钟',
            'db_name': 'v1v2_data.db'
        },
        {
            'name': '价格对比采集',
            'process': 'price_comparison_collector.py',
            'table': 'price_comparison',
            'time_column': 'last_update_time',
            'description': '多平台价格对比',
            'interval': '5分钟'
        },
        {
            'name': '加密指数采集',
            'process': 'crypto_index_collector.py',
            'table': 'crypto_index_klines',
            'time_column': 'timestamp',
            'description': '加密货币指数数据',
            'interval': '5分钟'
        },
        {
            'name': '爆仓金额采集',
            'process': 'liquidation_amount_collector.py',
            'table': 'liquidation_30days',
            'time_column': 'updated_at',
            'description': '爆仓金额数据采集',
            'interval': '5分钟'
        }
    ]
    
    results = []
    for collector in collectors:
        is_running = check_process_running(collector['process'])
        db_name = collector.get('db_name', 'crypto_data.db')
        last_time = get_latest_data_time(collector['table'], collector['time_column'], db_name)
        delay = calculate_delay_minutes(last_time) if last_time else None
        
        # 判断状态
        if not is_running:
            status = 'stopped'
            status_text = '已停止'
        elif delay is None:
            status = 'no_data'
            status_text = '无数据'
        elif delay > 30:
            status = 'error'
            status_text = '异常'
        elif delay > 10:
            status = 'warning'
            status_text = '延迟'
        else:
            status = 'normal'
            status_text = '正常'
        
        results.append({
            'name': collector['name'],
            'script': collector['process'],  # 添加script字段用于前端识别
            'process': collector['process'],
            'description': collector['description'],
            'interval': collector['interval'],
            'process_running': is_running,
            'log_exists': True,  # 假设日志存在
            'last_update': last_time,
            'delay_minutes': delay if delay is not None else 999.99,
            'db_table': collector['table'],
            'status': status,
            'status_text': status_text,
            'message': f"{collector['description']} - 采集频率: {collector['interval']}"
        })
    
    return results

if __name__ == '__main__':
    status = get_all_collectors_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
