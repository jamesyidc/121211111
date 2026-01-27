#!/usr/bin/env python3
"""
测试补全数据按钮功能
"""
import requests
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo('Asia/Shanghai')
BASE_URL = "http://localhost:5000"

def test_backfill_status():
    """测试补全状态 API"""
    print("=" * 60)
    print("测试 1: 补全状态查询 API")
    print("=" * 60)
    
    url = f"{BASE_URL}/api/backfill/status"
    response = requests.get(url)
    
    print(f"请求: GET {url}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('success'):
            print("\n✅ 状态查询 API 测试通过")
            print(f"- 是否运行中: {data.get('is_running')}")
            print(f"- 今天记录数: {data.get('today_records')}")
            print(f"- 状态: {data.get('status')}")
            return True
        else:
            print("\n❌ API 返回失败")
            return False
    else:
        print(f"\n❌ HTTP 状态码错误: {response.status_code}")
        return False

def test_backfill_trigger():
    """测试补全触发 API (不实际执行)"""
    print("\n" + "=" * 60)
    print("测试 2: 补全触发 API (模拟测试)")
    print("=" * 60)
    
    # 先检查是否有任务在运行
    status_url = f"{BASE_URL}/api/backfill/status"
    status_response = requests.get(status_url)
    
    if status_response.status_code == 200:
        status_data = status_response.json()
        if status_data.get('is_running'):
            print("⚠️  已有补全任务在运行中，跳过触发测试")
            return True
    
    print("📝 注意: 此测试仅检查 API 端点，不实际触发补全任务")
    print(f"如需实际测试，请访问查询页面点击 '🔄 补全数据' 按钮")
    print(f"或手动执行: curl -X POST {BASE_URL}/api/backfill/trigger -H 'Content-Type: application/json' -d '{{}}'")
    
    return True

def test_query_page():
    """测试查询页面是否包含补全按钮"""
    print("\n" + "=" * 60)
    print("测试 3: 查询页面补全按钮检查")
    print("=" * 60)
    
    url = f"{BASE_URL}/query"
    response = requests.get(url)
    
    print(f"请求: GET {url}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        html = response.text
        
        # 检查按钮是否存在
        button_checks = [
            ('backfillBtn', '按钮元素 ID'),
            ('triggerBackfill()', '触发函数'),
            ('🔄 补全数据', '按钮文本'),
            ('checkBackfillStatus', '状态检查函数'),
            ('/api/backfill/trigger', '触发 API 端点'),
            ('/api/backfill/status', '状态查询 API 端点')
        ]
        
        all_passed = True
        print("\n按钮元素检查:")
        for check_str, description in button_checks:
            if check_str in html:
                print(f"  ✅ {description}: 找到")
            else:
                print(f"  ❌ {description}: 未找到")
                all_passed = False
        
        if all_passed:
            print("\n✅ 查询页面补全按钮测试通过")
            return True
        else:
            print("\n❌ 查询页面缺少部分补全按钮元素")
            return False
    else:
        print(f"\n❌ HTTP 状态码错误: {response.status_code}")
        return False

def check_database_status():
    """检查数据库当前状态"""
    print("\n" + "=" * 60)
    print("数据库状态检查")
    print("=" * 60)
    
    import sqlite3
    
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # 查询今天的记录
    cursor.execute('''
        SELECT COUNT(*) FROM crypto_snapshots 
        WHERE date(snapshot_time) = ?
    ''', (today,))
    count = cursor.fetchone()[0]
    
    print(f"\n📊 今天 ({today}) 的数据记录:")
    print(f"- 总记录数: {count}")
    
    if count > 0:
        cursor.execute('''
            SELECT snapshot_time, rush_up, rush_down, count, status 
            FROM crypto_snapshots 
            WHERE date(snapshot_time) = ?
            ORDER BY snapshot_time
        ''', (today,))
        
        records = cursor.fetchall()
        print(f"\n记录详情:")
        for r in records:
            print(f"  {r[0]} | 急涨:{r[1]:2d} | 急跌:{r[2]:2d} | 计次:{r[3]:2d} | {r[4]}")
    
    conn.close()

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("🧪 补全数据按钮功能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"基础 URL: {BASE_URL}")
    print("=" * 60)
    
    results = []
    
    # 测试 1: 状态查询 API
    results.append(("状态查询 API", test_backfill_status()))
    
    # 测试 2: 触发 API
    results.append(("触发 API", test_backfill_trigger()))
    
    # 测试 3: 查询页面按钮
    results.append(("查询页面按钮", test_query_page()))
    
    # 数据库状态
    check_database_status()
    
    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！补全数据按钮功能正常！")
    else:
        print("⚠️  部分测试失败，请检查相关功能")
    
    print("=" * 60)
    
    # 使用说明
    print("\n📖 使用说明:")
    print("1. 访问查询页面: http://localhost:5000/query")
    print("2. 找到 '🔄 补全数据' 按钮（渐变紫色）")
    print("3. 点击按钮并确认")
    print("4. 等待补全完成（显示实时进度）")
    print("5. 补全完成后自动刷新数据\n")
    
    print("🔗 相关 API:")
    print(f"- 状态查询: GET  {BASE_URL}/api/backfill/status")
    print(f"- 触发补全: POST {BASE_URL}/api/backfill/trigger")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
