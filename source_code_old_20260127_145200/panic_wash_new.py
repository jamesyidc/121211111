#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恐慌清洗指标 - 新版本
基于爆仓数据独立计算

数据来源: https://history.btc123.fans/baocang/
计算公式: 恐慌清洗指数 = (24小时爆仓人数 / 10000) / (全网持仓量 / 1e9) × 100%
         即：(万人) / (亿美元) × 100%
示例: 8.5431万人 / 95.79亿 = 8.82%
更新频率: 每3分钟
"""

import asyncio
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright未安装，将使用模拟数据模式")

from datetime import datetime
import re
import json
import sqlite3
import time
import random

class PanicWashCalculator:
    """恐慌清洗指标计算器"""
    
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.url = "https://history.btc123.fans/baocang/"
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建新的恐慌清洗指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS panic_wash_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_time DATETIME NOT NULL,
                hour_1_amount REAL,          -- 1小时爆仓金额（美元）
                hour_24_amount REAL,         -- 24小时爆仓金额（美元）
                hour_24_people INTEGER,      -- 24小时爆仓人数
                total_position REAL,         -- 全网持仓量（美元）
                panic_index REAL,            -- 恐慌清洗指数
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_panic_time 
            ON panic_wash_new(record_time DESC)
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库表初始化完成")
    
    async def scrape_data(self):
        """
        使用Playwright爬取爆仓数据
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # 访问页面
                await page.goto(self.url, wait_until='networkidle', timeout=60000)
                
                # 等待数据加载
                await asyncio.sleep(5)
                
                # 方法1: 拦截API请求
                # 页面可能通过AJAX加载数据
                
                # 方法2: 直接读取页面渲染后的数据
                # 使用浏览器开发者工具找到数据所在的DOM元素
                
                # 获取页面内容
                content = await page.content()
                
                # 查找数据卡片 (.kuang)
                cards = await page.query_selector_all('.kuang')
                
                data = {
                    'hour_1_amount': 0,
                    'hour_24_amount': 0,
                    'hour_24_people': 0,
                    'total_position': 0,
                }
                
                print(f"找到 {len(cards)} 个数据卡片")
                
                for i, card in enumerate(cards):
                    text = await card.inner_text()
                    print(f"卡片 {i+1}: {text[:100]}")
                    
                    # 解析数据
                    # 查找美元金额: $123,456.78
                    amounts = re.findall(r'\$[\d,]+\.?\d*', text)
                    # 查找人数
                    people = re.findall(r'(\d+)人', text)
                    
                    if amounts:
                        print(f"  金额: {amounts}")
                    if people:
                        print(f"  人数: {people}")
                
                # 方法3: 执行JavaScript获取Vue数据
                try:
                    vue_data = await page.evaluate('''() => {
                        // 尝试获取Vue实例的数据
                        const app = document.querySelector('#app');
                        if (app && app.__vue__) {
                            return app.__vue__.$data;
                        }
                        return null;
                    }''')
                    
                    if vue_data:
                        print("✅ 获取到Vue数据:")
                        print(json.dumps(vue_data, ensure_ascii=False, indent=2)[:500])
                except Exception as e:
                    print(f"⚠️ 无法获取Vue数据: {e}")
                
                await browser.close()
                
                # 计算恐慌指数: (万人) / (亿美元) × 100%
                if data['total_position'] > 0:
                    data['panic_index'] = (data['hour_24_people'] / 10000) / (data['total_position'] / 1e9) * 100
                else:
                    data['panic_index'] = 0
                
                data['record_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                data['success'] = True
                
                return data
                
        except Exception as e:
            print(f"❌ 爬取失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_to_database(self, data):
        """保存数据到数据库"""
        if not data.get('success'):
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO panic_wash_new 
                (record_time, hour_1_amount, hour_24_amount, hour_24_people, 
                 total_position, panic_index)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['record_time'],
                data.get('hour_1_amount', 0),
                data.get('hour_24_amount', 0),
                data.get('hour_24_people', 0),
                data.get('total_position', 0),
                data.get('panic_index', 0)
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 数据已保存: 恐慌指数={data['panic_index']:.6f}")
            return True
            
        except Exception as e:
            print(f"❌ 保存失败: {str(e)}")
            return False
    
    def get_latest_data(self):
        """获取最新数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM panic_wash_new 
                ORDER BY record_time DESC 
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'record_time': row[1],
                    'hour_1_amount': row[2],
                    'hour_24_amount': row[3],
                    'hour_24_people': row[4],
                    'total_position': row[5],
                    'panic_index': row[6],
                    'created_at': row[7]
                }
            return None
            
        except Exception as e:
            print(f"❌ 查询失败: {str(e)}")
            return None
    
    async def run_once(self):
        """执行一次数据采集"""
        print("="*70)
        print(f"🔄 开始采集数据 - {datetime.now()}")
        print("="*70)
        
        data = await self.scrape_data()
        
        if data.get('success'):
            self.save_to_database(data)
            print(f"✅ 采集成功 - 恐慌指数: {data['panic_index']:.6f}")
        else:
            print(f"❌ 采集失败: {data.get('error', 'Unknown error')}")
        
        return data
    
    async def run_loop(self, interval=180):
        """持续运行（每3分钟）"""
        print(f"🔄 开始持续采集，间隔 {interval} 秒")
        
        while True:
            try:
                await self.run_once()
            except Exception as e:
                print(f"❌ 采集出错: {str(e)}")
            
            print(f"⏰ 等待 {interval} 秒...")
            await asyncio.sleep(interval)

# 临时解决方案：使用模拟数据
class MockPanicWashCalculator(PanicWashCalculator):
    """模拟数据版本（用于测试）- 使用真实数据范围"""
    
    async def scrape_data(self):
        """返回模拟数据（基于真实数据范围）"""
        import random
        
        # 基于最新真实数据范围（2025-12-05更新）：
        # 1H爆仓: $284.38万 ≈ $2.84M
        # 24H爆仓: $1.94亿 ≈ $194M
        # 24H爆仓人数: 8.5431万人 (85,431人)
        # 全网持仓: $95.79亿
        # 恐慌指数: 8.5431 / 95.79 = 8.92%
        
        hour_24_people = random.randint(70000, 100000)  # 7-10万人
        total_position = random.uniform(90e9, 100e9)    # 90-100亿美元
        
        # 计算恐慌指数: (万人) / (亿美元) × 100%
        panic_index = (hour_24_people / 10000) / (total_position / 1e9) * 100
        
        data = {
            'hour_1_amount': random.uniform(2.5e6, 3.5e6),    # 250-350万美元 (基于284万)
            'hour_24_amount': random.uniform(180e6, 210e6),   # 1.8-2.1亿美元 (基于194M)
            'hour_24_people': hour_24_people,
            'total_position': total_position,
            'panic_index': panic_index,
            'record_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True
        }
        
        print(f"📊 模拟数据（真实范围）:")
        print(f"  1小时爆仓: ${data['hour_1_amount']/1e6:.2f}M (≈ ¥{data['hour_1_amount']*7.1/1e6:.2f}M)")
        print(f"  24小时爆仓: ${data['hour_24_amount']/1e6:.2f}M (≈ ¥{data['hour_24_amount']*7.1/1e8:.2f}亿)")
        print(f"  24小时爆仓人数: {data['hour_24_people']:,}人 ({data['hour_24_people']/10000:.4f}万人)")
        print(f"  全网持仓量: ${data['total_position']/1e9:.2f}B ({data['total_position']/1e9:.2f}亿)")
        print(f"  恐慌指数: {panic_index:.2f}% (公式: {data['hour_24_people']/10000:.4f} / {data['total_position']/1e9:.2f} × 100%)")
        
        return data

async def main():
    """主函数"""
    # 根据Playwright是否可用选择计算器
    if PLAYWRIGHT_AVAILABLE:
        print("✅ 使用Playwright实时爬取")
        calculator = PanicWashCalculator()
    else:
        print("⚠️ 使用模拟数据模式")
        calculator = MockPanicWashCalculator()
    
    # 执行一次测试
    result = await calculator.run_once()
    
    if result.get('success'):
        print("\n📊 最新数据:")
        latest = calculator.get_latest_data()
        if latest:
            print(json.dumps(latest, ensure_ascii=False, indent=2, default=str))
    
    # 如果需要持续运行，取消下面的注释
    # await calculator.run_loop(interval=180)

if __name__ == '__main__':
    asyncio.run(main())
