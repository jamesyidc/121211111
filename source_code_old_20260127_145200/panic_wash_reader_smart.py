#!/usr/bin/env python3
"""
智能Panic Wash Reader
业务逻辑：不依赖文件列表，直接根据当前时间推算最新文件名并访问
"""

import re
import asyncio
from datetime import datetime, timedelta
import pytz
from playwright.async_api import async_playwright
import requests

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class PanicWashReaderSmart:
    """智能读取器 - 基于时间推算"""
    
    def __init__(self):
        self.latest_data = None
    
    def get_expected_latest_filename(self):
        """根据当前时间推算最新文件名"""
        now = datetime.now(BEIJING_TZ)
        
        # 对齐到10分钟
        minute = (now.minute // 10) * 10
        latest_time = now.replace(minute=minute, second=0, microsecond=0)
        
        # 尝试当前时间和前一个10分钟
        candidates = [
            latest_time,
            latest_time - timedelta(minutes=10),
            latest_time - timedelta(minutes=20)
        ]
        
        return [t.strftime("2025-12-06_%H%M.txt") for t in candidates]
    
    async def try_access_file_directly(self, filename):
        """
        尝试直接访问文件
        方法：在Google Drive搜索该文件名
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 访问Google Drive搜索
                search_url = f"https://drive.google.com/drive/search?q={filename}"
                print(f"  尝试搜索: {search_url}")
                
                await page.goto(search_url, timeout=30000)
                await asyncio.sleep(3)
                
                content = await page.content()
                
                # 检查是否找到文件
                if filename in content:
                    print(f"  ✓ 在搜索中找到文件")
                    
                    # 尝试点击打开
                    file_element = page.locator(f'[data-tooltip*="{filename}"]').first
                    if await file_element.count() > 0:
                        await file_element.dblclick()
                        await asyncio.sleep(3)
                        
                        text_content = await page.text_content('body')
                        await browser.close()
                        return text_content
                
            except Exception as e:
                print(f"  访问失败: {e}")
            
            await browser.close()
            return None
    
    def parse_content(self, content, filename):
        """解析文件内容"""
        if not content:
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
            
            # 解析币种
            in_coin_section = False
            for line in lines:
                if '[超级列表框_首页开始]' in line:
                    in_coin_section = True
                    continue
                elif '[超级列表框_首页结束]' in line:
                    break
                
                if in_coin_section and '|' in line:
                    parts = line.strip().split('|')
                    if len(parts) >= 14:
                        try:
                            coin = {
                                'seq_num': int(parts[0]),
                                'coin_name': parts[1],
                                'rise_speed': float(parts[2]) if parts[2] else 0.0,
                                'rise_signal': int(parts[3]) if parts[3] else 0,
                                'fall_signal': int(parts[4]) if parts[4] else 0,
                                'current_price': float(parts[13]) if parts[13] else 0.0,
                                'change_24h': float(parts[9]) if parts[9] else 0.0,
                            }
                            data['coins'].append(coin)
                        except:
                            pass
            
            return data
        except Exception as e:
            print(f"解析失败: {e}")
            return None
    
    async def get_data(self):
        """获取最新数据"""
        print("\n" + "="*60)
        print("智能Panic Wash Reader - 基于时间推算")
        print("="*60)
        
        # 获取候选文件名
        candidates = self.get_expected_latest_filename()
        print(f"\n候选文件名:")
        for i, filename in enumerate(candidates):
            print(f"  {i+1}. {filename}")
        
        # 逐个尝试
        for filename in candidates:
            print(f"\n尝试访问: {filename}")
            content = await self.try_access_file_directly(filename)
            
            if content:
                data = self.parse_content(content, filename)
                if data and data.get('rise_total', 0) >= 0:  # 验证数据有效
                    print(f"\n✅ 成功获取数据!")
                    print(f"  文件: {filename}")
                    print(f"  急涨: {data['rise_total']}")
                    print(f"  急跌: {data['fall_total']}")
                    self.latest_data = data
                    return data
        
        print("\n❌ 所有候选文件都无法访问")
        return None


if __name__ == '__main__':
    async def test():
        reader = PanicWashReaderSmart()
        data = await reader.get_data()
        
        if data:
            print(f"\n📊 最终数据:")
            print(f"  文件名: {data['filename']}")
            print(f"  急涨: {data['rise_total']}")
            print(f"  急跌: {data['fall_total']}")
            print(f"  比值: {data['rise_fall_ratio']}")
            print(f"  差值: {data['diff_result']}")
            print(f"  币种数量: {len(data['coins'])}")
        else:
            print(f"\n数据获取失败")
    
    asyncio.run(test())
