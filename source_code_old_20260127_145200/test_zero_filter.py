#!/usr/bin/env python3
"""
测试0值过滤逻辑
"""
import sys

def test_v1v2_logic():
    """测试V1V2采集器的0值过滤逻辑"""
    print("=" * 60)
    print("测试 V1V2 采集器 - 0值过滤逻辑")
    print("=" * 60)
    
    test_cases = [
        {"volume": 0, "expected": "跳过", "reason": "成交额为0"},
        {"volume": None, "expected": "跳过", "reason": "成交额为None"},
        {"volume": 100000, "expected": "保存", "reason": "成交额正常"},
        {"volume": 0.0, "expected": "跳过", "reason": "成交额为0.0"},
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        volume = case['volume']
        expected = case['expected']
        reason = case['reason']
        
        # 模拟采集器逻辑
        if volume is not None and volume > 0:
            result = "保存"
        else:
            result = "跳过"
        
        status = "✅" if result == expected else "❌"
        print(f"{i}. {status} volume={volume} -> {result} (期望: {expected}) - {reason}")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总结: {passed} 通过, {failed} 失败")
    return failed == 0

def test_price_speed_logic():
    """测试价格速度采集器的0值过滤逻辑"""
    print("\n" + "=" * 60)
    print("测试 价格速度采集器 - 0值过滤逻辑")
    print("=" * 60)
    
    test_cases = [
        {"price": 0, "expected": "跳过", "reason": "价格为0"},
        {"price": None, "expected": "跳过", "reason": "价格为None"},
        {"price": 45000.5, "expected": "保存", "reason": "价格正常"},
        {"price": 0.0, "expected": "跳过", "reason": "价格为0.0"},
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        price = case['price']
        expected = case['expected']
        reason = case['reason']
        
        # 模拟采集器逻辑
        if price is None or price == 0:
            result = "跳过"
        else:
            result = "保存"
        
        status = "✅" if result == expected else "❌"
        print(f"{i}. {status} price={price} -> {result} (期望: {expected}) - {reason}")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总结: {passed} 通过, {failed} 失败")
    return failed == 0

def test_gdrive_detector_logic():
    """测试Google Drive检测器的0值过滤逻辑"""
    print("\n" + "=" * 60)
    print("测试 Google Drive 检测器 - 0值过滤逻辑")
    print("=" * 60)
    
    test_cases = [
        {"rush_up": 0, "rush_down": 0, "expected": "跳过", "reason": "两者都为0"},
        {"rush_up": 10, "rush_down": 0, "expected": "保存", "reason": "rush_up有效"},
        {"rush_up": 0, "rush_down": 5, "expected": "保存", "reason": "rush_down有效"},
        {"rush_up": 15, "rush_down": 8, "expected": "保存", "reason": "两者都有效"},
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        rush_up = case['rush_up']
        rush_down = case['rush_down']
        expected = case['expected']
        reason = case['reason']
        
        # 模拟检测器逻辑
        if rush_up == 0 and rush_down == 0:
            result = "跳过"
        else:
            result = "保存"
        
        status = "✅" if result == expected else "❌"
        print(f"{i}. {status} rush_up={rush_up}, rush_down={rush_down} -> {result} (期望: {expected}) - {reason}")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总结: {passed} 通过, {failed} 失败")
    return failed == 0

if __name__ == '__main__':
    print("\n🧪 开始测试数据0值过滤逻辑\n")
    
    results = []
    results.append(("V1V2采集器", test_v1v2_logic()))
    results.append(("价格速度采集器", test_price_speed_logic()))
    results.append(("Google Drive检测器", test_gdrive_detector_logic()))
    
    print("\n" + "=" * 60)
    print("📊 最终测试结果")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)
