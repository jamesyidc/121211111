"""
OKEx API 配置文件 - 子账户
用于子账户API密钥配置和管理
"""

# 子账户API凭证
OKEX_API_KEY = "8650e46c-059b-431d-93cf-55f8c79babdb"
OKEX_SECRET_KEY = "4C2BD2AC6A08615EA7F36A6251857FCE"
OKEX_PASSPHRASE = "Wu666666."

# API基础配置
OKEX_REST_URL = "https://www.okx.com"
OKEX_WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKEX_WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"

# 账户类型
ACCOUNT_TYPE = "sub_account"  # 子账户
SIMULATED = False  # 实盘模式

# 权限说明
PERMISSIONS = {
    "read": True,      # 读取权限
    "trade": False,    # 交易权限（子账户通常限制）
    "withdraw": False  # 提现权限（子账户通常限制）
}

print("✅ OKEx 子账户API配置文件已创建")
