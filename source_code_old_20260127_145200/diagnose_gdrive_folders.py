#!/usr/bin/env python3
"""
诊断 Google Drive 中的日期文件夹
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
ROOT_FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"

def get_all_date_folders():
    """获取根文件夹中的所有日期文件夹"""
    url = f"https://drive.google.com/embeddedfolderview?id={ROOT_FOLDER_ID}"
    
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        folders = {}
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 匹配日期格式: YYYY-MM-DD
            if text and len(text) == 10 and text.count('-') == 2:
                try:
                    # 验证是否是有效日期
                    datetime.strptime(text, '%Y-%m-%d')
                    
                    # 提取文件夹ID
                    if 'id=' in href:
                        folder_id = href.split('id=')[1].split('&')[0]
                        folders[text] = folder_id
                except:
                    pass
        
        return folders
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        return {}

def main():
    print("=" * 80)
    print("🔍 Google Drive 日期文件夹诊断")
    print("=" * 80)
    
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    print(f"\n📅 今天日期（北京时间）: {today}")
    print(f"📂 根文件夹ID: {ROOT_FOLDER_ID}\n")
    
    print("正在扫描 Google Drive...")
    folders = get_all_date_folders()
    
    if not folders:
        print("\n❌ 没有找到任何日期文件夹！")
        print("   可能原因：")
        print("   1. 根文件夹ID不正确")
        print("   2. 网络连接问题")
        print("   3. Google Drive 权限问题")
        return
    
    print(f"\n✅ 找到 {len(folders)} 个日期文件夹：\n")
    
    # 按日期排序
    sorted_folders = sorted(folders.items(), reverse=True)
    
    for i, (date, folder_id) in enumerate(sorted_folders, 1):
        is_today = "👉 今天" if date == today else ""
        print(f"  {i}. 📅 {date}  {is_today}")
        print(f"     ID: {folder_id}")
    
    print("\n" + "=" * 80)
    print("💡 分析结果")
    print("=" * 80)
    
    if today in folders:
        print(f"\n✅ 找到今天的文件夹！")
        print(f"   日期: {today}")
        print(f"   ID: {folders[today]}")
        print(f"\n🔧 建议操作：")
        print(f"   1. 更新 daily_folder_config.json 为：")
        print(f"      {{'folder_id': '{folders[today]}', 'current_date': '{today}'}}")
        print(f"   2. 重启监控服务: pm2 restart gdrive-monitor")
    else:
        latest_date = sorted_folders[0][0]
        print(f"\n⚠️  没有找到今天 ({today}) 的文件夹")
        print(f"   最新的文件夹是: {latest_date}")
        print(f"   ID: {folders[latest_date]}")
        print(f"\n🔧 解决方案：")
        print(f"   选项1：等待外部程序在 Google Drive 中创建 {today} 文件夹")
        print(f"   选项2：临时使用最新文件夹 {latest_date}")
        print(f"   选项3：手动在 Google Drive 中创建 {today} 文件夹")

if __name__ == '__main__':
    main()
