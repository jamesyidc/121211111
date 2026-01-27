#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Panic Wash Reader V5 - 使用 Playwright 自动化浏览器
直接从 Google Drive 读取最新的 .txt 文件
每次调用都获取最新数据
"""

import re
import asyncio
from datetime import datetime
import pytz
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# Google Drive 文件夹配置
GOOGLE_DRIVE_FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
GOOGLE_DRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{GOOGLE_DRIVE_FOLDER_ID}"

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')


class PanicWashReaderV5:
    """使用 Playwright 从 Google Drive 读取数据"""
    
    def __init__(self):
        self.folder_url = GOOGLE_DRIVE_FOLDER_URL
        self.latest_data = None
        self.last_update_time = None
    
    async def get_latest_file_content(self):
        """
        使用 Playwright 获取最新文件内容
        Returns:
            tuple: (file_content, filename) 或 (None, None)
        """
        async with async_playwright() as p:
            # 启动浏览器（headless模式）
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                print(f"正在访问 Google Drive 文件夹...")
                # 访问文件夹页面
                await page.goto(self.folder_url, wait_until='networkidle', timeout=30000)
                
                # 等待页面加载
                await asyncio.sleep(3)
                
                # 滚动页面以加载更多文件（多次滚动）
                print("正在滚动页面加载更多文件...")
                for i in range(10):  # 滚动10次
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(0.5)
                
                # 再等待一下确保内容加载
                await asyncio.sleep(2)
                
                # 获取页面内容
                content = await page.content()
                
                # 从HTML中提取所有txt文件名
                txt_files = re.findall(r'2025-\d{2}-\d{2}_(\d{4})\.txt', content)
                if not txt_files:
                    print("未找到txt文件")
                    await browser.close()
                    return None, None
                
                # 获取最新文件
                txt_files_unique = list(dict.fromkeys(txt_files))
                txt_files_sorted = sorted(txt_files_unique)
                
                # 调试信息
                print(f"找到 {len(txt_files_sorted)} 个txt文件")
                if len(txt_files_sorted) >= 5:
                    print(f"最新5个: {txt_files_sorted[-5:]}")
                
                latest_time = txt_files_sorted[-1]
                
                # 构造日期部分
                beijing_now = datetime.now(BEIJING_TZ)
                date_str = beijing_now.strftime('%Y-%m-%d')
                latest_filename = f"{date_str}_{latest_time}.txt"
                
                print(f"找到最新文件: {latest_filename} ({latest_time[:2]}:{latest_time[2:]})")
                
                # 在页面中查找并点击该文件
                # 方法1: 尝试通过文件名定位
                try:
                    # 等待文件列表加载
                    await page.wait_for_selector('[data-tooltip*=".txt"]', timeout=5000)
                    
                    # 查找匹配的文件元素
                    file_elements = await page.query_selector_all('[data-tooltip*=".txt"]')
                    
                    target_element = None
                    for element in file_elements:
                        tooltip = await element.get_attribute('data-tooltip')
                        if latest_filename in tooltip:
                            target_element = element
                            break
                    
                    if target_element:
                        # 双击打开文件
                        await target_element.dblclick()
                        print("正在打开文件...")
                        
                        # 等待文件内容加载
                        await asyncio.sleep(3)
                        
                        # 获取文本内容
                        # Google Drive 预览页面的文本通常在特定的div中
                        text_content = await page.text_content('body')
                        
                        await browser.close()
                        return text_content, latest_filename
                    
                except Exception as e:
                    print(f"方法1失败: {e}")
                
                # 方法2: 通过HTML解析获取文件ID并直接访问
                print("尝试方法2: 直接解析文件ID...")
                
                # 在HTML中查找文件ID
                pattern = re.escape(latest_filename) + r'.*?"([-\w]{25,})"'
                match = re.search(pattern, content, re.DOTALL)
                
                if match:
                    file_id = match.group(1)
                    print(f"找到文件ID: {file_id}")
                    
                    # 直接访问文件
                    file_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                    response = await page.goto(file_url)
                    
                    if response and response.status == 200:
                        text_content = await page.content()
                        # 如果是下载链接，可能需要解析确认下载的内容
                        
                        # 尝试获取纯文本
                        try:
                            body_text = await page.text_content('body')
                            await browser.close()
                            return body_text, latest_filename
                        except:
                            await browser.close()
                            return text_content, latest_filename
                
                print("无法获取文件内容")
                await browser.close()
                return None, None
                
            except PlaywrightTimeout:
                print("页面加载超时")
                await browser.close()
                return None, None
            except Exception as e:
                print(f"获取文件内容出错: {e}")
                await browser.close()
                return None, None
    
    async def fetch_latest_data(self):
        """
        获取最新数据并解析
        Returns:
            dict: 解析后的数据，包含急涨、急跌等信息
        """
        content, filename = await self.get_latest_file_content()
        
        if not content:
            print("无法获取文件内容")
            return None
        
        # 解析内容
        data = self.parse_content(content, filename)
        
        if data:
            self.latest_data = data
            self.last_update_time = datetime.now(BEIJING_TZ)
            print(f"✓ 数据更新成功: {filename}")
        
        return data
    
    def parse_content(self, content, filename):
        """
        解析txt文件内容
        Args:
            content: 文件内容
            filename: 文件名
        Returns:
            dict: 解析后的数据
        """
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
        """
        获取数据的公共接口
        Returns:
            dict: 最新数据
        """
        return await self.fetch_latest_data()
    
    def get_cached_data(self):
        """
        获取缓存的数据（不重新请求）
        Returns:
            dict: 缓存的数据
        """
        return self.latest_data


# 同步包装函数
def get_latest_panic_wash_data():
    """
    同步方式获取最新数据（用于兼容现有代码）
    Returns:
        dict: 最新数据
    """
    reader = PanicWashReaderV5()
    loop = asyncio.get_event_loop()
    data = loop.run_until_complete(reader.get_data())
    return data


# 异步方式使用
async def get_latest_panic_wash_data_async():
    """
    异步方式获取最新数据
    Returns:
        dict: 最新数据
    """
    reader = PanicWashReaderV5()
    return await reader.get_data()


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("Panic Wash Reader V5 - Playwright 版本")
    print("=" * 60)
    
    async def test():
        reader = PanicWashReaderV5()
        
        print("\n正在获取最新数据...")
        data = await reader.get_data()
        
        if data:
            print("\n✓ 数据获取成功!")
            print(f"\n文件名: {data['filename']}")
            print(f"急涨: {data['rise_total']}")
            print(f"急跌: {data['fall_total']}")
            print(f"状态: {data['five_states']}")
            print(f"比值: {data['rise_fall_ratio']}")
            print(f"差值: {data['diff_result']}")
            print(f"绿色数量: {data['green_count']}")
            print(f"计次: {data['count_times']}")
            print(f"币种数量: {len(data['coins'])}")
            
            if data['coins']:
                print(f"\n前3个币种:")
                for i, coin in enumerate(data['coins'][:3], 1):
                    print(f"{i}. {coin['coin_name']}: 价格={coin['current_price']}, 24h涨幅={coin['change_24h']}%")
        else:
            print("\n✗ 数据获取失败")
    
    # 运行测试
    asyncio.run(test())
