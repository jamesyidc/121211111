#!/usr/bin/env python3
"""
更新每日Google Drive文件夹ID配置

使用方法:
  python3 update_folder_id.py <新文件夹ID>

示例:
  python3 update_folder_id.py 1AbCdEfGhIjKlMnOpQrStUvWxYz123456
"""

import json
import sys
from datetime import datetime
import pytz

CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def update_folder_id(new_folder_id):
    """更新今天的文件夹ID"""
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    now = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # 读取现有配置
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {
                "description": "每日Google Drive文件夹ID配置",
                "history": {}
            }
        
        # 保存旧ID到历史记录
        if 'folder_id' in config and 'current_date' in config:
            old_date = config['current_date']
            old_id = config['folder_id']
            config['history'][old_date] = old_id
        
        # 更新配置
        config['current_date'] = today
        config['folder_id'] = new_folder_id
        config['last_update'] = now
        config['history'][today] = new_folder_id
        
        # 写入配置文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✅ 文件夹ID更新成功！")
        print(f"📅 日期: {today}")
        print(f"📁 新文件夹ID: {new_folder_id}")
        print(f"🕐 更新时间: {now}")
        print(f"\n📂 配置文件: {CONFIG_FILE}")
        
        # 显示历史记录
        if config['history']:
            print("\n📜 历史记录:")
            for date in sorted(config['history'].keys(), reverse=True)[:5]:
                print(f"   {date}: {config['history'][date]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("❌ 错误: 请提供文件夹ID")
        print("\n使用方法:")
        print("  python3 update_folder_id.py <新文件夹ID>")
        print("\n示例:")
        print("  python3 update_folder_id.py 1AbCdEfGhIjKlMnOpQrStUvWxYz123456")
        print("\n如何获取文件夹ID:")
        print("  1. 在Google Drive中打开文件夹")
        print("  2. 查看浏览器地址栏URL")
        print("  3. URL格式: https://drive.google.com/drive/folders/[文件夹ID]")
        print("  4. 复制[文件夹ID]部分")
        sys.exit(1)
    
    new_folder_id = sys.argv[1].strip()
    
    # 验证文件夹ID格式
    if len(new_folder_id) < 20:
        print(f"⚠️ 警告: 文件夹ID似乎太短 (长度: {len(new_folder_id)})")
        print("   Google Drive文件夹ID通常是33个字符")
        response = input("是否继续? (y/n): ")
        if response.lower() != 'y':
            print("❌ 已取消")
            sys.exit(1)
    
    if update_folder_id(new_folder_id):
        print("\n✅ 完成！检测器将在下次检查时使用新的文件夹ID")
        print("   检测间隔: 30秒")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
