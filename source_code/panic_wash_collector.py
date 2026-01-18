#!/usr/bin/env python3
"""
恐慌清洗指数采集器
- 每3分钟采集一次爆仓数据
- 计算恐慌清洗指数 = 24小时爆仓人数(万人) / 全网持仓量(亿美元)
- 数据源：https://history.btc123.fans/baocang/
"""

import sqlite3
import requests
import time
import json
from datetime import datetime
import logging
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/panic_wash_collector.log'),
        logging.StreamHandler()
    ]
)

# API基础URL
BASE_URL = "https://api.btc126.com/bicoin.php"  # 更新为新的API地址

class PanicWashCollector:
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS panic_wash_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_time TEXT NOT NULL,
                record_date TEXT NOT NULL,
                hour_1_amount REAL DEFAULT 0,
                hour_24_amount REAL DEFAULT 0,
                hour_24_people INTEGER DEFAULT 0,
                total_position REAL DEFAULT 0,
                panic_index REAL DEFAULT 0,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_panic_record_time 
            ON panic_wash_index(record_time)
        ''')
        
        conn.commit()
        conn.close()
        logging.info("✅ 数据库初始化完成")
    
    def fetch_24h_blast_data(self, retry_count=0, max_retries=3):
        """
        获取24小时爆仓数据（带0值检测和重试）
        
        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
        """
        try:
            url = f"{BASE_URL}?from=24hbaocang"
            logging.info(f"  📡 请求24小时爆仓数据 (尝试 {retry_count + 1}/{max_retries + 1})...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                hour_24_amount = data['data'].get('totalBlastUsd24h', 0)
                hour_24_people = data['data'].get('totalBlastNum24h', 0)
                
                # 0值检测
                if hour_24_amount == 0 or hour_24_people == 0:
                    logging.warning(f"  ⚠️ 检测到0值数据: 24h金额=${hour_24_amount}, 人数={hour_24_people}")
                    
                    if retry_count < max_retries:
                        logging.info(f"  🔄 2秒后重试获取24小时爆仓数据...")
                        time.sleep(2)
                        return self.fetch_24h_blast_data(retry_count + 1, max_retries)
                    else:
                        logging.error(f"  ❌ 已达最大重试次数({max_retries+1}次)，仍为0值，放弃本次采集")
                        return None
                
                logging.info(f"  ✅ 24小时爆仓数据获取成功")
                return {
                    'hour_24_amount': hour_24_amount,
                    'hour_24_people': hour_24_people
                }
            
            logging.error(f"  ❌ API返回数据格式异常")
            return None
            
        except Exception as e:
            logging.error(f"  ❌ 获取24小时爆仓数据失败: {str(e)}")
            if retry_count < max_retries:
                logging.info(f"  🔄 2秒后重试...")
                time.sleep(2)
                return self.fetch_24h_blast_data(retry_count + 1, max_retries)
            return None
    
    def fetch_1h_blast_data(self, retry_count=0, max_retries=3):
        """
        获取1小时爆仓数据（带0值检测和重试）
        
        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
        """
        try:
            url = f"{BASE_URL}?from=1hbaocang"
            logging.info(f"  📡 请求1小时爆仓数据 (尝试 {retry_count + 1}/{max_retries + 1})...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                hour_1_amount = data['data'].get('totalBlastUsd1h', 0)
                
                # 0值检测
                if hour_1_amount == 0:
                    logging.warning(f"  ⚠️ 检测到0值: 1h爆仓金额=${hour_1_amount}")
                    
                    if retry_count < max_retries:
                        logging.info(f"  🔄 2秒后重试获取1小时爆仓数据...")
                        time.sleep(2)
                        return self.fetch_1h_blast_data(retry_count + 1, max_retries)
                    else:
                        logging.error(f"  ❌ 已达最大重试次数({max_retries+1}次)，仍为0值")
                        return 0
                
                logging.info(f"  ✅ 1小时爆仓数据获取成功")
                return hour_1_amount
            
            return 0
            
        except Exception as e:
            logging.error(f"  ❌ 获取1小时爆仓数据失败: {str(e)}")
            if retry_count < max_retries:
                logging.info(f"  🔄 2秒后重试...")
                time.sleep(2)
                return self.fetch_1h_blast_data(retry_count + 1, max_retries)
            return 0
    
    def fetch_total_position(self, retry_count=0, max_retries=3):
        """
        获取全网持仓量（带0值检测和重试）
        
        Args:
            retry_count: 当前重试次数
            max_retries: 最大重试次数
        """
        try:
            url = f"{BASE_URL}?from=realhold"
            logging.info(f"  📡 请求全网持仓数据 (尝试 {retry_count + 1}/{max_retries + 1})...")
            response = requests.get(url, timeout=30)
            data = response.json()
            
            if data.get('code') == 0 and data.get('data'):
                positions = data['data']
                
                # 查找"全网总计"
                for item in positions:
                    if item.get('exchange') == '全网总计':
                        total_position = item.get('amount', 0)
                        
                        # 0值检测
                        if total_position == 0:
                            logging.warning(f"  ⚠️ 检测到0值: 全网持仓=${total_position}")
                            
                            if retry_count < max_retries:
                                logging.info(f"  🔄 2秒后重试获取全网持仓数据...")
                                time.sleep(2)
                                return self.fetch_total_position(retry_count + 1, max_retries)
                            else:
                                logging.error(f"  ❌ 已达最大重试次数({max_retries+1}次)，仍为0值")
                                return 0
                        
                        logging.info(f"  ✅ 全网持仓数据获取成功")
                        return total_position
            
            return 0
            
        except Exception as e:
            logging.error(f"  ❌ 获取全网持仓量失败: {str(e)}")
            if retry_count < max_retries:
                logging.info(f"  🔄 2秒后重试...")
                time.sleep(2)
                return self.fetch_total_position(retry_count + 1, max_retries)
            return 0
    
    def calculate_panic_index(self, hour_24_people, total_position):
        """
        计算恐慌清洗指数
        
        公式：恐慌清洗指数 = 24小时爆仓人数(万人) / 全网持仓量(亿美元)
        
        参数:
            hour_24_people: 24小时爆仓人数（人）
            total_position: 全网持仓量（美元）
        
        返回:
            panic_index: 恐慌清洗指数（百分比）
        """
        if total_position <= 0:
            return 0
        
        # 24小时爆仓人数转换为万人
        people_wan = hour_24_people / 10000
        
        # 全网持仓量转换为亿美元
        position_yi = total_position / 100000000
        
        # 计算恐慌清洗指数
        # 公式: 万人 / 亿美元 = 比率（需要乘以100转换为百分比）
        panic_index = ((people_wan / position_yi) * 100) if position_yi > 0 else 0
        
        return round(panic_index, 2)
    
    def collect_data(self):
        """采集完整数据（带0值检测和单位换算日志）"""
        try:
            logging.info("=" * 80)
            logging.info("📊 开始采集恐慌清洗数据...")
            logging.info("=" * 80)
            
            # 1. 获取1小时爆仓金额
            hour_1_amount = self.fetch_1h_blast_data()
            if hour_1_amount == 0:
                logging.error("❌ 1小时爆仓金额为0，本次采集失败")
                return None
            
            hour_1_amount_wan = hour_1_amount / 10000  # 转换为万
            logging.info(f"  ✅ 1小时爆仓金额: ${hour_1_amount:,.2f} → {hour_1_amount_wan:.2f}万")
            
            # 2. 获取24小时爆仓数据
            blast_24h = self.fetch_24h_blast_data()
            if not blast_24h:
                logging.error("❌ 24小时爆仓数据获取失败，本次采集失败")
                return None
            
            hour_24_amount = blast_24h['hour_24_amount']
            hour_24_people = blast_24h['hour_24_people']
            
            # 单位换算：24小时爆仓金额转换为亿
            hour_24_amount_yi = hour_24_amount / 100000000
            # 单位换算：24小时爆仓人数转换为万人
            hour_24_people_wan = hour_24_people / 10000
            
            logging.info(f"  ✅ 24小时爆仓金额: ${hour_24_amount:,.2f} → {hour_24_amount_yi:.4f}亿")
            logging.info(f"  ✅ 24小时爆仓人数: {hour_24_people:,}人 → {hour_24_people_wan:.2f}万人")
            
            # 3. 获取全网持仓量
            total_position = self.fetch_total_position()
            if total_position == 0:
                logging.error("❌ 全网持仓量为0，本次采集失败")
                return None
            
            # 单位换算：全网持仓量转换为亿
            total_position_yi = total_position / 100000000
            logging.info(f"  ✅ 全网持仓量: ${total_position:,.2f} → {total_position_yi:.2f}亿")
            
            # 4. 计算恐慌清洗指数
            panic_index = self.calculate_panic_index(hour_24_people, total_position)
            
            # 详细计算日志
            logging.info("")
            logging.info("  " + "=" * 70)
            logging.info(f"  📈 恐慌清洗指数计算:")
            logging.info(f"     公式: 24小时爆仓人数(万人) / 全网持仓量(亿美元) × 100%")
            logging.info(f"     爆仓人数: {hour_24_people:,}人 = {hour_24_people_wan:.4f}万人")
            logging.info(f"     持仓量: ${total_position:,.2f} = {total_position_yi:.2f}亿美元")
            logging.info(f"     恐慌指数: {hour_24_people_wan:.4f} / {total_position_yi:.2f} × 100% = {panic_index}%")
            logging.info("  " + "=" * 70)
            
            result = {
                'hour_1_amount': hour_1_amount,
                'hour_24_amount': hour_24_amount,
                'hour_24_people': hour_24_people,
                'total_position': total_position,
                'panic_index': panic_index,
                'raw_data': json.dumps({
                    'hour_1_amount': hour_1_amount,
                    'hour_24_amount': hour_24_amount,
                    'hour_24_people': hour_24_people,
                    'total_position': total_position
                })
            }
            
            logging.info(f"✅ 数据采集成功: 恐慌指数={panic_index}%")
            return result
            
        except Exception as e:
            logging.error(f"❌ 数据采集失败: {str(e)}")
            return None
    
    def save_data(self, data):
        """保存数据到数据库（使用北京时间）"""
        if not data:
            return False
        
        try:
            # 使用北京时间
            beijing_tz = pytz.timezone('Asia/Shanghai')
            now = datetime.now(beijing_tz)
            record_time = now.strftime('%Y-%m-%d %H:%M:%S')
            record_date = now.strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.execute('PRAGMA busy_timeout=30000')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO panic_wash_index (
                    record_time, record_date, hour_1_amount, hour_24_amount,
                    hour_24_people, total_position, panic_index, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_time,
                record_date,
                data['hour_1_amount'],
                data['hour_24_amount'],
                data['hour_24_people'],
                data['total_position'],
                data['panic_index'],
                data['raw_data']
            ))
            
            conn.commit()
            conn.close()
            
            logging.info(f"💾 数据保存成功: {record_time}")
            return True
            
        except Exception as e:
            logging.error(f"❌ 数据保存失败: {str(e)}")
            return False
    
    def collect_once(self):
        """
        执行一次完整采集
        
        Returns:
            bool: True表示采集并保存成功，False表示失败
        """
        data = self.collect_data()
        if data:
            success = self.save_data(data)
            if success:
                logging.info("")
                logging.info(f"  💾 数据已成功保存到数据库")
                return True
            else:
                logging.error(f"  ❌ 数据保存失败")
                return False
        else:
            logging.error(f"  ❌ 数据采集失败")
            return False
    
    def run_daemon(self, interval=180):
        """
        守护进程模式运行（成功后才计时3分钟）
        
        Args:
            interval: 成功采集后的等待间隔（秒），默认180秒=3分钟
        
        规则:
            - 成功采集后，等待3分钟再进行下次采集
            - 采集失败时，立即重试，不受3分钟限制
        """
        logging.info("=" * 80)
        logging.info(f"🚀 恐慌清洗指数采集器启动")
        logging.info(f"   采集规则: 成功后等待{interval}秒(3分钟)，失败立即重试")
        logging.info("=" * 80)
        
        while True:
            try:
                # 尝试采集数据
                success = self.collect_once()
                
                if success:
                    # 成功采集，等待指定间隔
                    logging.info("=" * 80)
                    logging.info(f"✅ 本次采集成功！")
                    logging.info(f"⏳ 等待 {interval}秒 ({interval//60}分钟) 后进行下一次采集...")
                    logging.info("=" * 80)
                    time.sleep(interval)
                else:
                    # 采集失败，短暂等待后立即重试
                    retry_wait = 10
                    logging.warning("=" * 80)
                    logging.warning(f"❌ 本次采集失败！")
                    logging.warning(f"🔄 {retry_wait}秒后立即重试（不受3分钟限制）...")
                    logging.warning("=" * 80)
                    time.sleep(retry_wait)
                    
            except KeyboardInterrupt:
                logging.info("=" * 80)
                logging.info("⛔ 收到停止信号，退出采集")
                logging.info("=" * 80)
                break
            except Exception as e:
                logging.error("=" * 80)
                logging.error(f"❌ 采集过程出现异常: {str(e)}")
                logging.error(f"🔄 30秒后重试...")
                logging.error("=" * 80)
                time.sleep(30)

def main():
    collector = PanicWashCollector()
    
    # 立即执行一次采集
    logging.info("📊 执行首次恐慌清洗指数采集...")
    collector.collect_once()
    
    # 启动守护进程（3分钟间隔）
    collector.run_daemon(interval=180)

if __name__ == '__main__':
    main()
