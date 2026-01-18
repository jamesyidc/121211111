"""
币种选择和评分系统
根据多维度因子筛选和评分币种
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple

def get_db_connection(db_name: str = 'crypto_data.db'):
    """获取数据库连接"""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

def get_coin_pool() -> List[Dict]:
    """
    第一步：币种池筛选
    条件：
    1. V1V2 的币（ratio2 >= 100%，表示达到V1阈值）
    2. 只有急涨的币（rush_up > 0, rush_down = 0）
    3. 急涨大于急跌的币（rush_up > rush_down）
    4. 优先级 >= 4 的币
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最新时间的数据
        cursor.execute("""
            SELECT MAX(update_time) as latest_time
            FROM crypto_coin_data
        """)
        latest_time = cursor.fetchone()['latest_time']
        
        # 筛选符合条件的币种
        cursor.execute("""
            SELECT 
                symbol,
                rush_up,
                rush_down,
                priority_level,
                ratio1,
                ratio2,
                change_24h,
                current_price,
                update_time
            FROM crypto_coin_data
            WHERE update_time = ?
              AND ratio2 IS NOT NULL
              AND CAST(REPLACE(ratio2, '%', '') AS REAL) >= 100.0
              AND rush_up > rush_down
              AND (
                  priority_level LIKE '%4%' OR
                  priority_level LIKE '%5%' OR
                  priority_level LIKE '%6%' OR
                  priority_level LIKE '%7%' OR
                  priority_level LIKE '%8%' OR
                  priority_level LIKE '%9%'
              )
            ORDER BY rush_up DESC, CAST(REPLACE(ratio2, '%', '') AS REAL) DESC
        """, (latest_time,))
        
        coins = []
        for row in cursor.fetchall():
            coin = {
                'symbol': row['symbol'],
                'rush_up': row['rush_up'],
                'rush_down': row['rush_down'],
                'priority_level': row['priority_level'],
                'ratio1': row['ratio1'],
                'ratio2': row['ratio2'],
                'change_24h': row['change_24h'],
                'current_price': row['current_price'],
                'update_time': row['update_time']
            }
            coins.append(coin)
        
        conn.close()
        return coins
    except Exception as e:
        print(f"获取币种池失败: {e}")
        return []

def calculate_coin_score(symbol: str) -> Dict:
    """
    第二步：计算币种评分
    因子列表：
    1. 基础分
    2. 位置系统（position_system表）
    3. 空头/多头20以上（暂无数据）
    4. SAR象限（暂无数据）
    5. 布林带LB（暂无数据）
    6. RSI（暂无数据）
    7. 1分钟速涨速跌（暂无数据）
    8. V1V2成交量阈值
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        score = 0
        details = []
        
        # === 因子1：基础分 ===
        details.append("【基础筛选】通过 +0分")
        
        # === 因子2：位置系统 ===
        cursor.execute("""
            SELECT position_24h
            FROM position_system
            WHERE symbol = ? || '-USDT-SWAP'
            ORDER BY record_time DESC
            LIMIT 1
        """, (symbol,))
        
        pos_row = cursor.fetchone()
        if pos_row and pos_row['position_24h']:
            position = float(pos_row['position_24h'])
            if position < 1:
                score += 2
                details.append(f"【位置系统】24h位置{position:.1f}% < 1% → 做多 +2分")
            elif position < 5:
                score += 1
                details.append(f"【位置系统】24h位置{position:.1f}% < 5% → 做多 +1分")
            else:
                details.append(f"【位置系统】24h位置{position:.1f}% → +0分")
        else:
            details.append("【位置系统】无数据 → +0分")
        
        # === 因子8：V1V2成交量阈值 ===
        cursor.execute("""
            SELECT ratio1, ratio2
            FROM crypto_coin_data
            WHERE symbol = ?
            ORDER BY update_time DESC
            LIMIT 1
        """, (symbol,))
        
        ratio_row = cursor.fetchone()
        if ratio_row and ratio_row['ratio2']:
            ratio2_str = ratio_row['ratio2'].replace('%', '')
            ratio2 = float(ratio2_str) if ratio2_str else 0
            
            # 同时获取位置信息用于判断多空
            if pos_row and pos_row['position_24h']:
                position = float(pos_row['position_24h'])
                
                # V2阈值（ratio2 >= 200%）
                if ratio2 >= 200:
                    if position > 80:
                        score += 2
                        details.append(f"【V2成交量】ratio2={ratio2:.1f}% + 位置{position:.1f}% > 80% → 做空 +2分")
                    elif position < 20:
                        score += 2
                        details.append(f"【V2成交量】ratio2={ratio2:.1f}% + 位置{position:.1f}% < 20% → 做多 +2分")
                    else:
                        score += 2
                        details.append(f"【V2成交量】ratio2={ratio2:.1f}% 达到V2 +2分")
                
                # V1阈值（ratio2 >= 100%）
                elif ratio2 >= 100:
                    if position > 80:
                        score += 1
                        details.append(f"【V1成交量】ratio2={ratio2:.1f}% + 位置{position:.1f}% > 80% → 做空 +1分")
                    elif position < 20:
                        score += 1
                        details.append(f"【V1成交量】ratio2={ratio2:.1f}% + 位置{position:.1f}% < 20% → 做多 +1分")
                    else:
                        score += 1
                        details.append(f"【V1成交量】ratio2={ratio2:.1f}% 达到V1 +1分")
            else:
                details.append(f"【V1V2成交量】ratio2={ratio2:.1f}% → +0分（无位置数据）")
        else:
            details.append("【V1V2成交量】无数据 → +0分")
        
        # === 其他因子（暂无数据）===
        details.append("【因子3-7】暂无数据源 → +0分")
        
        conn.close()
        
        return {
            'symbol': symbol,
            'total_score': score,
            'details': details
        }
    
    except Exception as e:
        print(f"计算{symbol}评分失败: {e}")
        return {
            'symbol': symbol,
            'total_score': 0,
            'details': [f"评分计算失败: {e}"]
        }

def get_ranked_coins() -> List[Dict]:
    """
    获取排序后的币种列表
    返回：[(coin_data, score_data), ...]
    """
    # 第一步：获取币种池
    coin_pool = get_coin_pool()
    
    if not coin_pool:
        return []
    
    # 第二步：计算每个币的评分
    ranked_coins = []
    for coin in coin_pool:
        score_data = calculate_coin_score(coin['symbol'])
        ranked_coins.append({
            'coin_data': coin,
            'score_data': score_data
        })
    
    # 按评分排序
    ranked_coins.sort(key=lambda x: x['score_data']['total_score'], reverse=True)
    
    return ranked_coins

if __name__ == '__main__':
    # 测试
    print("=" * 70)
    print("🎯 币种选择和评分系统测试")
    print("=" * 70)
    
    # 获取币种池
    coin_pool = get_coin_pool()
    print(f"\n【币种池】筛选出 {len(coin_pool)} 个币种：")
    for coin in coin_pool[:5]:
        print(f"  {coin['symbol']:10s} 急涨={coin['rush_up']} 急跌={coin['rush_down']} 优先级={coin['priority_level']} ratio2={coin['ratio2']}")
    
    # 获取排序后的币种
    ranked_coins = get_ranked_coins()
    print(f"\n【评分排名】Top 5：")
    for i, item in enumerate(ranked_coins[:5], 1):
        coin = item['coin_data']
        score = item['score_data']
        print(f"\n{i}. {coin['symbol']} - 总分：{score['total_score']}分")
        for detail in score['details']:
            print(f"   {detail}")

