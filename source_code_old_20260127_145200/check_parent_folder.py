from playwright.sync_api import sync_playwright
import re

# 父文件夹URL (从之前的对话中得知)
PARENT_FOLDER_URL = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"

print("检查父文件夹结构...")
print("=" * 70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"访问父文件夹: {PARENT_FOLDER_URL}")
    page.goto(PARENT_FOLDER_URL, timeout=60000)
    page.wait_for_timeout(3000)
    
    # 获取页面内容
    html_content = page.content()
    
    # 查找日期文件夹
    date_pattern = r'2025-12-\d{2}'
    date_folders = sorted(set(re.findall(date_pattern, html_content)))
    
    print(f"\n找到 {len(date_folders)} 个日期文件夹:")
    for folder in date_folders[-10:]:  # 显示最后10个
        print(f"  - {folder}")
    
    # 特别检查今天的文件夹
    today_folder = "2025-12-06"
    if today_folder in html_content:
        print(f"\n✅ 找到今天的文件夹: {today_folder}")
        print("   尝试点击进入...")
        
        # 尝试找到并点击今天的文件夹
        try:
            folder_element = page.locator(f'[data-tooltip="{today_folder}"]').first
            if folder_element.count() > 0:
                # 获取文件夹的URL
                folder_element.dblclick(timeout=5000)
                page.wait_for_timeout(3000)
                
                new_url = page.url
                print(f"   新URL: {new_url}")
                
                # 提取文件夹ID
                folder_id_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', new_url)
                if folder_id_match:
                    folder_id = folder_id_match.group(1)
                    print(f"   文件夹ID: {folder_id}")
                
                # 检查这个文件夹中的文件
                page.wait_for_timeout(2000)
                html_content = page.content()
                
                # 查找txt文件
                txt_pattern = r'2025-12-06_\d{4}\.txt'
                txt_files = sorted(set(re.findall(txt_pattern, html_content)))
                
                print(f"\n   找到 {len(txt_files)} 个txt文件")
                if txt_files:
                    print("   最新的10个文件:")
                    for f in txt_files[-10:]:
                        print(f"     - {f}")
                    
                    latest = txt_files[-1]
                    print(f"\n   ✅ 最新文件: {latest}")
            else:
                print("   ⚠️  无法定位文件夹元素")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    else:
        print(f"\n❌ 未找到今天的文件夹: {today_folder}")
    
    browser.close()

