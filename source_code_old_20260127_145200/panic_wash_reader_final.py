#!/usr/bin/env python3
"""
最终版Panic Wash Reader
策略：根据时间推测文件名，直接尝试下载（不依赖搜索）
+10分钟查找，找不到就+1分钟微调，找到后以新时间为基准继续+10分钟
"""

import re
import asyncio
from datetime import datetime, timedelta
import pytz
from playwright.async_api import async_playwright
import json
import os

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
STATE_FILE = 'last_found_time.json'


class PanicWashReaderFinal:
    """自适应时间调整的读取器（终极版）"""
    
    def __init__(self):
        self.latest_data = None
        self.last_found_time = self.load_last_found_time()
    
    def load_last_found_time(self):
        """加载上次成功找到文件的时间"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    time_str = data.get('last_found_time')
                    if time_str:
                        return datetime.fromisoformat(time_str)
            except:
                pass
        return None
    
    def save_last_found_time(self, found_time):
        """保存成功找到文件的时间"""
        with open(STATE_FILE, 'w') as f:
            json.dump({
                'last_found_time': found_time.isoformat(),
                'timestamp': datetime.now(BEIJING_TZ).isoformat()
            }, f, indent=2)
    
    def generate_search_candidates(self):
        """
        生成搜索候选列表
        策略：
        1. 如果有上次记录，从上次时间+10分钟开始
        2. 如果找不到，+1分钟微调
        3. 最多尝试10次（10分钟范围内的每一分钟）
        """
        now = datetime.now(BEIJING_TZ)
        candidates = []
        
        if self.last_found_time:
            # 从上次时间+10分钟开始
            base_time = self.last_found_time + timedelta(minutes=10)
            print(f"📍 上次找到时间: {self.last_found_time.strftime('%H:%M')}")
            print(f"🎯 从 {base_time.strftime('%H:%M')} 开始搜索 (+10分钟)")
        else:
            # 首次运行，从当前时间对齐到10分钟开始
            minute = (now.minute // 10) * 10
            base_time = now.replace(minute=minute, second=0, microsecond=0)
            print(f"🆕 首次运行，从 {base_time.strftime('%H:%M')} 开始搜索")
        
        # 生成候选时间：base_time, base_time+1min, base_time+2min, ..., base_time+9min
        for i in range(11):  # 0到10分钟，共11个候选
            candidate_time = base_time + timedelta(minutes=i)
            # 不能超过当前时间+1分钟（允许一点点延迟）
            if candidate_time <= now + timedelta(minutes=1):
                filename = candidate_time.strftime("%Y-%m-%d_%H%M.txt")
                candidates.append({
                    'time': candidate_time,
                    'filename': filename,
                    'time_str': candidate_time.strftime('%H:%M'),
                    'offset': i  # 相对于base_time的偏移量
                })
        
        return candidates
    
    async def try_download_file(self, filename):
        """
        尝试直接下载文件
        通过访问文件夹并查找特定文件来获取其内容
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # 访问文件夹
                folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
                await page.goto(folder_url, timeout=30000)
                await asyncio.sleep(2)
                
                # 多次滚动以加载更多文件
                for _ in range(3):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(0.5)
                
                html = await page.content()
                
                # 检查文件是否在页面中
                if filename not in html:
                    await browser.close()
                    return None
                
                print(f"      ✓ 在文件夹中找到文件")
                
                # 尝试提取文件链接/ID
                # 方法1: 通过 data-tooltip 查找元素
                try:
                    # 查找包含文件名的元素
                    file_elements = await page.query_selector_all(f'[aria-label*="{filename}"]')
                    
                    if not file_elements:
                        file_elements = await page.query_selector_all(f'div:has-text("{filename}")')
                    
                    if file_elements:
                        print(f"      ✓ 找到 {len(file_elements)} 个匹配元素")
                        
                        # 尝试点击第一个元素打开文件
                        element = file_elements[0]
                        
                        # 右键点击以获取菜单
                        await element.click(button='right')
                        await asyncio.sleep(1)
                        
                        # 查找"在新标签页中打开"选项
                        new_tab_option = await page.query_selector('text="在新标签页中打开"')
                        if not new_tab_option:
                            new_tab_option = await page.query_selector('text="Open in new tab"')
                        
                        if new_tab_option:
                            # 监听新页面
                            async with context.expect_page() as new_page_info:
                                await new_tab_option.click()
                            
                            new_page = await new_page_info.value
                            await new_page.wait_for_load_state('load')
                            await asyncio.sleep(2)
                            
                            # 获取文本内容
                            text_content = await new_page.text_content('body')
                            
                            await browser.close()
                            return text_content
                        else:
                            # 直接双击打开
                            await element.dblclick()
                            await asyncio.sleep(3)
                            
                            # 检查是否打开了预览
                            text_content = await page.text_content('body')
                            
                            if text_content and len(text_content) > 500:
                                await browser.close()
                                return text_content
                    
                except Exception as e:
                    print(f"      ⚠ 打开文件时出错: {e}")
                
                await browser.close()
                return None
                
            except Exception as e:
                print(f"      ✗ 下载失败: {e}")
                await browser.close()
                return None
    
    def parse_content(self, content, filename):
        """解析文件内容"""
        if not content or len(content) < 50:
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
                if '急涨：' in line or '急涨:' in line:
                    match = re.search(r'急涨[：:](\d+)', line)
                    if match:
                        data['rise_total'] = int(match.group(1))
                elif '急跌：' in line or '急跌:' in line:
                    match = re.search(r'急跌[：:](\d+)', line)
                    if match:
                        data['fall_total'] = int(match.group(1))
                elif '状态：' in line or '状态:' in line:
                    match = re.search(r'状态[：:]([^\s]+)', line)
                    if match:
                        data['five_states'] = match.group(1)
                elif '比值：' in line or '比值:' in line:
                    match = re.search(r'比值[：:]([\d.]+)', line)
                    if match:
                        data['rise_fall_ratio'] = float(match.group(1))
                elif '差值：' in line or '差值:' in line:
                    match = re.search(r'差值[：:]([-\d.]+)', line)
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
            
            # 验证数据有效性
            if data['rise_total'] >= 0 and data['fall_total'] >= 0:
                return data
            
            return None
        except Exception as e:
            print(f"      ✗ 解析失败: {e}")
            return None
    
    async def get_data(self):
        """获取最新数据"""
        print("\n" + "="*70)
        print("🚀 自适应 Panic Wash Reader (终极版)")
        print("📋 策略: +10分钟查找，找不到就+1分钟微调")
        print("="*70)
        
        # 生成候选列表
        candidates = self.generate_search_candidates()
        
        if not candidates:
            print("\n❌ 没有可搜索的候选文件")
            return None
        
        print(f"\n📝 候选文件列表 ({len(candidates)}个):")
        for i, c in enumerate(candidates):
            offset_str = f"+{c['offset']}分钟" if c['offset'] > 0 else "基准时间"
            print(f"  {i+1}. {c['filename']} ({c['time_str']}) [{offset_str}]")
        
        # 逐个尝试
        for i, candidate in enumerate(candidates):
            print(f"\n🔍 [{i+1}/{len(candidates)}] 尝试: {candidate['filename']} ({candidate['time_str']})")
            
            content = await self.try_download_file(candidate['filename'])
            
            if content:
                # 解析数据
                data = self.parse_content(content, candidate['filename'])
                
                if data:
                    print(f"\n✅ 成功获取数据!")
                    print(f"  📄 文件: {candidate['filename']}")
                    print(f"  ⏰ 时间: {candidate['time_str']}")
                    print(f"  📈 急涨: {data['rise_total']}")
                    print(f"  📉 急跌: {data['fall_total']}")
                    print(f"  📊 比值: {data['rise_fall_ratio']}")
                    print(f"  ➖ 差值: {data['diff_result']}")
                    print(f"  🪙 币种: {len(data['coins'])}")
                    
                    # 保存成功找到的时间
                    self.save_last_found_time(candidate['time'])
                    print(f"\n  💾 已保存时间基准: {candidate['time_str']}")
                    
                    next_time = candidate['time'] + timedelta(minutes=10)
                    print(f"  ⏭️  下次将从 {next_time.strftime('%H:%M')} 开始搜索 (+10分钟)")
                    
                    self.latest_data = data
                    return data
            else:
                print(f"      ⏭  未找到，尝试下一个 (+1分钟)")
        
        print(f"\n❌ 所有候选文件都未找到")
        print(f"💡 提示: 可能需要等待新文件生成")
        return None


if __name__ == '__main__':
    async def test():
        reader = PanicWashReaderFinal()
        data = await reader.get_data()
        
        if data:
            print(f"\n" + "="*70)
            print(f"📊 最终结果")
            print(f"="*70)
            print(f"文件名: {data['filename']}")
            print(f"急涨: {data['rise_total']}")
            print(f"急跌: {data['fall_total']}")
            print(f"比值: {data['rise_fall_ratio']}")
            print(f"差值: {data['diff_result']}")
            print(f"币种数量: {len(data['coins'])}")
            print(f"="*70)
        else:
            print(f"\n❌ 数据获取失败")
    
    asyncio.run(test())
