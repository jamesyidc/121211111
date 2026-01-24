#!/usr/bin/env python3
"""
支撑压力线快照采集器
每1分钟保存一次4种情况的统计数据和符合条件的币种列表
数据源：从JSONL文件读取最新数据
"""

import os
import sys
import time
import sqlite3
import json
import pytz
from datetime import datetime
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')
from support_resistance_jsonl_manager import SupportResistanceJSONLManager

# 数据库配置（用于写入快照）
DB_PATH = '/home/user/webapp/databases/support_resistance.db'

# JSONL配置
JSONL_DIR = '/home/user/webapp/data/support_resistance_jsonl'
SNAPSHOT_FILE = os.path.join(JSONL_DIR, 'support_resistance_snapshots.jsonl')

# 日志文件
LOG_FILE = os.path.join(os.path.dirname(__file__), 'support_resistance_snapshot.log')

def log(message: str):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")

def create_snapshot_table():
    """创建快照表（如果不存在）"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建快照表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_resistance_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_time TEXT NOT NULL,
                snapshot_date TEXT NOT NULL,
                scenario_1_count INTEGER DEFAULT 0,
                scenario_2_count INTEGER DEFAULT 0,
                scenario_3_count INTEGER DEFAULT 0,
                scenario_4_count INTEGER DEFAULT 0,
                scenario_1_coins TEXT,
                scenario_2_coins TEXT,
                scenario_3_coins TEXT,
                scenario_4_coins TEXT,
                total_coins INTEGER DEFAULT 27,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshot_time 
            ON support_resistance_snapshots(snapshot_time)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_snapshot_date 
            ON support_resistance_snapshots(snapshot_date)
        ''')
        
        conn.commit()
        conn.close()
        log("✅ 快照表检查/创建完成")
        return True
        
    except Exception as e:
        log(f"❌ 创建快照表失败: {e}")
        return False

def get_latest_data() -> List[Dict]:
    """从JSONL获取最新的支撑压力线数据"""
    try:
        manager = SupportResistanceJSONLManager()
        
        # 获取所有币种的最新数据
        all_latest = manager.get_all_latest_levels()
        
        if not all_latest:
            log("⚠️ 从JSONL未获取到数据")
            return []
        
        results = []
        for record in all_latest:
            # 计算alert场景
            position_7d = record.get('position_7d', 0) or 0
            position_48h = record.get('position_48h', 0) or 0
            
            results.append({
                'symbol': record.get('symbol'),
                'current_price': record.get('current_price'),
                'support_line_1': record.get('support_line_1'),
                'support_line_2': record.get('support_line_2'),
                'resistance_line_1': record.get('resistance_line_1'),
                'resistance_line_2': record.get('resistance_line_2'),
                'position_s2_r1': position_7d,  # 7天位置
                'position_s1_r2': position_48h,  # 48小时位置
                'position_s1_r2_upper': position_48h,
                'position_s1_r1': position_7d,
                'alert_scenario_1': position_7d <= 5,  # 7天低位警报
                'alert_scenario_2': position_7d >= 95,  # 7天高位警报
                'alert_scenario_3': position_48h >= 95,  # 48h高位警报
                'alert_scenario_4': position_7d >= 95,  # 7天高位警报（与scenario_2相同逻辑）
                'record_time': record.get('record_time_beijing') or record.get('record_time')
            })
        
        log(f"✅ 从JSONL获取到 {len(results)} 个币种的最新数据")
        return results
        
    except Exception as e:
        log(f"❌ 获取最新数据失败: {e}")
        import traceback
        log(f"详细错误: {traceback.format_exc()}")
        return []

def analyze_scenarios(data_list: List[Dict]) -> Dict:
    """分析4种情况的统计数据"""
    scenario_1_coins = []
    scenario_2_coins = []
    scenario_3_coins = []
    scenario_4_coins = []
    
    for data in data_list:
        symbol = data['symbol']
        
        # 情况1: 支撑2→压力1 (<=5%)
        if data['alert_scenario_1']:
            scenario_1_coins.append({
                'symbol': symbol,
                'current_price': data['current_price'],
                'position': data['position_s2_r1'],
                'support_2': data['support_line_2'],
                'resistance_1': data['resistance_line_1']
            })
        
        # 情况2: 支撑1→压力2 (<=5%)
        if data['alert_scenario_2']:
            scenario_2_coins.append({
                'symbol': symbol,
                'current_price': data['current_price'],
                'position': data['position_s1_r2'],
                'support_1': data['support_line_1'],
                'resistance_2': data['resistance_line_2']
            })
        
        # 情况3: 支撑1→压力2 (>=95%)
        if data['alert_scenario_3']:
            scenario_3_coins.append({
                'symbol': symbol,
                'current_price': data['current_price'],
                'position': data['position_s1_r2_upper'],
                'support_1': data['support_line_1'],
                'resistance_2': data['resistance_line_2']
            })
        
        # 情况4: 支撑1→压力1 (>=95%)
        if data['alert_scenario_4']:
            scenario_4_coins.append({
                'symbol': symbol,
                'current_price': data['current_price'],
                'position': data['position_s1_r1'],
                'support_1': data['support_line_1'],
                'resistance_1': data['resistance_line_1']
            })
    
    return {
        'scenario_1': {
            'count': len(scenario_1_coins),
            'coins': scenario_1_coins
        },
        'scenario_2': {
            'count': len(scenario_2_coins),
            'coins': scenario_2_coins
        },
        'scenario_3': {
            'count': len(scenario_3_coins),
            'coins': scenario_3_coins
        },
        'scenario_4': {
            'count': len(scenario_4_coins),
            'coins': scenario_4_coins
        },
        'total_coins': len(data_list)
    }

def save_snapshot(analysis: Dict) -> bool:
    """保存快照到数据库和JSONL文件"""
    try:
        # 使用北京时间存储（UTC+8）
        now_beijing = datetime.now(pytz.timezone('Asia/Shanghai'))
        snapshot_time = now_beijing.strftime('%Y-%m-%d %H:%M:%S')
        snapshot_date = now_beijing.strftime('%Y-%m-%d')
        
        # 1. 保存到SQLite（用于兼容性）
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO support_resistance_snapshots (
                    snapshot_time, snapshot_date,
                    scenario_1_count, scenario_2_count, scenario_3_count, scenario_4_count,
                    scenario_1_coins, scenario_2_coins, scenario_3_coins, scenario_4_coins,
                    total_coins
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time, snapshot_date,
                analysis['scenario_1']['count'],
                analysis['scenario_2']['count'],
                analysis['scenario_3']['count'],
                analysis['scenario_4']['count'],
                json.dumps(analysis['scenario_1']['coins'], ensure_ascii=False),
                json.dumps(analysis['scenario_2']['coins'], ensure_ascii=False),
                json.dumps(analysis['scenario_3']['coins'], ensure_ascii=False),
                json.dumps(analysis['scenario_4']['coins'], ensure_ascii=False),
                analysis['total_coins']
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            log(f"⚠️ SQLite写入失败: {e}")
        
        # 2. 保存到JSONL文件（主要数据源）
        os.makedirs(JSONL_DIR, exist_ok=True)
        
        jsonl_record = {
            'snapshot_time': snapshot_time,
            'snapshot_date': snapshot_date,
            'scenario_1_count': analysis['scenario_1']['count'],
            'scenario_2_count': analysis['scenario_2']['count'],
            'scenario_3_count': analysis['scenario_3']['count'],
            'scenario_4_count': analysis['scenario_4']['count'],
            'scenario_1_coins': json.dumps(analysis['scenario_1']['coins'], ensure_ascii=False),
            'scenario_2_coins': json.dumps(analysis['scenario_2']['coins'], ensure_ascii=False),
            'scenario_3_coins': json.dumps(analysis['scenario_3']['coins'], ensure_ascii=False),
            'scenario_4_coins': json.dumps(analysis['scenario_4']['coins'], ensure_ascii=False),
            'total_coins': analysis['total_coins'],
            'created_at': snapshot_time,
            'snapshot_time_beijing': snapshot_time,
            'created_at_beijing': snapshot_time
        }
        
        with open(SNAPSHOT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(jsonl_record, ensure_ascii=False) + '\n')
        
        log(f"✅ 快照保存成功 (SQLite+JSONL): {snapshot_time} | "
            f"情况1:{analysis['scenario_1']['count']} "
            f"情况2:{analysis['scenario_2']['count']} "
            f"情况3:{analysis['scenario_3']['count']} "
            f"情况4:{analysis['scenario_4']['count']}")
        
        return True
        
    except Exception as e:
        log(f"❌ 保存快照失败: {e}")
        import traceback
        log(f"详细错误: {traceback.format_exc()}")
        return False

def collect_snapshot():
    """采集一次快照"""
    log("=" * 60)
    log("📸 开始采集支撑压力线快照")
    
    # 1. 获取最新数据
    data_list = get_latest_data()
    
    if not data_list:
        log("⚠️ 没有获取到数据")
        return False
    
    log(f"📊 获取到 {len(data_list)} 个币种的最新数据")
    
    # 2. 分析4种情况
    analysis = analyze_scenarios(data_list)
    
    log(f"📈 情况1（接近支撑2）: {analysis['scenario_1']['count']} 个币种")
    log(f"📈 情况2（接近支撑1）: {analysis['scenario_2']['count']} 个币种")
    log(f"📉 情况3（接近压力2）: {analysis['scenario_3']['count']} 个币种")
    log(f"📉 情况4（接近压力1）: {analysis['scenario_4']['count']} 个币种")
    
    # 3. 保存快照
    success = save_snapshot(analysis)
    
    log("=" * 60)
    return success

def main():
    """主函数"""
    log("🎯 支撑压力线快照采集器启动 (JSONL模式)")
    log(f"⏰ 采集间隔: 60秒 (1分钟)")
    log(f"📁 数据源: JSONL (/home/user/webapp/data/support_resistance_jsonl/)")
    log(f"📁 兼容写入: {DB_PATH}")
    
    # 创建表
    if not create_snapshot_table():
        log("❌ 无法创建数据库表，退出")
        return
    
    while True:
        try:
            collect_snapshot()
            log("⏳ 等待60秒后进行下一次采集...")
            time.sleep(60)  # 1分钟
            
        except KeyboardInterrupt:
            log("⚠️ 收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 采集出错: {e}")
            log("⏳ 等待60秒后重试...")
            time.sleep(60)

if __name__ == '__main__':
    main()
