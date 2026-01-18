from playwright.sync_api import sync_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"

# 根据截图，最新的文件
TARGET_FILES = [
    "2025-12-06_0829.txt",
    "2025-12-06_0839.txt", 
    "2025-12-06_0849.txt",
    "2025-12-06_0859.txt",
    "2025-12-06_0909.txt",
    "2025-12-06_0919.txt",
    "2025-12-06_0929.txt",
    "2025-12-06_0939.txt",
    "2025-12-06_0949.txt",
    "2025-12-06_1000.txt"
]

print("="*70)
print("尝试直接访问新文件...")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 先访问文件夹
    page.goto(FOLDER_URL, timeout=30000)
    page.wait_for_timeout(3000)
    
    # 获取完整HTML来查找文件ID
    html_content = page.content()
    
    # 尝试在HTML中查找所有文件ID和名称的映射
    print("\n在HTML中搜索文件...")
    
    for target_file in TARGET_FILES:
        # 在HTML中搜索这个文件名
        if target_file in html_content:
            print(f"✓ 找到文件: {target_file}")
            
            # 尝试提取文件ID
            pattern = re.escape(target_file) + r'.*?data-id="([a-zA-Z0-9_-]{20,})"'
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                file_id = match.group(1)
                print(f"  文件ID: {file_id}")
        else:
            print(f"✗ HTML中未找到: {target_file}")
    
    # 尝试通过搜索功能
    print("\n尝试使用文件夹内搜索...")
    try:
        # 查找搜索框
        search_box = page.locator('[aria-label*="搜索"], [placeholder*="搜索"], input[type="text"]').first
        if search_box.count() > 0:
            search_box.fill("2025-12-06_1000.txt")
            page.wait_for_timeout(2000)
            
            content = page.content()
            if "1000" in content:
                print("✓ 搜索到1000文件!")
            else:
                print("✗ 搜索未找到")
    except Exception as e:
        print(f"搜索失败: {e}")
    
    browser.close()

print("\n" + "="*70)
print("结论：文件在Google Drive中存在，但网页显示有50个文件限制")
print("需要使用其他方法突破限制...")
print("="*70)

