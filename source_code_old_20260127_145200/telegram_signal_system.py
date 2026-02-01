#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram信号推送系统 - 三大块系统整合
1. 支撑压力线系统（抄底/逃顶）
2. 计次预警系统
3. 交易信号系统（买点1-4 + 卖点1 + 7日/48h高低点）
"""

import requests
import sqlite3
import time
import json
import logging
from datetime import datetime, timedelta
import pytz
import os

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_signal_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Telegram配置
TG_BOT_TOKEN = "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0"
TG_CHAT_ID = "-1003227444260"
TG_API_BASE = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"

# API基础URL
API_BASE = "http://localhost:5000"

# 数据库文件
DB_FILE = 'telegram_signals.db'

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 支撑压力线信号表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_resistance_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type TEXT NOT NULL,  -- 'buy' (抄底) 或 'sell' (逃顶)
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            signal_time TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, signal_type, signal_time)
        )
    ''')
    
    # 计次预警表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS count_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_time TEXT NOT NULL,
            count_value INTEGER NOT NULL,
            threshold INTEGER NOT NULL,
            full_data TEXT NOT NULL,  -- JSON格式完整数据
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_time)
        )
    ''')
    
    # 计次基准记录表（每小时整点记录）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS count_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hour_time TEXT NOT NULL,  -- 格式: YYYY-MM-DD HH:00:00
            count_value INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hour_time)
        )
    ''')
    
    # 交易信号表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_type TEXT NOT NULL,  -- buy_point_1/2/3/4, sell_point_1, day7_high/low, h48_high/low
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            signal_time TEXT NOT NULL,
            rsi REAL,
            additional_info TEXT,  -- JSON格式的额外信息
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, signal_type, signal_time)
        )
    ''')
    
    conn.commit()
    conn.close()
    logging.info("✅ 数据库初始化完成")


def send_telegram_message(text, parse_mode='HTML'):
    """发送Telegram消息"""
    try:
        url = f"{TG_API_BASE}/sendMessage"
        data = {
            'chat_id': TG_CHAT_ID,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logging.info(f"✅ TG消息发送成功: {text[:50]}...")
            return True
        else:
            logging.error(f"❌ TG消息发送失败: {result.get('description')}")
            return False
    
    except Exception as e:
        logging.error(f"❌ 发送TG消息异常: {e}")
        return False


# ==================== 1. 支撑压力线系统 ====================

def check_support_resistance_signals():
    """
    检查支撑压力线系统信号（抄底/逃顶）
    从 support-resistance 页面的API获取数据
    """
    try:
        # 获取支撑压力线最新信号
        url = f"{API_BASE}/api/support-resistance/latest-signal"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if not data.get('success'):
            return
        
        # 检查抄底信号（scenario_1）
        buy_signals = data.get('data', {}).get('scenario_1_coins', [])
        # 检查逃顶信号（scenario_2）
        sell_signals = data.get('data', {}).get('scenario_2_coins', [])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ)
        cutoff_time = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 处理抄底信号
        for signal in buy_signals:
            symbol = signal.get('symbol')
            signal_time = signal.get('signal_time', now.strftime('%Y-%m-%d %H:%M:%S'))
            
            # 检查是否在2小时内且未发送
            if signal_time >= cutoff_time:
                try:
                    cursor.execute('''
                        INSERT INTO support_resistance_signals 
                        (signal_type, symbol, price, signal_time)
                        VALUES (?, ?, ?, ?)
                    ''', ('buy', symbol, signal.get('price', 0), signal_time))
                    
                    conn.commit()
                    
                    # 发送TG消息
                    message = (
                        f"🔵 <b>【抄底信号】</b>\n\n"
                        f"币种: {symbol}\n"
                        f"价格: ${signal.get('price', 0):.4f}\n"
                        f"时间: {signal_time}\n"
                        f"类型: 支撑压力线 - 抄底\n\n"
                        f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/support-resistance'>查看详情</a>"
                    )
                    send_telegram_message(message)
                    
                except sqlite3.IntegrityError:
                    pass  # 已发送过
        
        # 处理逃顶信号
        for signal in sell_signals:
            symbol = signal.get('symbol')
            signal_time = signal.get('signal_time', now.strftime('%Y-%m-%d %H:%M:%S'))
            
            if signal_time >= cutoff_time:
                try:
                    cursor.execute('''
                        INSERT INTO support_resistance_signals 
                        (signal_type, symbol, price, signal_time)
                        VALUES (?, ?, ?, ?)
                    ''', ('sell', symbol, signal.get('price', 0), signal_time))
                    
                    conn.commit()
                    
                    # 发送TG消息
                    message = (
                        f"🔴 <b>【逃顶信号】</b>\n\n"
                        f"币种: {symbol}\n"
                        f"价格: ${signal.get('price', 0):.4f}\n"
                        f"时间: {signal_time}\n"
                        f"类型: 支撑压力线 - 逃顶\n\n"
                        f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/support-resistance'>查看详情</a>"
                    )
                    send_telegram_message(message)
                    
                except sqlite3.IntegrityError:
                    pass
        
        conn.close()
        logging.info(f"✅ 支撑压力线检查完成: 抄底 {len(buy_signals)}, 逃顶 {len(sell_signals)}")
        
    except Exception as e:
        logging.error(f"❌ 检查支撑压力线信号失败: {e}")


# ==================== 2. 计次预警系统 ====================

def check_count_alerts():
    """
    检查计次预警系统
    1. 每小时整点记录基准值
    2. 当前计次 >= 基准值+2 时触发预警
    """
    try:
        # 获取历史数据查询API
        url = f"{API_BASE}/api/query/latest"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if not data.get('success'):
            return
        
        query_data = data.get('data', {})
        current_count = query_data.get('计次', 0)
        record_time = query_data.get('运算时间', datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'))
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ)
        current_hour = now.strftime('%Y-%m-%d %H:00:00')
        
        # 检查是否在整点（±2分钟内）
        minute = now.minute
        if minute <= 2 or minute >= 58:
            # 记录基准值
            try:
                cursor.execute('''
                    INSERT INTO count_baselines (hour_time, count_value)
                    VALUES (?, ?)
                ''', (current_hour, current_count))
                conn.commit()
                logging.info(f"✅ 记录整点基准值: {current_hour} = {current_count}次")
            except sqlite3.IntegrityError:
                pass  # 已记录过
        
        # 获取当前小时的基准值
        cursor.execute('''
            SELECT count_value FROM count_baselines
            WHERE hour_time = ?
        ''', (current_hour,))
        
        row = cursor.fetchone()
        if row:
            baseline_count = row[0]
            threshold = baseline_count + 2
            
            # 检查是否触发预警
            if current_count >= threshold:
                try:
                    full_data_json = json.dumps(query_data, ensure_ascii=False)
                    cursor.execute('''
                        INSERT INTO count_alerts 
                        (record_time, count_value, threshold, full_data)
                        VALUES (?, ?, ?, ?)
                    ''', (record_time, current_count, threshold, full_data_json))
                    
                    conn.commit()
                    
                    # 发送TG预警
                    message = (
                        f"⚠️ <b>【计次预警】</b>\n\n"
                        f"运算时间: {record_time}\n"
                        f"当前计次: {current_count}\n"
                        f"基准值: {baseline_count}\n"
                        f"阈值: {threshold}\n\n"
                        f"<b>完整数据:</b>\n"
                        f"急涨: {query_data.get('急涨', 0)}\n"
                        f"急跌: {query_data.get('急跌', 0)}\n"
                        f"本轮急涨: {query_data.get('本轮急涨', 0)}\n"
                        f"本轮急跌: {query_data.get('本轮急跌', 0)}\n"
                        f"计次得分: {query_data.get('计次得分', 'N/A')}\n"
                        f"状态: {query_data.get('状态', 'N/A')}\n"
                        f"差值: {query_data.get('差值', 0)}\n"
                        f"比价最低: {query_data.get('比价最低', 0)}\n"
                        f"比价创新高: {query_data.get('比价创新高', 0)}\n"
                        f"24h涨≥10%: {query_data.get('24h涨≥10%', 0)}\n"
                        f"24h跌≤-10%: {query_data.get('24h跌≤-10%', 0)}\n\n"
                        f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/query'>查看详情</a>"
                    )
                    send_telegram_message(message)
                    logging.info(f"✅ 触发计次预警: {current_count} >= {threshold}")
                    
                except sqlite3.IntegrityError:
                    pass  # 已发送过
        
        conn.close()
        
    except Exception as e:
        logging.error(f"❌ 检查计次预警失败: {e}")


# ==================== 3. 交易信号系统 ====================

def check_trading_signals():
    """
    检查交易信号系统
    包括: 买点1-4, 卖点1, 7日高低点, 48h高低点
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        now = datetime.now(BEIJING_TZ)
        cutoff_time = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 检查买点1-3 (trading-signals)
        url = f"{API_BASE}/api/trading-signals/analyze"
        response = requests.get(url, timeout=10)  # 增加超时时间，因为此API查询复杂
        data = response.json()
        
        if data.get('success'):
            signals = data.get('signals', [])
            
            for signal in signals:
                if signal.get('signal_time', '') >= cutoff_time:
                    signal_type = signal.get('signal_type', '')
                    symbol = signal.get('symbol', '')
                    
                    # 只处理买点1-3
                    if signal_type in ['buy_point_1', 'buy_point_2', 'buy_point_3']:
                        try:
                            cursor.execute('''
                                INSERT INTO trading_signals 
                                (signal_type, symbol, price, signal_time, rsi, additional_info)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                signal_type, 
                                symbol, 
                                signal.get('price', 0),
                                signal.get('signal_time', ''),
                                signal.get('rsi', None),
                                json.dumps(signal, ensure_ascii=False)
                            ))
                            
                            conn.commit()
                            
                            # 发送TG消息
                            signal_name = {
                                'buy_point_1': '买点1',
                                'buy_point_2': '买点2',
                                'buy_point_3': '买点3'
                            }.get(signal_type, signal_type)
                            
                            message = (
                                f"🟢 <b>【{signal_name}】</b>\n\n"
                                f"币种: {symbol}\n"
                                f"价格: ${signal.get('price', 0):.4f}\n"
                                f"时间: {signal.get('signal_time', '')}\n"
                                f"RSI: {signal.get('rsi', 'N/A')}\n\n"
                                f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/trading-signals'>查看详情</a>"
                            )
                            send_telegram_message(message)
                            
                        except sqlite3.IntegrityError:
                            pass
        
        # 2. 检查买点4, 卖点1, 7日/48h高低点 (kline-indicators)
        url = f"{API_BASE}/api/kline-indicators/signals"
        response = requests.get(url, timeout=10)  # 增加超时时间以保持一致性
        data = response.json()
        
        if data.get('success'):
            signals_data = data.get('data', {}).get('signals', {})
            
            # 买点4
            for signal in signals_data.get('buy_point_4', []):
                try:
                    cursor.execute('''
                        INSERT INTO trading_signals 
                        (signal_type, symbol, price, signal_time, rsi, additional_info)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        'buy_point_4',
                        signal.get('symbol', ''),
                        signal.get('price', 0),
                        signal.get('confirm_time', ''),
                        signal.get('confirm_rsi', None),
                        json.dumps(signal, ensure_ascii=False)
                    ))
                    
                    conn.commit()
                    
                    message = (
                        f"🟢 <b>【买点4】</b>\n\n"
                        f"币种: {signal.get('symbol', '')}\n"
                        f"价格: ${signal.get('price', 0):.4f}\n"
                        f"时间: {signal.get('confirm_time', '')}\n"
                        f"RSI: {signal.get('confirm_rsi', 'N/A')}\n"
                        f"7日低点: ${signal.get('low_7d', 0):.4f}\n\n"
                        f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/kline-indicators'>查看详情</a>"
                    )
                    send_telegram_message(message)
                    
                except sqlite3.IntegrityError:
                    pass
            
            # 卖点1
            for signal in signals_data.get('sell_point_1', []):
                try:
                    cursor.execute('''
                        INSERT INTO trading_signals 
                        (signal_type, symbol, price, signal_time, rsi, additional_info)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        'sell_point_1',
                        signal.get('symbol', ''),
                        signal.get('mark_price', 0),
                        signal.get('mark_time', ''),
                        signal.get('mark_rsi', None),
                        json.dumps(signal, ensure_ascii=False)
                    ))
                    
                    conn.commit()
                    
                    message = (
                        f"🔴 <b>【卖点1】</b>\n\n"
                        f"币种: {signal.get('symbol', '')}\n"
                        f"价格: ${signal.get('mark_price', 0):.4f}\n"
                        f"时间: {signal.get('mark_time', '')}\n"
                        f"RSI: {signal.get('mark_rsi', 'N/A')}\n"
                        f"高点: ${signal.get('high_price', 0):.4f}\n\n"
                        f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/kline-indicators'>查看详情</a>"
                    )
                    send_telegram_message(message)
                    
                except sqlite3.IntegrityError:
                    pass
            
            # 7日最高点/最低点
            for signal_type in ['day7_high', 'day7_low']:
                for signal in signals_data.get(signal_type, []):
                    try:
                        cursor.execute('''
                            INSERT INTO trading_signals 
                            (signal_type, symbol, price, signal_time, rsi, additional_info)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            signal_type,
                            signal.get('symbol', ''),
                            signal.get('price', 0),
                            signal.get('time', ''),
                            None,
                            json.dumps(signal, ensure_ascii=False)
                        ))
                        
                        conn.commit()
                        
                        signal_name = '7日最高点' if signal_type == 'day7_high' else '7日最低点'
                        icon = '📈' if signal_type == 'day7_high' else '📉'
                        
                        message = (
                            f"{icon} <b>【{signal_name}】</b>\n\n"
                            f"币种: {signal.get('symbol', '')}\n"
                            f"价格: ${signal.get('price', 0):.4f}\n"
                            f"时间: {signal.get('time', '')}\n\n"
                            f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/kline-indicators'>查看详情</a>"
                        )
                        send_telegram_message(message)
                        
                    except sqlite3.IntegrityError:
                        pass
            
            # 48h最高点/最低点
            for signal_type in ['h48_high', 'h48_low']:
                for signal in signals_data.get(signal_type, []):
                    try:
                        cursor.execute('''
                            INSERT INTO trading_signals 
                            (signal_type, symbol, price, signal_time, rsi, additional_info)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            signal_type,
                            signal.get('symbol', ''),
                            signal.get('price', 0),
                            signal.get('time', ''),
                            None,
                            json.dumps(signal, ensure_ascii=False)
                        ))
                        
                        conn.commit()
                        
                        signal_name = '48h最高点' if signal_type == 'h48_high' else '48h最低点'
                        icon = '📈' if signal_type == 'h48_high' else '📉'
                        
                        message = (
                            f"{icon} <b>【{signal_name}】</b>\n\n"
                            f"币种: {signal.get('symbol', '')}\n"
                            f"价格: ${signal.get('price', 0):.4f}\n"
                            f"时间: {signal.get('time', '')}\n\n"
                            f"<a href='https://5000-iz6uddj6rs3xe48ilsyqq-cbeee0f9.sandbox.novita.ai/kline-indicators'>查看详情</a>"
                        )
                        send_telegram_message(message)
                        
                    except sqlite3.IntegrityError:
                        pass
        
        conn.close()
        logging.info("✅ 交易信号检查完成")
        
    except Exception as e:
        logging.error(f"❌ 检查交易信号失败: {e}")


# ==================== 主循环 ====================

def main():
    """主循环 - 每1分钟检查一次所有信号"""
    logging.info("=" * 60)
    logging.info("🚀 Telegram信号推送系统启动")
    logging.info("=" * 60)
    
    # 初始化数据库
    init_database()
    
    # 发送启动消息
    start_message = (
        f"🤖 <b>【系统启动】</b>\n\n"
        f"Telegram信号推送系统已启动\n"
        f"监控间隔: 1分钟\n"
        f"启动时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"监控模块:\n"
        f"1️⃣ 支撑压力线系统 (抄底/逃顶)\n"
        f"2️⃣ 计次预警系统\n"
        f"3️⃣ 交易信号系统 (买点1-4 + 卖点1 + 7日/48h高低点)\n"
    )
    send_telegram_message(start_message)
    
    while True:
        try:
            now = datetime.now(BEIJING_TZ)
            logging.info(f"\n⏰ 开始检查信号 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 1. 检查支撑压力线信号
            check_support_resistance_signals()
            
            # 2. 检查计次预警
            check_count_alerts()
            
            # 3. 检查交易信号
            check_trading_signals()
            
            logging.info(f"✅ 本轮检查完成，等待60秒...\n")
            time.sleep(60)
            
        except KeyboardInterrupt:
            logging.info("⚠️ 收到停止信号，正在退出...")
            break
        except Exception as e:
            logging.error(f"❌ 主循环异常: {e}")
            time.sleep(60)


if __name__ == '__main__':
    main()
