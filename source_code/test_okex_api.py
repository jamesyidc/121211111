#!/usr/bin/env python3
import hmac
import base64
import requests
from datetime import datetime, timezone

api_key = "86cd5cc2-d87a-49f4-97fb-d02a78835be1"
secret_key = "B7FE5AB683B648E266689F3E9B2DC79E"
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

# 测试账户信息
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

print(f"测试OKEx API: {base_url}{request_path}")
print(f"Timestamp: {timestamp}")
print(f"Headers: {headers}\n")

try:
    response = requests.get(base_url + request_path, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
