#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆仓数据爬虫
从 https://history.btc123.fans/baocang/ 获取实时爆仓数据
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time

def scrape_liquidation_data():
    """
    爬取爆仓数据
    返回格式:
    {
        'hour_1_amount': float,  # 1小时爆仓金额（美元）
        'hour_24_amount': float,  # 24小时爆仓金额（美元）
        'hour_24_people': int,   # 24小时爆仓人数
        'total_position': float,  # 全网持仓量（美元）
        'panic_index': float,     # 恐慌清洗指数 = 24小时爆仓人数/全网持仓量
        'update_time': str,       # 更新时间
        'raw_data': dict         # 原始数据
    }
    """
    url = "https://history.btc123.fans/baocang/"
    
    try:
        # 设置请求头，模拟浏览器
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        html = response.text
        
        # 从HTML中提取Vue数据
        # 查找API端点或内嵌的JSON数据
        soup = BeautifulSoup(html, 'html.parser')
        
        # 方法1: 查找script标签中的数据
        scripts = soup.find_all('script')
        data_found = False
        result = {}
        
        for script in scripts:
            script_text = script.string
            if script_text and 'blast' in script_text.lower():
                # 尝试提取数据
                try:
                    # 查找类似 data: {...} 的模式
                    match = re.search(r'data[:\s]*{([^}]+)}', script_text)
                    if match:
                        print(f"找到数据段: {match.group(0)[:100]}...")
                except:
                    pass
        
        # 方法2: 直接请求API端点（如果存在）
        # 通常这类网站会有 /api/baocang 或类似的端点
        api_urls = [
            'https://history.btc123.fans/api/baocang',
            'https://history.btc123.fans/baocang/api',
            'https://api.btc123.fans/baocang',
        ]
        
        for api_url in api_urls:
            try:
                api_response = requests.get(api_url, headers=headers, timeout=10)
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    print(f"✅ 从API获取数据: {api_url}")
                    print(json.dumps(api_data, ensure_ascii=False, indent=2)[:500])
                    return parse_api_data(api_data)
            except Exception as e:
                continue
        
        # 如果API方法失败，返回模拟数据供测试
        print("⚠️ 无法从API获取数据，返回示例格式")
        
        return {
            'success': False,
            'message': '需要进一步分析页面结构或使用浏览器自动化',
            'url': url,
            'example_format': {
                'hour_1_amount': 1234567.89,
                'hour_24_amount': 98765432.10,
                'hour_24_people': 45678,
                'total_position': 12345678901.23,
                'panic_index': 0.0037,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
    except Exception as e:
        print(f"❌ 爬取失败: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def parse_api_data(api_data):
    """
    解析API返回的数据
    """
    try:
        # 根据实际API响应格式解析
        result = {
            'hour_1_amount': 0,
            'hour_24_amount': 0,
            'hour_24_people': 0,
            'total_position': 0,
            'panic_index': 0,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'success': True,
            'raw_data': api_data
        }
        
        # TODO: 根据实际API格式填充数据
        # 例如:
        # result['hour_24_amount'] = api_data.get('blast24h', 0)
        # result['total_position'] = api_data.get('totalPosition', 0)
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': f'解析失败: {str(e)}'
        }

def scrape_with_selenium():
    """
    使用Selenium动态爬取（如果需要）
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://history.btc123.fans/baocang/')
        
        # 等待数据加载
        time.sleep(5)
        
        # 查找包含数据的元素
        # 例如: driver.find_element(By.CLASS_NAME, 'kuang')
        
        # 提取数据
        page_text = driver.page_source
        
        driver.quit()
        
        # 解析数据
        soup = BeautifulSoup(page_text, 'html.parser')
        # ... 进一步解析
        
        return {'success': True}
        
    except ImportError:
        print("⚠️ Selenium未安装，无法使用浏览器自动化")
        return {'success': False, 'error': 'Selenium not installed'}
    except Exception as e:
        print(f"❌ Selenium爬取失败: {str(e)}")
        return {'success': False, 'error': str(e)}

if __name__ == '__main__':
    print("="*70)
    print("🕷️  爆仓数据爬虫测试")
    print("="*70)
    
    data = scrape_liquidation_data()
    
    print("\n📊 爬取结果:")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    if data.get('success'):
        print("\n✅ 数据获取成功")
        if 'panic_index' in data:
            print(f"恐慌清洗指数: {data['panic_index']:.6f}")
    else:
        print("\n⚠️ 需要进一步开发")
        print("💡 建议:")
        print("  1. 使用浏览器开发者工具查找API端点")
        print("  2. 使用Selenium/Playwright进行动态爬取")
        print("  3. 联系网站提供方获取API文档")
