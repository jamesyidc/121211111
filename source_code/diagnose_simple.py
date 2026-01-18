#!/usr/bin/env python3
import requests
import json
import re

# 获取页面HTML
response = requests.get('http://localhost:5000/symbol/UNI/v6')
html = response.text

# 提取JavaScript代码中的RSI过滤逻辑
print("=" * 80)
print("正在检查RSI过滤逻辑...")
print("=" * 80)

# 查找RSI过滤的代码段
rsi_pattern = re.compile(r'// 🔥 新增条件4：RSI过滤.*?(?=//|const)', re.DOTALL)
match = rsi_pattern.search(html)

if match:
    rsi_code = match.group(0)
    print("\n找到RSI过滤代码:")
    print("-" * 80)
    print(rsi_code[:500])  # 打印前500字符
    print("-" * 80)
else:
    print("\n❌ 未找到RSI过滤代码!")

# 检查是否有debug日志
if '[RSI检查]' in html:
    print("\n✅ 找到RSI检查日志")
else:
    print("\n❌ 未找到RSI检查日志")

if '[卖点1过滤]' in html:
    print("✅ 找到卖点1过滤日志")
else:
    print("❌ 未找到卖点1过滤日志")

# 检查是否有版本标识
version_pattern = re.compile(r'RSI Filter Active - Build (\w+)')
version_match = version_pattern.search(html)
if version_match:
    print(f"\n✅ 发现版本标识: {version_match.group(0)}")
else:
    print("\n⚠️ 未发现版本标识")

# 分析RSI过滤逻辑的关键部分
print("\n" + "=" * 80)
print("���键逻辑检查:")
print("=" * 80)

# 检查 null/undefined 处理
if 'maxHighRsi === null || maxHighRsi === undefined' in html:
    print("✅ 正确处理 null/undefined RSI")
else:
    print("❌ 可能未正确处理 null/undefined RSI")

# 检查RSI < 50 的过滤
if 'maxHighRsi < 50' in html:
    print("✅ 存在 RSI < 50 的过滤")
else:
    print("❌ 缺少 RSI < 50 的过滤")

# 获取UNI的K线数据
print("\n" + "=" * 80)
print("测试获取UNI的实际K线数据...")
print("=" * 80)

try:
    # 获取API数据
    api_url = 'http://localhost:5000/api/kline/UNI?interval=5m&limit=500'
    api_response = requests.get(api_url, timeout=10)
    
    if api_response.status_code == 200:
        data = api_response.json()
        print(f"\n✅ 成功获取数据，共 {len(data)} 根K线")
        
        # 检查是否有RSI数据
        if data and 'rsi' in data[0]:
            rsi_values = [item.get('rsi') for item in data if item.get('rsi') is not None]
            if rsi_values:
                print(f"✅ RSI数据可用，范围: {min(rsi_values):.2f} ~ {max(rsi_values):.2f}")
                rsi_below_50 = [r for r in rsi_values if r < 50]
                rsi_above_50 = [r for r in rsi_values if r >= 50]
                print(f"   - RSI < 50: {len(rsi_below_50)} 个 ({len(rsi_below_50)/len(rsi_values)*100:.1f}%)")
                print(f"   - RSI >= 50: {len(rsi_above_50)} 个 ({len(rsi_above_50)/len(rsi_values)*100:.1f}%)")
            else:
                print("⚠️ RSI数据为空")
        else:
            print("❌ 数据中不包含RSI字段")
    else:
        print(f"❌ API请求失败: {api_response.status_code}")
except Exception as e:
    print(f"❌ 获取数据时出错: {e}")

print("\n" + "=" * 80)
print("诊断完成")
print("=" * 80)
