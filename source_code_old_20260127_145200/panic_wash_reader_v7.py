#!/usr/bin/env python3
"""
Panic Wash Reader V7 - 终极自适应版本
策略：+10分钟查找，找不到就+1分钟微调
特点：
1. 尝试从文件夹获取最新可见文件
2. 使用时间推测策略查找新文件
3. 支持手动文件ID配置（用于突破50文件限制）
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
MANUAL_IDS_FILE = 'manual_file_ids.json'  # 手动文件ID配置


class PanicWashReaderV7:
    """终极自适应版本"""
    
    def __init__(self):
        self.latest_data = None
        self.last_found_time = self.load_last_found_time()
        self.manual_ids = self.load_manual_ids()
    
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
    
    def save_last_found_time(self, found_time, filename=None):
        """保存成功找到文件的时间"""
        data = {
            'last_found_time': found_time.isoformat(),
            'timestamp': datetime.now(BEIJING_TZ).isoformat()
        }
        if filename:
            data['filename'] = filename
        
        with open(STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_manual_ids(self):
        """加载手动配置的文件ID"""
        if os.path.exists(MANUAL_IDS_FILE):
            try:
                with open(MANUAL_IDS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def get_file_id_by_name(self, filename):
        """通过文件名获取文件ID（如果有手动配置）"""
        return self.manual_ids.get(filename)
    
    async def get_latest_from_folder(self):
        """从文件夹获取最新可见文件"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
                await page.goto(folder_url, timeout=30000)
                await asyncio.sleep(2)
                
                # 滚动几次
                for _ in range(3):
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await asyncio.sleep(0.5)
                
                html = await page.content()
                
                # 查找所有txt文件
                txt_files = re.findall(r'(2025-12-\d{2}_\d{4})\.txt', html)
                
                if txt_files:
                    # 找到最新的
                    unique_files = sorted(set(txt_files), reverse=True)
                    latest_file = unique_files[0] + '.txt'
                    
                    print(f"  📁 文件夹中最新可见文件: {latest_file}")
                    
                    # 解析时间
                    match = re.match(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})', unique_files[0])
                    if match:
                        year, month, day, hour, minute = map(int, match.groups())
                        file_time = datetime(year, month, day, hour, minute, tzinfo=BEIJING_TZ)
                        
                        await browser.close()
                        return {
                            'filename': latest_file,
                            'time': file_time,
                            'source': 'folder'
                        }
                
                await browser.close()
                return None
                
            except Exception as e:
                print(f"  ⚠ 文件夹访问失败: {e}")
                await browser.close()
                return None
    
    def generate_candidates(self, start_time):
        """生成候选文件列表"""
        now = datetime.now(BEIJING_TZ)
        candidates = []
        
        # 从start_time开始，生成+10, +11, +12, ... +19分钟的候选
        for offset in range(11):  # 0-10分钟
            candidate_time = start_time + timedelta(minutes=offset)
            
            # 不能超过当前时间
            if candidate_time <= now:
                filename = candidate_time.strftime("%Y-%m-%d_%H%M.txt")
                candidates.append({
                    'time': candidate_time,
                    'filename': filename,
                    'time_str': candidate_time.strftime('%H:%M'),
                    'offset': offset
                })
        
        return candidates
    
    async def try_access_file(self, filename, file_id=None):
        """尝试访问文件"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                if file_id:
                    # 如果有文件ID，直接访问
                    file_url = f"https://drive.google.com/file/d/{file_id}/view"
                    print(f"      使用文件ID访问: {file_id[:15]}...")
                else:
                    # 否则，先从文件夹查找
                    folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
                    await page.goto(folder_url, timeout=20000)
                    await asyncio.sleep(2)
                    
                    html = await page.content()
                    
                    # 检查文件是否可见
                    if filename not in html:
                        await browser.close()
                        return None
                    
                    # 文件可见，尝试提取ID
                    file_id_match = re.search(rf'{filename}[^<]*data-id="([^"]+)"', html)
                    if not file_id_match:
                        file_id_match = re.search(rf'data-id="([^"]+)"[^<]*{filename}', html)
                    
                    if file_id_match:
                        file_id = file_id_match.group(1)
                        file_url = f"https://drive.google.com/file/d/{file_id}/view"
                    else:
                        await browser.close()
                        return None
                
                # 访问文件
                await page.goto(file_url, timeout=20000)
                await asyncio.sleep(2)
                
                # 获取内容
                content = await page.text_content('body')
                
                await browser.close()
                
                if content and len(content) > 500:
                    return content
                
                return None
                
            except Exception as e:
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
                if '急涨' in line:
                    match = re.search(r'急涨[：:](\d+)', line)
                    if match:
                        data['rise_total'] = int(match.group(1))
                elif '急跌' in line:
                    match = re.search(r'急跌[：:](\d+)', line)
                    if match:
                        data['fall_total'] = int(match.group(1))
                elif '状态' in line:
                    match = re.search(r'状态[：:]([^\s]+)', line)
                    if match:
                        data['five_states'] = match.group(1)
                elif '比值' in line:
                    match = re.search(r'比值[：:]([\d.]+)', line)
                    if match:
                        data['rise_fall_ratio'] = float(match.group(1))
                elif '差值' in line:
                    match = re.search(r'差值[：:]([-\d.]+)', line)
                    if match:
                        data['diff_result'] = float(match.group(1))
            
            # 解析币种（简化版）
            in_coin_section = False
            for line in lines:
                if '[超级列表框_首页开始]' in line:
                    in_coin_section = True
                    continue
                elif '[超级列表框_首页结束]' in line:
                    break
                
                if in_coin_section and '|' in line:
                    parts = line.strip().split('|')
                    if len(parts) >= 5:
                        try:
                            coin = {
                                'seq_num': int(parts[0]),
                                'coin_name': parts[1],
                            }
                            data['coins'].append(coin)
                        except:
                            pass
            
            # 验证数据
            if data['rise_total'] >= 0 or data['fall_total'] >= 0:
                return data
            
            return None
        except Exception as e:
            return None
    
    async def get_data(self):
        """获取最新数据"""
        print("\n" + "="*70)
        print("🚀 Panic Wash Reader V7 - 终极自适应版本")
        print("📋 策略: +10分钟，找不到则+1分钟微调")
        print("="*70 + "\n")
        
        # 第一步：尝试从文件夹获取最新可见文件
        print("📂 步骤1: 检查文件夹中最新可见文件...")
        folder_latest = await self.get_latest_from_folder()
        
        # 确定搜索起点
        if self.last_found_time:
            # 有历史记录，从历史记录+10分钟开始
            start_time = self.last_found_time + timedelta(minutes=10)
            print(f"\n📌 步骤2: 从上次记录开始搜索")
            print(f"  上次成功时间: {self.last_found_time.strftime('%H:%M')}")
            print(f"  本次搜索起点: {start_time.strftime('%H:%M')} (+10分钟)")
        elif folder_latest:
            # 没有历史记录，但文件夹有最新文件，从最新文件+10分钟开始
            start_time = folder_latest['time'] + timedelta(minutes=10)
            print(f"\n📌 步骤2: 从文件夹最新文件开始搜索")
            print(f"  文件夹最新时间: {folder_latest['time'].strftime('%H:%M')}")
            print(f"  本次搜索起点: {start_time.strftime('%H:%M')} (+10分钟)")
        else:
            # 完全没有参考，从当前时间对齐到10分钟开始
            now = datetime.now(BEIJING_TZ)
            minute = (now.minute // 10) * 10
            start_time = now.replace(minute=minute, second=0, microsecond=0)
            print(f"\n📌 步骤2: 首次运行，从当前时间开始")
            print(f"  当前时间: {now.strftime('%H:%M')}")
            print(f"  搜索起点: {start_time.strftime('%H:%M')}")
        
        # 生成候选列表
        candidates = self.generate_candidates(start_time)
        
        if not candidates:
            print("\n❌ 没有可搜索的候选文件")
            return None
        
        print(f"\n📝 候选文件列表 ({len(candidates)}个):")
        for i, c in enumerate(candidates):
            offset_str = f"+{c['offset']}分钟" if c['offset'] > 0 else "起点"
            # 检查是否有手动配置的ID
            has_id = "🔑" if self.get_file_id_by_name(c['filename']) else "  "
            print(f"  {has_id} {i+1}. {c['filename']} ({c['time_str']}) [{offset_str}]")
        
        # 第三步：逐个尝试候选文件
        print(f"\n🔍 步骤3: 开始自适应搜索...")
        
        for i, candidate in enumerate(candidates):
            print(f"\n  [{i+1}/{len(candidates)}] {candidate['filename']} ({candidate['time_str']})")
            
            # 获取文件ID（如果有手动配置）
            file_id = self.get_file_id_by_name(candidate['filename'])
            
            # 尝试访问
            content = await self.try_access_file(candidate['filename'], file_id)
            
            if content:
                # 解析数据
                data = self.parse_content(content, candidate['filename'])
                
                if data:
                    print(f"    ✅ 成功!")
                    print(f"    📈 急涨: {data['rise_total']}")
                    print(f"    📉 急跌: {data['fall_total']}")
                    print(f"    📊 比值: {data['rise_fall_ratio']}")
                    print(f"    ➖ 差值: {data['diff_result']}")
                    print(f"    🪙 币种: {len(data['coins'])}")
                    
                    # 保存成功时间
                    self.save_last_found_time(candidate['time'], candidate['filename'])
                    
                    next_time = candidate['time'] + timedelta(minutes=10)
                    print(f"\n    💾 已保存时间基准")
                    print(f"    ⏭️  下次将从 {next_time.strftime('%H:%M')} 开始搜索")
                    
                    self.latest_data = data
                    return data
            else:
                print(f"    ⏭  未找到，尝试+1分钟...")
        
        print(f"\n❌ 所有候选文件都未找到")
        print(f"💡 提示:")
        print(f"  1. 可能需要等待新文件生成")
        print(f"  2. 如果文件已存在但超出50个限制，请配置 manual_file_ids.json")
        
        return None


async def main():
    """主函数"""
    reader = PanicWashReaderV7()
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
        return data
    else:
        print(f"\n❌ 数据获取失败")
        return None


if __name__ == '__main__':
    asyncio.run(main())
