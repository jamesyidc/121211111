#!/usr/bin/env python3
"""
智能最新文件查找器
业务逻辑：文件每10分钟生成一个，按时间命名
解决方案：根据当前时间推算最新文件名，直接尝试访问
"""

from datetime import datetime, timedelta
import pytz
from playwright.sync_api import sync_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def generate_expected_filenames(count=20):
    """
    根据当前时间生成预期的最新文件名列表
    参数：count - 生成多少个候选文件名（往回推）
    """
    now = datetime.now(BEIJING_TZ)
    filenames = []
    
    # 从当前时间往回推，每10分钟一个
    for i in range(count):
        # 计算时间（往回推i个10分钟）
        target_time = now - timedelta(minutes=i*10)
        
        # 对齐到10分钟整数
        minute = (target_time.minute // 10) * 10
        target_time = target_time.replace(minute=minute, second=0, microsecond=0)
        
        filename = target_time.strftime("2025-12-06_%H%M.txt")
        filenames.append({
            'filename': filename,
            'time_str': target_time.strftime("%H:%M"),
            'timestamp': target_time
        })
    
    return filenames

def try_access_file_by_search(page, filename):
    """
    尝试通过搜索功能访问特定文件
    """
    print(f"\n  尝试搜索文件: {filename}")
    
    try:
        # 按 Ctrl+F 或点击搜索
        page.keyboard.press('Control+f')
        page.wait_for_timeout(1000)
        
        # 输入文件名
        search_input = page.locator('input[type="search"], input[aria-label*="搜索"]').first
        if search_input.count() > 0:
            search_input.fill(filename)
            page.wait_for_timeout(2000)
            
            # 检查搜索结果
            content = page.content()
            if filename in content:
                print(f"  ✓ 在搜索结果中找到文件")
                return True
        
    except Exception as e:
        print(f"  搜索失败: {e}")
    
    return False

def try_construct_direct_url(filename):
    """
    尝试构造文件的直接访问URL
    业务逻辑：Google Drive的文件有固定的URL格式
    """
    # 这需要知道文件ID，但我们可以尝试猜测规律
    # 通常格式是: https://drive.google.com/file/d/{FILE_ID}/view
    pass

def smart_find_latest():
    """
    智能查找最新文件
    """
    print("="*70)
    print("智能最新文件查找器")
    print("="*70)
    
    # 1. 生成候选文件名
    candidates = generate_expected_filenames(count=20)
    
    print(f"\n根据当前时间生成 {len(candidates)} 个候选文件名:")
    print(f"时间范围: {candidates[-1]['time_str']} - {candidates[0]['time_str']}")
    
    # 显示前5个最新的候选
    print(f"\n最可能的5个最新文件:")
    for i, item in enumerate(candidates[:5]):
        print(f"  {i+1}. {item['filename']} ({item['time_str']})")
    
    # 2. 访问Google Drive并尝试验证
    print(f"\n开始验证...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"\n访问文件夹...")
        page.goto(FOLDER_URL, timeout=30000)
        page.wait_for_timeout(3000)
        
        # 获取页面HTML
        html = page.content()
        
        # 3. 在HTML中查找候选文件
        found_files = []
        for candidate in candidates:
            if candidate['filename'] in html:
                found_files.append(candidate)
                print(f"  ✓ 找到: {candidate['filename']}")
        
        if found_files:
            latest = found_files[0]
            print(f"\n✅ 最新文件: {latest['filename']}")
            print(f"   时间: {latest['time_str']}")
            
            # 4. 尝试打开并读取该文件
            print(f"\n尝试打开文件...")
            try:
                file_element = page.locator(f'[data-tooltip*="{latest["filename"]}"]').first
                if file_element.count() > 0:
                    file_element.dblclick()
                    page.wait_for_timeout(3000)
                    
                    text_content = page.text_content('body')
                    
                    # 解析数据
                    rise_match = re.search(r'急涨：(\d+)', text_content)
                    fall_match = re.search(r'急跌：(\d+)', text_content)
                    
                    if rise_match and fall_match:
                        print(f"\n📊 文件数据:")
                        print(f"   急涨: {rise_match.group(1)}")
                        print(f"   急跌: {fall_match.group(1)}")
                        
                        browser.close()
                        return {
                            'filename': latest['filename'],
                            'content': text_content
                        }
            except Exception as e:
                print(f"  打开文件失败: {e}")
        else:
            print(f"\n❌ 在页面中未找到任何候选文件")
            print(f"   这意味着所有候选文件都在50个文件限制之外")
            
            # 5. 回退方案：直接构造文件内容获取请求
            print(f"\n尝试回退方案...")
            print(f"   根据业务逻辑，最新文件应该是: {candidates[0]['filename']}")
            print(f"   建议：定期清理旧文件，或使用API访问")
        
        browser.close()
        return None

# 执行查找
result = smart_find_latest()

print("\n" + "="*70)
print("结论：")
print("="*70)
if result:
    print(f"✅ 成功找到并读取最新文件: {result['filename']}")
else:
    print(f"❌ 由于50文件限制，无法访问最新文件")
    print(f"\n业务逻辑解决方案：")
    print(f"1. 定期自动删除旧文件（保留最近50个）")
    print(f"2. 采集器直接根据时间推算文件名访问")
    print(f"3. 使用Google Drive API")
