#!/usr/bin/env python3
"""
测试单数/双数日期父文件夹选择逻辑
"""
from datetime import datetime
import pytz
import json

CONFIG_FILE = '/home/user/webapp/daily_folder_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def test_folder_selection():
    """测试文件夹选择逻辑"""
    today = datetime.now(BEIJING_TZ)
    day_of_month = today.day
    is_odd_day = day_of_month % 2 == 1
    
    print("=" * 70)
    print("🧪 单数/双数日期父文件夹选择测试")
    print("=" * 70)
    print()
    print(f"📅 今天日期: {today.strftime('%Y-%m-%d')}")
    print(f"📊 日期号数: {day_of_month}")
    print(f"🔢 日期类型: {'单数' if is_odd_day else '双数'}")
    print()
    
    # 从配置文件读取
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        root_folder_odd = config.get('root_folder_odd', 'N/A')
        root_folder_even = config.get('root_folder_even', 'N/A')
        
        print("📂 配置文件中的父文件夹ID:")
        print(f"   1️⃣  单数日期: {root_folder_odd}")
        print(f"   2️⃣  双数日期: {root_folder_even}")
        print()
        
        # 选择应该使用的文件夹
        if is_odd_day:
            selected = root_folder_odd
            status = "✅ 单数日期，使用单数父文件夹"
        else:
            selected = root_folder_even
            status = "✅ 双数日期，使用双数父文件夹"
        
        print("🎯 选择结果:")
        print(f"   {status}")
        print(f"   📂 使用的父文件夹: {selected}")
        print()
        
        # 检查是否相同（问题）
        if root_folder_odd == root_folder_even:
            print("⚠️  警告: 单数和双数父文件夹ID相同！")
            print("   这意味着还没有设置不同的父文件夹ID")
            print()
            print("🔧 解决方案:")
            print("   使用 update_root_folders.py 工具设置不同的父文件夹ID:")
            print()
            print("   python3 update_root_folders.py --odd <单数日期父文件夹ID>")
            print("   python3 update_root_folders.py --even <双数日期父文件夹ID>")
        else:
            print("✅ 单数和双数父文件夹ID不同，配置正确！")
        
    except FileNotFoundError:
        print("❌ 配置文件不存在")
    except json.JSONDecodeError:
        print("❌ 配置文件格式错误")
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print()
    print("=" * 70)

if __name__ == '__main__':
    test_folder_selection()
