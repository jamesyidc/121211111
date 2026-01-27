#!/usr/bin/env python3
"""
前端问题诊断脚本
诊断TG卡片和星星系统历史数据页面的问题
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

print("=" * 70)
print("🔍 前端问题诊断脚本")
print("=" * 70)

# 测试1: TG状态API
print("\n1️⃣ 测试 TG 状态 API")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/api/telegram/status", timeout=5)
    print(f"✅ HTTP状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API返回成功: {data.get('success')}")
        print(f"   运行状态: {data.get('status')}")
        print(f"   is_running: {data.get('is_running')}")
        print(f"   已推送: {data.get('total_sent')}条")
        print(f"   最后更新: {data.get('last_update')}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        print(f"   响应: {response.text[:200]}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试2: TG Dashboard页面
print("\n2️⃣ 测试 TG Dashboard 页面")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/telegram-dashboard", timeout=5)
    print(f"✅ HTTP状态: {response.status_code}")
    
    if response.status_code == 200:
        html = response.text
        print(f"✅ 页面大小: {len(html)} 字节")
        if "TG消息推送管理系统" in html:
            print("✅ 页面标题正确")
        if "@jamesyi9999_bot" in html:
            print("✅ Bot信息存在")
        if "echarts" in html.lower():
            print("✅ ECharts已加载")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试3: 首页TG卡片
print("\n3️⃣ 测试 首页 TG 卡片")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"✅ HTTP状态: {response.status_code}")
    
    if response.status_code == 200:
        html = response.text
        if "TG消息推送" in html:
            print("✅ TG卡片存在")
        if "telegram-dashboard" in html:
            print("✅ Dashboard链接存在")
        if "id=\"tg-card\"" in html:
            print("✅ TG卡片ID正确")
        if "loadTelegramStatus" in html:
            print("✅ TG状态加载函数存在")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试4: 星星系统历史API
print("\n4️⃣ 测试 星星系统历史 API")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/api/star-system/history?limit=3", timeout=5)
    print(f"✅ HTTP状态: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ API返回成功: {data.get('success')}")
        print(f"   记录数: {data.get('total_records')}")
        print(f"   可用日期: {data.get('available_dates')}")
        
        if data.get('data'):
            first_record = data['data'][0]
            print(f"   最新记录: {first_record.get('timestamp')}")
            print(f"   总星数: {first_record.get('total_stars')}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        print(f"   响应: {response.text[:200]}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试5: 星星系统页面
print("\n5️⃣ 测试 星星系统页面")
print("-" * 70)
try:
    response = requests.get(f"{BASE_URL}/star-system", timeout=5)
    print(f"✅ HTTP状态: {response.status_code}")
    
    if response.status_code == 200:
        html = response.text
        print(f"✅ 页面大小: {len(html)} 字节")
        if "星星系统" in html:
            print("✅ 页面标题存在")
        if "api/star-system/history" in html:
            print("✅ 历史API调用存在")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

# 测试6: 检查数据库
print("\n6️⃣ 检查 数据库状态")
print("-" * 70)
try:
    import sqlite3
    
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 检查star_system_history表
    cursor.execute("SELECT COUNT(*) FROM star_system_history")
    count = cursor.fetchone()[0]
    print(f"✅ star_system_history记录数: {count}")
    
    # 获取最新记录
    cursor.execute("SELECT timestamp, total_stars FROM star_system_history ORDER BY timestamp DESC LIMIT 1")
    latest = cursor.fetchone()
    if latest:
        print(f"   最新记录: {latest[0]} ({latest[1]}颗星)")
        
        # 检查日期
        latest_date = latest[0].split()[0]
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"   今天: {today}")
        print(f"   最新数据日期: {latest_date}")
        
        if latest_date < today:
            print(f"⚠️  数据不是今天的，可能需要更新")
    
    conn.close()
except Exception as e:
    print(f"❌ 数据库检查失败: {e}")

print("\n" + "=" * 70)
print("诊断完成！")
print("=" * 70)

# 总结问题
print("\n📋 问题总结:")
print("-" * 70)
print("1. TG卡片显示'旗帜失败':")
print("   - 可能原因: 前端JavaScript翻译问题或API超时")
print("   - 建议: 检查浏览器控制台错误，清除浏览器缓存")
print("")
print("2. 星星系统历史数据为空:")
print("   - API正常返回数据，但页面显示'你尚未访问此页面'")
print("   - 可能原因: 前端JavaScript错误或CORS问题")
print("   - 建议: 检查浏览器控制台，刷新页面")
print("")
print("🔧 建议操作:")
print("   1. 清除浏览器缓存 (Ctrl+Shift+Delete)")
print("   2. 硬刷新页面 (Ctrl+F5)")
print("   3. 检查浏览器控制台 (F12)")
print("=" * 70)
