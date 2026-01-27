import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import pytz
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

async def get_file(target_file):
    """获取指定文件"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
            await page.goto(folder_url, timeout=30000)
            await asyncio.sleep(2)
            
            # 使用键盘搜索
            await page.keyboard.press('/')
            await asyncio.sleep(1)
            await page.keyboard.type(target_file)
            await asyncio.sleep(2)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
            
            html = await page.content()
            
            if target_file in html:
                print(f"  ✓ 找到文件!")
                
                # 提取文件ID
                pos = html.find(target_file)
                snippet = html[max(0, pos-1000):min(len(html), pos+1000)]
                
                id_match = re.search(r'data-id="([^"]+)"', snippet)
                if not id_match:
                    id_match = re.search(r'"id":"([^"]+)"', snippet)
                
                if id_match:
                    file_id = id_match.group(1)
                    print(f"  ✓ 文件ID: {file_id[:30]}...")
                    
                    # 直接访问文件
                    file_url = f"https://drive.google.com/file/d/{file_id}/view"
                    await page.goto(file_url, timeout=30000)
                    await asyncio.sleep(3)
                    
                    content = await page.inner_text('body')
                    
                    if content and len(content) > 500:
                        print(f"  ✓ 成功获取内容 ({len(content)} 字节)")
                        
                        await browser.close()
                        return {
                            'filename': target_file,
                            'content': content
                        }
            else:
                print(f"  ✗ 未找到文件")
            
            await browser.close()
            return None
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            await browser.close()
            return None

async def main():
    now = datetime.now(BEIJING_TZ)
    
    # 计算可能的最新文件
    minute = (now.minute // 10) * 10
    latest_time = now.replace(minute=minute, second=0, microsecond=0)
    
    # 尝试当前时间和前10分钟
    target_files = [
        latest_time.strftime("%Y-%m-%d_%H%M.txt"),
        (latest_time - timedelta(minutes=10)).strftime("%Y-%m-%d_%H%M.txt"),
    ]
    
    from datetime import timedelta
    target_files = [
        "2025-12-06_1230.txt",
        "2025-12-06_1220.txt",
    ]
    
    print("="*70)
    print(f"🎯 尝试获取最新文件")
    print(f"⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    for target_file in target_files:
        print(f"\n📄 尝试: {target_file}")
        result = await get_file(target_file)
        
        if result:
            # 保存内容
            with open(f'content_{target_file}', 'w', encoding='utf-8') as f:
                f.write(result['content'])
            
            # 解析数据
            content = result['content']
            data = {}
            
            for line in content.split('\n'):
                if '急涨：' in line:
                    match = re.search(r'急涨：(\d+)', line)
                    if match:
                        data['急涨'] = int(match.group(1))
                if '急跌：' in line:
                    match = re.search(r'急跌：(\d+)', line)
                    if match:
                        data['急跌'] = int(match.group(1))
                if '状态：' in line:
                    match = re.search(r'状态：([^\s]+)', line)
                    if match:
                        data['状态'] = match.group(1)
                if '比值：' in line:
                    match = re.search(r'比值：(\d+)', line)
                    if match:
                        data['比值'] = int(match.group(1))
                if '差值：' in line:
                    match = re.search(r'差值：([-\d]+)', line)
                    if match:
                        data['差值'] = int(match.group(1))
                if '比价最低' in line:
                    match = re.search(r'比价最低\s+(\d+)\s+(\d+)', line)
                    if match:
                        data['比价最低'] = int(match.group(1))
                if '比价创新高' in line:
                    match = re.search(r'比价创新高\s+(\d+)\s+(\d+)', line)
                    if match:
                        data['比价创新高'] = int(match.group(1))
            
            print(f"\n  📊 提取的数据:")
            print(f"    急涨: {data.get('急涨', 'N/A')}")
            print(f"    急跌: {data.get('急跌', 'N/A')}")
            print(f"    状态: {data.get('状态', 'N/A')}")
            print(f"    比值: {data.get('比值', 'N/A')}")
            print(f"    差值: {data.get('差值', 'N/A')}")
            print(f"    比价最低: {data.get('比价最低', 'N/A')}")
            print(f"    比价创新高: {data.get('比价创新高', 'N/A')}")
            
            return result
    
    print("\n❌ 未能获取任何文件")
    return None

asyncio.run(main())
