# 尝试使用OAuth认证（即使没有credentials）
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    
    print("尝试PyDrive2...")
    # 尝试无认证模式
    gauth = GoogleAuth()
    print("认证对象创建成功")
except Exception as e:
    print(f"PyDrive2失败: {e}")

# 尝试使用selenium + 更激进的滚动
print("\n尝试使用不同的网页解析策略...")

from playwright.sync_api import sync_playwright
import re
import time

FOLDER_URL = "https://drive.google.com/drive/folders/1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()
    
    print("访问Google Drive...")
    page.goto(FOLDER_URL, wait_until='networkidle', timeout=60000)
    
    # 更激进的滚动策略
    print("执行激进滚动...")
    for i in range(30):  # 滚动30次
        # 滚到底部
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(1000)
        
        # 滚到顶部
        page.evaluate('window.scrollTo(0, 0)')
        page.wait_for_timeout(500)
        
        # 再滚到底部
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(1000)
        
        # 检查是否有新内容
        content = page.content()
        times = re.findall(r'2025-12-06_(\d{4})', content)
        unique_count = len(set(times))
        
        if i % 5 == 0:
            print(f"  第{i+1}次滚动，找到 {unique_count} 个文件")
        
        if unique_count > 50:
            print(f"✓ 突破50个限制！找到 {unique_count} 个文件")
            break
    
    # 最终统计
    content = page.content()
    times = re.findall(r'2025-12-06_(\d{4})', content)
    unique_times = sorted(set(times))
    
    print(f"\n最终结果: {len(unique_times)} 个唯一文件")
    print(f"最新文件: 2025-12-06_{unique_times[-1]}.txt")
    
    browser.close()

