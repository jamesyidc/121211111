#!/usr/bin/env python3
"""
1小时爆仓金额数据采集器
每分钟采集一次，从 /api/panic/latest 获取 hour_1_amount 数据
"""

import requests
import time
import sys
import os
from datetime import datetime, timedelta
import pytz

# 添加路径
sys.path.insert(0, '/home/user/webapp/source_code')
from liquidation_1h_manager import Liquidation1HManager

# 北京时间
TZ = pytz.timezone('Asia/Shanghai')

# 配置
API_URL = 'http://localhost:5000/api/panic/latest'
COLLECTION_INTERVAL = 60  # 60秒采集一次

# 日志文件
LOG_FILE = '/home/user/webapp/logs/liquidation_1h_collector.log'
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


def log(message):
    """记录日志"""
    now = datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{now}] {message}"
    print(log_msg)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass


def collect_data():
    """采集一次数据"""
    try:
        # 请求API
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('success'):
            log(f"❌ API返回失败: {data}")
            return False
        
        # 提取数据
        panic_data = data.get('data', {})
        hour_1_amount = panic_data.get('hour_1_amount')
        
        if hour_1_amount is None:
            log(f"⚠️ 缺少hour_1_amount字段: {panic_data}")
            return False
        
        # 保存数据
        manager = Liquidation1HManager()
        success = manager.add_record(
            hour_1_amount=hour_1_amount,
            panic_index=panic_data.get('panic_index'),
            hour_24_amount=panic_data.get('hour_24_amount'),
            total_position=panic_data.get('total_position')
        )
        
        if success:
            log(f"✅ 数据采集成功: 1小时爆仓 {hour_1_amount}万美元, 恐慌指数 {panic_data.get('panic_index', 'N/A')}")
            return True
        else:
            log(f"❌ 数据保存失败")
            return False
            
    except requests.exceptions.RequestException as e:
        log(f"❌ 网络请求失败: {e}")
        return False
    except Exception as e:
        log(f"❌ 采集异常: {e}")
        import traceback
        log(traceback.format_exc())
        return False


def main():
    """主循环"""
    log("=" * 80)
    log("🚀 1小时爆仓金额采集器启动")
    log(f"📊 数据源: {API_URL}")
    log(f"⏱️ 采集间隔: {COLLECTION_INTERVAL}秒")
    log(f"📁 数据文件: /home/user/webapp/data/liquidation_1h/liquidation_1h.jsonl")
    log("=" * 80)
    
    # 首次采集
    log("\n🔄 开始首次采集...")
    collect_data()
    
    # 进入循环
    while True:
        try:
            # 等待到下一分钟
            now = datetime.now(TZ)
            next_minute = (now.replace(second=0, microsecond=0) + 
                          timedelta(minutes=1))
            sleep_seconds = (next_minute - now).total_seconds()
            
            if sleep_seconds > 0:
                log(f"\n⏳ 等待 {int(sleep_seconds)}秒 到下一分钟 ({next_minute.strftime('%H:%M:%S')})...")
                time.sleep(sleep_seconds)
            
            # 采集数据
            log(f"\n🔄 开始采集 [{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}]")
            collect_data()
            
        except KeyboardInterrupt:
            log("\n\n⚠️ 收到中断信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 主循环异常: {e}")
            import traceback
            log(traceback.format_exc())
            time.sleep(60)  # 出错后等待60秒再继续


if __name__ == '__main__':
    main()
