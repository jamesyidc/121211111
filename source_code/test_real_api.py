#!/usr/bin/env python3
import hmac
import base64
import requests
from datetime import datetime, timezone

api_key = "77465009-2c87-443c-83c8-08b35c7f14b2"
secret_key = "11647B2578630D28501D41C748B3D809"
passphrase = "Tencent@123"
base_url = "https://www.okx.com"

def get_signature(timestamp, method, request_path, body=''):
    message = timestamp + method + request_path + body
    mac = hmac.new(
        bytes(secret_key, encoding='utf8'),
        bytes(message, encoding='utf-8'),
        digestmod='sha256'
    )
    d = mac.digest()
    return base64.b64encode(d).decode()

# 测试1: 获取账户余额
print("=" * 60)
print("测试1: 获取账户余额")
print("=" * 60)

method = 'GET'
request_path = '/api/v5/account/balance'
timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
signature = get_signature(timestamp, method, request_path)

headers = {
    'OK-ACCESS-KEY': api_key,
    'OK-ACCESS-SIGN': signature,
    'OK-ACCESS-TIMESTAMP': timestamp,
    'OK-ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json'
}

try:
    response = requests.get(base_url + request_path, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    data = response.json()
    if data.get('code') == '0':
        print("✅ 账户连接成功！")
        balance_data = data.get('data', [])
        if balance_data:
            print(f"账户数据: {len(balance_data)} 个资产账户")
    else:
        print(f"❌ 错误: {data.get('msg')} (code: {data.get('code')})")
except Exception as e:
    print(f"❌ 异常: {e}")

# 测试2: 获取持仓信息
print("\n" + "=" * 60)
print("测试2: 获取持仓信息")
print("=" * 60)

method = 'GET'
request_path = '/api/v5/account/positions'
timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
signature = get_signature(timestamp, method, request_path)

headers = {
    'OK-ACCESS-KEY': api_key,
    'OK-ACCESS-SIGN': signature,
    'OK-ACCESS-TIMESTAMP': timestamp,
    'OK-ACCESS-PASSPHRASE': passphrase,
    'Content-Type': 'application/json'
}

try:
    response = requests.get(base_url + request_path, headers=headers, timeout=10)
    print(f"状态码: {response.status_code}")
    data = response.json()
    if data.get('code') == '0':
        positions = data.get('data', [])
        # 过滤出有持仓的
        active_positions = [pos for pos in positions if float(pos.get('pos', 0)) != 0]
        
        print(f"✅ 持仓数据获取成功！")
        print(f"总持仓数: {len(active_positions)}")
        
        if active_positions:
            print("\n当前持仓:")
            for i, pos in enumerate(active_positions, 1):
                inst_id = pos.get('instId')
                pos_side = pos.get('posSide')
                pos_size = float(pos.get('pos', 0))
                avg_px = float(pos.get('avgPx', 0))
                mark_px = float(pos.get('markPx', 0))
                upl = float(pos.get('upl', 0))
                margin = float(pos.get('margin', 0))
                lever = float(pos.get('lever', 0))
                
                # 计算收益率
                if margin > 0:
                    profit_rate = (upl / margin) * 100
                else:
                    profit_rate = 0
                
                print(f"\n  【持仓 {i}】")
                print(f"    币种: {inst_id}")
                print(f"    方向: {pos_side} ({'做空' if pos_side == 'short' else '做多'})")
                print(f"    持仓量: {abs(pos_size)}")
                print(f"    杠杆: {lever}x")
                print(f"    开仓均价: ${avg_px:.4f}")
                print(f"    标记价格: ${mark_px:.4f}")
                print(f"    未实现盈亏: ${upl:.2f} USDT")
                print(f"    保证金: ${margin:.2f} USDT")
                print(f"    收益率: {profit_rate:+.2f}%")
        else:
            print("\n📝 当前无持仓")
    else:
        print(f"❌ 错误: {data.get('msg')} (code: {data.get('code')})")
except Exception as e:
    print(f"❌ 异常: {e}")

print("\n" + "=" * 60)
