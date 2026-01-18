"""
交易对保护系统
功能：监控主账户的交易对数量，自动补仓缺失的交易对
"""

import sys
import time
import json
import sqlite3
import requests
import hmac
import base64
import hashlib
import threading
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.append('/home/user/webapp')
from source_code.okex_api_config import OKEX_API_KEY, OKEX_SECRET_KEY, OKEX_PASSPHRASE

# 配置
OKEX_BASE_URL = "https://www.okx.com"
DB_PATH = "/home/user/webapp/databases/trading_decision.db"
PROTECTION_DB_PATH = "/home/user/webapp/databases/pair_protection.db"
CHECK_INTERVAL = 60  # 检查间隔（秒）
DEFAULT_MARGIN = 1.0  # 默认保证金1 USDT

# 保护状态
protection_enabled = False
protected_pairs = set()
protection_thread = None
last_check_time = None
fill_count = 0  # 自动补仓次数
current_position_count = 0  # 当前持仓数
missing_pairs_list = []  # 缺失的交易对列表

def init_protection_db():
    """初始化保护数据库"""
    conn = sqlite3.connect(PROTECTION_DB_PATH)
    cursor = conn.cursor()
    
    # 创建受保护交易对表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS protected_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT UNIQUE NOT NULL,
            pos_side TEXT NOT NULL,
            initial_count INTEGER DEFAULT 0,
            last_check_time TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建补仓记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS protection_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT NOT NULL,
            pos_side TEXT NOT NULL,
            action_type TEXT NOT NULL,
            margin_amount REAL,
            size REAL,
            price REAL,
            reason TEXT,
            status TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ 保护数据库初始化完成")

def get_signature(secret_key, timestamp, method, request_path, body=''):
    """生成OKEx API签名"""
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(secret_key, encoding='utf8'),
        bytes(message, encoding='utf8'),
        digestmod=hashlib.sha256
    )
    return base64.b64encode(mac.digest()).decode()

def get_headers(method, request_path, body=''):
    """获取API请求头"""
    timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    signature = get_signature(OKEX_SECRET_KEY, timestamp, method, request_path, body)
    
    return {
        'OK-ACCESS-KEY': OKEX_API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': OKEX_PASSPHRASE,
        'Content-Type': 'application/json'
    }

def get_current_positions():
    """获取当前OKEx持仓"""
    try:
        method = 'GET'
        request_path = '/api/v5/account/positions'
        headers = get_headers(method, request_path)
        
        response = requests.get(OKEX_BASE_URL + request_path, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('code') == '0':
            positions = data.get('data', [])
            # 只返回非零持仓
            return [p for p in positions if float(p.get('pos', 0)) != 0]
        else:
            print(f"❌ 获取持仓失败: {data.get('msg')}")
            return []
    except Exception as e:
        print(f"❌ 获取持仓异常: {e}")
        return []

def save_protected_pairs(positions):
    """保存当前需要保护的交易对"""
    conn = sqlite3.connect(PROTECTION_DB_PATH)
    cursor = conn.cursor()
    
    # 提取交易对
    current_pairs = set()
    for pos in positions:
        inst_id = pos.get('instId')
        pos_side = pos.get('posSide')
        if inst_id and pos_side:
            pair_key = f"{inst_id}_{pos_side}"
            current_pairs.add(pair_key)
            
            # 插入或更新
            cursor.execute('''
                INSERT INTO protected_pairs (inst_id, pos_side, initial_count, last_check_time, status)
                VALUES (?, ?, 1, ?, 'active')
                ON CONFLICT(inst_id) DO UPDATE SET
                    last_check_time = ?,
                    status = 'active'
            ''', (inst_id, pos_side, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    global protected_pairs
    protected_pairs = current_pairs
    
    print(f"✅ 已保存 {len(current_pairs)} 个受保护的交易对")
    return current_pairs

def get_protected_pairs():
    """获取受保护的交易对列表"""
    conn = sqlite3.connect(PROTECTION_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT inst_id, pos_side FROM protected_pairs WHERE status = 'active'
    ''')
    
    pairs = set()
    for row in cursor.fetchall():
        pair_key = f"{row[0]}_{row[1]}"
        pairs.add(pair_key)
    
    conn.close()
    return pairs

def place_order(inst_id, side, size, margin):
    """下单补仓（模拟）"""
    # 这里是模拟下单，实际生产环境需要真实调用OKEx API
    print(f"📝 模拟下单: {inst_id} {side} 数量: {size} 保证金: {margin} USDT")
    
    # 记录补仓动作
    conn = sqlite3.connect(PROTECTION_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO protection_actions 
        (inst_id, pos_side, action_type, margin_amount, size, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (inst_id, side, 'auto_replenish', margin, size, '交易对缺失自动补仓', 'simulated'))
    
    conn.commit()
    conn.close()
    
    return True

def check_and_protect():
    """检查并保护交易对"""
    global last_check_time, fill_count, current_position_count, missing_pairs_list
    
    if not protection_enabled:
        return
    
    print(f"\n{'='*60}")
    print(f"🔍 开始检查交易对 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 获取当前持仓
    current_positions = get_current_positions()
    current_pairs = set()
    
    for pos in current_positions:
        inst_id = pos.get('instId')
        pos_side = pos.get('posSide')
        if inst_id and pos_side:
            pair_key = f"{inst_id}_{pos_side}"
            current_pairs.add(pair_key)
    
    current_position_count = len(current_pairs)
    last_check_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"📊 当前持仓交易对数量: {current_position_count}")
    print(f"🛡️  受保护交易对数量: {len(protected_pairs)}")
    
    # 检查缺失的交易对
    missing_pairs = protected_pairs - current_pairs
    missing_pairs_list = list(missing_pairs)
    
    if missing_pairs:
        print(f"\n⚠️  发现 {len(missing_pairs)} 个交易对缺失！")
        print(f"{'='*60}")
        
        for pair_key in missing_pairs:
            inst_id, pos_side = pair_key.split('_')
            print(f"\n❌ 缺失: {inst_id} {pos_side}")
            print(f"   正在补仓...")
            
            # 计算补仓数量（基于1 USDT保证金）
            # 这里简化处理，实际需要根据合约面值计算
            replenish_size = 0.01  # 示例：0.01张合约
            
            # 执行补仓
            success = place_order(inst_id, pos_side, replenish_size, DEFAULT_MARGIN)
            
            if success:
                fill_count += 1
                print(f"   ✅ 补仓成功: {inst_id} {pos_side} 保证金: {DEFAULT_MARGIN} USDT")
            else:
                print(f"   ❌ 补仓失败: {inst_id} {pos_side}")
    else:
        print(f"✅ 所有交易对正常，无需补仓")
    
    print(f"{'='*60}\n")

def start_protection():
    """启动保护"""
    global protection_enabled, protection_thread, fill_count
    
    if protection_enabled:
        print("⚠️  保护系统已在运行中")
        return True
    
    print("="*60)
    print("🛡️  交易对保护系统启动")
    print("="*60)
    
    # 初始化数据库
    init_protection_db()
    
    # 获取并保存当前交易对
    positions = get_current_positions()
    if not positions:
        print("❌ 无法获取持仓，保护系统启动失败")
        return False
    
    save_protected_pairs(positions)
    protection_enabled = True
    fill_count = 0  # 重置补仓计数
    
    # 启动后台线程
    protection_thread = threading.Thread(target=protection_loop, daemon=True)
    protection_thread.start()
    
    print(f"✅ 保护系统已启动")
    print(f"📊 初始交易对数量: {len(protected_pairs)}")
    print(f"⏰ 检查间隔: {CHECK_INTERVAL} 秒")
    print("="*60)
    
    return True

def stop_protection():
    """停止保护"""
    global protection_enabled
    protection_enabled = False
    print("\n⏸️  保护系统已停止")

def protection_loop():
    """后台保护循环"""
    while protection_enabled:
        try:
            check_and_protect()
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            print(f"❌ 保护循环错误: {e}")
            time.sleep(CHECK_INTERVAL)

def get_protection_status():
    """获取保护状态"""
    return {
        'is_running': protection_enabled,
        'protected_count': len(protected_pairs),
        'current_count': current_position_count,
        'check_interval': CHECK_INTERVAL,
        'last_check': last_check_time,
        'fill_count': fill_count,
        'missing_pairs': missing_pairs_list
    }

def run_protection_loop():
    """运行保护循环（用于测试）"""
    if not start_protection():
        return
    
    try:
        while protection_enabled:
            check_and_protect()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n⏸️  收到停止信号")
        stop_protection()

if __name__ == "__main__":
    print("="*60)
    print("🛡️  交易对保护系统 - 测试模式")
    print("="*60)
    
    # 测试启动保护
    if start_protection():
        print("\n按 Ctrl+C 停止测试\n")
        run_protection_loop()

