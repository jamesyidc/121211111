#!/usr/bin/env python3
"""
得分系统 - 深度图评分计算模块
包含4个评分维度：
1. 价格深度得分 (Price Depth Score)
2. 交易信号得分 (Trading Signal Score)
3. 恐慌清洗得分 (Panic Wash Score)
4. 综合指数得分 (Composite Index Score)
"""

import sqlite3
from datetime import datetime, timedelta
import math
from typing import Dict, List, Tuple
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class ScoreCalculator:
    """得分计算器"""
    
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def calculate_price_depth_score(self, symbol: str, timeframe_hours: int = 24) -> Dict:
        """
        计算价格深度得分
        
        参数:
            symbol: 币种符号
            timeframe_hours: 时间范围（小时）
            
        返回:
            包含得分详情的字典
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取时间范围内的数据
        cutoff_time = (datetime.now(BEIJING_TZ) - timedelta(hours=timeframe_hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = """
        SELECT 
            symbol,
            change,
            rush_up,
            rush_down,
            high_price,
            decline,
            change_24h,
            current_price,
            priority_level,
            snapshot_time
        FROM crypto_coin_data
        WHERE symbol = ? AND snapshot_time >= ?
        ORDER BY snapshot_time DESC
        """
        
        cursor.execute(query, (symbol, cutoff_time))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                'symbol': symbol,
                'score': 0,
                'depth_level': 'N/A',
                'confidence': 0,
                'details': 'No data available'
            }
        
        # 计算各项指标
        total_records = len(rows)
        
        # 1. 价格波动深度 (40%)
        price_changes = [abs(row['change']) for row in rows if row['change']]
        avg_change = sum(price_changes) / len(price_changes) if price_changes else 0
        price_volatility_score = min(avg_change * 2, 40)  # 最高40分
        
        # 2. 急涨急跌频次 (30%)
        rush_up_count = sum(1 for row in rows if row['rush_up'] > 0)
        rush_down_count = sum(1 for row in rows if row['rush_down'] > 0)
        rush_frequency = (rush_up_count + rush_down_count) / total_records
        rush_score = min(rush_frequency * 100, 30)  # 最高30分
        
        # 3. 24小时涨跌幅 (20%)
        latest_change_24h = rows[0]['change_24h'] if rows[0]['change_24h'] else 0
        change_24h_score = min(abs(latest_change_24h), 20)  # 最高20分
        
        # 4. 价格新高/新低出现率 (10%)
        high_price_count = sum(1 for row in rows if row['high_price'] and row['high_price'] > 0)
        high_price_rate = high_price_count / total_records
        high_price_score = high_price_rate * 10  # 最高10分
        
        # 总分
        total_score = price_volatility_score + rush_score + change_24h_score + high_price_score
        
        # 深度等级
        if total_score >= 80:
            depth_level = '极深 (S级)'
            confidence = 95
        elif total_score >= 60:
            depth_level = '深 (A级)'
            confidence = 85
        elif total_score >= 40:
            depth_level = '中等 (B级)'
            confidence = 70
        elif total_score >= 20:
            depth_level = '浅 (C级)'
            confidence = 50
        else:
            depth_level = '极浅 (D级)'
            confidence = 30
        
        return {
            'symbol': symbol,
            'score': round(total_score, 2),
            'depth_level': depth_level,
            'confidence': confidence,
            'details': {
                'price_volatility': round(price_volatility_score, 2),
                'rush_frequency': round(rush_score, 2),
                'change_24h': round(change_24h_score, 2),
                'high_price': round(high_price_score, 2),
                'total_records': total_records,
                'timeframe': f'{timeframe_hours}h'
            }
        }
    
    def calculate_all_coins_depth_scores(self, timeframe_hours: int = 24, limit: int = 50) -> List[Dict]:
        """
        计算所有币种的深度得分
        
        参数:
            timeframe_hours: 时间范围（小时）
            limit: 返回币种数量限制
            
        返回:
            币种得分列表，按得分降序排列
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取活跃币种列表
        cutoff_time = (datetime.now(BEIJING_TZ) - timedelta(hours=timeframe_hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = """
        SELECT DISTINCT symbol
        FROM crypto_coin_data
        WHERE snapshot_time >= ?
        ORDER BY symbol
        LIMIT ?
        """
        
        cursor.execute(query, (cutoff_time, limit))
        symbols = [row['symbol'] for row in cursor.fetchall()]
        conn.close()
        
        # 计算每个币种的得分
        scores = []
        for symbol in symbols:
            score_data = self.calculate_price_depth_score(symbol, timeframe_hours)
            scores.append(score_data)
        
        # 按得分降序排序
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        return scores
    
    def calculate_average_market_score(self, timeframe_hours: int = 24) -> Dict:
        """
        计算市场平均得分
        
        参数:
            timeframe_hours: 时间范围（小时）
            
        返回:
            市场平均得分数据
        """
        all_scores = self.calculate_all_coins_depth_scores(timeframe_hours, limit=100)
        
        if not all_scores:
            return {
                'average_score': 0,
                'market_depth_level': 'N/A',
                'total_coins': 0,
                'score_distribution': {}
            }
        
        # 计算平均分
        total_score = sum(item['score'] for item in all_scores)
        average_score = total_score / len(all_scores)
        
        # 市场深度等级
        if average_score >= 60:
            market_depth_level = '极活跃'
        elif average_score >= 45:
            market_depth_level = '活跃'
        elif average_score >= 30:
            market_depth_level = '正常'
        elif average_score >= 15:
            market_depth_level = '平淡'
        else:
            market_depth_level = '沉闷'
        
        # 得分分布
        score_ranges = {
            'S级(80-100)': sum(1 for s in all_scores if s['score'] >= 80),
            'A级(60-79)': sum(1 for s in all_scores if 60 <= s['score'] < 80),
            'B级(40-59)': sum(1 for s in all_scores if 40 <= s['score'] < 60),
            'C级(20-39)': sum(1 for s in all_scores if 20 <= s['score'] < 40),
            'D级(0-19)': sum(1 for s in all_scores if s['score'] < 20),
        }
        
        return {
            'average_score': round(average_score, 2),
            'market_depth_level': market_depth_level,
            'total_coins': len(all_scores),
            'score_distribution': score_ranges,
            'top_10': all_scores[:10],
            'bottom_10': all_scores[-10:] if len(all_scores) >= 10 else all_scores,
            'timeframe': f'{timeframe_hours}h'
        }
    
    def calculate_okex_crypto_index(self) -> Dict:
        """
        计算OKEX加密货币综合指数
        
        返回:
            OKEX指数数据
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取最新快照数据
        query = """
        SELECT 
            rush_up,
            rush_down,
            ratio,
            count,
            round_rush_up,
            round_rush_down,
            snapshot_time
        FROM crypto_snapshots
        ORDER BY snapshot_time DESC
        LIMIT 1
        """
        
        cursor.execute(query)
        snapshot = cursor.fetchone()
        
        if not snapshot:
            conn.close()
            return {
                'index_value': 0,
                'trend': 'neutral',
                'strength': 0,
                'details': 'No data available'
            }
        
        # 获取24小时数据
        cutoff_time = (datetime.now(BEIJING_TZ) - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        
        query_24h = """
        SELECT 
            AVG(rush_up) as avg_rush_up,
            AVG(rush_down) as avg_rush_down,
            AVG(ratio) as avg_ratio,
            COUNT(*) as snapshot_count
        FROM crypto_snapshots
        WHERE snapshot_time >= ?
        """
        
        cursor.execute(query_24h, (cutoff_time,))
        stats_24h = cursor.fetchone()
        
        # 获取恐慌指数
        query_panic = """
        SELECT panic_index
        FROM panic_wash_index
        ORDER BY created_at DESC
        LIMIT 1
        """
        
        cursor.execute(query_panic)
        panic_data = cursor.fetchone()
        
        # 获取BTC的4个周期平均位置
        query_positions = """
        SELECT position_4h, position_12h, position_24h, position_48h
        FROM position_system
        WHERE symbol = 'BTC-USDT-SWAP'
        ORDER BY record_time DESC
        LIMIT 1
        """
        
        cursor.execute(query_positions)
        position_data = cursor.fetchone()
        
        conn.close()
        
        # 计算OKEX指数 (0-100分)
        # 1. 急涨急跌动能 (40%)
        rush_momentum = (snapshot['rush_up'] - snapshot['rush_down']) * 2
        momentum_score = min(max(rush_momentum + 20, 0), 40)
        
        # 2. 市场比值 (30%)
        ratio_score = min(abs(snapshot['ratio']) * 15, 30) if snapshot['ratio'] else 0
        
        # 3. 恐慌指数 (20%)
        panic_score = 0
        if panic_data and panic_data['panic_index']:
            panic_index = panic_data['panic_index']
            # 恐慌指数越高,得分越高
            panic_score = min(abs(panic_index) / 5, 20)
        
        # 4. 24小时平均活跃度 (10%)
        if stats_24h and stats_24h['avg_rush_up']:
            activity_score = min((stats_24h['avg_rush_up'] + stats_24h['avg_rush_down']) / 2, 10)
        else:
            activity_score = 0
        
        # 总指数
        index_value = momentum_score + ratio_score + panic_score + activity_score
        
        # 趋势判断
        if snapshot['rush_up'] > snapshot['rush_down'] * 1.5:
            trend = 'bullish'  # 牛市
            trend_cn = '牛市'
        elif snapshot['rush_down'] > snapshot['rush_up'] * 1.5:
            trend = 'bearish'  # 熊市
            trend_cn = '熊市'
        else:
            trend = 'neutral'  # 震荡
            trend_cn = '震荡'
        
        # 强度评级
        if index_value >= 75:
            strength = '极强'
        elif index_value >= 60:
            strength = '强'
        elif index_value >= 45:
            strength = '中等'
        elif index_value >= 30:
            strength = '弱'
        else:
            strength = '极弱'
        
        # 准备周期位置数据（格式化为前端期望的格式）
        averages = {}
        if position_data:
            averages = {
                '4h': round(position_data['position_4h'], 2) if position_data['position_4h'] else '--',
                '12h': round(position_data['position_12h'], 2) if position_data['position_12h'] else '--',
                '24h': round(position_data['position_24h'], 2) if position_data['position_24h'] else '--',
                '48h': round(position_data['position_48h'], 2) if position_data['position_48h'] else '--'
            }
        
        return {
            'index_value': round(index_value, 2),
            'trend': trend,
            'trend_cn': trend_cn,
            'strength': strength,
            'averages': averages,  # 添加4个周期的平均位置
            'details': {
                'momentum_score': round(momentum_score, 2),
                'ratio_score': round(ratio_score, 2),
                'panic_score': round(panic_score, 2),
                'activity_score': round(activity_score, 2),
                'rush_up': snapshot['rush_up'],
                'rush_down': snapshot['rush_down'],
                'ratio': snapshot['ratio'],
                'panic_index': panic_data['panic_index'] if panic_data else None,
                'snapshot_time': snapshot['snapshot_time']
            }
        }
    
    def get_depth_chart_data(self, timeframe_hours: int = 24, top_n: int = 20) -> Dict:
        """
        获取深度图表数据
        
        参数:
            timeframe_hours: 时间范围（小时）
            top_n: 返回Top N币种
            
        返回:
            图表数据
        """
        scores = self.calculate_all_coins_depth_scores(timeframe_hours, limit=top_n)
        
        return {
            'symbols': [s['symbol'] for s in scores],
            'scores': [s['score'] for s in scores],
            'depth_levels': [s['depth_level'] for s in scores],
            'confidences': [s['confidence'] for s in scores],
            'timeframe': f'{timeframe_hours}h',
            'total_count': len(scores)
        }


if __name__ == '__main__':
    # 测试代码
    calculator = ScoreCalculator()
    
    print("=== 测试深度图得分系统 ===\n")
    
    # 1. 测试单个币种得分
    print("1. 单个币种深度得分:")
    btc_score = calculator.calculate_price_depth_score('BTC', 24)
    print(f"   BTC 得分: {btc_score['score']}")
    print(f"   深度等级: {btc_score['depth_level']}")
    print(f"   置信度: {btc_score['confidence']}%")
    print()
    
    # 2. 测试所有币种得分
    print("2. 所有币种深度得分 (Top 10):")
    all_scores = calculator.calculate_all_coins_depth_scores(24, limit=50)
    for i, score in enumerate(all_scores[:10], 1):
        print(f"   {i}. {score['symbol']}: {score['score']} ({score['depth_level']})")
    print()
    
    # 3. 测试市场平均得分
    print("3. 市场平均得分:")
    market_score = calculator.calculate_average_market_score(24)
    print(f"   平均得分: {market_score['average_score']}")
    print(f"   市场深度: {market_score['market_depth_level']}")
    print(f"   总币种数: {market_score['total_coins']}")
    print(f"   得分分布: {market_score['score_distribution']}")
    print()
    
    # 4. 测试OKEX指数
    print("4. OKEX加密货币指数:")
    okex_index = calculator.calculate_okex_crypto_index()
    print(f"   指数值: {okex_index['index_value']}")
    print(f"   趋势: {okex_index['trend_cn']}")
    print(f"   强度: {okex_index['strength']}")
    print(f"   详情: {okex_index['details']}")
