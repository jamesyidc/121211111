#!/usr/bin/env python3
"""
紧急Google Drive修复脚本
当找不到今天文件夹时的应急方案
"""
import requests
import json
from datetime import datetime, timedelta
import pytz

beijing_tz = pytz.timezone('Asia/Shanghai')
today = datetime.now(beijing_tz).strftime('%Y-%m-%d')

print("="*70)
print("🚨 Google Drive 紧急诊断和修复工具")
print("="*70)
print(f"📅 当前日期: {today} ({datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')})")
print()

# 读取现有配置
try:
    with open('daily_folder_config.json', 'r') as f:
        config = json.load(f)
    print(f"📂 当前配置:")
    print(f"   日期: {config.get('current_date')}")
    print(f"   文件夹ID: {config.get('folder_id')}")
    print(f"   更新时间: {config.get('updated_at')}")
    print()
except:
    config = {}
    print("⚠️ 无法读取配置文件\n")

# 测试固定文件ID（从gdrive_final_detector.py）
FIXED_FILE_ID = "1eyYiU6lU8n7SwWUvFtm_kUIvaZI0SO4U"

print(f"🔍 方案1: 测试固定文件ID访问...")
print(f"   文件ID: {FIXED_FILE_ID}")

url = f"https://drive.google.com/uc?export=download&id={FIXED_FILE_ID}"
try:
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        content = response.text[:200]
        print(f"   ✅ 可以访问固定文件ID！")
        print(f"   数据预览: {content[:100]}...")
        print(f"   → 建议：继续使用固定文件ID模式")
    else:
        print(f"   ❌ 固定文件ID无法访问 (状态码: {response.status_code})")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print()

# 方案2: 搜索最近几天的文件夹
known_folders = {
    "2025-12-11": "1k3I_NALUR24-lAapPnSJ7_gMvCOiX5cV",
    "2025-12-09": "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM",
}

print(f"🔍 方案2: 检查已知文件夹...")
for date_str, folder_id in known_folders.items():
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    try:
        response = requests.get(url, timeout=5)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        txt_files = [link.text.strip() for link in soup.find_all('a', href=True) 
                     if '.txt' in link.text.lower()]
        
        if txt_files:
            latest = sorted(txt_files)[-1] if txt_files else "无"
            print(f"   📁 {date_str}: {len(txt_files)}个文件 (最新: {latest})")
    except:
        print(f"   ❌ {date_str}: 无法访问")

print()
print("="*70)
print("💡 建议的解决方案:")
print("="*70)
print("1. 如果固定文件ID可用 → 系统可以继续工作（使用实时更新的文件）")
print("2. 如果今天的文件夹还未创建 → 等待文件夹创建后手动更新配置")
print("3. 如果需要手动更新 → 提供今天的文件夹ID，我立即更新")
print()
print("🔗 手动更新命令示例:")
print("   python3 -c \"import json; json.dump({'current_date': '2025-12-12',")
print("   'folder_id': '你的文件夹ID'}, open('daily_folder_config.json','w'))\"")
print("="*70)
