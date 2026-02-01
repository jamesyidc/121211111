import sys
from playwright.sync_api import sync_playwright
import re
from datetime import datetime
import pytz

# Google Drive folder URL
FOLDER_URL = "https://drive.google.com/drive/folders/1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

def get_latest_file():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"访问 Google Drive 文件夹...")
        page.goto(FOLDER_URL, timeout=60000)
        page.wait_for_timeout(5000)
        
        # 多次滚动以加载更多内容
        print("开始滚动页面以加载所有文件...")
        for i in range(10):  # 滚动10次
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            print(f"  第 {i+1} 次滚动完成")
        
        # 获取页面完整HTML
        html_content = page.content()
        
        # 提取所有文件名（包括完整HTML中的所有匹配）
        pattern = r'2025-\d{2}-\d{2}_\d{4}\.txt'
        all_files = re.findall(pattern, html_content)
        unique_files = sorted(set(all_files))
        
        print(f"\n找到 {len(unique_files)} 个唯一的txt文件")
        
        if unique_files:
            # 显示最后10个文件
            print("\n最新的10个文件:")
            for f in unique_files[-10:]:
                print(f"  {f}")
            
            latest_file = unique_files[-1]
            print(f"\n✅ 最新文件: {latest_file}")
            
            # 提取时间
            time_match = re.search(r'_(\d{2})(\d{2})\.txt', latest_file)
            if time_match:
                hour = time_match.group(1)
                minute = time_match.group(2)
                print(f"   文件时间: {hour}:{minute}")
                
                # 计算距离现在多久
                beijing_tz = pytz.timezone('Asia/Shanghai')
                now = datetime.now(beijing_tz)
                print(f"   当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("❌ 未找到任何txt文件")
        
        browser.close()

if __name__ == "__main__":
    get_latest_file()
