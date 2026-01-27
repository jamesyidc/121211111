from playwright.sync_api import sync_playwright
import re

PARENT_FOLDER_URL = "https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"

print("查找2025-12-06文件夹的ID...")
print("=" * 70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto(PARENT_FOLDER_URL, timeout=60000)
    page.wait_for_timeout(3000)
    
    # 获取完整HTML
    html_content = page.content()
    
    # 保存HTML用于分析
    with open('/tmp/parent_folder.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("HTML已保存到 /tmp/parent_folder.html")
    
    # 查找所有文件夹ID模式
    # Google Drive的文件夹链接格式: /folders/{folder_id}
    folder_pattern = r'data-id="([a-zA-Z0-9_-]+)"[^>]*>.*?2025-12-06'
    matches = re.findall(folder_pattern, html_content, re.DOTALL)
    
    if matches:
        print(f"\n找到匹配的文件夹ID:")
        for folder_id in matches[:5]:
            print(f"  - {folder_id}")
            folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"    URL: {folder_url}")
    
    # 另一种方法：查找所有带有2025-12-06的data属性
    print("\n\n尝试方法2: 搜索所有包含2025-12-06的元素...")
    
    # 使用更宽泛的搜索
    pattern2 = r'([a-zA-Z0-9_-]{20,})"[^>]*2025-12-06|2025-12-06[^>]*"([a-zA-Z0-9_-]{20,})"'
    matches2 = re.findall(pattern2, html_content)
    
    potential_ids = []
    for match in matches2:
        for group in match:
            if group and len(group) > 20:
                potential_ids.append(group)
    
    potential_ids = list(set(potential_ids))
    print(f"找到 {len(potential_ids)} 个潜在的文件夹ID")
    
    if potential_ids:
        print("\n测试这些ID:")
        for pid in potential_ids[:3]:
            test_url = f"https://drive.google.com/drive/folders/{pid}"
            print(f"\n  测试: {test_url}")
            try:
                page.goto(test_url, timeout=10000)
                page.wait_for_timeout(2000)
                
                if "2025-12-06" in page.content():
                    print(f"    ✅ 这是正确的文件夹!")
                    
                    # 统计txt文件
                    txt_pattern = r'2025-12-06_\d{4}\.txt'
                    txt_files = sorted(set(re.findall(txt_pattern, page.content())))
                    print(f"    找到 {len(txt_files)} 个txt文件")
                    if txt_files:
                        print(f"    最新文件: {txt_files[-1]}")
                        break
                else:
                    print(f"    ❌ 不是目标文件夹")
            except Exception as e:
                print(f"    ❌ 访问失败: {e}")
    
    browser.close()

