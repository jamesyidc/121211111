#!/usr/bin/env python3
"""
支撑压力线全局趋势采集器
功能：每15分钟采集一次关键统计数据，用于生成全局趋势图（一个月）
数据点：每天 96 个点 (24h * 4次/h)
一个月：约 2,880 个数据点
"""

import os
import sys
import time
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, List

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))
from support_resistance_daily_manager import SupportResistanceDailyManager

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 全局趋势数据存储路径
TREND_DATA_DIR = '/home/user/webapp/data/support_resistance_trend'
os.makedirs(TREND_DATA_DIR, exist_ok=True)

# 日志文件
LOG_FILE = os.path.join(os.path.dirname(__file__), 'support_resistance_trend.log')

def log(message: str):
    """记录日志"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except Exception as e:
        print(f"写入日志失败: {e}")

def get_trend_file_path(date_str: str = None) -> str:
    """获取趋势数据文件路径（按月存储）"""
    if date_str is None:
        beijing_now = datetime.now(BEIJING_TZ)
    else:
        beijing_now = datetime.strptime(date_str, '%Y%m%d')
    
    # 按月存储：support_resistance_trend_YYYYMM.jsonl
    month_str = beijing_now.strftime('%Y%m')
    return os.path.join(TREND_DATA_DIR, f'support_resistance_trend_{month_str}.jsonl')

def collect_trend_point():
    """采集一个趋势数据点"""
    try:
        beijing_now = datetime.now(BEIJING_TZ)
        
        log("=" * 60)
        log(f"📊 开始采集全局趋势数据点")
        
        # 获取最新数据
        manager = SupportResistanceDailyManager()
        latest_levels = manager.get_latest_levels(limit=27)
        
        if not latest_levels:
            log("⚠️ 未获取到数据，跳过本次采集")
            return
        
        # 统计关键指标
        total_coins = 0
        scenario_1_count = 0  # 7日低位（<= 10%）
        scenario_2_count = 0  # 7日高位（>= 90%）
        scenario_3_count = 0  # 48h低位（<= 10%）
        scenario_4_count = 0  # 48h高位（>= 90%）
        
        # 平均位置
        total_position_7d = 0
        total_position_48h = 0
        
        # 接近支撑/压力的币种数量
        near_support_count = 0  # 距离支撑线 <= 5%
        near_resistance_count = 0  # 距离压力线 <= 5%
        
        for level in latest_levels:
            data = level.get('data', level)
            
            if not data.get('symbol'):
                continue
            
            total_coins += 1
            
            position_7d = data.get('position_7d', 0)
            position_48h = data.get('position_48h', 0)
            
            total_position_7d += position_7d
            total_position_48h += position_48h
            
            # 场景统计
            if position_7d <= 10:
                scenario_1_count += 1
            if position_7d >= 90:
                scenario_2_count += 1
            if position_48h <= 10:
                scenario_3_count += 1
            if position_48h >= 90:
                scenario_4_count += 1
            
            # 支撑/压力接近度统计
            dist_support_1 = data.get('distance_to_support_1', 100)
            dist_resistance_1 = data.get('distance_to_resistance_1', 100)
            
            if dist_support_1 <= 5:
                near_support_count += 1
            if dist_resistance_1 <= 5:
                near_resistance_count += 1
        
        # 计算平均值
        avg_position_7d = round(total_position_7d / total_coins, 2) if total_coins > 0 else 0
        avg_position_48h = round(total_position_48h / total_coins, 2) if total_coins > 0 else 0
        
        # 构建趋势数据点
        trend_point = {
            'timestamp': beijing_now.isoformat(),
            'datetime': beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
            'date': beijing_now.strftime('%Y-%m-%d'),
            'time': beijing_now.strftime('%H:%M'),
            'total_coins': total_coins,
            
            # 场景统计
            'scenario_1_count': scenario_1_count,  # 7日低位
            'scenario_2_count': scenario_2_count,  # 7日高位
            'scenario_3_count': scenario_3_count,  # 48h低位
            'scenario_4_count': scenario_4_count,  # 48h高位
            
            # 平均位置
            'avg_position_7d': avg_position_7d,
            'avg_position_48h': avg_position_48h,
            
            # 接近度统计
            'near_support_count': near_support_count,
            'near_resistance_count': near_resistance_count,
            
            # 逃顶/抄底信号
            'escape_signal': scenario_3_count + scenario_4_count,  # 48h高位+低位
            'buy_signal': scenario_1_count + scenario_3_count,     # 低位币种总数
            'sell_signal': scenario_2_count + scenario_4_count     # 高位币种总数
        }
        
        # 写入JSONL文件
        trend_file = get_trend_file_path()
        with open(trend_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trend_point, ensure_ascii=False) + '\n')
        
        log(f"✅ 趋势数据点采集成功")
        log(f"   总币种: {total_coins}")
        log(f"   7日低位: {scenario_1_count}, 7日高位: {scenario_2_count}")
        log(f"   48h低位: {scenario_3_count}, 48h高位: {scenario_4_count}")
        log(f"   平均7日位置: {avg_position_7d}%, 平均48h位置: {avg_position_48h}%")
        log(f"   接近支撑: {near_support_count}, 接近压力: {near_resistance_count}")
        log(f"   逃顶信号: {scenario_3_count + scenario_4_count}")
        log(f"   数据文件: {trend_file}")
        log("=" * 60)
        
        return True
        
    except Exception as e:
        log(f"❌ 采集趋势数据点失败: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def main():
    """主函数"""
    log("🎯 支撑压力线全局趋势采集器启动")
    log(f"⏰ 采集间隔: 15分钟")
    log(f"📁 数据存储: {TREND_DATA_DIR}")
    log(f"📊 数据密度: 每天96个点，一个月约2,880个点")
    
    while True:
        try:
            beijing_now = datetime.now(BEIJING_TZ)
            current_minute = beijing_now.minute
            current_second = beijing_now.second
            
            # 每15分钟采集一次：0, 15, 30, 45
            if current_minute % 15 == 0 and current_second < 30:
                log(f"⏰ 到达采集时间点: {beijing_now.strftime('%H:%M')}")
                collect_trend_point()
                # 等待60秒，避免重复采集
                time.sleep(60)
            else:
                # 计算到下一个15分钟的等待时间
                next_minute = ((current_minute // 15) + 1) * 15
                if next_minute >= 60:
                    next_minute = 0
                    wait_minutes = 60 - current_minute
                else:
                    wait_minutes = next_minute - current_minute
                
                wait_seconds = wait_minutes * 60 - current_second
                next_time = beijing_now + timedelta(seconds=wait_seconds)
                
                log(f"⏳ 下次采集时间: {next_time.strftime('%Y-%m-%d %H:%M')}, 等待 {wait_minutes} 分钟...")
                time.sleep(min(60, wait_seconds))
            
        except KeyboardInterrupt:
            log("⚠️ 收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 采集出错: {e}")
            log("⏳ 等待60秒后重试...")
            time.sleep(60)

if __name__ == '__main__':
    main()
