#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网页数据爬虫 - 从两个得分网页抓取数据并合并
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import Dict, List, Tuple
import time
from datetime import datetime

class ScoreWebScraper:
    """从网页抓取得分数据"""
    
    def __init__(self):
        self.urls = {
            'source_1': 'https://3000-i42fq2f1mk8544uuc8pew-5c13a017.sandbox.novita.ai/score_overview.html',
            'source_2': 'https://3000-itkyuobnbphje7wgo4xbk-c07dda5e.sandbox.novita.ai/score_overview.html'
        }
        self.time_ranges = ['3m', '1h', '3h', '6h', '12h', '24h']
        self.timeout = 15
    
    def fetch_page(self, url: str) -> str:
        """获取网页HTML内容"""
        try:
            print(f"📡 正在获取: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            print(f"✅ 成功获取，大小: {len(response.text)} 字节")
            return response.text
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            return None
    
    def parse_table_data(self, html: str, source_name: str) -> Dict:
        """解析HTML表格数据"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            data = {}
            
            # 查找表格
            table = soup.find('table')
            if not table:
                print(f"⚠️ {source_name}: 未找到表格")
                return data
            
            # 解析表头，找到时间范围列的位置
            headers = []
            thead = table.find('thead')
            if thead:
                header_row = thead.find_all('th')
                for th in header_row:
                    text = th.get_text(strip=True)
                    headers.append(text)
                print(f"📋 {source_name} 表头: {headers}")
            
            # 解析表格数据行
            tbody = table.find('tbody')
            if not tbody:
                print(f"⚠️ {source_name}: 未找到表格数据")
                return data
            
            rows = tbody.find_all('tr')
            print(f"📊 {source_name}: 找到 {len(rows)} 行数据")
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                
                # 第一列是币种名称
                coin_cell = cells[0]
                coin_name = coin_cell.get_text(strip=True)
                
                # 标准化币种名称
                if not coin_name.endswith('-USDT-SWAP'):
                    coin_name = f"{coin_name}-USDT-SWAP"
                
                data[coin_name] = {}
                
                # 解析各时间段的数据
                # 通常格式是：币种 | 3m做多 3m做空 3m差值 | 1h做多 1h做空 1h差值 | ...
                cell_idx = 1
                for time_range in self.time_ranges:
                    if cell_idx + 2 < len(cells):
                        try:
                            # 提取做多、做空、差值
                            long_text = cells[cell_idx].get_text(strip=True)
                            short_text = cells[cell_idx + 1].get_text(strip=True)
                            diff_text = cells[cell_idx + 2].get_text(strip=True)
                            
                            # 清理数据，提取数字
                            long_score = self.extract_number(long_text)
                            short_score = self.extract_number(short_text)
                            diff_score = self.extract_number(diff_text)
                            
                            if long_score is not None and short_score is not None:
                                data[coin_name][time_range] = {
                                    'long_score': long_score,
                                    'short_score': short_score,
                                    'diff': diff_score if diff_score is not None else (long_score - short_score)
                                }
                        except Exception as e:
                            print(f"⚠️ 解析 {coin_name} {time_range} 数据失败: {e}")
                        
                        cell_idx += 3
            
            return data
            
        except Exception as e:
            print(f"❌ {source_name} 解析失败: {e}")
            return {}
    
    def extract_number(self, text: str) -> float:
        """从文本中提取数字"""
        if not text:
            return None
        
        # 移除所有非数字和小数点、负号的字符
        cleaned = re.sub(r'[^\d.\-+]', '', text)
        if not cleaned or cleaned in ['-', '+', '.']:
            return None
        
        try:
            return float(cleaned)
        except:
            return None
    
    def scrape_all_sources(self) -> Dict:
        """抓取所有数据源"""
        print("\n" + "="*80)
        print("🚀 开始抓取网页数据")
        print("="*80 + "\n")
        
        all_data = {}
        
        # 抓取第一个数据源（19种币）
        print("\n📌 数据源1（19种币）")
        html1 = self.fetch_page(self.urls['source_1'])
        if html1:
            data1 = self.parse_table_data(html1, 'source_1')
            print(f"✅ 数据源1: 获取到 {len(data1)} 个币种")
            all_data.update(data1)
        else:
            print("❌ 数据源1: 无法获取数据")
        
        time.sleep(1)  # 避免请求过快
        
        # 抓取第二个数据源（8种币）
        print("\n📌 数据源2（8种币）")
        html2 = self.fetch_page(self.urls['source_2'])
        if html2:
            data2 = self.parse_table_data(html2, 'source_2')
            print(f"✅ 数据源2: 获取到 {len(data2)} 个币种")
            
            # 合并数据（如果有重复币种，保留第一个数据源的数据）
            for coin, scores in data2.items():
                if coin not in all_data:
                    all_data[coin] = scores
                else:
                    print(f"ℹ️  {coin}: 已存在，跳过")
        else:
            print("❌ 数据源2: 无法获取数据")
        
        print("\n" + "="*80)
        print(f"✅ 抓取完成: 总计 {len(all_data)} 个币种")
        print("="*80 + "\n")
        
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
    
    def print_statistics(self, statistics: List[Dict]):
        """打印统计结果"""
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


def main():
    """主函数"""
    scraper = ScoreWebScraper()
    
    # 抓取所有数据
    all_data = scraper.scrape_all_sources()
    
    if not all_data:
        print("❌ 没有获取到任何数据")
        return
    
    # 打印币种列表
    print("\n📋 获取到的币种列表:")
    for i, coin in enumerate(sorted(all_data.keys()), 1):
        time_ranges = list(all_data[coin].keys())
        print(f"  {i:2d}. {coin:20s} - {len(time_ranges)} 个时间段")
    
    # 计算统计数据
    print("\n📊 计算统计数据...")
    statistics = scraper.calculate_statistics(all_data)
    
    # 打印统计结果
    scraper.print_statistics(statistics)
    
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
    main()
