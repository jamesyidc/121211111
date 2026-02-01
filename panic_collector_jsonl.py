#!/usr/bin/env python3
"""
恐慌清洗指数采集器 - JSONL版本
- 每1分钟采集一次爆仓数据
- 计算恐慌清洗指数
- 存储到JSONL文件
"""

import requests
import time
import json
import sys
import os
from datetime import datetime
import logging
import pytz

# 添加路径
sys.path.insert(0, '/home/user/webapp')
from panic_jsonl_manager import PanicJSONLManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/panic_collector.log'),
        logging.StreamHandler()
    ]
)

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
BASE_URL = "https://api.btc126.com/bicoin.php"  # 更新为新的API地址

class PanicWashCollectorJSONL:
    def __init__(self):
        self.manager = PanicJSONLManager()
        logging.info("✅ 恐慌清洗指数采集器已启动 (JSONL存储)")
    
    def fetch_24h_blast_data(self, retry_count=0, max_retries=3):
        """获取24小时爆仓数据"""
        try:
            url = f"{BASE_URL}?from=24hbaocang"
            logging.info(f"📡 请求24小时爆仓数据 (尝试 {retry_count + 1}/{max_retries + 1})...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                hour_24_amount = data['data'].get('totalBlastUsd24h', 0)
                hour_24_people = data['data'].get('totalBlastNum24h', 0)
                
                # 0值检测
                if hour_24_amount == 0 or hour_24_people == 0:
                    logging.warning(f"⚠️ 检测到0值数据: 24h金额=${hour_24_amount}, 人数={hour_24_people}")
                    
                    if retry_count < max_retries:
                        logging.info(f"🔄 2秒后重试获取24小时爆仓数据...")
                        time.sleep(2)
                        return self.fetch_24h_blast_data(retry_count + 1, max_retries)
                    else:
                        logging.error(f"❌ 已达最大重试次数({max_retries+1}次)，仍为0值")
                        return None
                
                logging.info(f"✅ 24小时爆仓数据: 金额=${hour_24_amount:,.2f}, 人数={hour_24_people:,}")
                return {
                    'hour_24_amount': hour_24_amount,
                    'hour_24_people': hour_24_people
                }
            else:
                logging.error(f"❌ API返回错误: {data}")
                return None
                
        except Exception as e:
            logging.error(f"❌ 获取24小时爆仓数据失败: {e}")
            return None
    
    def fetch_1h_blast_data(self):
        """获取1小时爆仓数据"""
        try:
            url = f"{BASE_URL}?from=1hbaocang"
            logging.info(f"📡 请求1小时爆仓数据...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                hour_1_amount = data['data'].get('totalBlastUsd1h', 0)
                logging.info(f"✅ 1小时爆仓金额: ${hour_1_amount:,.2f}")
                return hour_1_amount
            else:
                logging.error(f"❌ 1小时爆仓API返回错误: {data}")
                return 0
                
        except Exception as e:
            logging.error(f"❌ 获取1小时爆仓数据失败: {e}")
            return 0
    
    def fetch_total_position(self):
        """获取全网持仓量（从realhold API）
        
        返回:
            tuple: (total_position, is_estimated)
            - total_position: 全网持仓量（美元）
            - is_estimated: 是否为估算值
        """
        try:
            # 使用realhold API获取实时持仓数据
            url = f"{BASE_URL}?from=realhold"
            logging.info(f"📡 请求全网持仓量（realhold）...")
            response = requests.get(url, timeout=30)  # 增加超时到30秒
            
            if response.status_code != 200:
                logging.warning(f"⚠️ HTTP错误: {response.status_code}，将跳过本次采集")
                return None, True
            
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                # data是列表，找到"全网总计"的记录
                for item in data['data']:
                    if item.get('exchange') == '全网总计' or item.get('exchangeOtherName') == 'Net total':
                        total_position = item.get('amount', 0)
                        if total_position > 0:
                            logging.info(f"✅ 全网持仓量: ${total_position:,.2f} = ${total_position/100000000:.2f}亿")
                            return total_position, False  # 返回真实数据
                
                logging.warning(f"⚠️ 未找到全网总计数据，将跳过本次采集")
                return None, True
            else:
                logging.warning(f"⚠️ API返回错误: {data}，将跳过本次采集")
                return None, True
                
        except Exception as e:
            logging.warning(f"⚠️ 获取全网持仓量失败: {e}，将跳过本次采集")
            return None, True
    
    def calculate_panic_index(self, hour_24_people, total_position):
        """
        计算恐慌指数
        恐慌指数 = 24小时爆仓人数(万人) / 全网持仓量(亿美元)
        """
        if total_position == 0:
            return 0
        
        # 转换单位
        people_wan = hour_24_people / 10000  # 转为万人
        position_yi = total_position / 100000000  # 转为亿美元
        
        if position_yi == 0:
            return 0
        
        panic_index = people_wan / position_yi
        return round(panic_index, 2)
    
    def calculate_wash_index(self, hour_24_amount, total_position):
        """
        计算清洗指数
        清洗指数 = 24小时爆仓金额(亿美元) / 全网持仓量(亿美元) * 100
        """
        if total_position == 0:
            return 0
        
        # 转换单位
        amount_yi = hour_24_amount / 100000000  # 转为亿美元
        position_yi = total_position / 100000000
        
        if position_yi == 0:
            return 0
        
        wash_index = (amount_yi / position_yi) * 100
        return round(wash_index, 2)
    
    def collect_once(self):
        """执行一次数据采集"""
        try:
            now = datetime.now(BEIJING_TZ)
            record_time = now.strftime('%Y-%m-%d %H:%M:%S')
            record_date = now.strftime('%Y-%m-%d')
            
            logging.info(f"\n{'='*60}")
            logging.info(f"🚀 开始采集恐慌清洗指数数据: {record_time}")
            logging.info(f"{'='*60}")
            
            # 获取数据
            blast_24h = self.fetch_24h_blast_data()
            if not blast_24h:
                logging.error("❌ 无法获取24小时爆仓数据，跳过本次采集")
                return False
            
            hour_1_amount = self.fetch_1h_blast_data()
            total_position, is_estimated = self.fetch_total_position()
            
            # 如果获取的是估算值，跳过本次采集
            if is_estimated or total_position is None:
                logging.warning("⚠️ 无法获取真实的全网持仓量，跳过本次采集（不保存估算值数据）")
                return False
            
            # 转换单位（先转换，再计算指数）
            # 注意：爆仓金额API返回的是分(cents)，需要除以100转为美元
            #      但全网持仓API返回的已经是美元，不需要除以100
            hour_1_amount_wan = hour_1_amount / 10000  # 美元 → 万美元
            hour_24_amount_wan = blast_24h['hour_24_amount'] / 10000  # 美元 → 万美元
            hour_24_people_wan = blast_24h['hour_24_people'] / 10000  # 人 → 万人
            total_position_yi = total_position / 100000000  # 美元 → 亿美元（已经是美元，不需要除以100）
            
            # 计算指数（使用转换后的单位）
            # 恐慌指数 = 24小时爆仓人数(万人) / 全网持仓量(亿美元)
            panic_index = hour_24_people_wan / total_position_yi if total_position_yi > 0 else 0
            # 清洗指数 = 24小时爆仓金额(万美元) / 全网持仓量(亿美元)
            wash_index = (hour_24_amount_wan / (total_position_yi * 10000)) * 100 if total_position_yi > 0 else 0
            
            # 构建记录（保存转换后的单位）
            record = {
                'record_time': record_time,
                'record_date': record_date,
                'hour_1_amount': hour_1_amount_wan,  # 万美元
                'hour_24_amount': hour_24_amount_wan,  # 万美元（改为万美元，便于显示）
                'hour_24_people': hour_24_people_wan,  # 万人
                'total_position': total_position_yi,  # 亿美元
                'panic_index': panic_index,
                'wash_index': wash_index,
                'raw_data': json.dumps({
                    'blast_24h': blast_24h,
                    'hour_1_amount': hour_1_amount,
                    'total_position': total_position
                })
            }
            
            # 保存到JSONL
            success = self.manager.append_record('panic_wash_index', record)
            
            if success:
                logging.info(f"\n{'='*60}")
                logging.info(f"✅ 数据采集完成并保存到JSONL")
                logging.info(f"📊 恐慌指数: {panic_index}")
                logging.info(f"📊 清洗指数: {wash_index}%")
                logging.info(f"{'='*60}\n")
                return True
            else:
                logging.error("❌ 保存数据失败")
                return False
                
        except Exception as e:
            logging.error(f"❌ 采集过程出错: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return False
    
    def run(self, interval=60):
        """持续运行采集器"""
        logging.info(f"🔄 采集器已启动，采集间隔: {interval}秒 ({interval/60:.1f}分钟)")
        
        while True:
            try:
                self.collect_once()
                logging.info(f"😴 等待 {interval} 秒后进行下次采集...\n")
                time.sleep(interval)
            except KeyboardInterrupt:
                logging.info("\n👋 采集器已停止")
                break
            except Exception as e:
                logging.error(f"❌ 运行出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再试


if __name__ == '__main__':
    collector = PanicWashCollectorJSONL()
    
    # 如果有命令行参数 'once'，只执行一次
    if len(sys.argv) > 1 and sys.argv[1] == 'once':
        collector.collect_once()
    else:
        collector.run(interval=60)  # 1分钟
