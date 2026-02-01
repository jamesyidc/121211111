import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import pytz
import re
import time

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

async def try_all_methods():
    """尝试所有可能的方法获取12:20文件"""
    
    now = datetime.now(BEIJING_TZ)
    
    # 目标文件
    target_files = [
        "2025-12-06_1220.txt",
        "2025-12-06_1210.txt", 
        "2025-12-06_1200.txt",
    ]
    
    print("="*70)
    print(f"🎯 目标: 获取真实的最新文件内容")
    print(f"⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for target_file in target_files:
            print(f"\n{'='*70}")
            print(f"📄 尝试文件: {target_file}")
            print(f"{'='*70}")
            
            # 方法1: 直接构造下载链接（尝试不同的文件ID模式）
            print("\n方法1: 尝试通过文件夹搜索获取文件...")
            
            folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
            
            try:
                await page.goto(folder_url, timeout=30000)
                await asyncio.sleep(2)
                
                # 尝试使用搜索功能
                print("  尝试激活搜索框...")
                
                # 按 / 键激活搜索
                await page.keyboard.press('/')
                await asyncio.sleep(1)
                
                # 输入文件名
                await page.keyboard.type(target_file)
                await asyncio.sleep(2)
                
                # 按回车搜索
                await page.keyboard.press('Enter')
                await asyncio.sleep(3)
                
                html = await page.content()
                
                # 保存搜索结果HTML
                with open(f'search_{target_file}.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                
                print(f"  搜索结果HTML已保存到 search_{target_file}.html")
                
                # 检查是否找到文件
                if target_file in html:
                    print(f"  ✓ 搜索到文件!")
                    
                    # 查找文件ID
                    pos = html.find(target_file)
                    snippet = html[max(0, pos-1000):min(len(html), pos+1000)]
                    
                    # 尝试多种ID模式
                    id_patterns = [
                        r'data-id="([^"]+)"',
                        r'"id":"([^"]+)"',
                        r'/file/d/([A-Za-z0-9_-]+)/',
                        r'docid=([A-Za-z0-9_-]+)',
                    ]
                    
                    file_id = None
                    for pattern in id_patterns:
                        matches = re.findall(pattern, snippet)
                        if matches:
                            file_id = matches[0]
                            print(f"  ✓ 提取到文件ID: {file_id[:30]}...")
                            break
                    
                    if file_id:
                        # 尝试下载
                        download_urls = [
                            f"https://drive.google.com/uc?export=download&id={file_id}",
                            f"https://drive.google.com/file/d/{file_id}/view",
                            f"https://docs.google.com/document/d/{file_id}/export?format=txt",
                        ]
                        
                        for url in download_urls:
                            try:
                                print(f"\n  尝试URL: {url[:60]}...")
                                await page.goto(url, timeout=20000)
                                await asyncio.sleep(2)
                                
                                content = await page.inner_text('body')
                                
                                if content and len(content) > 500 and '急涨' in content:
                                    print(f"  ✅ 成功获取内容! ({len(content)} 字节)")
                                    
                                    # 保存内容
                                    with open(f'content_{target_file}', 'w', encoding='utf-8') as f:
                                        f.write(content)
                                    
                                    await browser.close()
                                    return {
                                        'filename': target_file,
                                        'content': content,
                                        'method': 'search + download'
                                    }
                            except Exception as e:
                                print(f"  ✗ URL失败: {e}")
                else:
                    print(f"  ✗ 搜索未找到文件")
                
            except Exception as e:
                print(f"  ✗ 方法1失败: {e}")
            
            # 返回文件夹主页
            await page.goto(folder_url, timeout=30000)
            await asyncio.sleep(2)
        
        await browser.close()
        return None

async def main():
    result = await try_all_methods()
    
    if result:
        print("\n" + "="*70)
        print("✅ 成功获取文件内容!")
        print("="*70)
        print(f"文件名: {result['filename']}")
        print(f"方法: {result['method']}")
        print(f"内容长度: {len(result['content'])} 字节")
        
        # 快速解析数据
        content = result['content']
        
        data = {}
        for line in content.split('\n'):
            if '急涨' in line and '本轮' not in line:
                match = re.search(r'急涨[：:](\d+)', line)
                if match:
                    data['急涨'] = match.group(1)
            if '急跌' in line and '本轮' not in line:
                match = re.search(r'急跌[：:](\d+)', line)
                if match:
                    data['急跌'] = match.group(1)
            if '状态' in line:
                match = re.search(r'状态[：:]([^\s\|]+)', line)
                if match:
                    data['状态'] = match.group(1)
            if '比值' in line:
                match = re.search(r'比值[：:]([.\d]+)', line)
                if match:
                    data['比值'] = match.group(1)
            if '差值' in line:
                match = re.search(r'差值[：:]([-.\d]+)', line)
                if match:
                    data['差值'] = match.group(1)
        
        print("\n提取的数据:")
        for key, value in data.items():
            print(f"  {key}: {value}")
        
        return result
    else:
        print("\n" + "="*70)
        print("❌ 所有方法均失败")
        print("="*70)
        return None

asyncio.run(main())
