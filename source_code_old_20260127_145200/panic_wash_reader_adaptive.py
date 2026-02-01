#!/usr/bin/env python3
"""
自适应Panic Wash Reader
策略：+10分钟查找，找不到就+1分钟微调，找到后以新时间为基准继续+10分钟
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


class PanicWashReaderAdaptive:
    """自适应时间调整的读取器"""
    
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
            }, f)
    
    def generate_search_candidates(self):
        """
        生成搜索候选列表
        策略：
        1. 如果有上次记录，从上次时间+10分钟开始
        2. 如果找不到，+1分钟微调
        3. 最多尝试20次（10分钟范围内的每一分钟）
        """
        now = datetime.now(BEIJING_TZ)
        candidates = []
        
        if self.last_found_time:
            # 从上次时间+10分钟开始
            base_time = self.last_found_time + timedelta(minutes=10)
            print(f"  上次找到时间: {self.last_found_time.strftime('%H:%M')}")
            print(f"  从 {base_time.strftime('%H:%M')} 开始搜索")
        else:
            # 首次运行，从当前时间对齐到10分钟开始
            minute = (now.minute // 10) * 10
            base_time = now.replace(minute=minute, second=0, microsecond=0)
            print(f"  首次运行，从 {base_time.strftime('%H:%M')} 开始搜索")
        
        # 生成候选时间：base_time, base_time+1min, base_time+2min, ..., base_time+9min
        for i in range(10):
            candidate_time = base_time + timedelta(minutes=i)
            # 不能超过当前时间
            if candidate_time <= now:
                filename = candidate_time.strftime("%Y-%m-%d_%H%M.txt")
                candidates.append({
                    'time': candidate_time,
                    'filename': filename,
                    'time_str': candidate_time.strftime('%Y-%m-%d %H:%M')
                })
        
        return candidates
    
    async def search_file(self, filename):
        """搜索文件并尝试获取内容"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # 搜索文件
                search_url = f"https://drive.google.com/drive/search?q={filename}"
                await page.goto(search_url, timeout=30000)
                await asyncio.sleep(3)
                
                html = await page.content()
                
                # 检查是否找到文件
                if filename not in html:
                    await browser.close()
                    return None
                
                print(f"    ✓ 找到文件")
                
                # 提取文件ID（从 data-id 属性）
                file_id_match = re.search(r'data-id="([^"]+)"', html)
                if file_id_match:
                    file_id = file_id_match.group(1)
                    print(f"    ✓ 提取到文件ID: {file_id[:20]}...")
                    
                    # 访问文件预览页
                    preview_url = f"https://drive.google.com/file/d/{file_id}/view"
                    await page.goto(preview_url, timeout=30000)
                    await asyncio.sleep(3)
                    
                    # 尝试获取文本内容
                    text_content = await page.text_content('body')
                    
                    if text_content and len(text_content) > 100:
                        print(f"    ✓ 成功读取内容 ({len(text_content)} 字节)")
                        await browser.close()
                        return text_content
                    else:
                        print(f"    ⚠ 内容太短或为空")
                
                await browser.close()
                return None
                
            except Exception as e:
                print(f"    ✗ 搜索失败: {e}")
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
            
            # 验证数据有效性
            if data['rise_total'] >= 0 and data['fall_total'] >= 0:
                return data
            
            return None
        except Exception as e:
            print(f"    ✗ 解析失败: {e}")
            return None
    
    async def get_data(self):
        """获取最新数据"""
        print("\n" + "="*70)
        print("自适应Panic Wash Reader")
        print("策略: +10分钟查找，找不到就+1分钟微调")
        print("="*70)
        
        # 生成候选列表
        candidates = self.generate_search_candidates()
        
        if not candidates:
            print("\n没有可搜索的候选文件")
            return None
        
        print(f"\n候选文件列表 ({len(candidates)}个):")
        for i, c in enumerate(candidates):
            print(f"  {i+1}. {c['filename']} ({c['time_str']})")
        
        # 逐个搜索
        for candidate in candidates:
            print(f"\n尝试: {candidate['filename']} ({candidate['time_str']})")
            
            content = await self.search_file(candidate['filename'])
            
            if content:
                # 解析数据
                data = self.parse_content(content, candidate['filename'])
                
                if data:
                    print(f"\n✅ 成功获取数据!")
                    print(f"  文件: {candidate['filename']}")
                    print(f"  时间: {candidate['time_str']}")
                    print(f"  急涨: {data['rise_total']}")
                    print(f"  急跌: {data['fall_total']}")
                    print(f"  比值: {data['rise_fall_ratio']}")
                    print(f"  差值: {data['diff_result']}")
                    
                    # 保存成功找到的时间
                    self.save_last_found_time(candidate['time'])
                    print(f"\n  ✓ 已保存时间基准: {candidate['time_str']}")
                    print(f"  ✓ 下次将从 {(candidate['time'] + timedelta(minutes=10)).strftime('%H:%M')} 开始搜索")
                    
                    self.latest_data = data
                    return data
        
        print(f"\n❌ 所有候选文件都未找到")
        return None


if __name__ == '__main__':
    async def test():
        reader = PanicWashReaderAdaptive()
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
        else:
            print(f"\n数据获取失败")
    
    asyncio.run(test())
