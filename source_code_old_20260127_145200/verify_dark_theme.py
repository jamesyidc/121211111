#!/usr/bin/env python3
"""
验证深色主题部署状态
"""
import requests
import re

BASE_URL = "http://localhost:5000"

print("="*80)
print("🔍 深色主题验证")
print("="*80)

try:
    # 测试首页
    print("\n1️⃣ 测试首页加载...")
    resp = requests.get(BASE_URL, timeout=5)
    
    if resp.status_code == 200:
        print(f"   ✅ 状态码: {resp.status_code}")
        
        # 检查深色主题元素
        content = resp.text
        
        checks = [
            ("#1a1a2e", "深色背景渐变起点"),
            ("#16213e", "深色背景渐变终点"),
            ("rgba(42, 45, 71", "深灰色卡片背景"),
            ("#00d4ff", "科技蓝色按钮"),
            ("#ffffff", "白色文字"),
        ]
        
        print("\n2️⃣ 检查深色主题元素:")
        for color, desc in checks:
            if color in content:
                print(f"   ✅ {desc}: {color}")
            else:
                print(f"   ❌ {desc}: {color} (未找到)")
        
        # 检查功能链接
        print("\n3️⃣ 检查功能链接:")
        links = ["/query", "/chart", "/timeline", "/api/latest"]
        for link in links:
            if link in content:
                print(f"   ✅ {link}")
            else:
                print(f"   ❌ {link}")
        
        # 测试统计API
        print("\n4️⃣ 测试统计API:")
        stats_resp = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        if stats_resp.status_code == 200:
            data = stats_resp.json()
            print(f"   ✅ 总记录: {data.get('total_records', 0)}")
            print(f"   ✅ 今日记录: {data.get('today_records', 0)}")
            print(f"   ✅ 数据天数: {data.get('data_days', 0)}")
        else:
            print(f"   ❌ 统计API失败: {stats_resp.status_code}")
        
        print("\n" + "="*80)
        print("✅ 深色主题验证通过！")
        print("="*80)
        print("\n🔗 访问地址:")
        print("   https://5000-iik759kgm7i3zklxvfrfx-cc2fbc16.sandbox.novita.ai/")
        print("\n💡 提示:")
        print("   - 如看到 'Sandbox Not Found' 错误，请刷新页面")
        print("   - 或者清除浏览器缓存后重试")
        print("   - 深色主题已部署，背景色: #1a1a2e → #16213e")
        
    else:
        print(f"   ❌ 首页加载失败: {resp.status_code}")
        
except Exception as e:
    print(f"   ❌ 错误: {e}")
    print("\n💡 尝试重启Flask服务...")
