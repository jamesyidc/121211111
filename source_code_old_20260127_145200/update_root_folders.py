#!/usr/bin/env python3
"""
更新父文件夹ID的工具脚本
用于设置单数日期和双数日期的父文件夹ID
"""
import json
import sys
from datetime import datetime
import pytz

CONFIG_FILE = '/home/user/webapp/daily_folder_config.json'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def update_root_folders(odd_folder_id=None, even_folder_id=None):
    """更新父文件夹ID"""
    config = load_config()
    now = datetime.now(BEIJING_TZ)
    
    if odd_folder_id:
        config['root_folder_odd'] = odd_folder_id
        print(f"✅ 已更新单数日期父文件夹ID: {odd_folder_id}")
    
    if even_folder_id:
        config['root_folder_even'] = even_folder_id
        print(f"✅ 已更新双数日期父文件夹ID: {even_folder_id}")
    
    config['last_update'] = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # 确保描述信息存在
    if 'root_folder_description' not in config:
        config['root_folder_description'] = {
            'odd': '单数日期父文件夹 (1, 3, 5, 7, 9, 11...)',
            'even': '双数日期父文件夹 (2, 4, 6, 8, 10, 12...)'
        }
    
    save_config(config)
    print(f"\n📝 配置已保存到: {CONFIG_FILE}")
    print(f"⏰ 更新时间: {config['last_update']}")

def show_current_config():
    """显示当前配置"""
    config = load_config()
    today = datetime.now(BEIJING_TZ)
    day_of_month = today.day
    is_odd_day = day_of_month % 2 == 1
    
    print("=" * 70)
    print("📂 当前父文件夹ID配置")
    print("=" * 70)
    print()
    print(f"📅 今天日期: {today.strftime('%Y-%m-%d')} ({day_of_month}号)")
    print(f"📌 今天使用: {'单数日期父文件夹' if is_odd_day else '双数日期父文件夹'}")
    print()
    print("1️⃣  单数日期父文件夹 (1, 3, 5, 7, 9, 11, 13...)")
    print(f"   ID: {config.get('root_folder_odd', '未设置')}")
    print(f"   状态: {'✅ 今天使用' if is_odd_day else '📂 备用'}")
    print()
    print("2️⃣  双数日期父文件夹 (2, 4, 6, 8, 10, 12, 14...)")
    print(f"   ID: {config.get('root_folder_even', '未设置')}")
    print(f"   状态: {'✅ 今天使用' if not is_odd_day else '📂 备用'}")
    print()
    print(f"⏰ 最后更新: {config.get('last_update', '未知')}")
    print("=" * 70)

def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 没有参数，显示当前配置
        show_current_config()
        print()
        print("💡 使用方法:")
        print("  查看当前配置:")
        print("    python3 update_root_folders.py")
        print()
        print("  更新单数日期父文件夹:")
        print("    python3 update_root_folders.py --odd <folder_id>")
        print()
        print("  更新双数日期父文件夹:")
        print("    python3 update_root_folders.py --even <folder_id>")
        print()
        print("  同时更新两个:")
        print("    python3 update_root_folders.py --odd <id1> --even <id2>")
        print()
        return
    
    odd_id = None
    even_id = None
    
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--odd' and i + 1 < len(sys.argv):
            odd_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--even' and i + 1 < len(sys.argv):
            even_id = sys.argv[i + 1]
            i += 2
        else:
            print(f"❌ 未知参数: {sys.argv[i]}")
            sys.exit(1)
    
    if odd_id or even_id:
        update_root_folders(odd_id, even_id)
        print()
        print("=" * 70)
        print("更新后的配置:")
        print("=" * 70)
        show_current_config()
    else:
        print("❌ 错误：请提供至少一个文件夹ID")
        sys.exit(1)

if __name__ == '__main__':
    main()
