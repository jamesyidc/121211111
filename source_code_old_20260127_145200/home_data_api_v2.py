#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页数据API - 带缓存版本
"""

from flask import Flask, jsonify, send_file
import asyncio
import sys
import os
import threading
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# 全局缓存
CACHE = {
    'data': None,
    'last_update': None,
    'updating': False
}

# 缓存有效期（秒）
CACHE_VALIDITY = 60  # 1分钟（降低缓存时间以获取更及时的数据）

# 更新周期（秒）- 匹配Google Drive的3分钟更新周期
UPDATE_CYCLE = 180  # 3分钟更新一次（匹配数据源更新频率）

# Google Drive上传等待时间（秒）- 在每个3分钟周期的10-15秒之间获取数据
GDRIVE_WAIT_TIME = 10  # 等待到第10秒开始获取数据
GDRIVE_WAIT_MAX = 15  # 最多等待到第15秒

def parse_home_data(content):
    """解析首页数据内容"""
    lines = content.strip().split('\n')
    
    stats = {}
    coins = []
    
    in_coin_section = False
    
    for line in lines:
        line = line.strip()
        
        # 解析统计数据
        if line.startswith('透明标签_'):
            parts = line.split('=')
            if len(parts) == 2:
                key = parts[0].replace('透明标签_', '')
                value = parts[1]
                
                if '急涨总和' in key:
                    stats['rushUp'] = value.split('：')[1] if '：' in value else value
                elif '急跌总和' in key:
                    stats['rushDown'] = value.split('：')[1] if '：' in value else value
                elif '五种状态' in key:
                    stats['status'] = value.split('：')[1] if '：' in value else value
                elif '急涨急跌比值' in key:
                    stats['ratio'] = value.split('：')[1] if '：' in value else value
                elif '绿色数量' in key:
                    stats['greenCount'] = value
                elif '百分比' in key:
                    stats['percentage'] = value
        
        # 币种数据
        if '[超级列表框_首页开始]' in line:
            in_coin_section = True
            continue
        
        if '[超级列表框_首页结束]' in line:
            break
        
        if in_coin_section and '|' in line:
            parts = line.split('|')
            if len(parts) >= 16:
                coin = {
                    'index': parts[0],
                    'symbol': parts[1],
                    'change': parts[2],
                    'rushUp': parts[3],
                    'rushDown': parts[4],
                    'updateTime': parts[5],
                    'highPrice': parts[6],
                    'highTime': parts[7],
                    'decline': parts[8],
                    'change24h': parts[9],
                    'rank': parts[12],
                    'currentPrice': parts[13],
                    'ratio1': parts[14],
                    'ratio2': parts[15]
                }
                coins.append(coin)
    
    # 获取更新时间
    update_time = coins[0]['updateTime'] if coins else ''
    
    return {
        'stats': stats,
        'coins': coins,
        'updateTime': update_time
    }

def save_to_home_cache(parsed_data, filename, time_diff, update_time):
    """保存首页数据到缓存表"""
    import json
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 提取统计数据
        stats = parsed_data.get('stats', {})
        coins = parsed_data.get('coins', [])
        
        cursor.execute("""
            INSERT INTO home_data_cache 
            (filename, time_diff, rush_up, rush_down, status, ratio, 
             green_count, percentage, coin_data, update_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filename,
            time_diff,
            stats.get('rushUp', 0),
            stats.get('rushDown', 0),
            stats.get('status', ''),
            stats.get('ratio', 0),
            stats.get('green_count', 0),
            stats.get('percentage', 0),
            json.dumps(coins, ensure_ascii=False),
            update_time
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"   ⚠️  保存到home_cache失败: {str(e)}")
        return False

def update_cache():
    """后台更新缓存"""
    global CACHE
    
    if CACHE['updating']:
        print("已经在更新中，跳过...")
        return
    
    CACHE['updating'] = True
    print(f"\n{'='*60}")
    print(f"开始更新数据缓存... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        from gdrive_home_data_reader import get_latest_file_by_sorting
        
        # 获取最新数据
        result = asyncio.run(get_latest_file_by_sorting())
        
        if result and result.get('content'):
            parsed_data = parse_home_data(result['content'])
            
            CACHE['data'] = {
                'parsed_data': parsed_data,
                'filename': result['filename'],
                'time_diff': result['time_diff']
            }
            CACHE['last_update'] = time.time()
            
            print(f"✅ 缓存更新成功")
            print(f"   文件名: {result['filename']}")
            print(f"   时间差: {result['time_diff']:.1f} 分钟")
            
            # 保存到home_data_cache表（快速缓存）
            try:
                update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if save_to_home_cache(parsed_data, result['filename'], result['time_diff'], update_time):
                    print(f"   💾 已保存到快速缓存表")
            except Exception as cache_error:
                print(f"   ⚠️  快速缓存保存失败: {str(cache_error)}")
            
            # 自动保存到历史数据库
            try:
                from import_history_simple import parse_filename_datetime, parse_home_data as parse_for_db, save_to_database
                
                filename = result['filename']
                content = result['content']
                record_time = parse_filename_datetime(filename)
                
                if record_time:
                    stats, coins = parse_for_db(content)
                    success, msg = save_to_database(filename, record_time, stats, coins)
                    if success:
                        print(f"   💾 已自动保存到历史数据库")
                    else:
                        print(f"   💾 历史数据库: {msg}")
            except Exception as db_error:
                print(f"   ⚠️  保存到历史数据库失败: {str(db_error)}")
            
            # 触发比价检查
            try:
                trigger_price_comparison(parsed_data['coins'])
            except Exception as price_error:
                print(f"   ⚠️  比价检查失败: {str(price_error)}")
            
            print(f"{'='*60}\n")
        else:
            print("❌ 获取数据失败")
    except Exception as e:
        print(f"❌ 更新缓存失败: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        CACHE['updating'] = False

def sync_signal_stats():
    """同步做多做空信号统计数据"""
    try:
        print("\n" + "="*60)
        print("同步信号统计数据...")
        print("="*60)
        
        import requests
        from datetime import timezone, timedelta
        
        BEIJING_TZ = timezone(timedelta(hours=8))
        EXTERNAL_API = "https://8080-ieo4kftymfy546kbm6o33-2e77fc33.sandbox.novita.ai/api/filtered-signals/stats"
        
        # 获取数据
        params = {
            'limit': 200,
            'rsi_short_threshold': 65,
            'rsi_long_threshold': 30
        }
        
        response = requests.get(EXTERNAL_API, params=params, timeout=10)
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ API返回失败")
            return False
        
        # 提取数据
        summary = data.get('summary', {})
        breakdown = data.get('breakdown', {})
        
        # 生成记录时间（北京时间，精确到分钟）
        beijing_now = datetime.now(BEIJING_TZ)
        record_time = beijing_now.strftime('%Y-%m-%d %H:%M:00')
        
        total_count = summary.get('total', 0)
        long_count = summary.get('long', 0)
        short_count = summary.get('short', 0)
        chaodi_count = breakdown.get('抄底做多', 0)
        dibu_count = breakdown.get('底部做多', 0)
        dingbu_count = breakdown.get('顶部做空', 0)
        
        # 保存到数据库
        import sqlite3
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute(
            'SELECT id FROM signal_stats_history WHERE record_time = ?',
            (record_time,)
        )
        existing = cursor.fetchone()
        
        if existing:
            print(f"⏭️  记录已存在: {record_time}")
            conn.close()
            return False
        
        # 插入数据
        cursor.execute('''
            INSERT INTO signal_stats_history 
            (record_time, total_count, long_count, short_count,
             chaodi_count, dibu_count, dingbu_count, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_time, total_count, long_count, short_count,
            chaodi_count, dibu_count, dingbu_count, EXTERNAL_API
        ))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 信号数据同步成功: {record_time}")
        print(f"   总计: {total_count}, 做多: {long_count}, 做空: {short_count}")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ 信号数据同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def sync_panic_wash_data():
    """同步恐慌清洗指标数据"""
    try:
        import sqlite3
        
        # 从恐慌清洗API获取最新数据（优先使用V4读取器，支持本地文件）
        try:
            from panic_wash_reader_v5 import get_panic_wash_data_sync
        except:
            try:
                from panic_wash_reader_v4 import get_panic_wash_data_sync
            except:
                from panic_wash_simple import get_panic_wash_data_sync
        data = get_panic_wash_data_sync()
        
        if not data:
            print("⚠️  恐慌清洗数据获取失败")
            return False
        
        # 解析数据
        panic_indicator_str = data['panic_indicator']  # 例如: "10.77-绿"
        parts = panic_indicator_str.split('-')
        panic_indicator = float(parts[0])
        panic_color = parts[1] if len(parts) > 1 else None
        
        trend_rating = int(data['trend_rating'])
        market_zone = data['market_zone']
        liquidation_24h_people = int(data['liquidation_24h_people'])
        liquidation_24h_amount = float(data['liquidation_24h_amount'])
        total_position = float(data['total_position'])
        record_time = data['update_time']
        
        # 保存到数据库
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO panic_wash_history 
            (record_time, panic_indicator, panic_color, trend_rating, market_zone,
             liquidation_24h_people, liquidation_24h_amount, total_position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (record_time, panic_indicator, panic_color, trend_rating, market_zone,
              liquidation_24h_people, liquidation_24h_amount, total_position))
        
        conn.commit()
        conn.close()
        
        if cursor.rowcount > 0:
            print(f"✅ 恐慌清洗数据同步成功: {record_time}")
            print(f"   指标: {panic_indicator} ({panic_color}), 持仓量: {total_position}亿")
        else:
            print(f"⚠️  恐慌清洗数据已存在: {record_time}")
        
        return True
        
    except Exception as e:
        print(f"❌ 恐慌清洗数据同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def background_updater():
    """后台定时更新线程 - 严格每3分钟更新一次"""
    print("🚀 后台更新线程启动")
    print(f"⏰ 更新周期: {UPDATE_CYCLE}秒 ({UPDATE_CYCLE/60:.1f}分钟)")
    print(f"⏰ 数据采集策略: 首次对齐3分钟周期，后续固定间隔180秒")
    print("="*70)
    
    # 首次启动：计算到下一个3分钟周期（对齐到0,3,6,9...分钟）
    now = datetime.now()
    current_minute = now.minute
    current_second = now.second
    
    # 计算下一个3分钟周期的分钟数
    next_cycle_minute = ((current_minute // 3) + 1) * 3
    
    # 处理跨小时的情况
    if next_cycle_minute >= 60:
        next_hour = (now.hour + 1) % 24
        next_minute = next_cycle_minute - 60
        target_time = now.replace(hour=next_hour, minute=next_minute, second=GDRIVE_WAIT_TIME, microsecond=0)
        if target_time < now:  # 跨天的情况
            target_time = target_time + timedelta(days=1)
    else:
        target_time = now.replace(minute=next_cycle_minute, second=GDRIVE_WAIT_TIME, microsecond=0)
    
    # 首次等待到目标时间
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime('%H:%M:%S')
        print(f"⏰ [{beijing_time}北京] 首次启动，等待 {wait_seconds:.0f}秒 到下一个3分钟周期", flush=True)
        print(f"   目标时间: {(target_time + timedelta(hours=8)).strftime('%H:%M:%S')} 北京时间", flush=True)
        time.sleep(wait_seconds)
    
    # 主循环：固定180秒间隔
    while True:
        try:
            # 执行数据采集
            collect_time = datetime.now()
            beijing_time = (datetime.utcnow() + timedelta(hours=8)).strftime('%H:%M:%S')
            print(f"\n📡 [{beijing_time}北京] ===== 开始数据更新 =====", flush=True)
            
            try:
                print("  ↳ 更新首页缓存...")
                update_cache()
                print("  ✓ 首页缓存更新完成")
            except Exception as e:
                print(f"  ✗ 首页缓存更新失败: {e}")
            
            try:
                print("  ↳ 同步信号统计...")
                sync_signal_stats()
                print("  ✓ 信号统计同步完成")
            except Exception as e:
                print(f"  ✗ 信号统计同步失败: {e}")
            
            try:
                print("  ↳ 同步恐慌清洗数据...")
                sync_panic_wash_data()
                print("  ✓ 恐慌清洗数据同步完成")
            except Exception as e:
                print(f"  ✗ 恐慌清洗数据同步失败: {e}")
            
            finish_time = datetime.now()
            duration = (finish_time - collect_time).total_seconds()
            
            # 计算实际应该等待的时间（从周期开始计算）
            sleep_time = max(0, UPDATE_CYCLE - duration)
            next_update_time = collect_time + timedelta(seconds=UPDATE_CYCLE)
            next_beijing = (next_update_time + timedelta(hours=8)).strftime('%H:%M:%S')
            
            print(f"\n✅ [{beijing_time}北京] 数据更新完成 (耗时: {duration:.1f}秒)", flush=True)
            print(f"⏰ 下次更新时间: {next_beijing} 北京时间", flush=True)
            print(f"💤 等待 {sleep_time:.1f}秒 到下一个周期", flush=True)
            print("="*70 + "\n", flush=True)
            
            # 等待到下一个周期（从周期开始计算，扣除已用时间）
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"\n❌ 后台更新线程错误: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"⏰ 60秒后重试...\n")
            time.sleep(60)

@app.route('/')
def index():
    """首页 - 导航页"""
    return send_file('index.html')

@app.route('/live')
def live():
    """实时监控页面"""
    return send_file('crypto_home_v2.html')

@app.route('/history')
def history():
    """历史回看页面"""
    return send_file('history_viewer.html')

@app.route('/panic-wash')
def panic_wash():
    """恐慌清洗指标监控页面"""
    return send_file('panic_wash_monitor.html')

@app.route('/panic-wash-v3')
def panic_wash_v3():
    """恐慌清洗指标监控页面 V3 - 双Y轴曲线图+完整数据列表"""
    return send_file('panic_wash_monitor_v3.html')

@app.route('/panic-wash-history')
def panic_wash_history():
    """恐慌清洗历史曲线页面"""
    return send_file('panic_wash_history.html')

@app.route('/test-cache')
def test_cache():
    """缓存测试页面"""
    return send_file('test_cache.html')

@app.route('/test-coin-display')
def test_coin_display():
    """币名显示测试页面"""
    return send_file('test_coin_display.html')

@app.route('/coin-list-test')
def coin_list_test():
    """币名列表简单测试页面"""
    return send_file('coin_list_simple.html')

@app.route('/api/panic-wash')
def get_panic_wash_api():
    """恐慌清洗API - 直接返回数据"""
    try:
        try:
            from panic_wash_reader_v5 import get_panic_wash_data_sync
        except:
            try:
                from panic_wash_reader_v4 import get_panic_wash_data_sync
            except:
                from panic_wash_simple import get_panic_wash_data_sync
        data = get_panic_wash_data_sync()
        
        if data:
            return jsonify({
                'success': True,
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'error': '暂无数据'
            }), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/home-data')
def get_home_data():
    """获取首页数据API（使用缓存）"""
    try:
        # 检查缓存
        if CACHE['data'] is None:
            # 第一次请求，立即更新
            update_cache()
        elif CACHE['last_update'] and (time.time() - CACHE['last_update']) > CACHE_VALIDITY:
            # 缓存过期，触发后台更新（但立即返回旧数据）
            threading.Thread(target=update_cache, daemon=True).start()
        
        if CACHE['data'] is None:
            return jsonify({
                'success': False,
                'error': '数据尚未加载'
            }), 503
        
        cached = CACHE['data']
        
        return jsonify({
            'success': True,
            'data': cached['parsed_data'],
            'filename': cached['filename'],
            'time_diff': cached['time_diff'],
            'cached_at': datetime.fromtimestamp(CACHE['last_update']).strftime('%Y-%m-%d %H:%M:%S') if CACHE['last_update'] else None
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/home-data/force-refresh')
def force_refresh_home_data():
    """强制刷新首页数据API（绕过缓存立即获取最新数据）"""
    try:
        print("🔄 收到强制刷新请求，立即获取最新数据...")
        update_cache()
        
        if CACHE['data'] is None:
            return jsonify({
                'success': False,
                'error': '数据刷新失败'
            }), 503
        
        cached = CACHE['data']
        
        return jsonify({
            'success': True,
            'data': cached['parsed_data'],
            'filename': cached['filename'],
            'time_diff': cached['time_diff'],
            'cached_at': datetime.fromtimestamp(CACHE['last_update']).strftime('%Y-%m-%d %H:%M:%S') if CACHE['last_update'] else None,
            'message': '已强制刷新数据'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 历史数据API ====================

def query_history_data(start_time=None, end_time=None, limit=100):
    """查询历史数据"""
    import sqlite3
    conn = sqlite3.connect('crypto_data.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        where_clauses = []
        params = []
        
        if start_time:
            where_clauses.append('record_time >= ?')
            params.append(start_time)
        
        if end_time:
            where_clauses.append('record_time <= ?')
            params.append(end_time)
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        # 查询统计数据
        cursor.execute(f'''
            SELECT * FROM stats_history
            WHERE {where_sql}
            ORDER BY record_time DESC
            LIMIT ?
        ''', params + [limit])
        
        stats_records = [dict(row) for row in cursor.fetchall()]
        
        # 为每条统计数据查询对应的币种数据
        for record in stats_records:
            cursor.execute('''
                SELECT * FROM coin_history
                WHERE stats_id = ?
                ORDER BY index_num
            ''', (record['id'],))
            
            record['coins'] = [dict(row) for row in cursor.fetchall()]
        
        return stats_records
        
    finally:
        conn.close()

@app.route('/api/history/dates')
def get_dates():
    """获取有数据的日期列表"""
    try:
        import sqlite3
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT DATE(record_time) as date
            FROM stats_history
            ORDER BY date DESC
        ''')
        
        dates = [row[0] for row in cursor.fetchall()]
        
        # 获取每个日期的统计信息
        date_info = []
        for date in dates:
            cursor.execute('''
                SELECT COUNT(*) as count,
                       MIN(record_time) as min_time,
                       MAX(record_time) as max_time
                FROM stats_history
                WHERE DATE(record_time) = ?
            ''', (date,))
            
            row = cursor.fetchone()
            date_info.append({
                'date': date,
                'count': row[0],
                'min_time': row[1],
                'max_time': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'dates': date_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/query')
def query_history():
    """查询历史数据"""
    try:
        from flask import request
        
        # 获取查询参数
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        date = request.args.get('date')  # 如果只查询某一天
        limit = int(request.args.get('limit', 100))
        
        # 如果指定了日期，自动设置时间范围
        if date:
            start_time = f"{date} 00:00:00"
            end_time = f"{date} 23:59:59"
        
        records = query_history_data(start_time, end_time, limit)
        
        return jsonify({
            'success': True,
            'count': len(records),
            'data': records,
            'query': {
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/stats')
def get_history_stats():
    """获取数据库统计信息"""
    try:
        import sqlite3
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM stats_history')
        stats_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM coin_history')
        coin_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
        time_range = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(DISTINCT DATE(record_time)) FROM stats_history')
        day_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_records': stats_count,
                'total_coins': coin_count,
                'earliest': time_range[0],
                'latest': time_range[1],
                'days': day_count
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/import/current', methods=['POST'])
def import_current():
    """导入当前最新数据"""
    try:
        from import_history_simple import import_current_data
        asyncio.run(import_current_data())
        return jsonify({
            'success': True,
            'message': '导入成功'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============== 信号统计历史API ==============

@app.route('/signal-history')
def signal_history_page():
    """信号统计历史回看页面"""
    return send_file('signal_history_viewer.html')

@app.route('/api/signal-stats/save', methods=['POST'])
def save_signal_stats():
    """保存信号统计数据"""
    try:
        from flask import request
        import sqlite3
        
        data = request.json
        record_time = data.get('record_time')
        
        if not record_time:
            record_time = datetime.now().strftime('%Y-%m-%d %H:%M:00')
        
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO signal_stats_history 
            (record_time, total_count, long_count, short_count, 
             chaodi_count, dibu_count, dingbu_count, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_time,
            data.get('total', 0),
            data.get('long', 0),
            data.get('short', 0),
            data.get('chaodi', 0),
            data.get('dibu', 0),
            data.get('dingbu', 0),
            data.get('source_url', '')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '保存成功',
            'record_time': record_time
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signal-stats/query')
def query_signal_stats():
    """查询信号统计历史数据"""
    try:
        from flask import request
        import sqlite3
        
        date = request.args.get('date')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = request.args.get('limit', 200, type=int)
        
        conn = sqlite3.connect('crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询
        where_clauses = []
        params = []
        
        if date:
            if start_time and end_time:
                where_clauses.append('record_time BETWEEN ? AND ?')
                params.extend([f'{date} {start_time}:00', f'{date} {end_time}:59'])
            else:
                where_clauses.append('DATE(record_time) = ?')
                params.append(date)
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
        
        query = f'''
            SELECT 
                record_time, total_count, long_count, short_count,
                chaodi_count, dibu_count, dingbu_count, source_url
            FROM signal_stats_history
            {where_sql}
            ORDER BY record_time DESC
            LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                'record_time': row['record_time'],
                'total': row['total_count'],
                'long': row['long_count'],
                'short': row['short_count'],
                'chaodi': row['chaodi_count'],
                'dibu': row['dibu_count'],
                'dingbu': row['dingbu_count'],
                'source_url': row['source_url']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signal-stats/stats')
def signal_stats_db_stats():
    """获取信号统计数据库统计信息"""
    try:
        import sqlite3
        
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM signal_stats_history')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM signal_stats_history')
        time_range = cursor.fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_records': total,
            'time_range': {
                'start': time_range[0],
                'end': time_range[1]
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/signal-stats/latest')
def get_latest_signal_stats():
    """获取最新的信号统计数据"""
    try:
        import sqlite3
        
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 查询最新的一条记录
        cursor.execute('''
            SELECT long_count, short_count, record_time
            FROM signal_stats_history
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'success': True,
                'data': {
                    'long_count': row[0],
                    'short_count': row[1],
                    'record_time': row[2]
                }
            })
        else:
            # 如果没有数据，返回默认值
            return jsonify({
                'success': True,
                'data': {
                    'long_count': 0,
                    'short_count': 0,
                    'record_time': None
                }
            })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/panic-wash/history')
def get_panic_wash_history():
    """查询恐慌清洗历史数据"""
    try:
        import sqlite3
        from flask import request
        
        # 获取查询参数
        start_time = request.args.get('start')
        end_time = request.args.get('end')
        limit = request.args.get('limit', 1000)  # 默认最多返回1000条
        
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        # 查询历史数据
        if start_time and end_time:
            # 按时间范围查询
            cursor.execute('''
                SELECT 
                    record_time,
                    panic_indicator,
                    panic_color,
                    trend_rating,
                    market_zone,
                    liquidation_24h_people,
                    liquidation_24h_amount,
                    total_position
                FROM panic_wash_history
                WHERE record_time BETWEEN ? AND ?
                ORDER BY record_time DESC
                LIMIT ?
            ''', (start_time, end_time, limit))
        else:
            # 查询所有数据（或最近的limit条）
            cursor.execute('''
                SELECT 
                    record_time,
                    panic_indicator,
                    panic_color,
                    trend_rating,
                    market_zone,
                    liquidation_24h_people,
                    liquidation_24h_amount,
                    total_position
                FROM panic_wash_history
                ORDER BY record_time DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 格式化数据
        data = []
        for row in rows:
            # 格式化时间显示（只保留时分）
            time_str = row[0]  # 2025-12-03 15:09:05
            if len(time_str) >= 16:
                time_display = time_str[5:16]  # 12-03 15:09
            else:
                time_display = time_str
            
            # 组合恐慌指标和颜色
            panic_indicator_full = f"{row[1]}-{row[2]}" if row[2] else str(row[1])
            
            data.append({
                'time': time_display,
                'record_time': row[0],
                'full_time': row[0],
                'panic_indicator': panic_indicator_full,
                'panic_indicator_value': row[1],
                'panic_color': row[2],
                'trend_rating': row[3],
                'market_zone': row[4],
                'liquidation_24h_people': row[5],
                'liquidation_24h_amount': row[6],
                'total_position': row[7]
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 比价系统集成
# ============================================================

from price_comparison_system import PriceComparisonSystem

# 初始化比价系统
price_comparison = PriceComparisonSystem()

@app.route('/price-comparison')
def price_comparison_page():
    """比价系统页面"""
    return send_file('price_comparison.html')

@app.route('/api/price-comparison/report')
def get_price_comparison_report():
    """获取完整比价报告"""
    try:
        report = price_comparison.get_full_report()
        return jsonify(report)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/price-comparison/baseline')
def get_baseline():
    """获取价格基准数据"""
    try:
        baseline = price_comparison.get_baseline_data()
        return jsonify({
            'success': True,
            'data': baseline
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/price-comparison/today')
def get_today_records():
    """获取今日创新高低记录"""
    try:
        records = price_comparison.get_daily_new_records()
        return jsonify({
            'success': True,
            'data': records
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def trigger_price_comparison(coins_data):
    """
    触发比价检查
    在数据更新后调用此函数
    """
    try:
        # 批量比价
        results = price_comparison.batch_compare(coins_data)
        
        # 统计创新高低
        new_highs = [r for r in results if r['action'] == 'new_high']
        new_lows = [r for r in results if r['action'] == 'new_low']
        
        if new_highs or new_lows:
            print(f"\n📊 比价结果:")
            print(f"   🔥 创新高: {len(new_highs)} 个币种")
            print(f"   📉 创新低: {len(new_lows)} 个币种")
            
            # 显示创新高
            for r in new_highs[:3]:  # 只显示前3个
                print(f"      {r['symbol']}: {r['old_value']:.8f} → {r['new_value']:.8f}")
            
            # 显示创新低
            for r in new_lows[:3]:  # 只显示前3个
                print(f"      {r['symbol']}: {r['old_value']:.8f} → {r['new_value']:.8f}")
        
        return results
    except Exception as e:
        print(f"❌ 比价失败: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    print("="*60)
    print("首页数据监控服务器 V2 (带缓存)")
    print("="*60)
    print("访问: http://0.0.0.0:5003/")
    print("缓存有效期: 5 分钟")
    print("="*60)
    
    # 启动后台更新线程
    updater_thread = threading.Thread(target=background_updater, daemon=True)
    updater_thread.start()
    print("✅ 后台更新线程已启动\n")
    
    app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)
