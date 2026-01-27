import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import pytz
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

async def try_access():
    now = datetime.now(BEIJING_TZ)
    
    # 生成最近10个可能的文件名
    candidates = []
    base_minute = (now.minute // 10) * 10
    base_time = now.replace(minute=base_minute, second=0, microsecond=0)
    
    for i in range(-2, 2):  # 前20分钟到未来10分钟
        t = base_time + timedelta(minutes=i * 10)
        if t <= now:
            filename = t.strftime("%Y-%m-%d_%H%M.txt")
            candidates.append(filename)
    
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n尝试访问以下文件:")
    for f in candidates:
        print(f"  - {f}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 策略：先获取文件夹中所有文件的完整列表（通过查看源代码）
        folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
        print(f"\n访问文件夹: {folder_url}")
        
        await page.goto(folder_url, timeout=30000)
        await asyncio.sleep(3)
        
        # 尝试激活键盘快捷键来查看所有文件
        # Ctrl+A 全选
        await page.keyboard.press('Control+a')
        await asyncio.sleep(1)
        
        # 获取页面源代码
        html = await page.content()
        
        # 查找所有文件ID模式
        # Google Drive 文件ID通常是 33 个字符的字母数字字符串
        file_id_pattern = r'data-id="([A-Za-z0-9_-]{20,})"'
        file_ids = re.findall(file_id_pattern, html)
        
        print(f"\n找到 {len(file_ids)} 个文件ID")
        
        # 查找文件名和ID的对应关系
        for candidate in candidates:
            # 查找包含该文件名的片段
            pattern = f'{candidate}[^"]*data-id="([^"]+)"'
            match = re.search(pattern, html)
            
            if not match:
                # 反向查找
                pattern = f'data-id="([^"]+)"[^<]*{candidate}'
                match = re.search(pattern, html)
            
            if match:
                file_id = match.group(1)
                print(f"\n✓ 找到文件: {candidate}")
                print(f"  ID: {file_id}")
                
                # 尝试直接访问文件
                file_url = f"https://drive.google.com/file/d/{file_id}/view"
                print(f"  尝试访问: {file_url}")
                
                try:
                    await page.goto(file_url, timeout=15000)
                    await asyncio.sleep(2)
                    
                    content = await page.text_content('body')
                    
                    if content and len(content) > 500:
                        print(f"  ✓ 成功读取内容 ({len(content)} 字节)")
                        
                        # 检查是否包含关键数据
                        if '急涨' in content or '急跌' in content:
                            print(f"  ✓ 内容验证成功")
                            
                            # 提取数据
                            rise_match = re.search(r'急涨[：:](\d+)', content)
                            fall_match = re.search(r'急跌[：:](\d+)', content)
                            
                            if rise_match and fall_match:
                                print(f"\n  📊 数据预览:")
                                print(f"    急涨: {rise_match.group(1)}")
                                print(f"    急跌: {fall_match.group(1)}")
                            
                            await browser.close()
                            return {
                                'filename': candidate,
                                'file_id': file_id,
                                'content': content,
                                'success': True
                            }
                    else:
                        print(f"  ✗ 内容为空或过短")
                
                except Exception as e:
                    print(f"  ✗ 访问失败: {e}")
        
        await browser.close()
        return None

result = asyncio.run(try_access())

if result:
    print(f"\n{'='*70}")
    print(f"✅ 成功找到并读取最新文件")
    print(f"{'='*70}")
    print(f"文件名: {result['filename']}")
    print(f"文件ID: {result['file_id']}")
else:
    print(f"\n{'='*70}")
    print(f"❌ 未能找到任何可用文件")
    print(f"{'='*70}")
