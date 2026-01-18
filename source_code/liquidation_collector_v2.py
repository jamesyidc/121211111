#!/usr/bin/env python3
"""
爆仓数据采集器 v2.0
数据源: https://history.btc126.com/baocang/

改版说明：
- 网站改为Vue.js渲染，需要使用Selenium抓取
- 采集指标：
  * 1小时爆仓金额
  * 24小时爆仓金额
  * 24小时爆仓人数
  * 全网总计
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

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

class BaocangScraper:
    """爆仓数据爬虫"""
    
    def __init__(self):
        self.driver = None
        self.init_driver()
    
    def init_driver(self):
        """初始化Chrome driver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 使用系统Chrome
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Chrome WebDriver初始化成功")
            
        except Exception as e:
            logger.error(f"❌ Chrome WebDriver初始化失败: {e}")
            self.driver = None
    
    def extract_value(self, text):
        """从文本中提取数值
        
        例如: "$369.80万" -> 369.80
             "54550人" -> 54550
             "$103.55亿" -> 103550 (转换为万)
        """
        try:
            # 移除$符号和空格
            text = text.replace('$', '').replace(' ', '').strip()
            
            # 提取数字部分
            import re
            match = re.search(r'[\d,.]+', text)
            if not match:
                return 0
            
            value_str = match.group().replace(',', '')
            value = float(value_str)
            
            # 处理单位
            if '亿' in text:
                value = value * 10000  # 亿转换为万
            elif '人' in text:
                value = value / 10000  # 人数转换为万人
            
            return round(value, 2)
            
        except Exception as e:
            logger.error(f"提取数值失败: {text} -> {e}")
            return 0
    
    def scrape_data(self):
        """抓取数据"""
        if not self.driver:
            logger.error("❌ WebDriver未初始化")
            return None
        
        try:
            url = "https://history.btc126.com/baocang/"
            logger.info(f"🌐 访问: {url}")
            
            self.driver.get(url)
            
            # 等待页面加载完成
            wait = WebDriverWait(self.driver, 20)
            
            # 等待数据加载（等待stat-value元素出现）
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "stat-value")))
            
            # 额外等待确保Vue渲染完成
            time.sleep(3)
            
            # 提取数据
            stat_values = self.driver.find_elements(By.CLASS_NAME, "stat-value")
            stat_labels = self.driver.find_elements(By.CLASS_NAME, "stat-label")
            
            logger.info(f"📊 找到 {len(stat_values)} 个数据项")
            
            # 构建数据字典
            data = {}
            for i, (label_elem, value_elem) in enumerate(zip(stat_labels, stat_values)):
                label = label_elem.text.strip()
                value_text = value_elem.text.strip()
                
                logger.info(f"  [{i}] {label}: {value_text}")
                
                if '1小时爆仓' in label:
                    data['hour_1_amount'] = self.extract_value(value_text)
                elif '24小时爆仓' in label and '人数' not in label:
                    data['hour_24_amount'] = self.extract_value(value_text)
                elif '24小时爆仓人数' in label:
                    data['hour_24_people'] = self.extract_value(value_text)
                elif '全网总计' in label:
                    data['total_position'] = self.extract_value(value_text)
            
            # 计算恐慌指数
            if data.get('hour_1_amount') and data.get('total_position'):
                panic_index = (data['hour_1_amount'] / data['total_position']) * 100
                data['panic_index'] = round(panic_index, 4)
            else:
                data['panic_index'] = 0
            
            logger.info(f"✅ 数据提取成功:")
            logger.info(f"  1小时爆仓: {data.get('hour_1_amount', 0)}万")
            logger.info(f"  24小时爆仓: {data.get('hour_24_amount', 0)}万")
            logger.info(f"  24小时人数: {data.get('hour_24_people', 0)}万人")
            logger.info(f"  全网总计: {data.get('total_position', 0)}万")
            logger.info(f"  恐慌指数: {data.get('panic_index', 0)}%")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ 抓取数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def save_to_jsonl(self, data):
        """保存数据到JSONL"""
        try:
            now = datetime.now(TZ)
            
            record = {
                "timestamp": int(now.timestamp()),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "hour_1_amount": data.get('hour_1_amount', 0),
                "panic_index": data.get('panic_index', 0),
                "hour_24_amount": data.get('hour_24_amount', 0),
                "hour_24_people": data.get('hour_24_people', 0),
                "total_position": data.get('total_position', 0)
            }
            
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            logger.info(f"💾 数据已保存")
            return True
            
        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            return False
    
    def collect_once(self):
        """执行一次采集"""
        data = self.scrape_data()
        
        if data:
            self.save_to_jsonl(data)
            return True
        else:
            logger.warning("⚠️  本次采集失败")
            return False
    
    def cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🧹 WebDriver已关闭")
            except:
                pass

def main():
    """主函数"""
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║           爆仓数据采集器 v2.0                                      ║
║           数据源: https://history.btc126.com/baocang/             ║
║           采集间隔: 1分钟                                          ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    scraper = BaocangScraper()
    
    if not scraper.driver:
        logger.error("❌ 无法初始化WebDriver，退出")
        return
    
    try:
        # 首次采集
        logger.info("🚀 开始首次采集...")
        scraper.collect_once()
        
        # 定时采集
        logger.info(f"⏰ 开始定时采集（间隔: {COLLECTION_INTERVAL}秒）\n")
        
        while True:
            time.sleep(COLLECTION_INTERVAL)
            
            logger.info(f"📊 开始新一轮采集 - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            scraper.collect_once()
            logger.info("")
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  收到退出信号")
    except Exception as e:
        logger.error(f"❌ 运行错误: {e}")
    finally:
        scraper.cleanup()
        logger.info("👋 程序退出")

if __name__ == "__main__":
    main()
