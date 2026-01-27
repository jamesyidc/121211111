import asyncio
from playwright.async_api import async_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

async def download_latest():
    """下载最新可见文件"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 访问文件夹
            folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
            print(f"访问文件夹...\n")
            await page.goto(folder_url, timeout=30000)
            await asyncio.sleep(2)
            
            # 滚动加载
            for _ in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(0.5)
            
            html = await page.content()
            
            # 查找最新文件
            txt_files = re.findall(r'(2025-12-\d{2}_\d{4})\.txt', html)
            unique_files = sorted(set(txt_files), reverse=True)
            
            if not unique_files:
                print("未找到任何txt文件")
                await browser.close()
                return None
            
            latest_file = unique_files[0] + '.txt'
            print(f"最新可见文件: {latest_file}\n")
            
            # 提取文件ID
            pos = html.find(latest_file)
            if pos > 0:
                snippet = html[max(0, pos-500):min(len(html), pos+500)]
                id_match = re.search(r'data-id="([^"]+)"', snippet)
                
                if id_match:
                    file_id = id_match.group(1)
                    print(f"文件ID: {file_id}\n")
                    
                    # 使用下载URL而不是预览URL
                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    print(f"下载URL: {download_url}\n")
                    
                    # 访问下载URL
                    response = await page.goto(download_url, timeout=30000)
                    await asyncio.sleep(2)
                    
                    # 获取内容
                    content = await page.content()
                    
                    # 如果是HTML，尝试提取body中的文本
                    if '<html' in content.lower():
                        # 获取纯文本
                        text_content = await page.inner_text('body')
                        content = text_content
                    
                    print(f"✓ 成功获取内容 ({len(content)} 字节)\n")
                    
                    # 保存到文件
                    with open('latest_file_content.txt', 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print("内容已保存到 latest_file_content.txt\n")
                    
                    # 解析数据
                    data = parse_content(content, latest_file)
                    
                    await browser.close()
                    return data
            
            await browser.close()
            return None
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()
            return None

def parse_content(content, filename):
    """解析文件内容"""
    data = {
        'filename': filename,
        '急涨': None,
        '急跌': None,
        '本轮急涨': None,
        '本轮急跌': None,
        '状态': None,
        '比值': None,
        '差值': None,
        '比价最低': None,
        '比价创新高': None,
    }
    
    lines = content.split('\n')
    
    print("文件内容前50行:")
    print("-" * 70)
    for i, line in enumerate(lines[:50]):
        if line.strip():  # 只打印非空行
            print(f"{i+1:3d}: {line.strip()[:100]}")
    print("-" * 70)
    print()
    
    for line in lines:
        line = line.strip()
        
        # 急涨（排除本轮）
        if '急涨' in line and '本轮' not in line:
            match = re.search(r'急涨[：:](\d+)', line)
            if match and data['急涨'] is None:
                data['急涨'] = int(match.group(1))
        
        # 急跌（排除本轮）
        if '急跌' in line and '本轮' not in line:
            match = re.search(r'急跌[：:](\d+)', line)
            if match and data['急跌'] is None:
                data['急跌'] = int(match.group(1))
        
        # 本轮急涨
        if '本轮急涨' in line:
            match = re.search(r'本轮急涨[：:](\d+)', line)
            if match:
                data['本轮急涨'] = int(match.group(1))
        
        # 本轮急跌
        if '本轮急跌' in line:
            match = re.search(r'本轮急跌[：:](\d+)', line)
            if match:
                data['本轮急跌'] = int(match.group(1))
        
        # 状态
        if '状态' in line:
            match = re.search(r'状态[：:]([^\s\|]+)', line)
            if match and data['状态'] is None:
                data['状态'] = match.group(1)
        
        # 比值
        if '比值' in line:
            match = re.search(r'比值[：:]([.\d]+)', line)
            if match and data['比值'] is None:
                data['比值'] = float(match.group(1))
        
        # 差值
        if '差值' in line:
            match = re.search(r'差值[：:]([-.d]+)', line)
            if match and data['差值'] is None:
                try:
                    data['差值'] = float(match.group(1))
                except:
                    pass
        
        # 比价最低
        if '比价最低' in line:
            match = re.search(r'比价最低[：:](\d+)', line)
            if match:
                data['比价最低'] = int(match.group(1))
        
        # 比价创新高
        if '比价创新高' in line:
            match = re.search(r'比价创新高[：:](\d+)', line)
            if match:
                data['比价创新高'] = int(match.group(1))
    
    return data

def print_result(data):
    """打印结果"""
    if not data:
        print("\n❌ 未能获取数据")
        return
    
    print("="*70)
    print(f"📊 文件数据")
    print("="*70)
    print(f"\n📄 文件名: {data['filename']}")
    print(f"\n📈 急涨: {data['急涨']}")
    print(f"📉 急跌: {data['急跌']}")
    print(f"🔼 本轮急涨: {data['本轮急涨']}")
    print(f"🔽 本轮急跌: {data['本轮急跌']}")
    print(f"📍 状态: {data['状态']}")
    print(f"📊 比值: {data['比值']}")
    print(f"➖ 差值: {data['差值']}")
    print(f"💵 比价最低: {data['比价最低']}")
    print(f"🚀 比价创新高: {data['比价创新高']}")
    print("\n" + "="*70)

# 运行
result = asyncio.run(download_latest())
print_result(result)
