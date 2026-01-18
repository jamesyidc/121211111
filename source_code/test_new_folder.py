from playwright.sync_api import sync_playwright
import re

# 测试新发现的文件夹ID
TEST_ID = "1y0Dm0W8S1enfjobDKAyXiOA2U33pUbsD"
TEST_URL = f"https://drive.google.com/drive/folders/{TEST_ID}"

print("测试新发现的文件夹...")
print("=" * 70)
print(f"文件夹ID: {TEST_ID}")
print(f"URL: {TEST_URL}")
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    try:
        print("访问文件夹...")
        page.goto(TEST_URL, timeout=30000)
        page.wait_for_timeout(3000)
        
        html_content = page.content()
        
        # 检查是否是2025-12-06相关的文件夹
        if '2025-12-06' in html_content:
            print("✅ 这个文件夹包含2025-12-06相关内容")
            
            # 查找txt文件
            txt_pattern = r'2025-12-06_\d{4}\.txt'
            txt_files = sorted(set(re.findall(txt_pattern, html_content)))
            
            print(f"\n找到 {len(txt_files)} 个txt文件")
            
            if txt_files:
                print("\n所有文件列表:")
                for i, f in enumerate(txt_files, 1):
                    time_match = re.search(r'_(\d{2})(\d{2})\.txt', f)
                    if time_match:
                        hour = time_match.group(1)
                        minute = time_match.group(2)
                        print(f"  {i:2d}. {f} ({hour}:{minute})")
                
                latest = txt_files[-1]
                time_match = re.search(r'_(\d{2})(\d{2})\.txt', latest)
                if time_match:
                    hour = time_match.group(1)
                    minute = time_match.group(2)
                    print(f"\n🎯 最新文件: {latest} (时间: {hour}:{minute})")
                    
                    # 显示时间范围
                    first = txt_files[0]
                    first_time = re.search(r'_(\d{2})(\d{2})\.txt', first)
                    if first_time:
                        print(f"   时间范围: {first_time.group(1)}:{first_time.group(2)} - {hour}:{minute}")
            else:
                print("❌ 未找到txt文件")
        else:
            print("❌ 这个文件夹不包含2025-12-06相关内容")
            
            # 显示文件夹包含的内容
            print("\n文件夹内容预览:")
            print(html_content[:1000])
            
    except Exception as e:
        print(f"❌ 访问失败: {e}")
    
    browser.close()

