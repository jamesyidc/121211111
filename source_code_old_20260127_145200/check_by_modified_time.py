from playwright.sync_api import sync_playwright
import re
import time

FOLDER_URL = "https://drive.google.com/drive/folders/1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

print("="*70)
print("尝试按修改时间排序获取最新文件")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # 使用有头模式观察
    page = browser.new_page()
    
    print("\n1. 访问 Google Drive 文件夹...")
    page.goto(FOLDER_URL, wait_until='networkidle', timeout=60000)
    time.sleep(5)
    
    print("\n2. 查找并点击排序选项...")
    
    # 尝试多种方法点击修改时间排序
    try:
        # 方法1：查找"修改日期"列标题
        print("   尝试方法1：查找修改日期列标题...")
        # 使用更宽泛的选择器
        selectors = [
            '[role="columnheader"]:has-text("修改")',
            '[role="columnheader"]:has-text("Modified")',
            'div:has-text("修改日期")',
            'div[data-column="modifiedTime"]',
            '[aria-label*="修改"]',
            '[aria-label*="Modified"]'
        ]
        
        clicked = False
        for selector in selectors:
            elements = page.locator(selector)
            count = elements.count()
            if count > 0:
                print(f"   ✓ 找到元素: {selector} (数量: {count})")
                elements.first.click()
                time.sleep(2)
                # 再点击一次确保倒序
                elements.first.click()
                time.sleep(2)
                clicked = True
                print("   ✓ 已点击排序")
                break
        
        if not clicked:
            print("   ⚠ 未找到修改时间列标题")
            
            # 方法2：尝试右键菜单
            print("\n   尝试方法2：使用右键菜单...")
            page.click('body', button='right')
            time.sleep(1)
            
            # 查找排序选项
            sort_menu = page.locator('text=排序,text=Sort')
            if sort_menu.count() > 0:
                sort_menu.first.click()
                time.sleep(1)
                
                # 点击修改时间
                modified_option = page.locator('text=修改时间,text=Modified time')
                if modified_option.count() > 0:
                    modified_option.first.click()
                    time.sleep(2)
                    print("   ✓ 通过右键菜单设置排序")
                    clicked = True
        
        if not clicked:
            print("\n   ⚠ 无法点击排序，使用默认排序")
    
    except Exception as e:
        print(f"   ✗ 排序操作失败: {e}")
    
    print("\n3. 等待页面更新...")
    time.sleep(3)
    
    print("\n4. 获取页面内容并提取文件...")
    content = page.content()
    
    # 提取所有txt文件时间
    times = re.findall(r'2025-12-06_(\d{4})\.txt', content)
    unique_times = sorted(set(times))
    
    print(f"\n找到 {len(unique_times)} 个txt文件")
    if unique_times:
        print(f"时间范围: {unique_times[0][:2]}:{unique_times[0][2:]} - {unique_times[-1][:2]}:{unique_times[-1][2:]}")
        print(f"\n前10个文件:")
        for t in unique_times[:10]:
            print(f"  - 2025-12-06_{t}.txt ({t[:2]}:{t[2:]})")
        
        if len(unique_times) > 10:
            print(f"\n最后10个文件:")
            for t in unique_times[-10:]:
                print(f"  - 2025-12-06_{t}.txt ({t[:2]}:{t[2:]})")
        
        print(f"\n📄 最新文件: 2025-12-06_{unique_times[-1]}.txt")
    else:
        print("未找到txt文件")
    
    # 保持浏览器打开几秒以便查看
    print("\n5. 保持浏览器打开5秒...")
    time.sleep(5)
    
    browser.close()

print("\n" + "="*70)
