#!/usr/bin/env python3
"""
爆仓数据采集器 v3.0
数据源: https://history.btc126.com/baocang/

使用策略：
1. 先尝试直接API调用（如果能找到）
2. 如果API失败，使用requests_html渲染JavaScript
3. 作为后备方案，可以解析页面HTML
"""
import os
import sys
import json
import time
import logging
import re
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
TZ = pytz.timezone('Asia/Shanghai')
DATA_DIR = '/home/user/webapp/data/liquidation_1h'
JSONL_FILE = os.path.join(DATA_DIR, 'liquidation_1h.jsonl')
COLLECTION_INTERVAL = 60  # 1分钟采集一次

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

class BaocangCollector:
    """爆仓数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def extract_value(self, text):
        """从文本中提取数值
        
        例如: "$369.80万" -> 369.80
             "54550人" -> 54550
             "$103.55亿" -> 103550 (转换为万)
        """
        try:
            # 移除$符号和空格
            text = str(text).replace('$', '').replace(' ', '').replace(',', '').strip()
            
            # 提取数字部分
            match = re.search(r'[\d.]+', text)
            if not match:
                return 0
            
            value = float(match.group())
            
            # 处理单位
            if '亿' in text:
                value = value * 10000  # 亿转换为万
            elif '人' in text:
                value = value / 10000  # 人数转换为万人（实际上人数可能就是个数）
            
            return round(value, 2)
            
        except Exception as e:
            logger.error(f"提取数值失败: {text} -> {e}")
            return 0
    
    def try_api_method(self):
        """尝试通过API获取数据"""
        # 尝试常见的API端点
        api_endpoints = [
            "https://api.btc126.com/baocang/latest",
            "https://history.btc126.com/api/baocang",
            "https://history.btc126.com/api/liquidation",
            "https://api.btc126.com/liquidation/latest",
        ]
        
        for url in api_endpoints:
            try:
                logger.info(f"🔍 尝试API: {url}")
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ API返回数据: {data}")
                    
                    # 尝试解析数据
                    result = self.parse_api_response(data)
                    if result:
                        return result
                        
            except Exception as e:
                logger.debug(f"  API失败: {e}")
                continue
        
        return None
    
    def parse_api_response(self, data):
        """解析API响应"""
        try:
            # 尝试不同的数据结构
            if isinstance(data, dict):
                result = {}
                
                # 查找关键字段
                for key in data.keys():
                    key_lower = key.lower()
                    
                    if '1h' in key_lower or 'hour_1' in key_lower:
                        result['hour_1_amount'] = self.extract_value(data[key])
                    elif '24h' in key_lower or 'hour_24' in key_lower:
                        if 'people' in key_lower or 'count' in key_lower:
                            result['hour_24_people'] = self.extract_value(data[key])
                        else:
                            result['hour_24_amount'] = self.extract_value(data[key])
                    elif 'total' in key_lower:
                        result['total_position'] = self.extract_value(data[key])
                
                if len(result) >= 2:
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"解析API响应失败: {e}")
            return None
    
    def try_html_method(self):
        """通过HTML页面获取数据"""
        try:
            url = "https://history.btc126.com/baocang/"
            logger.info(f"🌐 访问HTML页面: {url}")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"❌ HTTP错误: {response.status_code}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 方法1: 查找Vue模板中的数据
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'baocangData' in script.string:
                    logger.info("✅ 找到baocangData")
                    # 尝试提取数据
                    result = self.extract_from_script(script.string)
                    if result:
                        return result
            
            # 方法2: 如果页面有初始数据
            # 查找__NUXT__或__INITIAL_STATE__等
            for script in scripts:
                if script.string:
                    if '__NUXT__' in script.string or 'window.__data' in script.string:
                        logger.info("✅ 找到初始数据")
                        result = self.extract_from_script(script.string)
                        if result:
                            return result
            
            # 方法3: 使用Coinglass API（备选数据源）
            logger.info("📊 尝试使用Coinglass API作为备选")
            return self.try_coinglass_api()
            
        except Exception as e:
            logger.error(f"❌ HTML方法失败: {e}")
            return None
    
    def extract_from_script(self, script_content):
        """从script标签中提取数据"""
        try:
            # 尝试查找数字模式
            patterns = {
                'hour_1': r'totalBlastUsd1h["\']?\s*:\s*([0-9.]+)',
                'hour_24': r'totalBlastUsd24h["\']?\s*:\s*([0-9.]+)',
                'total': r'totalPosition["\']?\s*:\s*([0-9.]+)',
            }
            
            result = {}
            for key, pattern in patterns.items():
                match = re.search(pattern, script_content)
                if match:
                    result[key] = float(match.group(1))
            
            if len(result) >= 2:
                return {
                    'hour_1_amount': result.get('hour_1', 0),
                    'hour_24_amount': result.get('hour_24', 0),
                    'total_position': result.get('total', 0)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"从script提取数据失败: {e}")
            return None
    
    def try_coinglass_api(self):
        """使用Coinglass API作为备选数据源"""
        try:
            # Coinglass公开API
            url = "https://open-api.coinglass.com/public/v2/liquidation"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and data.get('data'):
                    liquidation_data = data['data']
                    
                    # 提取1小时和24小时数据
                    hour_1 = liquidation_data.get('liquidationVolume', {}).get('1h', 0)
                    hour_24 = liquidation_data.get('liquidationVolume', {}).get('24h', 0)
                    
                    # 单位转换（Coinglass返回的是美元，需要转换为万）
                    return {
                        'hour_1_amount': round(hour_1 / 10000, 2),
                        'hour_24_amount': round(hour_24 / 10000, 2),
                        'total_position': 0,  # Coinglass可能没有这个数据
                        'source': 'coinglass'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Coinglass API失败: {e}")
            return None
    
    def collect_data(self):
        """采集数据（尝试多种方法）"""
        logger.info("📊 开始采集数据...")
        
        # 方法1: API
        result = self.try_api_method()
        if result:
            logger.info("✅ 通过API获取数据成功")
            return result
        
        # 方法2: HTML
        result = self.try_html_method()
        if result:
            logger.info("✅ 通过HTML获取数据成功")
            return result
        
        # 所有方法都失败
        logger.error("❌ 所有数据采集方法都失败了")
        return None
    
    def calculate_panic_index(self, data):
        """计算恐慌指数"""
        hour_1 = data.get('hour_1_amount', 0)
        total = data.get('total_position', 0)
        
        if hour_1 > 0 and total > 0:
            return round((hour_1 / total) * 100, 4)
        else:
            # 如果没有total_position，使用简化公式
            # 假设1小时爆仓量超过300万为高恐慌
            if hour_1 >= 300:
                return round(hour_1 / 100, 4)
            else:
                return round(hour_1 / 200, 4)
    
    def save_to_jsonl(self, data):
        """保存数据到JSONL"""
        try:
            now = datetime.now(TZ)
            
            # 计算恐慌指数
            panic_index = self.calculate_panic_index(data)
            
            record = {
                "timestamp": int(now.timestamp()),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "hour_1_amount": data.get('hour_1_amount', 0),
                "panic_index": panic_index,
                "hour_24_amount": data.get('hour_24_amount', 0),
                "hour_24_people": data.get('hour_24_people', 0),
                "total_position": data.get('total_position', 0),
                "source": data.get('source', 'btc126')
            }
            
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            logger.info(f"💾 数据已保存:")
            logger.info(f"  1小时爆仓: {record['hour_1_amount']}万")
            logger.info(f"  24小时爆仓: {record['hour_24_amount']}万")
            logger.info(f"  恐慌指数: {record['panic_index']}%")
            logger.info(f"  数据源: {record['source']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            return False
    
    def collect_once(self):
        """执行一次采集"""
        data = self.collect_data()
        
        if data:
            self.save_to_jsonl(data)
            return True
        else:
            logger.warning("⚠️  本次采集失败")
            return False

def main():
    """主函数"""
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║           爆仓数据采集器 v3.0                                      ║
║           主数据源: https://history.btc126.com/baocang/          ║
║           备用数据源: Coinglass API                                ║
║           采集间隔: 1分钟                                          ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    collector = BaocangCollector()
    
    try:
        # 首次采集
        logger.info("🚀 开始首次采集...")
        collector.collect_once()
        
        # 定时采集
        logger.info(f"\n⏰ 开始定时采集（间隔: {COLLECTION_INTERVAL}秒）\n")
        
        while True:
            time.sleep(COLLECTION_INTERVAL)
            
            logger.info(f"📊 开始新一轮采集 - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            collector.collect_once()
            logger.info("")
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  收到退出信号")
    except Exception as e:
        logger.error(f"❌ 运行错误: {e}")
    finally:
        logger.info("👋 程序退出")

if __name__ == "__main__":
    main()
