import asyncio
from playwright.async_api import async_playwright
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"

async def read_latest_visible():
    """读取文件夹中最新可见文件的数据"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 访问文件夹
            folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
            print(f"访问文件夹: {folder_url}\n")
            await page.goto(folder_url, timeout=30000)
            await asyncio.sleep(2)
            
            # 滚动加载
            for _ in range(5):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(0.5)
            
            html = await page.content()
            
            # 查找所有txt文件
            txt_files = re.findall(r'(2025-12-\d{2}_\d{4})\.txt', html)
            unique_files = sorted(set(txt_files), reverse=True)
            
            if not unique_files:
                print("未找到任何txt文件")
                await browser.close()
                return None
            
            latest_file = unique_files[0] + '.txt'
            print(f"文件夹中最新可见文件: {latest_file}")
            print(f"共找到 {len(unique_files)} 个唯一文件\n")
            
            # 尝试提取文件ID并打开
            patterns = [
                rf'{latest_file}[^<]*data-id="([^"]+)"',
                rf'data-id="([^"]+)"[^<]*{latest_file}',
            ]
            
            file_id = None
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    file_id = match.group(1)
                    break
            
            if not file_id:
                print("未能提取文件ID")
                
                # 尝试另一种方法：在HTML中查找所有data-id
                # 保存HTML供分析
                with open('folder_debug.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                
                print("HTML已保存到 folder_debug.html")
                
                # 查找latest_file周围的上下文
                pos = html.find(latest_file)
                if pos > 0:
                    snippet = html[max(0, pos-500):min(len(html), pos+500)]
                    
                    # 在snippet中查找data-id
                    id_match = re.search(r'data-id="([^"]+)"', snippet)
                    if id_match:
                        file_id = id_match.group(1)
                        print(f"从上下文中提取到文件ID: {file_id[:20]}...")
            
            if file_id:
                print(f"文件ID: {file_id[:30]}...\n")
                
                # 访问文件
                file_url = f"https://drive.google.com/file/d/{file_id}/view"
                print(f"访问文件: {file_url}\n")
                
                await page.goto(file_url, timeout=30000)
                await asyncio.sleep(3)
                
                # 获取内容
                content = await page.text_content('body')
                
                if content and len(content) > 500:
                    print(f"✓ 成功读取内容 ({len(content)} 字节)\n")
                    
                    # 解析数据
                    data = parse_content(content, latest_file)
                    
                    await browser.close()
                    return data
                else:
                    print(f"内容为空或过短")
            
            await browser.close()
            return None
            
        except Exception as e:
            print(f"错误: {e}")
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
    
    # 打印前30行以便调试
    print("文件内容前30行:")
    print("-" * 70)
    for i, line in enumerate(lines[:30]):
        print(f"{i+1:3d}: {line[:100]}")
    print("-" * 70)
    print()
    
    for line in lines:
        line = line.strip()
        
        # 急涨
        if '急涨' in line and '本轮' not in line:
            match = re.search(r'急涨[：:](\d+)', line)
            if match:
                data['急涨'] = int(match.group(1))
        
        # 急跌
        if '急跌' in line and '本轮' not in line:
            match = re.search(r'急跌[：:](\d+)', line)
            if match:
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
            if match:
                data['状态'] = match.group(1)
        
        # 比值
        if '比值' in line:
            match = re.search(r'比值[：:]([.\d]+)', line)
            if match:
                data['比值'] = float(match.group(1))
        
        # 差值
        if '差值' in line:
            match = re.search(r'差值[：:]([-.\d]+)', line)
            if match:
                data['差值'] = float(match.group(1))
        
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
    print(f"📊 最新可见文件数据")
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
result = asyncio.run(read_latest_visible())
print_result(result)
