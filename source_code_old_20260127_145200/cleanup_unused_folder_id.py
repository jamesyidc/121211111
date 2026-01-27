#!/usr/bin/env python3
"""
每日定时任务：清理未使用的父文件夹ID
在每天00:10执行，根据今天是单数还是双数日期，删除另一个不需要的父文件夹ID
"""
import json
from datetime import datetime
import pytz

CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def cleanup_unused_folder_id():
    """清理未使用的父文件夹ID"""
    
    # 1. 获取今天日期
    today = datetime.now(BEIJING_TZ)
    day_num = today.day
    is_odd = day_num % 2 == 1
    day_type = "单数" if is_odd else "双数"
    
    print(f"\n{'='*80}")
    print(f"🧹 每日父文件夹ID清理任务")
    print(f"{'='*80}\n")
    print(f"📅 今天日期: {today.strftime('%Y年%m月%d号')}")
    print(f"📊 日期类型: {day_type} ({day_num} % 2 = {day_num % 2})")
    
    # 2. 读取配置文件
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n📂 清理前配置:")
        if 'root_folder_odd' in config:
            print(f"   ├─ 单数父文件夹: {config['root_folder_odd']}")
        if 'root_folder_even' in config:
            print(f"   └─ 双数父文件夹: {config['root_folder_even']}")
        
        # 3. 根据今天日期清理不需要的ID
        if is_odd:
            # 今天是单数，删除双数父文件夹ID
            if 'root_folder_even' in config:
                removed_id = config['root_folder_even']
                del config['root_folder_even']
                print(f"\n🗑️  删除双数父文件夹ID: {removed_id}")
                print(f"✅ 今天是{day_num}号（单数），只保留单数父文件夹ID")
            else:
                print(f"\nℹ️  配置中没有双数父文件夹ID，无需删除")
        else:
            # 今天是双数，删除单数父文件夹ID
            if 'root_folder_odd' in config:
                removed_id = config['root_folder_odd']
                del config['root_folder_odd']
                print(f"\n🗑️  删除单数父文件夹ID: {removed_id}")
                print(f"✅ 今天是{day_num}号（双数），只保留双数父文件夹ID")
            else:
                print(f"\nℹ️  配置中没有单数父文件夹ID，无需删除")
        
        # 4. 添加清理记录
        config['last_cleanup'] = today.strftime('%Y-%m-%d %H:%M:%S')
        config['cleanup_reason'] = f"每日00:10自动清理，今天是{day_type}日期"
        
        # 5. 保存更新后的配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        print(f"\n📂 清理后配置:")
        if 'root_folder_odd' in config:
            print(f"   ├─ 单数父文件夹: {config['root_folder_odd']}")
        if 'root_folder_even' in config:
            print(f"   ├─ 双数父文件夹: {config['root_folder_even']}")
        print(f"   └─ 清理时间: {config['last_cleanup']}")
        
        print(f"\n✅ 清理完成！")
        print(f"{'='*80}\n")
        
    except FileNotFoundError:
        print(f"❌ 配置文件不存在: {CONFIG_FILE}")
    except json.JSONDecodeError:
        print(f"❌ 配置文件格式错误")
    except Exception as e:
        print(f"❌ 清理失败: {e}")

if __name__ == "__main__":
    cleanup_unused_folder_id()
