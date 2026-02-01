#!/usr/bin/env python3
"""
诊断工具：检查单数/双数父文件夹ID配置
"""
import json
from datetime import datetime
import pytz

CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def diagnose():
    print("\n" + "="*80)
    print("🔍 单数/双数父文件夹ID配置诊断")
    print("="*80 + "\n")
    
    # 1. 获取今天日期
    today = datetime.now(BEIJING_TZ)
    day_num = today.day
    is_odd = day_num % 2 == 1
    day_type = "单数" if is_odd else "双数"
    
    print(f"📅 今天日期: {today.strftime('%Y年%m月%d号')}")
    print(f"📊 日期类型: {day_type} ({day_num} % 2 = {day_num % 2})")
    print(f"✅ 应该使用: {'单数日期父文件夹' if is_odd else '双数日期父文件夹'}")
    print()
    
    # 2. 读取配置文件
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        odd_id = config.get('root_folder_odd', 'N/A')
        even_id = config.get('root_folder_even', 'N/A')
        folder_id = config.get('folder_id', 'N/A')
        
        print("📂 当前配置:")
        print(f"   ├─ 单数父文件夹 (1,3,5,7,9,11,13...): {odd_id}")
        print(f"   ├─ 双数父文件夹 (2,4,6,8,10,12,14...): {even_id}")
        print(f"   └─ 子账号今日文件夹: {folder_id}")
        print()
        
        # 3. 检测问题
        issues = []
        
        if odd_id == even_id:
            issues.append("❌ 严重错误: 单数和双数父文件夹ID完全相同！")
            issues.append("   这意味着系统无法区分单数日期和双数日期")
            issues.append(f"   相同的ID: {odd_id}")
        
        if odd_id == 'N/A' or even_id == 'N/A':
            issues.append("❌ 配置缺失: 父文件夹ID未设置")
        
        if issues:
            print("⚠️  检测到问题:")
            for issue in issues:
                print(f"   {issue}")
            print()
        else:
            print("✅ 配置正常: 单数和双数父文件夹ID不同")
            print()
        
        # 4. 显示今天应该使用的ID
        expected_id = odd_id if is_odd else even_id
        print(f"🎯 今天({day_num}号)应该使用的父文件夹ID:")
        print(f"   → {expected_id}")
        print()
        
        # 5. 提供修复建议
        if odd_id == even_id:
            print("🔧 修复方案:")
            print("   您需要提供两个**不同的**Google Drive文件夹ID:")
            print()
            print("   1. 单数日期父文件夹ID (用于1,3,5,7,9,11,13...号)")
            print("   2. 双数日期父文件夹ID (用于2,4,6,8,10,12,14...号)")
            print()
            print("   然后运行:")
            print("   python3 update_root_folders.py --odd '单数文件夹ID' --even '双数文件夹ID'")
            print()
        
    except Exception as e:
        print(f"❌ 无法读取配置文件: {e}")
        print()
    
    print("="*80)
    print()

if __name__ == "__main__":
    diagnose()
