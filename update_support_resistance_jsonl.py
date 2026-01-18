#!/usr/bin/env python3
"""
支撑压力线系统 - JSONL 数据更新脚本
功能：从 OKX API 获取最新数据并更新到 JSONL 文件
时区：统一使用北京时间 (UTC+8)
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')

from support_resistance_jsonl_manager import SupportResistanceJSONLManager

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 监控的币种列表（27个）
SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT', 'SOLUSDT',
    'LTCUSDT', 'DOGEUSDT', 'SUIUSDT', 'TRXUSDT', 'TONUSDT',
    'ETCUSDT', 'BCHUSDT', 'HBARUSDT', 'XLMUSDT', 'FILUSDT',
    'LINKUSDT', 'CROUSDT', 'DOTUSDT', 'AAVEUSDT', 'UNIUSDT',
    'NEARUSDT', 'APTUSDT', 'CFXUSDT', 'CRVUSDT', 'STXUSDT',
    'LDOUSDT', 'TAOUSDT'
]

# OKX API 配置
OKX_API_BASE = 'https://www.okx.com'


def log(message: str):
    """打印日志"""
    beijing_now = datetime.now(BEIJING_TZ)
    timestamp = beijing_now.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def get_current_price(symbol: str) -> Optional[float]:
    """获取当前价格"""
    try:
        # 转换为 OKX 永续合约格式
        okx_symbol = f"{symbol[:-4]}-{symbol[-4:]}-SWAP"
        
        url = f"{OKX_API_BASE}/api/v5/market/ticker"
        params = {'instId': okx_symbol}
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            return float(data['data'][0]['last'])
        
        return None
        
    except Exception as e:
        log(f"  ❌ 获取 {symbol} 价格失败: {e}")
        return None


def get_baseline_price(manager: SupportResistanceJSONLManager, 
                       symbol: str, current_price: float) -> Dict:
    """
    获取或创建今日基准价格
    
    返回: {'baseline_price': float, 'price_change': float, 'change_percent': float}
    """
    beijing_now = datetime.now(BEIJING_TZ)
    today_date = beijing_now.strftime('%Y-%m-%d')
    
    # 查询今日基准价格
    baselines = manager.get_daily_baseline_prices(symbol=symbol, limit=10)
    
    baseline_price = None
    for record in baselines:
        baseline_date = record.get('baseline_date')
        if baseline_date and baseline_date.startswith(today_date):
            baseline_price = record.get('baseline_price')
            break
    
    if baseline_price is None:
        # 创建今日基准价格
        baseline_price = current_price
        baseline_record = {
            'symbol': symbol,
            'baseline_date': today_date,
            'baseline_price': baseline_price,
            'baseline_time': f"{today_date} 00:00:00",
            'baseline_time_beijing': f"{today_date} 00:00:00",
            'created_at': beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
            'created_at_beijing': beijing_now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        manager.append_record('daily_baseline_prices', baseline_record)
        log(f"  📌 创建今日基准价格: ${baseline_price:.4f}")
    
    # 计算涨跌
    price_change = current_price - baseline_price
    change_percent = (price_change / baseline_price * 100) if baseline_price > 0 else 0
    
    return {
        'baseline_price': baseline_price,
        'price_change': round(price_change, 4),
        'change_percent': round(change_percent, 2)
    }


def calculate_support_resistance(symbol: str, manager: SupportResistanceJSONLManager) -> Optional[Dict]:
    """
    计算支撑压力线
    
    返回完整的支撑压力线数据
    """
    try:
        # 1. 获取当前价格
        current_price = get_current_price(symbol)
        if not current_price:
            return None
        
        # 2. 转换币种格式
        okx_symbol = f"{symbol[:-4]}-{symbol[-4:]}-SWAP"
        
        # 3. 获取1周K线（最新1根）
        url_1w = f"{OKX_API_BASE}/api/v5/market/candles"
        params_1w = {'instId': okx_symbol, 'bar': '1W', 'limit': 1}
        
        response_1w = requests.get(url_1w, params=params_1w, timeout=10)
        data_1w = response_1w.json()
        
        if data_1w.get('code') != '0' or not data_1w.get('data'):
            log(f"  ⚠️  获取1周K线失败")
            return None
        
        kline_1w = data_1w['data'][0]
        historical_7d_high = float(kline_1w[2])
        historical_7d_low = float(kline_1w[3])
        
        # 4. 获取2天K线（最新1根）
        url_2d = f"{OKX_API_BASE}/api/v5/market/candles"
        params_2d = {'instId': okx_symbol, 'bar': '2D', 'limit': 1}
        
        response_2d = requests.get(url_2d, params=params_2d, timeout=10)
        data_2d = response_2d.json()
        
        if data_2d.get('code') != '0' or not data_2d.get('data'):
            log(f"  ⚠️  获取2天K线失败")
            return None
        
        kline_2d = data_2d['data'][0]
        historical_48h_high = float(kline_2d[2])
        historical_48h_low = float(kline_2d[3])
        
        # 5. 计算支撑压力线（包含当前价格，防止负值）
        support_line_1 = min(historical_7d_low, current_price)
        resistance_line_1 = max(historical_7d_high, current_price)
        support_line_2 = min(historical_48h_low, current_price)
        resistance_line_2 = max(historical_48h_high, current_price)
        
        # 6. 计算距离
        distance_to_support_1 = ((current_price - support_line_1) / current_price * 100) if current_price > 0 else 0
        distance_to_support_2 = ((current_price - support_line_2) / current_price * 100) if current_price > 0 else 0
        distance_to_resistance_1 = ((resistance_line_1 - current_price) / current_price * 100) if current_price > 0 else 0
        distance_to_resistance_2 = ((resistance_line_2 - current_price) / current_price * 100) if current_price > 0 else 0
        
        # 7. 计算位置百分比
        s1_r1_range = resistance_line_1 - support_line_1
        position_s1_r1 = ((current_price - support_line_1) / s1_r1_range * 100) if s1_r1_range > 0 else 0
        
        s2_r2_range = resistance_line_2 - support_line_2
        position_s1_r2 = ((current_price - support_line_2) / s2_r2_range * 100) if s2_r2_range > 0 else 0
        
        # 8. 获取基准价格
        baseline_info = get_baseline_price(manager, symbol, current_price)
        
        # 9. 构建记录
        beijing_now = datetime.now(BEIJING_TZ)
        record_time = beijing_now.strftime('%Y-%m-%d %H:%M:%S')
        
        record = {
            'symbol': symbol,
            'current_price': current_price,
            'support_line_1': support_line_1,
            'support_line_2': support_line_2,
            'resistance_line_1': resistance_line_1,
            'resistance_line_2': resistance_line_2,
            'support_1_days': 7,
            'support_2_hours': 48,
            'resistance_1_days': 7,
            'resistance_2_hours': 48,
            'distance_to_support_1': round(distance_to_support_1, 4),
            'distance_to_support_2': round(distance_to_support_2, 4),
            'distance_to_resistance_1': round(distance_to_resistance_1, 4),
            'distance_to_resistance_2': round(distance_to_resistance_2, 4),
            'record_time': record_time,
            'record_time_beijing': record_time,
            'position_s2_r1': round(position_s1_r1, 2),
            'position_s1_r2': round(position_s1_r2, 2),
            'position_s1_r2_upper': round(position_s1_r2, 2),
            'position_s1_r1': round(position_s1_r1, 2),
            'position_7d': round(position_s1_r1, 2),
            'position_48h': round(position_s1_r2, 2),
            'price_change_24h': baseline_info['price_change'],
            'change_percent_24h': baseline_info['change_percent'],
            'baseline_price_24h': baseline_info['baseline_price'],
            'alert_scenario_1': 0,
            'alert_scenario_2': 0,
            'alert_scenario_3': 0,
            'alert_scenario_4': 0,
            'alert_triggered': 0,
            'alert_7d_low': 0,
            'alert_7d_high': 0,
            'alert_48h_low': 0,
            'alert_48h_high': 0
        }
        
        return record
        
    except Exception as e:
        log(f"  ❌ 计算失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_symbol_data(symbol: str, manager: SupportResistanceJSONLManager) -> bool:
    """更新单个币种的数据"""
    try:
        log(f"📊 {symbol}")
        
        # 计算支撑压力线
        record = calculate_support_resistance(symbol, manager)
        
        if not record:
            log(f"  ❌ 数据获取失败")
            return False
        
        # 追加到 JSONL
        success = manager.append_record('support_resistance_levels', record)
        
        if success:
            log(f"  ✅ 价格: ${record['current_price']:.4f}")
            log(f"  ✅ 支撑1: ${record['support_line_1']:.4f} | 压力1: ${record['resistance_line_1']:.4f}")
            log(f"  ✅ 24H涨跌: {record['change_percent_24h']:.2f}%")
            log(f"  ✅ 记录时间: {record['record_time_beijing']} (北京时间)")
            return True
        else:
            log(f"  ❌ 写入失败")
            return False
        
    except Exception as e:
        log(f"  ❌ 更新失败: {e}")
        return False


def main():
    """主函数"""
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║     🔄 支撑压力线系统 - JSONL 数据更新                       ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    beijing_now = datetime.now(BEIJING_TZ)
    log(f"开始更新 | 时间: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    log(f"币种数量: {len(SYMBOLS)}")
    print()
    
    # 创建管理器
    manager = SupportResistanceJSONLManager()
    
    # 更新所有币种
    success_count = 0
    fail_count = 0
    
    for symbol in SYMBOLS:
        if update_symbol_data(symbol, manager):
            success_count += 1
        else:
            fail_count += 1
        
        print()  # 空行分隔
    
    # 汇总
    print("="*60)
    log("更新完成!")
    print("="*60)
    log(f"✅ 成功: {success_count}/{len(SYMBOLS)}")
    log(f"❌ 失败: {fail_count}")
    
    # 显示统计
    stats = manager.get_statistics()
    log(f"📊 总记录数: {stats['total_records']:,}")
    log(f"📊 support_resistance_levels: {stats['support_resistance_levels']:,} 条")
    
    print()
    print("🎉 更新完成！")
    print()


if __name__ == '__main__':
    main()
