#!/usr/bin/env python3
"""
爆仓数据采集器 v4.0 - 使用Playwright
数据源: https://history.btc126.com/baocang/

使用Playwright获取JavaScript渲染后的页面数据
"""
import os
import sys
import json
import time
import logging
import re
import asyncio
from datetime import datetime
import pytz
from playwright.async_api import async_playwright

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
        self.browser = None
        self.page = None
    
    async def init_browser(self):
        """初始化浏览器"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            logger.info("✅ Playwright浏览器初始化成功")
        except Exception as e:
            logger.error(f"❌ 浏览器初始化失败: {e}")
            raise
    
    def extract_value(self, text):
        """从文本中提取数值
        
        例如: "$369.80万" -> 369.80
             "$6192.63万" -> 6192.63
             "54550人" -> 54550
             "$103.55亿" -> 103550 (转换为万)
        """
        try:
            # 移除$符号、逗号和空格
            text = str(text).replace('$', '').replace(',', '').replace(' ', '').strip()
            
            # 提取数字部分
            match = re.search(r'[\d.]+', text)
            if not match:
                return 0
            
            value = float(match.group())
            
            # 处理单位
            if '亿' in text:
                value = value * 10000  # 亿转换为万
            elif '万' in text:
                pass  # 已经是万
            elif '人' in text:
                # 人数保持原样（个数）
                pass
            
            return round(value, 2)
            
        except Exception as e:
            logger.error(f"提取数值失败: {text} -> {e}")
            return 0
    
    async def scrape_data(self):
        """抓取数据"""
        try:
            url = "https://history.btc126.com/baocang/"
            logger.info(f"🌐 访问: {url}")
            
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待stat-value元素加载
            await self.page.wait_for_selector('.stat-value', timeout=15000)
            
            # 额外等待以确保Vue渲染完成
            await asyncio.sleep(2)
            
            # 提取所有stat-card的数据
            cards = await self.page.query_selector_all('.stat-card')
            logger.info(f"📊 找到 {len(cards)} 个数据卡片")
            
            data = {}
            
            for card in cards:
                # 获取标题
                header = await card.query_selector('.stat-header')
                if not header:
                    continue
                
                header_text = await header.inner_text()
                
                # 获取值
                value_elem = await card.query_selector('.stat-value')
                if not value_elem:
                    continue
                
                value_text = await value_elem.inner_text()
                
                logger.info(f"  {header_text.strip()}: {value_text.strip()}")
                
                # 根据标题判断数据类型
                if '1小时爆仓' in header_text:
                    data['hour_1_amount'] = self.extract_value(value_text)
                elif '24小时爆仓' in header_text and '人数' not in header_text:
                    data['hour_24_amount'] = self.extract_value(value_text)
                elif '24H爆仓人数' in header_text or '24小时爆仓人数' in header_text:
                    data['hour_24_people'] = self.extract_value(value_text)
            
            # 查找全网总计（可能在不同的位置）
            try:
                total_elem = await self.page.query_selector('text=/全网总计/')
                if total_elem:
                    # 获取父元素
                    parent = await total_elem.evaluate_handle('el => el.parentElement')
                    parent_text = await parent.inner_text()
                    
                    # 提取数值
                    value_match = re.search(r'\$?([\d,.]+)[万亿]', parent_text)
                    if value_match:
                        data['total_position'] = self.extract_value(value_match.group(0))
                        logger.info(f"  全网总计: {value_match.group(0)}")
            except:
                logger.warning("  ⚠️  未找到全网总计数据")
                data['total_position'] = 0
            
            # 计算恐慌指数
            if data.get('hour_1_amount') and data.get('total_position'):
                panic_index = (data['hour_1_amount'] / data['total_position']) * 100
                data['panic_index'] = round(panic_index, 4)
            else:
                # 简化计算
                hour_1 = data.get('hour_1_amount', 0)
                if hour_1 >= 300:
                    data['panic_index'] = round(hour_1 / 100, 4)
                else:
                    data['panic_index'] = round(hour_1 / 200, 4)
            
            logger.info(f"✅ 数据提取成功:")
            logger.info(f"  1小时爆仓: {data.get('hour_1_amount', 0)}万")
            logger.info(f"  24小时爆仓: {data.get('hour_24_amount', 0)}万")
            logger.info(f"  24小时人数: {data.get('hour_24_people', 0)}人")
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
    
    async def collect_once(self):
        """执行一次采集"""
        data = await self.scrape_data()
        
        if data and len(data) >= 2:
            self.save_to_jsonl(data)
            return True
        else:
            logger.warning("⚠️  本次采集失败或数据不完整")
            return False
    
    async def cleanup(self):
        """清理资源"""
        if self.browser:
            await self.browser.close()
            logger.info("🧹 浏览器已关闭")

async def main():
    """主函数"""
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║           爆仓数据采集器 v4.0 (Playwright)                        ║
║           数据源: https://history.btc126.com/baocang/             ║
║           采集间隔: 1分钟                                          ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    collector = BaocangCollector()
    
    try:
        # 初始化浏览器
        await collector.init_browser()
        
        # 首次采集
        logger.info("🚀 开始首次采集...")
        await collector.collect_once()
        
        # 定时采集
        logger.info(f"\n⏰ 开始定时采集（间隔: {COLLECTION_INTERVAL}秒）\n")
        
        while True:
            await asyncio.sleep(COLLECTION_INTERVAL)
            
            logger.info(f"📊 开始新一轮采集 - {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            await collector.collect_once()
            logger.info("")
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  收到退出信号")
    except Exception as e:
        logger.error(f"❌ 运行错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await collector.cleanup()
        logger.info("👋 程序退出")

if __name__ == "__main__":
    asyncio.run(main())
