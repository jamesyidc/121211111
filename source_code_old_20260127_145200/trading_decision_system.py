#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点系统 - 自动交易决策系统
基于锚点系统的持仓监控数据，实现自动交易决策
"""

import sqlite3
import json
import time
from datetime import datetime
import pytz

# 配置
DB_PATH = '/home/user/webapp/trading_decision.db'
ANCHOR_DB_PATH = '/home/user/webapp/anchor_system.db'
CONFIG_PATH = '/home/user/webapp/trading_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 默认配置
DEFAULT_CONFIG = {
    "market_mode": "manual",  # manual（手动）/ auto（自动）
    "market_trend": "neutral",  # bullish（多头主导）/ bearish（空头主导）/ neutral（中性）
    "total_capital": 1000,  # 总本金（USDT）
    "position_limit_mode": "manual",  # manual（手动）/ auto（自动）
    "position_limit_percent": 60,  # 可开仓额百分比
    "anchor_capital_limit": 200,  # 锚点单资金上限（USDT）
    "anchor_capital_percent": 10,  # 锚点单资金百分比上限
    "allow_long": False,  # 是否允许开多单
    "allow_short": True,  # 是否允许开空单
    "allow_anchor": True,  # 是否允许开锚点单 ⭐
    "max_long_position": 500,  # 多单最大仓位（USDT）
    "max_short_position": 600,  # 空单最大仓位（USDT）
    "max_single_coin_percent": 10,  # 单个币种最大占比（%）⭐ 新增
    "min_granularity": 1,  # 最小颗粒度（%）
    "long_granularity": 10,  # 多单颗粒度（%）
    "enabled": False  # 是否启用自动交易
}


def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    # 1. 市场环境配置表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        market_mode TEXT NOT NULL,
        market_trend TEXT NOT NULL,
        total_capital REAL NOT NULL,
        position_limit_mode TEXT NOT NULL,
        position_limit_percent REAL NOT NULL,
        anchor_capital_limit REAL NOT NULL,
        anchor_capital_percent REAL NOT NULL,
        allow_long INTEGER NOT NULL DEFAULT 0,
        allow_short INTEGER NOT NULL DEFAULT 1,
        allow_anchor INTEGER NOT NULL DEFAULT 1,
        max_long_position REAL NOT NULL DEFAULT 500,
        max_short_position REAL NOT NULL DEFAULT 600,
        min_granularity REAL NOT NULL,
        long_granularity REAL NOT NULL,
        enabled INTEGER NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 2. 锚点单维护记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS anchor_maintenance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        original_size REAL NOT NULL,
        original_price REAL NOT NULL,
        maintenance_price REAL NOT NULL,
        maintenance_size REAL NOT NULL,
        profit_rate REAL NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 3. 交易决策记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trading_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        action TEXT NOT NULL,
        decision_type TEXT NOT NULL,
        current_size REAL NOT NULL,
        target_size REAL NOT NULL,
        close_size REAL NOT NULL,
        close_percent REAL NOT NULL,
        profit_rate REAL NOT NULL,
        current_price REAL NOT NULL,
        reason TEXT,
        executed INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 4. 开仓记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS position_opens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        open_price REAL NOT NULL,
        open_size REAL NOT NULL,
        open_percent REAL NOT NULL,
        granularity REAL NOT NULL,
        total_positions INTEGER NOT NULL,
        is_anchor INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 5. 补仓记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS position_adds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        add_price REAL NOT NULL,
        add_size REAL NOT NULL,
        add_percent REAL NOT NULL,
        profit_rate_trigger REAL NOT NULL,
        level INTEGER NOT NULL,
        total_size_after REAL NOT NULL,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 6. 挂单记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pending_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        order_type TEXT NOT NULL,
        anchor_price REAL NOT NULL,
        target_price REAL NOT NULL,
        price_diff_percent REAL NOT NULL,
        order_size REAL NOT NULL,
        status TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(inst_id, pos_side, order_type)
    )
    ''')
    
    # 7. 交易信号表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trading_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_type TEXT NOT NULL,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        action TEXT NOT NULL,
        price REAL NOT NULL,
        size REAL NOT NULL,
        reason TEXT,
        priority INTEGER NOT NULL,
        executed INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 8. 锚点单管理表 ⭐
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS anchor_positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        anchor_size REAL NOT NULL,
        anchor_price REAL NOT NULL,
        current_price REAL,
        profit_rate REAL,
        upl REAL,
        status TEXT NOT NULL,
        open_time TEXT NOT NULL,
        update_time TEXT,
        close_time TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(inst_id, pos_side, status)
    )
    ''')
    
    # 9. 模拟交易记录表 ⭐
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulated_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trade_type TEXT NOT NULL,
        inst_id TEXT NOT NULL,
        pos_side TEXT NOT NULL,
        action TEXT NOT NULL,
        order_side TEXT NOT NULL,
        price REAL NOT NULL,
        size REAL NOT NULL,
        amount REAL NOT NULL,
        reason TEXT,
        trigger_condition TEXT,
        profit_rate REAL,
        executed_at TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 交易决策系统数据库初始化完成（包含9张表）")


def load_config():
    """加载配置"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config):
    """保存配置"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("✅ 配置已保存")


def get_market_config():
    """获取市场配置"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM market_config ORDER BY updated_at DESC LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'market_mode': result[1],
            'market_trend': result[2],
            'total_capital': result[3],
            'position_limit_mode': result[4],
            'position_limit_percent': result[5],
            'anchor_capital_limit': result[6],
            'anchor_capital_percent': result[7],
            'allow_long': bool(result[8]),
            'min_granularity': result[9],
            'long_granularity': result[10],
            'enabled': bool(result[11]),
            'updated_at': result[12]
        }
    else:
        # 插入默认配置
        save_market_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_market_config(config):
    """保存市场配置"""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    cursor = conn.cursor()
    
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
    INSERT INTO market_config (
        market_mode, market_trend, total_capital, position_limit_mode,
        position_limit_percent, anchor_capital_limit, anchor_capital_percent,
        allow_long, allow_short, allow_anchor, max_long_position, max_short_position,
        min_granularity, long_granularity, enabled, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        config.get('market_mode', 'manual'),
        config.get('market_trend', 'neutral'),
        config.get('total_capital', 1000),
        config.get('position_limit_mode', 'manual'),
        config.get('position_limit_percent', 60),
        config.get('anchor_capital_limit', 200),
        config.get('anchor_capital_percent', 10),
        1 if config.get('allow_long', False) else 0,
        1 if config.get('allow_short', True) else 0,
        1 if config.get('allow_anchor', True) else 0,
        config.get('max_long_position', 500),
        config.get('max_short_position', 600),
        config.get('min_granularity', 1),
        config.get('long_granularity', 10),
        1 if config.get('enabled', False) else 0,
        timestamp
    ))
    
    conn.commit()
    conn.close()
    print("✅ 市场配置已保存到数据库")


if __name__ == '__main__':
    print("=" * 80)
    print("锚点系统 - 自动交易决策系统")
    print("=" * 80)
    
    # 初始化数据库
    init_database()
    
    # 加载配置
    config = load_config()
    print(f"\n当前配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
    
    # 保存到数据库
    save_market_config(config)
    
    print("\n✅ 系统初始化完成")
