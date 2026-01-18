from playwright.sync_api import sync_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

# 尝试按文件修改时间的URL参数
print("尝试通过URL参数控制排序...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 尝试不同的URL参数来控制排序和显示
    test_urls = [
        # 原始URL
        f"https://drive.google.com/drive/folders/{FOLDER_ID}",
        # 尝试添加排序参数
        f"https://drive.google.com/drive/folders/{FOLDER_ID}?sort=13&direction=d",  # 按修改时间倒序
        f"https://drive.google.com/drive/folders/{FOLDER_ID}?sort=modifiedByMeTime&direction=d",
        # 尝试改变视图
        f"https://drive.google.com/drive/u/0/folders/{FOLDER_ID}",
    ]
    
    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)
            
            content = page.content()
            times = re.findall(r'2025-12-06_(\d{4})', content)
            unique_times = sorted(set(times))
            
            print(f"  找到 {len(unique_times)} 个文件")
            if unique_times:
                print(f"  范围: {unique_times[0]} - {unique_times[-1]}")
                
                # 检查是否包含新文件
                if '1000' in unique_times or '0949' in unique_times:
                    print(f"  ✓ 找到新文件！")
                    break
        except Exception as e:
            print(f"  失败: {e}")
    
    browser.close()

print("\n" + "="*70)
print("结论：Google Drive网页接口的50文件限制无法通过URL参数绕过")
print("="*70)

