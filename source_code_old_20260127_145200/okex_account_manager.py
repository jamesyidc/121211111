"""
OKEx账户管理器
支持主账户和子账户之间的切换
"""

# 主账户配置
MAIN_ACCOUNT = {
    "api_key": "0b05a729-40eb-4809-b3eb-eb2de75b7e9e",
    "secret_key": "4E4DA8BE3B18D01AA07185A006BF9F8E",
    "passphrase": "Tencent@123",
    "account_type": "main",
    "name": "主账户",
    "permissions": ["read", "trade", "withdraw"]
}

# 子账户配置
SUB_ACCOUNT = {
    "api_key": "8650e46c-059b-431d-93cf-55f8c79babdb",
    "secret_key": "4C2BD2AC6A08615EA7F36A6251857FCE",
    "passphrase": "Wu666666.",
    "account_type": "sub",
    "name": "子账户",
    "permissions": ["read"]
}

# 默认使用主账户
ACTIVE_ACCOUNT = "main"  # 可选: "main" 或 "sub"

def get_active_account_config():
    """获取当前活跃账户配置"""
    if ACTIVE_ACCOUNT == "main":
        return MAIN_ACCOUNT
    else:
        return SUB_ACCOUNT

def switch_account(account_type):
    """切换账户
    Args:
        account_type: "main" 或 "sub"
    """
    global ACTIVE_ACCOUNT
    if account_type in ["main", "sub"]:
        ACTIVE_ACCOUNT = account_type
        account = get_active_account_config()
        print(f"✅ 已切换到{account['name']} ({account['api_key']})")
        return True
    else:
        print(f"❌ 无效的账户类型: {account_type}")
        return False

def get_account_info():
    """获取当前账户信息"""
    account = get_active_account_config()
    return {
        "name": account["name"],
        "type": account["account_type"],
        "api_key": account["api_key"],
        "permissions": account["permissions"]
    }

# API基础配置（所有账户共用）
OKEX_REST_URL = "https://www.okx.com"
OKEX_WS_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"
OKEX_WS_PRIVATE_URL = "wss://ws.okx.com:8443/ws/v5/private"
SIMULATED = False

if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("OKEx账户管理器")
    print("=" * 60)
    
    # 显示主账户信息
    switch_account("main")
    info = get_account_info()
    print(f"账户名称: {info['name']}")
    print(f"账户类型: {info['type']}")
    print(f"权限: {', '.join(info['permissions'])}")
    
    print("\n" + "-" * 60 + "\n")
    
    # 切换到子账户
    switch_account("sub")
    info = get_account_info()
    print(f"账户名称: {info['name']}")
    print(f"账户类型: {info['type']}")
    print(f"权限: {', '.join(info['permissions'])}")
    
    print("\n" + "=" * 60)

