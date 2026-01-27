"""
OKEx API 配置文件
包含 API 密钥和基本配置
"""

# OKEx API 凭据
OKEX_API_KEY = "0b05a729-40eb-4809-b3eb-eb2de75b7e9e"
OKEX_SECRET_KEY = "4E4DA8BE3B18D01AA07185A006BF9F8E"
OKEX_PASSPHRASE = "Tencent@123"

# API 端点
OKEX_REST_URL = "https://www.okx.com"
OKEX_WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKEX_WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"

# 配置
SIMULATED = False  # False = 实盘, True = 模拟盘

print("✅ OKEx API 配置文件已创建")
