#!/usr/bin/env python3
"""
数据采集监控和自动恢复脚本
功能：
1. 检测是否按时采集数据（预期每10分钟一次）
2. 如果发现漏采，自动触发数据采集
3. 提供API接口查询监控状态
"""

import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
import pytz
import time
import json

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = 'crypto_data.db'
COLLECTION_INTERVAL = 10  # 预期采集间隔（分钟）
TOLERANCE = 2  # 容错时间（分钟）

def get_latest_snapshot_time():
    """获取最新的数据快照时间"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT snapshot_time, COUNT(*) as coin_count
            FROM crypto_coin_data 
            GROUP BY snapshot_time 
            ORDER BY snapshot_time DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            snapshot_time_str, coin_count = result
            snapshot_time = datetime.strptime(snapshot_time_str, '%Y-%m-%d %H:%M:%S')
            return snapshot_time, coin_count
        return None, 0
    except Exception as e:
        print(f"❌ 获取最新快照时间失败: {e}")
        return None, 0

def should_collect_now():
    """
    判断当前是否应该有数据采集
    返回: (是否需要采集, 状态信息)
    """
    now = datetime.now(BEIJING_TZ).replace(tzinfo=None)
    latest_snapshot, coin_count = get_latest_snapshot_time()
    
    if latest_snapshot is None:
        return True, {
            'need_collection': True,
            'reason': '数据库中没有任何数据',
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'latest_snapshot': None,
            'minutes_since_last': None,
            'expected_next': None
        }
    
    # 计算时间差（分钟）
    time_diff = (now - latest_snapshot).total_seconds() / 60
    
    # 计算预期的下一次采集时间
    expected_next = latest_snapshot + timedelta(minutes=COLLECTION_INTERVAL)
    
    # 判断是否需要采集：
    # 1. 如果距离上次采集超过了 (COLLECTION_INTERVAL + TOLERANCE) 分钟
    # 2. 或者已经超过了预期的采集时间
    if time_diff >= (COLLECTION_INTERVAL + TOLERANCE):
        return True, {
            'need_collection': True,
            'reason': f'距离上次采集已经 {time_diff:.1f} 分钟，超过了预期间隔 {COLLECTION_INTERVAL} 分钟',
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'latest_snapshot': latest_snapshot.strftime('%Y-%m-%d %H:%M:%S'),
            'coin_count': coin_count,
            'minutes_since_last': round(time_diff, 1),
            'expected_next': expected_next.strftime('%Y-%m-%d %H:%M:%S'),
            'overdue_minutes': round(time_diff - COLLECTION_INTERVAL, 1)
        }
    
    return False, {
        'need_collection': False,
        'reason': '数据采集正常',
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'latest_snapshot': latest_snapshot.strftime('%Y-%m-%d %H:%M:%S'),
        'coin_count': coin_count,
        'minutes_since_last': round(time_diff, 1),
        'expected_next': expected_next.strftime('%Y-%m-%d %H:%M:%S'),
        'next_check_in': round(COLLECTION_INTERVAL + TOLERANCE - time_diff, 1)
    }

def trigger_collection():
    """触发数据采集"""
    print("\n" + "="*80)
    print("🚀 触发数据采集...")
    print("="*80)
    
    try:
        # 执行采集脚本
        result = subprocess.run(
            ['python3', 'collect_and_store.py'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print("\n✅ 数据采集成功!")
            print(result.stdout)
            return {
                'success': True,
                'message': '数据采集成功',
                'output': result.stdout,
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            print(f"\n❌ 数据采集失败! (退出码: {result.returncode})")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return {
                'success': False,
                'message': f'数据采集失败 (退出码: {result.returncode})',
                'error': result.stderr,
                'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
    except subprocess.TimeoutExpired:
        print("\n⏱️  数据采集超时（超过5分钟）")
        return {
            'success': False,
            'message': '数据采集超时',
            'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"\n❌ 触发采集时发生错误: {e}")
        return {
            'success': False,
            'message': f'触发采集失败: {str(e)}',
            'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }

def check_and_recover(silent=False):
    """检查并自动恢复数据采集
    
    Args:
        silent: 是否静默模式（只输出JSON，不输出中间信息）
    """
    if not silent:
        print("\n" + "="*80)
        print("🔍 检查数据采集状态...")
        print("="*80)
    
    need_collection, status = should_collect_now()
    
    if not silent:
        print(f"\n当前时间: {status['current_time']}")
        print(f"最新快照: {status.get('latest_snapshot', 'N/A')}")
        if status.get('coin_count'):
            print(f"币种数量: {status['coin_count']}")
        if status.get('minutes_since_last'):
            print(f"距离上次采集: {status['minutes_since_last']} 分钟")
        print(f"预期下次采集: {status.get('expected_next', 'N/A')}")
        print(f"\n状态: {status['reason']}")
    
    if need_collection:
        if not silent:
            print(f"\n⚠️  检测到漏采数据!")
            if status.get('overdue_minutes'):
                print(f"   超期时间: {status['overdue_minutes']} 分钟")
        
        # 触发采集
        collection_result = trigger_collection()
        
        return {
            'status': status,
            'action_taken': True,
            'collection_result': collection_result
        }
    else:
        if not silent:
            print(f"\n✅ 数据采集正常")
            if status.get('next_check_in'):
                print(f"   下次检查时间: {status['next_check_in']} 分钟后")
        
        return {
            'status': status,
            'action_taken': False,
            'collection_result': None
        }

def get_collection_history(hours=2):
    """获取最近N小时的采集历史"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ).replace(tzinfo=None)
        start_time = now - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT snapshot_time, COUNT(*) as coin_count
            FROM crypto_coin_data 
            WHERE snapshot_time >= ?
            GROUP BY snapshot_time 
            ORDER BY snapshot_time DESC
        """, (start_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        snapshots = cursor.fetchall()
        conn.close()
        
        history = []
        for i, (snapshot_time_str, coin_count) in enumerate(snapshots):
            snapshot_time = datetime.strptime(snapshot_time_str, '%Y-%m-%d %H:%M:%S')
            
            # 计算与下一个快照的时间间隔
            interval = None
            status = 'normal'
            if i < len(snapshots) - 1:
                next_time = datetime.strptime(snapshots[i+1][0], '%Y-%m-%d %H:%M:%S')
                interval = (snapshot_time - next_time).total_seconds() / 60
                
                # 判断间隔是否异常
                if interval > COLLECTION_INTERVAL + TOLERANCE:
                    status = 'gap'
                elif interval < COLLECTION_INTERVAL - TOLERANCE:
                    status = 'too_frequent'
            
            history.append({
                'snapshot_time': snapshot_time_str,
                'coin_count': coin_count,
                'interval_to_next': round(interval, 1) if interval else None,
                'status': status
            })
        
        return history
    except Exception as e:
        print(f"❌ 获取采集历史失败: {e}")
        return []

def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'status':
            # 只检查状态，不触发采集
            need_collection, status = should_collect_now()
            print(json.dumps(status, indent=2, ensure_ascii=False))
            sys.exit(0 if not need_collection else 1)
        
        elif command == 'history':
            # 显示采集历史
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 2
            history = get_collection_history(hours)
            print(json.dumps(history, indent=2, ensure_ascii=False))
            sys.exit(0)
        
        elif command == 'check':
            # 检查并自动恢复
            silent = '--silent' in sys.argv
            result = check_and_recover(silent=silent)
            if not silent:
                print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(json.dumps(result, ensure_ascii=False))
            sys.exit(0 if result['status']['need_collection'] == False else 1)
        
        elif command == 'force':
            # 强制触发采集
            result = trigger_collection()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(0 if result['success'] else 1)
        
        else:
            print(f"未知命令: {command}")
            print("\n用法:")
            print("  python3 monitor_data_collection.py status   - 查看当前状态")
            print("  python3 monitor_data_collection.py history  - 查看采集历史")
            print("  python3 monitor_data_collection.py check    - 检查并自动恢复")
            print("  python3 monitor_data_collection.py force    - 强制触发采集")
            sys.exit(1)
    else:
        # 默认：检查并自动恢复
        silent = '--silent' in sys.argv
        result = check_and_recover(silent=silent)
        if not silent:
            print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result['status']['need_collection'] == False else 1)

if __name__ == '__main__':
    main()
