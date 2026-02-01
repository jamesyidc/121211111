from playwright.sync_api import sync_playwright
import re
import json

FOLDER_URL = "https://drive.google.com/drive/folders/1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

print("="*70)
print("按修改时间获取最新文件")
print("="*70)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("\n访问 Google Drive 文件夹...")
    page.goto(FOLDER_URL, wait_until='networkidle', timeout=60000)
    page.wait_for_timeout(5000)
    
    # 尝试从页面的JavaScript数据中提取文件信息
    print("\n尝试从页面数据中提取文件信息...")
    
    # 执行JavaScript获取页面中的数据
    result = page.evaluate('''() => {
        // 尝试获取Google Drive页面中的数据
        const scripts = document.querySelectorAll('script');
        let filesData = [];
        
        for (let script of scripts) {
            const content = script.textContent;
            // 查找包含文件信息的数据结构
            if (content && (content.includes('2025-12-06') || content.includes('.txt'))) {
                // 尝试提取文件名和时间信息
                const matches = content.matchAll(/2025-12-06_(\d{4})\\.txt/g);
                for (let match of matches) {
                    filesData.push({
                        name: match[0],
                        time: match[1]
                    });
                }
            }
        }
        
        // 也从DOM中提取
        const elements = document.querySelectorAll('[data-tooltip], [aria-label], [title]');
        for (let el of elements) {
            const tooltip = el.getAttribute('data-tooltip') || el.getAttribute('aria-label') || el.getAttribute('title') || '';
            const matches = tooltip.matchAll(/2025-12-06_(\d{4})\\.txt/g);
            for (let match of matches) {
                filesData.push({
                    name: match[0],
                    time: match[1]
                });
            }
        }
        
        return filesData;
    }''')
    
    if result:
        # 去重并按时间排序
        unique_files = {}
        for item in result:
            unique_files[item['time']] = item['name']
        
        sorted_times = sorted(unique_files.keys())
        
        print(f"\n从页面数据中提取到 {len(sorted_times)} 个文件")
        
        if sorted_times:
            print(f"时间范围: {sorted_times[0][:2]}:{sorted_times[0][2:]} - {sorted_times[-1][:2]}:{sorted_times[-1][2:]}")
            
            print(f"\n最后10个文件:")
            for t in sorted_times[-10:]:
                print(f"  - {unique_files[t]} ({t[:2]}:{t[2:]})")
            
            latest_time = sorted_times[-1]
            print(f"\n✅ 最新文件: {unique_files[latest_time]}")
            print(f"   文件时间: {latest_time[:2]}:{latest_time[2:]}")
    else:
        print("未能从JavaScript数据中提取文件信息")
    
    # 回退方法：直接从HTML提取
    print("\n使用HTML提取方法...")
    content = page.content()
    times = re.findall(r'2025-12-06_(\d{4})\.txt', content)
    unique_times = sorted(set(times))
    
    print(f"HTML中找到 {len(unique_times)} 个文件")
    if unique_times:
        print(f"时间范围: {unique_times[0][:2]}:{unique_times[0][2:]} - {unique_times[-1][:2]}:{unique_times[-1][2:]}")
        print(f"\n✅ HTML中最新文件: 2025-12-06_{unique_times[-1]}.txt ({unique_times[-1][:2]}:{unique_times[-1][2:]})")
    
    browser.close()

print("\n" + "="*70)
print("注意：由于Google Drive的50文件显示限制，")
print("如果文件夹有超过50个文件，只能看到前50个。")
print("="*70)
