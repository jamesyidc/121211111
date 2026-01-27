#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚定系统空单盈利监控
每分钟采集空单持仓盈利数据，统计四个指标：
1. 空单盈利 <= 40%
2. 空单盈利为亏损 (< 0%)
3. 空单盈利 >= 80%
4. 空单盈利 >= 120%
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path

# 数据存储路径
DATA_DIR = Path('/home/user/webapp/data/anchor_profit_stats')
DATA_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE = DATA_DIR / 'anchor_profit_stats.jsonl'

# 逃顶信号数据路径
ESCAPE_SIGNAL_FILE = Path('/home/user/webapp/data/escape_signal_jsonl/escape_signal_stats.jsonl')

# API基础URL
API_BASE_URL = 'http://localhost:5000'


def get_positions_by_side():
    """获取多头和空单持仓（通过API）"""
    try:
        # 调用锚定系统API获取当前持仓
        url = f'{API_BASE_URL}/api/anchor-system/current-positions?trade_mode=real'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ API请求失败: {response.status_code}")
            return [], []
        
        result = response.json()
        
        if not result.get('success', False):
            print(f"❌ API返回失败: {result.get('error', '未知错误')}")
            return [], []
        
        all_positions = result.get('positions', [])
        print(f"📊 获取到持仓总数: {len(all_positions)}")
        
        # 分别取多头和空单
        long_positions = []
        short_positions = []
        
        for pos in all_positions:
            pos_side = pos.get('pos_side', '').lower()
            profit_rate = float(pos.get('profit_rate', 0))
            
            position_data = {
                'inst_id': pos.get('symbol', pos.get('inst_id', '')),
                'pos_side': pos_side,
                'pos_size': abs(float(pos.get('position', 0))),
                'profit_rate': profit_rate,
                'avg_price': float(pos.get('avg_price', 0)),
                'mark_price': float(pos.get('mark_price', 0)),
                'unrealized_pnl': float(pos.get('unrealized_pnl', 0))
            }
            
            if pos_side == 'long':
                long_positions.append(position_data)
            elif pos_side == 'short':
                short_positions.append(position_data)
        
        print(f"📊 多头总数: {len(long_positions)}")
        print(f"📊 空单总数: {len(short_positions)}")
        return long_positions, short_positions
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求异常: {e}")
        return [], []
    except Exception as e:
        print(f"❌ 获取持仓异常: {e}")
        import traceback
        traceback.print_exc()
        return [], []


def get_short_positions():
    """获取所有空单持仓（兼容旧接口）"""
    _, short_positions = get_positions_by_side()
    return short_positions


def calculate_stats(positions):
    """计算单个方向的统计数据"""
    if not positions:
        return {
            'lte_40': 0,
            'loss': 0,
            'gte_80': 0,
            'gte_120': 0,
            'total': 0
        }
    
    lte_40_count = 0    # <= 40%
    loss_count = 0       # < 0%
    gte_80_count = 0     # >= 80%
    gte_120_count = 0    # >= 120%
    
    for pos in positions:
        profit_rate = pos['profit_rate']
        
        if profit_rate <= 40:
            lte_40_count += 1
        
        if profit_rate < 0:
            loss_count += 1
        
        if profit_rate >= 80:
            gte_80_count += 1
        
        if profit_rate >= 120:
            gte_120_count += 1
    
    return {
        'lte_40': lte_40_count,      # 盈利 <= 40%
        'loss': loss_count,           # 亏损
        'gte_80': gte_80_count,       # 盈利 >= 80%
        'gte_120': gte_120_count,     # 盈利 >= 120%
        'total': len(positions)
    }


def calculate_stats_both(long_positions, short_positions):
    """计算多头和空单的统计数据"""
    return {
        'long': calculate_stats(long_positions),
        'short': calculate_stats(short_positions)
    }


def get_escape_signal_2h():
    """获取最近的2小时逃顶信号数量"""
    try:
        if not ESCAPE_SIGNAL_FILE.exists():
            print("⚠️ 逃顶信号数据文件不存在")
            return 0
        
        # 读取最后一行（最新数据）
        with open(ESCAPE_SIGNAL_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            return 0
        
        last_line = lines[-1].strip()
        if not last_line:
            return 0
        
        data = json.loads(last_line)
        signal_2h_count = data.get('signal_2h_count', 0)
        
        print(f"⚡ 2小时逃顶信号: {signal_2h_count}")
        return signal_2h_count
        
    except Exception as e:
        print(f"❌ 获取逃顶信号失败: {e}")
        return 0


def save_to_jsonl(timestamp, stats, long_positions, short_positions, escape_signal_2h=0):
    """保存到JSONL文件"""
    data = {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'stats': stats,
        'escape_signal_2h': escape_signal_2h,
        'long_positions': long_positions,
        'short_positions': short_positions,
        'long_count': len(long_positions),
        'short_count': len(short_positions)
    }
    
    with open(JSONL_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')


def collect_once():
    """采集一次数据"""
    timestamp = int(time.time())
    
    print(f"\n{'='*60}")
    print(f"⏰ {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 获取多头和空单持仓
    long_positions, short_positions = get_positions_by_side()
    
    # 计算统计数据
    stats = calculate_stats_both(long_positions, short_positions)
    
    # 获取2小时逃顶信号
    escape_signal_2h = get_escape_signal_2h()
    
    print(f"🟢 多头统计:")
    print(f"  盈利 <= 40%: {stats['long']['lte_40']}")
    print(f"  亏损 (< 0%): {stats['long']['loss']}")
    print(f"  盈利 >= 80%: {stats['long']['gte_80']}")
    print(f"  盈利 >= 120%: {stats['long']['gte_120']}")
    
    print(f"🔴 空单统计:")
    print(f"  盈利 <= 40%: {stats['short']['lte_40']}")
    print(f"  亏损 (< 0%): {stats['short']['loss']}")
    print(f"  盈利 >= 80%: {stats['short']['gte_80']}")
    print(f"  盈利 >= 120%: {stats['short']['gte_120']}")
    
    # 保存到JSONL
    save_to_jsonl(timestamp, stats, long_positions, short_positions, escape_signal_2h)
    print(f"✅ 数据已保存到: {JSONL_FILE}")
    
    return {
        'timestamp': timestamp,
        'datetime': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'stats': stats,
        'escape_signal_2h': escape_signal_2h,
        'long_count': len(long_positions),
        'short_count': len(short_positions)
    }


def get_recent_data(limit=60):
    """获取最近N条数据"""
    if not JSONL_FILE.exists():
        return []
    
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if not lines:
        return []
    
    # 取最后limit条
    recent_lines = lines[-limit:] if len(lines) > limit else lines
    
    data_list = []
    for line in recent_lines:
        line = line.strip()
        if line:
            data_list.append(json.loads(line))
    
    return data_list


def collect_and_save():
    """采集并保存数据（供API调用）"""
    return collect_once()


def main():
    """主循环"""
    print("🚀 启动锚定系统空单盈利监控...")
    print(f"📁 数据文件: {JSONL_FILE}")
    print(f"⏱️  采集间隔: 1分钟")
    
    while True:
        try:
            collect_once()
            
            # 等待60秒
            print(f"⏳ 等待60秒后下次采集...")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n👋 收到停止信号，退出...")
            break
        except Exception as e:
            print(f"❌ 采集异常: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == '__main__':
    main()
