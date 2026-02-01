import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import pytz
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

async def get_latest_file_data():
    """获取最新文件的数据"""
    
    # 计算最新文件名
    now = datetime.now(BEIJING_TZ)
    minute = (now.minute // 10) * 10
    latest_time = now.replace(minute=minute, second=0, microsecond=0)
    
    # 尝试最近的3个时间点
    candidates = []
    for i in range(3):
        t = latest_time - timedelta(minutes=i*10)
        filename = t.strftime("%Y-%m-%d_%H%M.txt")
        candidates.append({
            'filename': filename,
            'time_str': t.strftime('%H:%M')
        })
    
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n尝试获取最新数据，候选文件:")
    for c in candidates:
        print(f"  - {c['filename']} ({c['time_str']})")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for candidate in candidates:
            print(f"\n正在尝试: {candidate['filename']}...")
            
            try:
                # 访问文件夹
                folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
                await page.goto(folder_url, timeout=30000)
                await asyncio.sleep(2)
                
                # 滚动加载
                for _ in range(5):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(0.5)
                
                html = await page.content()
                
                # 检查文件是否存在
                if candidate['filename'] in html:
                    print(f"  ✓ 文件在文件夹中找到!")
                    
                    # 尝试提取文件ID
                    # 尝试多种模式
                    patterns = [
                        rf'{candidate["filename"]}[^<]*data-id="([^"]+)"',
                        rf'data-id="([^"]+)"[^<]*{candidate["filename"]}',
                    ]
                    
                    file_id = None
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            file_id = match.group(1)
                            break
                    
                    if file_id:
                        print(f"  ✓ 提取到文件ID: {file_id[:20]}...")
                        
                        # 直接访问文件
                        file_url = f"https://drive.google.com/file/d/{file_id}/view"
                        await page.goto(file_url, timeout=30000)
                        await asyncio.sleep(3)
                        
                        content = await page.text_content('body')
                        
                        if content and len(content) > 500:
                            print(f"  ✓ 成功读取内容 ({len(content)} 字节)")
                            
                            # 解析数据
                            data = parse_data(content, candidate['filename'])
                            
                            await browser.close()
                            return data
                    else:
                        print(f"  ✗ 未能提取文件ID")
                else:
                    print(f"  ⏭ 文件不在可见范围内（50文件限制）")
                
            except Exception as e:
                print(f"  ✗ 访问失败: {e}")
        
        await browser.close()
        return None

def parse_data(content, filename):
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
    
    for line in lines:
        line = line.strip()
        
        # 急涨
        if '急涨：' in line or '急涨:' in line:
            match = re.search(r'急涨[：:](\d+)', line)
            if match:
                data['急涨'] = int(match.group(1))
        
        # 急跌
        if '急跌：' in line or '急跌:' in line:
            match = re.search(r'急跌[：:](\d+)', line)
            if match:
                data['急跌'] = int(match.group(1))
        
        # 本轮急涨
        if '本轮急涨：' in line or '本轮急涨:' in line:
            match = re.search(r'本轮急涨[：:](\d+)', line)
            if match:
                data['本轮急涨'] = int(match.group(1))
        
        # 本轮急跌
        if '本轮急跌：' in line or '本轮急跌:' in line:
            match = re.search(r'本轮急跌[：:](\d+)', line)
            if match:
                data['本轮急跌'] = int(match.group(1))
        
        # 状态
        if '状态：' in line or '状态:' in line:
            match = re.search(r'状态[：:]([^\s\|]+)', line)
            if match:
                data['状态'] = match.group(1)
        
        # 比值
        if '比值：' in line or '比值:' in line:
            match = re.search(r'比值[：:]([\d.]+)', line)
            if match:
                data['比值'] = float(match.group(1))
        
        # 差值
        if '差值：' in line or '差值:' in line:
            match = re.search(r'差值[：:]([-\d.]+)', line)
            if match:
                data['差值'] = float(match.group(1))
        
        # 比价最低
        if '比价最低：' in line or '比价最低:' in line:
            match = re.search(r'比价最低[：:](\d+)', line)
            if match:
                data['比价最低'] = int(match.group(1))
        
        # 比价创新高
        if '比价创新高：' in line or '比价创新高:' in line:
            match = re.search(r'比价创新高[：:](\d+)', line)
            if match:
                data['比价创新高'] = int(match.group(1))
    
    return data

def print_data(data):
    """打印数据"""
    if not data:
        print("\n❌ 未能获取数据")
        return
    
    print("\n" + "="*70)
    print(f"📊 最新文件数据")
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
data = asyncio.run(get_latest_file_data())
print_data(data)
