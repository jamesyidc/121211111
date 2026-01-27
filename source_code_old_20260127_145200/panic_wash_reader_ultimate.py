#!/usr/bin/env python3
"""
终极Panic Wash Reader
方案：搜索文件 -> 提取文件ID -> 直接下载内容
"""

import re
import asyncio
from datetime import datetime, timedelta
import pytz
from playwright.async_api import async_playwright
import requests

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class PanicWashReaderUltimate:
    """终极读取器"""
    
    def __init__(self):
        self.latest_data = None
    
    def get_expected_latest_filename(self):
        """根据当前时间推算最新文件名"""
        now = datetime.now(BEIJING_TZ)
        minute = (now.minute // 10) * 10
        latest_time = now.replace(minute=minute, second=0, microsecond=0)
        
        candidates = [
            latest_time,
            latest_time - timedelta(minutes=10),
            latest_time - timedelta(minutes=20)
        ]
        
        return [t.strftime("2025-12-06_%H%M.txt") for t in candidates]
    
    async def get_file_id_from_search(self, filename):
        """从搜索页面提取文件ID"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                search_url = f"https://drive.google.com/drive/search?q={filename}"
                await page.goto(search_url, timeout=30000)
                await asyncio.sleep(3)
                
                # 获取页面HTML
                html = await page.content()
                
                # 查找文件ID - Google Drive的文件ID通常是28-40个字符的字符串
                # 模式1: 在data-id属性中
                id_pattern1 = r'data-id="([a-zA-Z0-9_-]{28,})"'
                matches = re.findall(id_pattern1, html)
                
                # 模式2: 在URL中 /file/d/{ID}/
                id_pattern2 = r'/file/d/([a-zA-Z0-9_-]{28,})/'
                matches2 = re.findall(id_pattern2, html)
                
                # 模式3: 直接搜索文件名附近的ID
                filename_context = html.find(filename)
                if filename_context > 0:
                    context = html[max(0, filename_context-500):min(len(html), filename_context+500)]
                    id_pattern3 = r'([a-zA-Z0-9_-]{28,40})'
                    context_ids = re.findall(id_pattern3, context)
                    
                    # 过滤掉明显不是文件ID的
                    for cid in context_ids:
                        if len(cid) >= 28 and len(cid) <= 40:
                            print(f"  找到候选ID: {cid}")
                            await browser.close()
                            return cid
                
                all_ids = list(set(matches + matches2))
                if all_ids:
                    file_id = all_ids[0]
                    print(f"  ✓ 找到文件ID: {file_id}")
                    await browser.close()
                    return file_id
                    
            except Exception as e:
                print(f"  提取ID失败: {e}")
            
            await browser.close()
            return None
    
    def download_file_content(self, file_id):
        """通过文件ID直接下载内容"""
        try:
            # 方法1: 使用export链接
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            print(f"  尝试下载: {download_url}")
            
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                print(f"  ✓ 下载成功")
                return response.text
            
            # 方法2: 使用open链接
            open_url = f"https://drive.google.com/file/d/{file_id}/view"
            print(f"  尝试访问: {open_url}")
            
            # 这需要用Playwright打开
            return None
            
        except Exception as e:
            print(f"  下载失败: {e}")
            return None
    
    async def try_download_via_playwright(self, file_id):
        """使用Playwright下载文件"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 直接访问文件URL
                file_url = f"https://drive.google.com/file/d/{file_id}/view"
                await page.goto(file_url, timeout=30000)
                await asyncio.sleep(3)
                
                # 获取文本内容
                text_content = await page.text_content('body')
                
                await browser.close()
                return text_content
                
            except Exception as e:
                print(f"  Playwright下载失败: {e}")
            
            await browser.close()
            return None
    
    def parse_content(self, content, filename):
        """解析文件内容"""
        if not content or len(content) < 10:
            return None
        
        try:
            data = {
                'filename': filename,
                'rise_total': 0,
                'fall_total': 0,
                'five_states': '',
                'rise_fall_ratio': 0.0,
                'diff_result': 0.0,
                'green_count': 0,
                'count_times': 0,
                'coins': []
            }
            
            lines = content.split('\n')
            
            for line in lines:
                if '急涨：' in line:
                    match = re.search(r'急涨：(\d+)', line)
                    if match:
                        data['rise_total'] = int(match.group(1))
                elif '急跌：' in line:
                    match = re.search(r'急跌：(\d+)', line)
                    if match:
                        data['fall_total'] = int(match.group(1))
                elif '状态：' in line:
                    match = re.search(r'状态：([^\s]+)', line)
                    if match:
                        data['five_states'] = match.group(1)
                elif '比值：' in line:
                    match = re.search(r'比值：([\d.]+)', line)
                    if match:
                        data['rise_fall_ratio'] = float(match.group(1))
                elif '差值：' in line:
                    match = re.search(r'差值：([-\d.]+)', line)
                    if match:
                        data['diff_result'] = float(match.group(1))
                elif '绿色数量=' in line:
                    match = re.search(r'绿色数量=(\d+)', line)
                    if match:
                        data['green_count'] = int(match.group(1))
                elif '计次=' in line:
                    match = re.search(r'计次=(\d+)', line)
                    if match:
                        data['count_times'] = int(match.group(1))
            
            # 验证数据有效性
            if data['rise_total'] >= 0 or data['fall_total'] >= 0:
                return data
            
            return None
        except Exception as e:
            print(f"  解析失败: {e}")
            return None
    
    async def get_data(self):
        """获取最新数据"""
        print("\n" + "="*70)
        print("终极Panic Wash Reader")
        print("方案：搜索 -> 提取ID -> 下载内容")
        print("="*70)
        
        candidates = self.get_expected_latest_filename()
        print(f"\n候选文件:")
        for i, filename in enumerate(candidates):
            print(f"  {i+1}. {filename}")
        
        for filename in candidates:
            print(f"\n{'='*70}")
            print(f"尝试: {filename}")
            print(f"{'='*70}")
            
            # 步骤1: 获取文件ID
            file_id = await self.get_file_id_from_search(filename)
            
            if file_id:
                # 步骤2: 下载内容
                print(f"\n步骤2: 下载文件内容...")
                content = self.download_file_content(file_id)
                
                if not content:
                    # 尝试Playwright方法
                    content = await self.try_download_via_playwright(file_id)
                
                # 步骤3: 解析数据
                if content:
                    print(f"\n步骤3: 解析数据...")
                    data = self.parse_content(content, filename)
                    
                    if data:
                        print(f"\n✅ 成功获取数据!")
                        print(f"  文件: {filename}")
                        print(f"  急涨: {data['rise_total']}")
                        print(f"  急跌: {data['fall_total']}")
                        self.latest_data = data
                        return data
        
        print(f"\n❌ 所有方法都失败了")
        return None


if __name__ == '__main__':
    async def test():
        reader = PanicWashReaderUltimate()
        data = await reader.get_data()
        
        if data:
            print(f"\n" + "="*70)
            print(f"📊 最终数据")
            print(f"="*70)
            print(f"文件名: {data['filename']}")
            print(f"急涨: {data['rise_total']}")
            print(f"急跌: {data['fall_total']}")
            print(f"比值: {data['rise_fall_ratio']}")
            print(f"差值: {data['diff_result']}")
        else:
            print(f"\n数据获取失败")
    
    asyncio.run(test())
