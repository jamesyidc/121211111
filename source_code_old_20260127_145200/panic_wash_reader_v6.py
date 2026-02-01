#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panic Wash Reader V6 - 解决50文件限制问题
通过点击排序按钮，按修改时间排序来获取最新文件
"""

import re
import asyncio
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

GOOGLE_DRIVE_FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
GOOGLE_DRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class PanicWashReaderV6:
    """使用按时间排序获取最新文件"""
    
    def __init__(self):
        self.folder_url = GOOGLE_DRIVE_FOLDER_URL
        self.latest_data = None
        self.last_update_time = None
    
    async def get_latest_file_content(self):
        """获取最新文件内容 - 使用时间排序"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                print(f"访问 Google Drive 文件夹...")
                await page.goto(self.folder_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)
                
                # 关键：点击排序，按修改时间倒序排列
                print("尝试按修改时间排序...")
                try:
                    # 查找"修改日期"或"修改时间"列标题并点击
                    # Google Drive界面可能有不同的选择器
                    
                    # 方法1：点击修改日期列标题
                    modified_header = page.locator('text=修改日期,text=Modified,text=修改时间').first
                    if await modified_header.count() > 0:
                        await modified_header.click()
                        await asyncio.sleep(2)
                        # 再点击一次确保是倒序（最新在前）
                        await modified_header.click()
                        await asyncio.sleep(2)
                        print("✓ 已按修改时间倒序排列")
                    else:
                        print("⚠ 未找到修改时间列标题，尝试其他方法...")
                        
                        # 方法2：使用键盘快捷键或右键菜单
                        # 右键点击文件列表区域
                        await page.keyboard.press('Escape')
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"排序失败，使用默认排序: {e}")
                
                # 获取页面内容
                await asyncio.sleep(2)
                content = await page.content()
                
                # 提取文件时间戳
                txt_files = re.findall(r'2025-12-06_(\d{4})\.txt', content)
                if not txt_files:
                    print("未找到txt文件")
                    await browser.close()
                    return None, None
                
                # 获取唯一文件并排序
                unique_times = sorted(set(txt_files))
                latest_time = unique_times[-1]
                
                print(f"找到 {len(unique_times)} 个文件")
                if len(unique_times) >= 5:
                    print(f"时间范围: {unique_times[0]} - {unique_times[-1]}")
                
                date_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
                latest_filename = f"{date_str}_{latest_time}.txt"
                
                print(f"目标文件: {latest_filename}")
                
                # 在页面中查找并打开这个文件
                file_elements = await page.query_selector_all('[data-tooltip*=".txt"]')
                
                for element in file_elements:
                    tooltip = await element.get_attribute('data-tooltip')
                    if latest_filename in tooltip:
                        await element.dblclick()
                        print("正在打开文件...")
                        await asyncio.sleep(3)
                        
                        text_content = await page.text_content('body')
                        await browser.close()
                        return text_content, latest_filename
                
                print("未能打开文件")
                await browser.close()
                return None, None
                
            except Exception as e:
                print(f"获取文件内容出错: {e}")
                await browser.close()
                return None, None
    
    def parse_content(self, content, filename):
        """解析txt文件内容"""
        try:
            lines = content.split('\n') if isinstance(content, str) else content
            
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
            
            # 解析汇总数据
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
            
            # 解析币种数据
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
            print(f"解析内容失败: {e}")
            return None
    
    async def get_data(self):
        """获取数据的公共接口"""
        content, filename = await self.get_latest_file_content()
        
        if not content:
            return None
        
        data = self.parse_content(content, filename)
        
        if data:
            self.latest_data = data
            self.last_update_time = datetime.now(BEIJING_TZ)
        
        return data


if __name__ == '__main__':
    async def test():
        reader = PanicWashReaderV6()
        data = await reader.get_data()
        
        if data:
            print("\n✓ 数据获取成功!")
            print(f"文件名: {data['filename']}")
            print(f"急涨: {data['rise_total']}")
            print(f"急跌: {data['fall_total']}")
            print(f"比值: {data['rise_fall_ratio']}")
            print(f"差值: {data['diff_result']}")
        else:
            print("\n✗ 数据获取失败")
    
    asyncio.run(test())
