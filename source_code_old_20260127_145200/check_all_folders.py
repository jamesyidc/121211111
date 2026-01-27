from playwright.sync_api import sync_playwright
import re
from datetime import datetime
import pytz

# 所有找到的文件夹
FOLDERS = [
    ("1-IfqZxMV9VCSg3ct6XVMyFtAbuCV3huQ", "文件夹1"),
    ("1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh", "文件夹2"),
    ("1JNZKKnZLeoBkxSumjS63SOInCriPfAKX", "当前使用的文件夹"),
    ("1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV", "父文件夹"),
]

beijing_tz = pytz.timezone('Asia/Shanghai')
now = datetime.now(beijing_tz)

print("="*70)
print(f"检查所有 Google Drive 文件夹")
print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for folder_id, name in FOLDERS:
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        print(f"\n【{name}】")
        print(f"ID: {folder_id}")
        print(f"URL: {url}")
        
        try:
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)
            
            # 滚动加载
            for i in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(500)
            
            content = page.content()
            
            # 查找今天的txt文件
            today_pattern = r'2025-12-06_(\d{4})\.txt'
            files = re.findall(today_pattern, content)
            
            if files:
                unique_files = sorted(set(files))
                print(f"✅ 找到 {len(unique_files)} 个今天的txt文件")
                print(f"   时间范围: {unique_files[0][:2]}:{unique_files[0][2:]} - {unique_files[-1][:2]}:{unique_files[-1][2:]}")
                print(f"   最新文件: 2025-12-06_{unique_files[-1]}.txt")
            else:
                print(f"❌ 未找到今天的txt文件")
        
        except Exception as e:
            print(f"❌ 访问失败: {e}")
    
    browser.close()

print("\n" + "="*70)
