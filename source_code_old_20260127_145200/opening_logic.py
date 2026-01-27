"""
开仓逻辑系统
根据多维度因子判断市场趋势，给出开仓建议
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple

def get_db_connection(db_name: str):
    """获取数据库连接"""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

def get_star_data() -> Dict:
    """获取星星数据 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        # 从聚合JSONL读取最新数据
        aggregate_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        latest_aggregate = aggregate_manager.get_latest_aggregate()
        
        if latest_aggregate:
            # 从聚合数据读取
            count_val = latest_aggregate.get('count_aggregate', 0) or 0
            score_type = latest_aggregate.get('count_score_type', '') or ''
            
            return {
                'solid_stars': count_val if 'solid' in score_type else 0,
                'hollow_stars': count_val if 'hollow' in score_type else 0,
                'rush_up': latest_aggregate.get('rush_up_total', 0) or 0,
                'rush_down': latest_aggregate.get('rush_down_total', 0) or 0
            }
        return {'solid_stars': 0, 'hollow_stars': 0, 'rush_up': 0, 'rush_down': 0}
    except Exception as e:
        print(f"获取星星数据失败: {e}")
        import traceback
        traceback.print_exc()
        return {'solid_stars': 0, 'hollow_stars': 0, 'rush_up': 0, 'rush_down': 0}

def get_btc_eth_change() -> Dict:
    """获取BTC和ETH的真实24小时涨跌幅 - 从crypto_coin_data表获取"""
    try:
        conn = get_db_connection('crypto_data.db')
        cursor = conn.cursor()
        
        result = {'BTC': 0.0, 'ETH': 0.0}
        
        # 从crypto_coin_data表获取真实的24h涨跌幅
        for coin_name in ['BTC', 'ETH']:
            cursor.execute("""
                SELECT change_24h
                FROM crypto_coin_data
                WHERE symbol = ?
                ORDER BY update_time DESC
                LIMIT 1
            """, (coin_name,))
            row = cursor.fetchone()
            
            if row and row['change_24h'] is not None:
                result[coin_name] = float(row['change_24h'])
        
        conn.close()
        return result
    except Exception as e:
        print(f"获取BTC/ETH涨跌幅失败: {e}")
        return {'BTC': 0.0, 'ETH': 0.0}

def get_total_position() -> float:
    """获取全网持仓量（单位：亿美元）"""
    try:
        conn = get_db_connection('crypto_data.db')
        cursor = conn.cursor()
        
        # 从panic_wash_index表获取最新的全网持仓量
        cursor.execute("""
            SELECT total_position
            FROM panic_wash_index
            WHERE total_position > 1000000000
            ORDER BY record_time DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row and row['total_position']:
            # 转换为亿美元
            position_yi = round(float(row['total_position']) / 100000000, 2)
            return position_yi
        return 0.0
    except Exception as e:
        print(f"获取全网持仓量失败: {e}")
        return 0.0

def get_breakthrough_data() -> Dict:
    """获取创新高/创新低次数"""
    try:
        conn = get_db_connection('crypto_data.db')
        cursor = conn.cursor()
        
        # 获取今天的创新高/创新低次数
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN event_type = 'new_high' THEN 1 ELSE 0 END) as new_high_count,
                SUM(CASE WHEN event_type = 'new_low' THEN 1 ELSE 0 END) as new_low_count
            FROM price_breakthrough_events
            WHERE DATE(event_time) = ?
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'new_high_count': row['new_high_count'] or 0,
                'new_low_count': row['new_low_count'] or 0
            }
        return {'new_high_count': 0, 'new_low_count': 0}
    except Exception as e:
        print(f"获取创新高/创新低数据失败: {e}")
        return {'new_high_count': 0, 'new_low_count': 0}

def get_extreme_change_count() -> Dict:
    """获取24h极端涨跌币种数量 - 只统计每个币种的最新数据"""
    try:
        conn = get_db_connection('crypto_data.db')
        cursor = conn.cursor()
        
        # 24h涨≥10%的币种数 (只统计每个symbol的最新记录)
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol) as count
            FROM (
                SELECT symbol, change_24h, 
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY update_time DESC) as rn
                FROM crypto_coin_data
                WHERE change_24h IS NOT NULL
            ) latest
            WHERE rn = 1 AND change_24h >= 10
        """)
        extreme_up = cursor.fetchone()['count']
        
        # 24h跌≤-10%的币种数 (只统计每个symbol的最新记录)
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol) as count
            FROM (
                SELECT symbol, change_24h,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY update_time DESC) as rn
                FROM crypto_coin_data
                WHERE change_24h IS NOT NULL
            ) latest
            WHERE rn = 1 AND change_24h <= -10
        """)
        extreme_down = cursor.fetchone()['count']
        
        conn.close()
        return {'extreme_up': extreme_up or 0, 'extreme_down': extreme_down or 0}
    except Exception as e:
        print(f"获取极端涨跌数据失败: {e}")
        return {'extreme_up': 0, 'extreme_down': 0}

def get_score_system_avg() -> Dict:
    """获取得分系统的多空平均分"""
    try:
        conn = get_db_connection('signal_data.db')
        cursor = conn.cursor()
        
        # 获取最新的做多和做空平均分
        cursor.execute("""
            SELECT 
                AVG(CASE WHEN signal_type = 'long' THEN score ELSE NULL END) as long_avg,
                AVG(CASE WHEN signal_type = 'short' THEN score ELSE NULL END) as short_avg
            FROM trading_signals
            WHERE timestamp > datetime('now', '-1 hour')
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'long_avg': float(row['long_avg'] or 0),
                'short_avg': float(row['short_avg'] or 0)
            }
        return {'long_avg': 0.0, 'short_avg': 0.0}
    except Exception as e:
        print(f"获取得分系统数据失败: {e}")
        return {'long_avg': 0.0, 'short_avg': 0.0}

def calculate_trend_score() -> Tuple[int, List[Dict], Dict]:
    """
    计算趋势得分
    返回: (总得分, 得分详情列表, 原始数据)
    """
    score = 0
    details = []
    
    # 获取所有数据
    star_data = get_star_data()
    btc_eth_change = get_btc_eth_change()
    breakthrough = get_breakthrough_data()
    extreme = get_extreme_change_count()
    score_avg = get_score_system_avg()
    total_position = get_total_position()
    
    solid = star_data['solid_stars']
    hollow = star_data['hollow_stars']
    btc_change = btc_eth_change['BTC']
    eth_change = btc_eth_change['ETH']
    
    # 1. 星星差值判断
    star_diff = solid - hollow
    if star_diff >= 10:
        score += 5
        details.append({'factor': '实心星星优势', 'level': '很强做多', 'score': 5, 'value': f'+{star_diff}'})
    elif star_diff >= 5:
        score += 2
        details.append({'factor': '实心星星优势', 'level': '较强做多', 'score': 2, 'value': f'+{star_diff}'})
    elif star_diff >= 3:
        score += 1
        details.append({'factor': '实心星星优势', 'level': '一般做多', 'score': 1, 'value': f'+{star_diff}'})
    elif star_diff <= -10:
        score -= 5
        details.append({'factor': '空心星星优势', 'level': '很强做空', 'score': -5, 'value': f'{star_diff}'})
    elif star_diff <= -5:
        score -= 2
        details.append({'factor': '空心星星优势', 'level': '较强做空', 'score': -2, 'value': f'{star_diff}'})
    elif star_diff <= -3:
        score -= 1
        details.append({'factor': '空心星星优势', 'level': '一般做空', 'score': -1, 'value': f'{star_diff}'})
    
    # 2. BTC涨跌幅判断
    if btc_change >= 3:
        score += 5
        details.append({'factor': 'BTC涨幅', 'level': '很强做多', 'score': 5, 'value': f'{btc_change:.2f}%'})
    elif btc_change >= 2:
        score += 2
        details.append({'factor': 'BTC涨幅', 'level': '较强做多', 'score': 2, 'value': f'{btc_change:.2f}%'})
    elif btc_change >= 1:
        score += 1
        details.append({'factor': 'BTC涨幅', 'level': '一般做多', 'score': 1, 'value': f'{btc_change:.2f}%'})
    elif btc_change <= -3:
        score -= 5
        details.append({'factor': 'BTC跌幅', 'level': '很强做空', 'score': -5, 'value': f'{btc_change:.2f}%'})
    elif btc_change <= -2:
        score -= 2
        details.append({'factor': 'BTC跌幅', 'level': '较强做空', 'score': -2, 'value': f'{btc_change:.2f}%'})
    elif btc_change <= -1:
        score -= 1
        details.append({'factor': 'BTC跌幅', 'level': '一般做空', 'score': -1, 'value': f'{btc_change:.2f}%'})
    
    # 3. ETH涨跌幅判断
    if eth_change >= 3:
        score += 5
        details.append({'factor': 'ETH涨幅', 'level': '很强做多', 'score': 5, 'value': f'{eth_change:.2f}%'})
    elif eth_change >= 2:
        score += 2
        details.append({'factor': 'ETH涨幅', 'level': '较强做多', 'score': 2, 'value': f'{eth_change:.2f}%'})
    elif eth_change >= 1:
        score += 1
        details.append({'factor': 'ETH涨幅', 'level': '一般做多', 'score': 1, 'value': f'{eth_change:.2f}%'})
    elif eth_change <= -3:
        score -= 5
        details.append({'factor': 'ETH跌幅', 'level': '很强做空', 'score': -5, 'value': f'{eth_change:.2f}%'})
    elif eth_change <= -2:
        score -= 2
        details.append({'factor': 'ETH跌幅', 'level': '较强做空', 'score': -2, 'value': f'{eth_change:.2f}%'})
    elif eth_change <= -1:
        score -= 1
        details.append({'factor': 'ETH跌幅', 'level': '一般做空', 'score': -1, 'value': f'{eth_change:.2f}%'})
    
    # 汇总原始数据
    raw_data = {
        'star_data': star_data,
        'btc_eth_change': btc_eth_change,
        'breakthrough': breakthrough,
        'extreme': extreme,
        'score_avg': score_avg,
        'total_position': total_position
    }
    
    return score, details, raw_data

def check_restrictions(raw_data: Dict) -> Tuple[bool, bool, List[str]]:
    """
    检查趋势判断限制条件
    返回: (can_long, can_short, reasons)
    """
    can_long = True
    can_short = True
    reasons = []
    
    btc_change = raw_data['btc_eth_change']['BTC']
    eth_change = raw_data['btc_eth_change']['ETH']
    star_data = raw_data['star_data']
    breakthrough = raw_data['breakthrough']
    extreme = raw_data['extreme']
    score_avg = raw_data['score_avg']
    
    # BTC涨幅限制
    if btc_change >= 3:
        can_short = False
        reasons.append(f'BTC涨幅{btc_change:.2f}% ≥ 3% → 不做空')
    elif btc_change >= 2:
        can_short = False
        reasons.append(f'BTC涨幅{btc_change:.2f}% ≥ 2% → 不做空')
    
    # BTC跌幅限制
    if btc_change <= -3:
        can_long = False
        reasons.append(f'BTC跌幅{btc_change:.2f}% ≤ -3% → 不做多')
    elif btc_change <= -2:
        can_long = False
        reasons.append(f'BTC跌幅{btc_change:.2f}% ≤ -2% → 不做多')
    
    # ETH涨幅限制
    if eth_change >= 3:
        can_short = False
        reasons.append(f'ETH涨幅{eth_change:.2f}% ≥ 3% → 不做空')
    elif eth_change >= 2:
        can_short = False
        reasons.append(f'ETH涨幅{eth_change:.2f}% ≥ 2% → 不做空')
    
    # ETH跌幅限制
    if eth_change <= -3:
        can_long = False
        reasons.append(f'ETH跌幅{eth_change:.2f}% ≤ -3% → 不做多')
    elif eth_change <= -2:
        can_long = False
        reasons.append(f'ETH跌幅{eth_change:.2f}% ≤ -2% → 不做多')
    
    # 创新高/创新低限制
    if breakthrough['new_high_count'] >= 3:
        can_short = False
        reasons.append(f'创新高次数{breakthrough["new_high_count"]} ≥ 3 → 不做空')
    
    if breakthrough['new_low_count'] >= 3:
        can_long = False
        reasons.append(f'创新低次数{breakthrough["new_low_count"]} ≥ 3 → 不做多')
    
    # 星星数量限制
    if star_data['hollow_stars'] >= 3:
        can_long = False
        reasons.append(f'空心星星{star_data["hollow_stars"]}个 ≥ 3 → 不做多')
    
    if star_data['solid_stars'] >= 3:
        can_short = False
        reasons.append(f'实心星星{star_data["solid_stars"]}个 ≥ 3 → 不做空')
    
    # 急涨急跌限制
    rush_diff = star_data['rush_up'] - star_data['rush_down']
    if rush_diff >= 20:
        can_short = False
        reasons.append(f'急涨-急跌={rush_diff} ≥ 20 → 不做空')
    elif rush_diff <= -20:
        can_long = False
        reasons.append(f'急涨-急跌={rush_diff} ≤ -20 → 不做多')
    
    # 极端涨跌限制
    if extreme['extreme_up'] >= 2:
        can_short = False
        reasons.append(f'24h涨≥10%币种数{extreme["extreme_up"]} ≥ 2 → 不做空')
    
    if extreme['extreme_down'] >= 2:
        can_long = False
        reasons.append(f'24h跌≤-10%币种数{extreme["extreme_down"]} ≥ 2 → 不做多')
    
    # 得分系统限制
    if score_avg['short_avg'] >= 85:
        can_long = False
        reasons.append(f'做空平均分{score_avg["short_avg"]:.1f} ≥ 85 → 不做多')
    
    if score_avg['long_avg'] >= 85:
        can_short = False
        reasons.append(f'做多平均分{score_avg["long_avg"]:.1f} ≥ 85 → 不做空')
    
    return can_long, can_short, reasons

def calculate_position_size(raw_data: Dict, can_long: bool, can_short: bool) -> Dict:
    """
    计算建议仓位（整合星星仓位 + 全网持仓量仓位，上限70%）
    返回: {
        'position_percent': 总仓位百分比,
        'position_type': 'long'/'short'/'neutral',
        'position_level': '描述',
        'star_position': 星星仓位,
        'oi_position': 全网持仓量仓位,
        'calculation_details': 计算详情
    }
    """
    star_data = raw_data['star_data']
    solid = star_data['solid_stars']
    hollow = star_data['hollow_stars']
    rush_up = star_data['rush_up']
    rush_down = star_data['rush_down']
    total_position = raw_data.get('total_position', 0)
    
    # 计算星星差值
    star_diff = solid - hollow
    
    # 计算急涨急跌总和
    rush_sum = rush_up + rush_down
    
    details = []
    star_position = 0
    oi_position = 0
    position_type = 'neutral'
    
    # ========== 第一部分：星星仓位判断 ==========
    details.append("【星星仓位判断】")
    
    # 无序波动优先判断
    if rush_sum <= 10:
        star_position = 10
        position_type = 'neutral'
        details.append(f'急涨({rush_up}) + 急跌({rush_down}) = {rush_sum} ≤ 10 → 无序波动 +10%')
    
    # 做多仓位（实心星星优势）
    elif star_diff >= 10 and can_long:
        star_position = 60
        position_type = 'long'
        details.append(f'实心星星({solid}) - 空心星星({hollow}) = {star_diff} ≥ 10 → 强势做多 +60%')
    elif star_diff >= 5 and can_long:
        star_position = 40
        position_type = 'long'
        details.append(f'实心星星({solid}) - 空心星星({hollow}) = {star_diff} ≥ 5 → 中等做多 +40%')
    elif star_diff >= 3 and can_long:
        star_position = 20
        position_type = 'long'
        details.append(f'实心星星({solid}) - 空心星星({hollow}) = {star_diff} ≥ 3 → 轻仓做多 +20%')
    
    # 做空仓位（空心星星优势）
    elif star_diff <= -10 and can_short:
        star_position = 60
        position_type = 'short'
        details.append(f'空心星星({hollow}) - 实心星星({solid}) = {abs(star_diff)} ≥ 10 → 强势做空 +60%')
    elif star_diff <= -5 and can_short:
        star_position = 40
        position_type = 'short'
        details.append(f'空心星星({hollow}) - 实心星星({solid}) = {abs(star_diff)} ≥ 5 → 中等做空 +40%')
    elif star_diff <= -3 and can_short:
        star_position = 20
        position_type = 'short'
        details.append(f'空心星星({hollow}) - 实心星星({solid}) = {abs(star_diff)} ≥ 3 → 轻仓做空 +20%')
    
    # 不满足条件
    else:
        star_position = 0
        if star_diff > 0 and not can_long:
            details.append(f'实心星星优势{star_diff}，但做多受限 → +0%')
        elif star_diff < 0 and not can_short:
            details.append(f'空心星星优势{abs(star_diff)}，但做空受限 → +0%')
        elif abs(star_diff) < 3:
            details.append(f'星星差值{star_diff}不足3 → +0%')
        else:
            details.append('星星仓位 → +0%')
    
    # ========== 第二部分：全网持仓量仓位判断 ==========
    details.append("")
    details.append("【全网持仓量仓位】")
    details.append(f'当前持仓量: {total_position}亿美元')
    
    if total_position > 0:
        # 做多区间
        if total_position < 92:
            if can_long and position_type in ['long', 'neutral']:
                oi_position = 20
                details.append(f'< 92亿 → 强烈做多 +20%')
                if position_type == 'neutral':
                    position_type = 'long'
            else:
                details.append(f'< 92亿 → 强烈做多，但受限 +0%')
        elif 92 <= total_position < 95:
            if can_long and position_type in ['long', 'neutral']:
                oi_position = 10
                details.append(f'92-95亿 → 一般做多 +10%')
                if position_type == 'neutral':
                    position_type = 'long'
            else:
                details.append(f'92-95亿 → 一般做多，但受限 +0%')
        elif 95 <= total_position < 100:
            if can_long and position_type in ['long', 'neutral']:
                oi_position = 5
                details.append(f'95-100亿 → 可以做多 +5%')
                if position_type == 'neutral':
                    position_type = 'long'
            else:
                details.append(f'95-100亿 → 可以做多，但受限 +0%')
        
        # 做空区间
        elif 100 <= total_position < 110:
            if can_short and position_type in ['short', 'neutral']:
                oi_position = 5
                details.append(f'100-110亿 → 可以做空 +5%')
                if position_type == 'neutral':
                    position_type = 'short'
            else:
                details.append(f'100-110亿 → 可以做空，但受限 +0%')
        elif 110 <= total_position < 115:
            if can_short and position_type in ['short', 'neutral']:
                oi_position = 10
                details.append(f'110-115亿 → 一般做空 +10%')
                if position_type == 'neutral':
                    position_type = 'short'
            else:
                details.append(f'110-115亿 → 一般做空，但受限 +0%')
        elif total_position >= 115:
            if can_short and position_type in ['short', 'neutral']:
                oi_position = 20
                details.append(f'≥ 115亿 → 强烈做空 +20%')
                if position_type == 'neutral':
                    position_type = 'short'
            else:
                details.append(f'≥ 115亿 → 强烈做空，但受限 +0%')
        else:
            details.append('持仓量未在做多/做空区间 → +0%')
    else:
        details.append('无持仓量数据 → +0%')
    
    # ========== 第三部分：计算总仓位（上限70%） ==========
    total_pos = star_position + oi_position
    if total_pos > 70:
        details.append("")
        details.append(f'【仓位上限控制】')
        details.append(f'原始总仓位: {star_position}% + {oi_position}% = {total_pos}%')
        details.append(f'超过上限70%，调整为70%')
        total_pos = 70
    else:
        details.append("")
        details.append(f'【总仓位】')
        details.append(f'星星仓位 + 持仓量仓位 = {star_position}% + {oi_position}% = {total_pos}%')
    
    # 确定仓位等级描述
    if position_type == 'long':
        if total_pos >= 60:
            level = '强势做多'
        elif total_pos >= 40:
            level = '中等做多'
        elif total_pos >= 20:
            level = '轻仓做多'
        else:
            level = '观望'
    elif position_type == 'short':
        if total_pos >= 60:
            level = '强势做空'
        elif total_pos >= 40:
            level = '中等做空'
        elif total_pos >= 20:
            level = '轻仓做空'
        else:
            level = '观望'
    else:
        level = '观望' if total_pos == 0 else '无序波动'
    
    return {
        'position_percent': total_pos,
        'position_type': position_type,
        'position_level': level,
        'star_position': star_position,
        'oi_position': oi_position,
        'calculation_details': details
    }

def track_position_suggestion(position_info: Dict) -> Dict:
    """
    跟踪仓位建议，记录首次出现时间
    返回: 包含首次出现时间和首次开仓建议的字典
    """
    try:
        position_type = position_info['position_type']
        position_percent = position_info['position_percent']
        position_level = position_info['position_level']
        
        # 生成建议唯一标识
        suggestion_key = f"{position_type}_{position_percent}"
        
        conn = get_db_connection('crypto_data.db')
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查是否已存在该建议
        cursor.execute("""
            SELECT first_appeared_at, position_percent 
            FROM opening_logic_suggestions 
            WHERE suggestion_key = ? AND is_active = 1
        """, (suggestion_key,))
        existing = cursor.fetchone()
        
        if existing:
            # 已存在，更新最后更新时间
            first_appeared_at = existing['first_appeared_at']
            cursor.execute("""
                UPDATE opening_logic_suggestions 
                SET last_updated_at = ? 
                WHERE suggestion_key = ? AND is_active = 1
            """, (current_time, suggestion_key))
        else:
            # 新建议，将旧建议标记为失效
            cursor.execute("""
                UPDATE opening_logic_suggestions 
                SET is_active = 0, last_updated_at = ? 
                WHERE is_active = 1
            """, (current_time,))
            
            # 插入新建议
            first_appeared_at = current_time
            cursor.execute("""
                INSERT INTO opening_logic_suggestions 
                (suggestion_key, position_type, position_percent, position_level, 
                 first_appeared_at, last_updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (suggestion_key, position_type, position_percent, position_level, 
                  first_appeared_at, current_time))
        
        conn.commit()
        conn.close()
        
        # 计算首次开仓建议（30%）
        initial_position = int(position_percent * 0.3)
        
        return {
            'first_appeared_at': first_appeared_at,
            'initial_position_percent': initial_position,  # 首次开仓占建议总仓位的30%
            'suggestion_key': suggestion_key
        }
    except Exception as e:
        print(f"跟踪仓位建议失败: {e}")
        return {
            'first_appeared_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'initial_position_percent': int(position_info.get('position_percent', 0) * 0.3),
            'suggestion_key': f"{position_info.get('position_type', 'neutral')}_{position_info.get('position_percent', 0)}"
        }

def get_opening_suggestion() -> Dict:
    """
    获取开仓建议
    """
    # 计算趋势得分
    trend_score, score_details, raw_data = calculate_trend_score()
    
    # 检查限制条件
    can_long, can_short, restrictions = check_restrictions(raw_data)
    
    # 计算建议仓位
    position_info = calculate_position_size(raw_data, can_long, can_short)
    
    # 跟踪仓位建议，获取首次出现时间
    tracking_info = track_position_suggestion(position_info)
    
    # 将跟踪信息添加到仓位信息中
    position_info['first_appeared_at'] = tracking_info['first_appeared_at']
    position_info['initial_position_percent'] = tracking_info['initial_position_percent']
    position_info['suggestion_key'] = tracking_info['suggestion_key']
    
    # 判断趋势
    if trend_score >= 10:
        trend = '很强做多'
        trend_level = 'very_strong_long'
        color = '#00ff00'
    elif trend_score >= 5:
        trend = '较强做多'
        trend_level = 'strong_long'
        color = '#7fff00'
    elif trend_score >= 2:
        trend = '一般做多'
        trend_level = 'normal_long'
        color = '#90ee90'
    elif trend_score <= -10:
        trend = '很强做空'
        trend_level = 'very_strong_short'
        color = '#ff0000'
    elif trend_score <= -5:
        trend = '较强做空'
        trend_level = 'strong_short'
        color = '#ff4500'
    elif trend_score <= -2:
        trend = '一般做空'
        trend_level = 'normal_short'
        color = '#ff6347'
    else:
        trend = '震荡观望'
        trend_level = 'neutral'
        color = '#ffa500'
    
    # 生成开仓建议
    if trend_level in ['very_strong_long', 'strong_long', 'normal_long']:
        if can_long:
            suggestion = f'✅ 建议做多 ({trend})'
            suggestion_type = 'long'
        else:
            suggestion = f'⚠️ 趋势做多但受限制，观望为主'
            suggestion_type = 'restricted'
    elif trend_level in ['very_strong_short', 'strong_short', 'normal_short']:
        if can_short:
            suggestion = f'✅ 建议做空 ({trend})'
            suggestion_type = 'short'
        else:
            suggestion = f'⚠️ 趋势做空但受限制，观望为主'
            suggestion_type = 'restricted'
    else:
        suggestion = '⚠️ 震荡行情，建议观望'
        suggestion_type = 'neutral'
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'trend_score': trend_score,
        'trend': trend,
        'trend_level': trend_level,
        'color': color,
        'suggestion': suggestion,
        'suggestion_type': suggestion_type,
        'can_long': can_long,
        'can_short': can_short,
        'score_details': score_details,
        'restrictions': restrictions,
        'raw_data': raw_data,
        'position_info': position_info  # 包含首次出现时间和首次开仓建议
    }

if __name__ == '__main__':
    # 测试
    result = get_opening_suggestion()
    print(f"趋势得分: {result['trend_score']}")
    print(f"趋势判断: {result['trend']}")
    print(f"开仓建议: {result['suggestion']}")
    print(f"可以做多: {result['can_long']}")
    print(f"可以做空: {result['can_short']}")

