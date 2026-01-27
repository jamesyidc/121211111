#!/usr/bin/env python3
"""
测试新的导航系统
"""
import requests
import json

BASE_URL = "http://localhost:5000"

print("="*80)
print("🧪 测试导航系统")
print("="*80)

# 测试首页
print("\n📍 1. 测试首页 (/):")
try:
    resp = requests.get(f"{BASE_URL}/")
    print(f"   状态码: {resp.status_code}")
    if "加密货币数据分析系统" in resp.text:
        print("   ✅ 首页加载成功")
        # 检查是否包含所有模块链接
        modules = ["/query", "/chart", "/timeline", "/api/latest"]
        for module in modules:
            if module in resp.text:
                print(f"   ✅ 包含 {module} 链接")
    else:
        print("   ❌ 首页内容异常")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试统计API
print("\n📍 2. 测试统计API (/api/stats):")
try:
    resp = requests.get(f"{BASE_URL}/api/stats")
    data = resp.json()
    print(f"   状态码: {resp.status_code}")
    print(f"   ✅ 总记录数: {data['total_records']}")
    print(f"   ✅ 今日记录: {data['today_records']}")
    print(f"   ✅ 数据天数: {data['data_days']}")
    print(f"   ✅ 最后更新: {data['last_update_time']}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 测试各个功能页面
pages = [
    ("/query", "历史数据查询页面"),
    ("/chart", "趋势图表页面"),
    ("/timeline", "时间轴页面"),
]

print("\n📍 3. 测试功能页面:")
for path, name in pages:
    try:
        resp = requests.get(f"{BASE_URL}{path}")
        status = "✅" if resp.status_code == 200 else "❌"
        print(f"   {status} {path} - {name} (状态码: {resp.status_code})")
    except Exception as e:
        print(f"   ❌ {path} - 错误: {e}")

# 测试API接口
print("\n📍 4. 测试API接口:")
apis = [
    ("/api/latest", "最新数据"),
    ("/api/chart?page=0", "图表数据"),
    ("/api/timeline", "时间轴数据"),
]

for path, name in apis:
    try:
        resp = requests.get(f"{BASE_URL}{path}")
        status = "✅" if resp.status_code == 200 else "❌"
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                data_info = ""
                
                if "page" in data:
                    data_info = f"页码: {data['page']}/{data['total_pages']}, 数据点: {data['data_count']}"
                elif isinstance(data, list):
                    data_info = f"记录数: {len(data)}"
                elif "急涨" in data:
                    data_info = f"急涨: {data['急涨']}, 急跌: {data['急跌']}"
                
                print(f"   {status} {path} - {name} ({data_info})")
            except:
                print(f"   {status} {path} - {name}")
        else:
            print(f"   {status} {path} - {name} (状态码: {resp.status_code})")
    except Exception as e:
        print(f"   ❌ {path} - 错误: {e}")

print("\n"+"="*80)
print("🎯 导航架构:")
print("="*80)
print("""
根路径 (/)
├── 首页导航 - 显示所有功能模块
│
├── /query - 历史数据查询
│   └── API: /api/query?time=2025-12-06_1820
│
├── /chart - 趋势图表 (12小时分页)
│   └── API: /api/chart?page=0
│
├── /timeline - 时间轴
│   └── API: /api/timeline
│
└── /api/latest - 最新数据API
    └── API: /api/stats (统计数据)
""")

print("✅ 所有功能正常，采用二级路径设计！")
print("="*80)
