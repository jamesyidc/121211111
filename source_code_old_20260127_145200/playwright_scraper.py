#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Playwright从网页抓取动态加载的得分数据
"""

import asyncio
from playwright.async_api import async_playwright
import json
import re
from datetime import datetime
from typing import Dict, List

class PlaywrightScoreScraper:
    """使用Playwright抓取得分数据"""
    
    def __init__(self):
        self.urls = {
            'source_1': 'https://3000-i42fq2f1mk8544uuc8pew-5c13a017.sandbox.novita.ai/score_overview.html',
            'source_2': 'https://3000-itkyuobnbphje7wgo4xbk-c07dda5e.sandbox.novita.ai/score_overview.html'
        }
        self.time_ranges = ['3m', '1h', '3h', '6h', '12h', '24h']
    
    async def scrape_page(self, page, url: str, source_name: str) -> Dict:
        """抓取单个页面的数据"""
        print(f"\n📡 正在加载: {url}")
        
        try:
            # 访问页面
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待表格加载
            await page.wait_for_selector('table tbody tr', timeout=10000)
            print(f"✅ {source_name}: 页面加载完成")
            
            # 等待额外时间让数据完全加载
            await asyncio.sleep(3)
            
            # 获取所有表格行
            rows = await page.query_selector_all('table tbody tr')
            print(f"📊 {source_name}: 找到 {len(rows)} 行数据")
            
            data = {}
            
            for row in rows:
                # 获取所有单元格
                cells = await row.query_selector_all('td')
                
                if len(cells) < 4:
                    continue
                
                # 第一列是币种名称
                coin_cell = cells[0]
                coin_text = await coin_cell.inner_text()
                coin_name = coin_text.strip()
                
                if not coin_name:
                    continue
                
                # 标准化币种名称
                if not coin_name.endswith('-USDT-SWAP'):
                    coin_name = f"{coin_name}-USDT-SWAP"
                
                print(f"  处理币种: {coin_name}")
                
                data[coin_name] = {}
                
                # 解析各时间段的数据
                # 表格结构：币种 | 3m(做多做空差值) | 1h(做多做空差值) | ...
                cell_idx = 1
                for time_range in self.time_ranges:
                    if cell_idx + 2 < len(cells):
                        try:
                            long_cell = cells[cell_idx]
                            short_cell = cells[cell_idx + 1]
                            diff_cell = cells[cell_idx + 2]
                            
                            long_text = await long_cell.inner_text()
                            short_text = await short_cell.inner_text()
                            diff_text = await diff_cell.inner_text()
                            
                            long_score = self.extract_number(long_text)
                            short_score = self.extract_number(short_text)
                            diff_score = self.extract_number(diff_text)
                            
                            if long_score is not None and short_score is not None:
                                data[coin_name][time_range] = {
                                    'long_score': long_score,
                                    'short_score': short_score,
                                    'diff': diff_score if diff_score is not None else (long_score - short_score)
                                }
                                print(f"    {time_range}: 做多={long_score:.2f}, 做空={short_score:.2f}, 差值={data[coin_name][time_range]['diff']:.2f}")
                        except Exception as e:
                            print(f"    ⚠️ {time_range}: 解析失败 - {e}")
                        
                        cell_idx += 3
                
                # 如果没有获取到任何时间段的数据，删除这个币种
                if not data[coin_name]:
                    del data[coin_name]
            
            return data
            
        except Exception as e:
            print(f"❌ {source_name}: 抓取失败 - {e}")
            return {}
    
    def extract_number(self, text: str) -> float:
        """从文本中提取数字"""
        if not text:
            return None
        
        # 移除所有非数字、小数点和负号的字符
        cleaned = re.sub(r'[^\d.\-+]', '', text.strip())
        if not cleaned or cleaned in ['-', '+', '.']:
            return None
        
        try:
            return float(cleaned)
        except:
            return None
    
    async def scrape_all(self) -> Dict:
        """抓取所有数据源"""
        print("\n" + "="*80)
        print("🚀 使用Playwright抓取网页数据")
        print("="*80)
        
        all_data = {}
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # 抓取第一个数据源
            print("\n📌 数据源1（19种币）")
            data1 = await self.scrape_page(page, self.urls['source_1'], 'source_1')
            if data1:
                print(f"✅ 数据源1: 获取到 {len(data1)} 个币种")
                all_data.update(data1)
            else:
                print("❌ 数据源1: 未获取到数据")
            
            await asyncio.sleep(2)
            
            # 抓取第二个数据源
            print("\n📌 数据源2（8种币）")
            data2 = await self.scrape_page(page, self.urls['source_2'], 'source_2')
            if data2:
                print(f"✅ 数据源2: 获取到 {len(data2)} 个币种")
                # 合并数据
                for coin, scores in data2.items():
                    if coin not in all_data:
                        all_data[coin] = scores
                    else:
                        print(f"  ℹ️  {coin}: 已存在，跳过")
            else:
                print("❌ 数据源2: 未获取到数据")
            
            await browser.close()
        
        print("\n" + "="*80)
        print(f"✅ 抓取完成: 总计 {len(all_data)} 个币种")
        print("="*80)
        
        return all_data
    
    def calculate_statistics(self, all_data: Dict) -> List[Dict]:
        """计算统计数据"""
        statistics = []
        
        for time_range in self.time_ranges:
            long_scores = []
            short_scores = []
            diffs = []
            
            for coin, scores in all_data.items():
                if time_range in scores:
                    score_data = scores[time_range]
                    long_scores.append(score_data['long_score'])
                    short_scores.append(score_data['short_score'])
                    diffs.append(score_data['diff'])
            
            if long_scores and short_scores:
                avg_long = sum(long_scores) / len(long_scores)
                avg_short = sum(short_scores) / len(short_scores)
                avg_diff = sum(diffs) / len(diffs)
                
                statistics.append({
                    'time_range': time_range,
                    'avg_long_score': round(avg_long, 2),
                    'avg_short_score': round(avg_short, 2),
                    'avg_diff': round(avg_diff, 2),
                    'coin_count': len(long_scores),
                    'trend': '📈 看多' if avg_diff > 0 else '📉 看空'
                })
        
        return statistics
    
    def print_results(self, all_data: Dict, statistics: List[Dict]):
        """打印结果"""
        # 打印币种列表
        print("\n📋 获取到的币种列表:")
        for i, coin in enumerate(sorted(all_data.keys()), 1):
            time_ranges = list(all_data[coin].keys())
            print(f"  {i:2d}. {coin:20s} - {len(time_ranges)} 个时间段")
        
        # 打印统计数据
        print("\n" + "╔" + "═"*78 + "╗")
        print("║" + "合并后的统计数据".center(78) + "║")
        print("╠" + "═"*78 + "╣")
        
        time_labels = {
            '3m': '3分钟',
            '1h': '1小时',
            '3h': '3小时',
            '6h': '6小时',
            '12h': '12小时',
            '24h': '24小时'
        }
        
        print("║" + "时间段".center(10) + "│" + "平均做多".center(12) + "│" + 
              "平均做空".center(12) + "│" + "平均差值".center(12) + "│" + 
              "币种数".center(8) + "│" + "趋势".center(10) + "║")
        print("╠" + "─"*10 + "┼" + "─"*12 + "┼" + "─"*12 + "┼" + 
              "─"*12 + "┼" + "─"*8 + "┼" + "─"*10 + "╣")
        
        for stat in statistics:
            tr = time_labels.get(stat['time_range'], stat['time_range'])
            long_score = f"{stat['avg_long_score']:.2f}"
            short_score = f"{stat['avg_short_score']:.2f}"
            diff = f"{stat['avg_diff']:+.2f}"
            count = str(stat['coin_count'])
            trend = '📈' if stat['avg_diff'] > 0 else '📉'
            
            print(f"║ {tr:>8s} │ {long_score:>10s} │ {short_score:>10s} │ " +
                  f"{diff:>10s} │ {count:>6s} │ {trend:^8s} ║")
        
        print("╚" + "═"*78 + "╝\n")


async def main():
    """主函数"""
    scraper = PlaywrightScoreScraper()
    
    # 抓取所有数据
    all_data = await scraper.scrape_all()
    
    if not all_data:
        print("❌ 没有获取到任何数据")
        return
    
    # 计算统计数据
    print("\n📊 计算统计数据...")
    statistics = scraper.calculate_statistics(all_data)
    
    # 打印结果
    scraper.print_results(all_data, statistics)
    
    # 保存数据到JSON
    output_data = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'statistics': statistics,
        'coins': all_data
    }
    
    with open('scraped_score_data.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print("💾 数据已保存到: scraped_score_data.json\n")


if __name__ == '__main__':
    asyncio.run(main())
