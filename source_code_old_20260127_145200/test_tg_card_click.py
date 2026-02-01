import requests
import json

# 测试首页是否包含TG卡片
print("=" * 60)
print("1. 测试首页TG卡片是否存在")
print("=" * 60)

response = requests.get("http://localhost:5000/")
if "TG消息推送" in response.text and "telegram-dashboard" in response.text:
    print("✅ 首页TG卡片存在且链接正确")
else:
    print("❌ 首页TG卡片可能有问题")

# 测试TG Dashboard页面
print("\n" + "=" * 60)
print("2. 测试TG Dashboard页面")
print("=" * 60)

response = requests.get("http://localhost:5000/telegram-dashboard")
if response.status_code == 200:
    print(f"✅ TG Dashboard页面访问正常 (HTTP {response.status_code})")
    if "TG消息推送管理系统" in response.text:
        print("✅ 页面标题正确")
    if "@jamesyi9999_bot" in response.text:
        print("✅ Bot信息显示正确")
else:
    print(f"❌ TG Dashboard页面访问失败 (HTTP {response.status_code})")

# 测试API
print("\n" + "=" * 60)
print("3. 测试相关API接口")
print("=" * 60)

# 测试 /api/telegram/status
response = requests.get("http://localhost:5000/api/telegram/status")
if response.status_code == 200:
    data = response.json()
    print(f"✅ /api/telegram/status 正常")
    print(f"   运行状态: {data.get('is_running')}")
    print(f"   已推送: {data.get('total_sent')} 条")
    print(f"   最后更新: {data.get('last_update')}")
else:
    print(f"❌ /api/telegram/status 失败")

# 测试 /api/telegram/logs
response = requests.get("http://localhost:5000/api/telegram/logs")
if response.status_code == 200:
    data = response.json()
    print(f"✅ /api/telegram/logs 正常")
    print(f"   日志条数: {data.get('total_lines')}")
    print(f"   最近一条: {data['logs'][-1][:50]}..." if data.get('logs') else "")
else:
    print(f"❌ /api/telegram/logs 失败")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)
print(f"\n🌐 在线访问地址:")
print(f"   首页: https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/")
print(f"   TG管理页面: https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/telegram-dashboard")
