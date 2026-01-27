import requests
import json

print("=" * 70)
print("FIL K线图修复 - 最终综合测试")
print("=" * 70)

base_url = "http://localhost:5000"
symbol = "FIL"

# 1. Test kline API
print("\n1️⃣  测试 Kline API")
print("-" * 70)
kline_resp = requests.get(f"{base_url}/api/symbol/{symbol}/kline?timeframe=5m")
kline_data = kline_resp.json()
print(f"   ✓ 状态码: {kline_resp.status_code}")
print(f"   ✓ 成功: {kline_data.get('success')}")
print(f"   ✓ 数据量: {len(kline_data.get('data', []))} 条")
kline_first = kline_data['data'][0] if kline_data.get('data') else {}
kline_last = kline_data['data'][-1] if kline_data.get('data') else {}
print(f"   ✓ 首条时间戳: {kline_first.get('timestamp')}")
print(f"   ✓ 末条时间戳: {kline_last.get('timestamp')}")

# 2. Test indicators API
print("\n2️⃣  测试 Indicators API")
print("-" * 70)
ind_resp = requests.get(f"{base_url}/api/symbol/{symbol}/indicators?timeframe=5m")
ind_data = ind_resp.json()
print(f"   ✓ 状态码: {ind_resp.status_code}")
print(f"   ✓ 成功: {ind_data.get('success')}")
print(f"   ✓ 数据量: {len(ind_data.get('data', []))} 条")
ind_first = ind_data['data'][0] if ind_data.get('data') else {}
ind_last = ind_data['data'][-1] if ind_data.get('data') else {}
print(f"   ✓ 首条时间戳: {ind_first.get('timestamp')}")
print(f"   ✓ 末条时间戳: {ind_last.get('timestamp')}")
print(f"   ✓ 包含字段: {', '.join(ind_first.keys())}")

# 3. Verify data alignment
print("\n3️⃣  验证数据对齐")
print("-" * 70)
kline_count = len(kline_data.get('data', []))
ind_count = len(ind_data.get('data', []))
print(f"   Kline 数据量: {kline_count}")
print(f"   Indicators 数据量: {ind_count}")
if kline_count == ind_count:
    print(f"   ✓ 数据量匹配")
else:
    print(f"   ✗ 数据量不匹配 (差值: {abs(kline_count - ind_count)})")

# Check timestamp alignment
if kline_first.get('timestamp') == ind_first.get('timestamp'):
    print(f"   ✓ 首条时间戳对齐")
else:
    print(f"   ✗ 首条时间戳不对齐")

if kline_last.get('timestamp') == ind_last.get('timestamp'):
    print(f"   ✓ 末条时间戳对齐")
else:
    print(f"   ✗ 末条时间戳不对齐")

# 4. Check page accessibility
print("\n4️⃣  测试页面可访问性")
print("-" * 70)
page_resp = requests.get(f"{base_url}/symbol/{symbol}")
print(f"   ✓ 状态码: {page_resp.status_code}")
if "FIL K线图" in page_resp.text:
    print(f"   ✓ 页面标题正确")
if "kline-chart" in page_resp.text:
    print(f"   ✓ 图表元素存在")

# 5. Summary
print("\n" + "=" * 70)
print("📊 测试总结")
print("=" * 70)
all_passed = (
    kline_resp.status_code == 200 and
    ind_resp.status_code == 200 and
    kline_count == ind_count and
    kline_first.get('timestamp') == ind_first.get('timestamp') and
    kline_last.get('timestamp') == ind_last.get('timestamp') and
    page_resp.status_code == 200
)

if all_passed:
    print("✅ 所有测试通过！FIL K线图已完全修复")
    print(f"✅ 数据量: {kline_count} 条（约 {kline_count / 288:.1f} 天的5分钟K线）")
    print("✅ 时间戳对齐正确")
    print("✅ 页面可正常访问")
else:
    print("⚠️  部分测试未通过，请检查具体项目")

print("=" * 70)
