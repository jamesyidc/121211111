#!/usr/bin/env python3
"""
支撑压力线快照采集器 v2.0 - 完全基于JSONL
每1分钟保存一次4种情况的统计数据和符合条件的币种列表
数据源：从JSONL文件读取最新数据
数据存储：JSONL按日期分片存储，不再使用数据库
"""

import os
import sys
import time
import json
import pytz
from datetime import datetime
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))
from support_resistance_daily_manager import SupportResistanceDailyManager

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

def get_latest_data() -> List[Dict]:
    """从按日期JSONL获取最新的支撑压力线数据"""
    try:
        manager = SupportResistanceDailyManager()
        
        # 尝试获取最近7天的数据
        latest_records = None
        used_date = None
        
        for days_ago in range(8):  # 尝试今天和过去7天
            if days_ago == 0:
                # 今天
                latest_records = manager.get_latest_levels(limit=27)
                if latest_records:
                    used_date = "today"
                    break
            else:
                # 过去N天
                from datetime import datetime, timedelta
                past_date = (datetime.now(pytz.timezone('Asia/Shanghai')) - timedelta(days=days_ago)).strftime('%Y%m%d')
                latest_records = manager.get_latest_levels(date_str=past_date, limit=27)
                if latest_records:
                    used_date = past_date
                    log(f"✅ 使用 {days_ago} 天前的数据 ({past_date})")
                    break
        
        if not latest_records:
            log("⚠️ 从按日期JSONL未获取到数据（尝试了最近8天）")
            return []
        
        results = []
        for record in latest_records:
            # 提取data字段
            data = record.get('data', {})
            
            # 计算alert场景
            position_7d = data.get('position_7d', 0) or 0
            position_48h = data.get('position_48h', 0) or 0
            
            results.append({
                'symbol': data.get('symbol'),
                'current_price': data.get('current_price'),
                'support_line_1': data.get('support_line_1'),
                'support_line_2': data.get('support_line_2'),
                'resistance_line_1': data.get('resistance_line_1'),
                'resistance_line_2': data.get('resistance_line_2'),
                'position_s2_r1': position_7d,  # 7天位置
                'position_s1_r2': position_48h,  # 48小时位置
                'position_s1_r2_upper': position_48h,
                'position_s1_r1': position_7d,
                'alert_scenario_1': position_7d <= 10,  # 情况1: 7天低位（接近支撑2）
                'alert_scenario_2': position_7d <= 10,  # 情况2: 7天低位（接近支撑1）
                'alert_scenario_3': position_48h <= 10,  # 情况3: 48h低位（接近压力2）
                'alert_scenario_4': position_48h >= 90,  # 情况4: 48h高位（接近压力1）
                'record_time': data.get('record_time_beijing') or data.get('record_time')
            })
        
        log(f"✅ 从按日期JSONL获取到 {len(results)} 个币种的最新数据")
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
    """保存快照到数据库和按日期JSONL文件"""
    try:
        # 使用北京时间存储（UTC+8）
        now_beijing = datetime.now(pytz.timezone('Asia/Shanghai'))
        snapshot_time = now_beijing.strftime('%Y-%m-%d %H:%M:%S')
        snapshot_date = now_beijing.strftime('%Y-%m-%d')
        
        # 保存快照到JSONL（按日期存储）
        manager = SupportResistanceDailyManager()
        
        snapshot_data = {
            'snapshot_time': snapshot_time,
            'snapshot_date': snapshot_date,
            'scenario_1_count': analysis['scenario_1']['count'],
            'scenario_2_count': analysis['scenario_2']['count'],
            'scenario_3_count': analysis['scenario_3']['count'],
            'scenario_4_count': analysis['scenario_4']['count'],
            'scenario_1_coins': analysis['scenario_1']['coins'],
            'scenario_2_coins': analysis['scenario_2']['coins'],
            'scenario_3_coins': analysis['scenario_3']['coins'],
            'scenario_4_coins': analysis['scenario_4']['coins'],
            'total_coins': analysis['total_coins'],
            'created_at': snapshot_time,
            'snapshot_time_beijing': snapshot_time,
            'created_at_beijing': snapshot_time
        }
        
        manager.write_snapshot_record(snapshot_data)
        
        log(f"✅ 快照保存成功 (Daily JSONL): {snapshot_time} | "
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
    log("🎯 支撑压力线快照采集器启动 (JSONL模式 v2.0)")
    log(f"⏰ 采集间隔: 60秒 (1分钟)")
    log(f"📁 数据源: JSONL 按日期存储 (/home/user/webapp/data/support_resistance_daily/)")
    log(f"✅ 数据存储: 仅JSONL，不再写入数据库")
    
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
