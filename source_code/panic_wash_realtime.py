#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恐慌清洗指标 - 实时数据采集版本
直接从API获取真实数据，每3分钟更新
使用北京时间
"""

import requests
import sqlite3
from datetime import datetime, timedelta
import pytz
import time

class RealTimePanicWashCollector:
    """实时恐慌清洗数据采集器"""
    
    def __init__(self, db_path='crypto_data.db'):
        self.db_path = db_path
        self.api_url = "https://api.btc123.fans/bicoin.php?from=24hbaocang"
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        
    def get_beijing_time(self):
        """获取北京时间"""
        return datetime.now(self.beijing_tz)
    
    def fetch_real_data(self):
        """从API获取真实数据"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] == 0 and 'data' in data:
                api_data = data['data']
                
                # 提取关键数据
                hour_1_amount = api_data.get('totalBlastUsd1h', 0)  # 1小时爆仓(美元)
                hour_24_amount = api_data.get('totalBlastUsd24h', 0)  # 24小时爆仓(美元)
                hour_24_people = api_data.get('totalBlastNum24h', 0)  # 24小时爆仓人数
                
                # 从realhold API获取持仓量
                try:
                    hold_response = requests.get(
                        "https://api.btc123.fans/bicoin.php?from=realhold",
                        timeout=10
                    )
                    hold_data = hold_response.json()
                    
                    # 全网持仓量（美元）
                    if hold_data['code'] == 0 and 'data' in hold_data:
                        # data是数组，最后一个元素是全网总计
                        hold_list = hold_data['data']
                        if isinstance(hold_list, list) and len(hold_list) > 0:
                            # 找到exchange为"全网总计"的条目
                            for item in hold_list:
                                if '全网' in item.get('exchange', '') or 'total' in item.get('exchange', '').lower():
                                    total_position = item.get('amount', 95e9)
                                    break
                            else:
                                # 如果没找到，使用最后一个（通常是总计）
                                total_position = hold_list[-1].get('amount', 95e9)
                        else:
                            total_position = 95e9
                    else:
                        total_position = 95e9
                except Exception as e:
                    print(f"  ⚠️ 获取持仓量失败，使用默认值: {e}")
                    total_position = 95e9  # 默认值
                
                # 计算恐慌指数: (万人) / (亿美元) × 100%
                if total_position > 0:
                    panic_index = (hour_24_people / 10000) / (total_position / 1e8) * 100
                else:
                    panic_index = 0
                
                beijing_time = self.get_beijing_time()
                
                result = {
                    'hour_1_amount': hour_1_amount,
                    'hour_24_amount': hour_24_amount,
                    'hour_24_people': hour_24_people,
                    'total_position': total_position,
                    'panic_index': panic_index,
                    'record_time': beijing_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'success': True
                }
                
                print(f"\n✅ 实时数据获取成功 [{beijing_time.strftime('%Y-%m-%d %H:%M:%S')} 北京时间]")
                print(f"  1小时爆仓: ${result['hour_1_amount']/1e6:.2f}M")
                print(f"  24小时爆仓: ${result['hour_24_amount']/1e6:.2f}M")
                print(f"  24小时爆仓人数: {result['hour_24_people']:,}人 ({result['hour_24_people']/10000:.4f}万人)")
                print(f"  全网持仓量: ${result['total_position']/1e9:.2f}B")
                print(f"  恐慌指数: {result['panic_index']:.2f}%")
                
                return result
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API请求失败: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            print(f"❌ 数据处理失败: {e}")
            return {'success': False, 'error': str(e)}
    
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
                data['hour_1_amount'],
                data['hour_24_amount'],
                data['hour_24_people'],
                data['total_position'],
                data['panic_index']
            ))
            
            conn.commit()
            conn.close()
            
            print(f"✅ 数据已保存到数据库")
            return True
            
        except Exception as e:
            print(f"❌ 数据库保存失败: {e}")
            return False
    
    def run_once(self):
        """执行一次采集"""
        print("="*70)
        print(f"🔄 开始采集实时数据")
        print("="*70)
        
        data = self.fetch_real_data()
        
        if data.get('success'):
            self.save_to_database(data)
            return True
        else:
            print(f"❌ 采集失败: {data.get('error', 'Unknown error')}")
            return False
    
    def run_loop(self, interval=180):
        """持续运行（每3分钟）"""
        print(f"🚀 恐慌清洗指标实时采集服务启动")
        print(f"⏰ 采集间隔: {interval}秒 ({interval/60:.0f}分钟)")
        print(f"🕐 时区: 北京时间 (Asia/Shanghai)")
        print(f"📡 数据源: https://api.btc123.fans/")
        print()
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                print(f"❌ 采集出错: {e}")
            
            print(f"\n⏰ 等待 {interval} 秒后进行下次采集...")
            print(f"💤 下次采集时间: {(self.get_beijing_time() + timedelta(seconds=interval)).strftime('%H:%M:%S')}")
            print()
            time.sleep(interval)

if __name__ == '__main__':
    from datetime import timedelta
    
    collector = RealTimePanicWashCollector()
    
    # 立即执行一次
    print("🎯 首次数据采集")
    collector.run_once()
    
    print("\n" + "="*70)
    input("按Enter键开始持续采集服务（Ctrl+C停止）...")
    print()
    
    # 开始持续采集
    try:
        collector.run_loop(interval=180)  # 3分钟
    except KeyboardInterrupt:
        print("\n\n🛑 采集服务已停止")
