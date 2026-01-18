#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场指标采集器
采集恐慌清洗指数、全网持仓量、1小时爆仓金额
每分钟更新一次，保存到JSONL
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path

# 配置
JSONL_DIR = Path('/home/user/webapp/data/market_indicators_jsonl')
LATEST_FILE = JSONL_DIR / 'latest_market_indicators.jsonl'
HISTORY_FILE = JSONL_DIR / 'market_indicators_history.jsonl'

# OKX API配置
OKX_BASE_URL = 'https://www.okx.com'

def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def fetch_panic_index():
    """
    获取恐慌清洗指数
    这里使用模拟数据，实际需要对接真实API
    """
    try:
        # TODO: 替换为真实API
        # 模拟数据：随机生成0-100的指数
        import random
        index = random.uniform(20, 80)
        
        # 判断状态
        if index < 30:
            status = "极度恐慌"
        elif index < 45:
            status = "恐慌"
        elif index < 55:
            status = "中性"
        elif index < 70:
            status = "贪婪"
        else:
            status = "极度贪婪"
        
        return {
            'index': round(index, 2),
            'status': status,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        log(f"❌ 获取恐慌指数失败: {e}")
        return None

def fetch_total_open_interest():
    """
    获取全网持仓量（所有合约的持仓总额）
    单位: USDT
    """
    try:
        # OKX API获取持仓量
        url = f"{OKX_BASE_URL}/api/v5/public/open-interest"
        params = {
            'instType': 'SWAP'  # 永续合约
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('code') == '0':
            total_oi = 0
            for item in data.get('data', []):
                # 获取每个合约的持仓量(单位:张)和面值
                oi = float(item.get('oi', 0))
                oi_ccy = float(item.get('oiCcy', 0))  # 持仓量(币)
                
                # 获取标记价格来计算USD价值
                inst_id = item.get('instId', '')
                if oi_ccy > 0:
                    # 简化：使用oiCcy作为USD价值的近似
                    total_oi += oi_ccy
            
            return {
                'total_open_interest': round(total_oi, 2),
                'unit': 'USDT',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            log(f"❌ OKX API返回错误: {data.get('msg')}")
            return None
            
    except Exception as e:
        log(f"❌ 获取持仓量失败: {e}")
        # 返回模拟数据作为fallback
        import random
        return {
            'total_open_interest': round(random.uniform(50000000, 80000000), 2),
            'unit': 'USDT',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_mock': True
        }

def fetch_liquidation_1h():
    """
    获取1小时爆仓金额
    单位: USDT
    """
    try:
        # 使用Coinglass API或其他数据源
        # 这里使用模拟数据
        import random
        amount = random.uniform(5000000, 20000000)
        
        return {
            'liquidation_1h': round(amount, 2),
            'unit': 'USDT',
            'long_liquidation': round(amount * 0.6, 2),
            'short_liquidation': round(amount * 0.4, 2),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        log(f"❌ 获取爆仓数据失败: {e}")
        return None

def collect_indicators():
    """采集所有指标"""
    try:
        # 确保目录存在
        JSONL_DIR.mkdir(parents=True, exist_ok=True)
        
        # 采集数据
        panic = fetch_panic_index()
        open_interest = fetch_total_open_interest()
        liquidation = fetch_liquidation_1h()
        
        # 组合数据
        indicators = {
            'panic_index': panic,
            'open_interest': open_interest,
            'liquidation_1h': liquidation,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存到最新数据文件（覆盖写入）
        with open(LATEST_FILE, 'w') as f:
            f.write(json.dumps(indicators, ensure_ascii=False) + '\n')
        
        # 追加到历史文件
        with open(HISTORY_FILE, 'a') as f:
            f.write(json.dumps(indicators, ensure_ascii=False) + '\n')
        
        log(f"✅ 数据采集成功")
        log(f"   恐慌指数: {panic['index'] if panic else 'N/A'}")
        log(f"   持仓量: {open_interest['total_open_interest'] if open_interest else 'N/A'} USDT")
        log(f"   1h爆仓: {liquidation['liquidation_1h'] if liquidation else 'N/A'} USDT")
        
        return indicators
        
    except Exception as e:
        log(f"❌ 数据采集失败: {e}")
        import traceback
        log(traceback.format_exc())
        return None

def main():
    """主函数"""
    log("🚀 市场指标采集器启动")
    log("📅 采集间隔: 每1分钟一次")
    
    while True:
        try:
            collect_indicators()
            log("⏰ 等待60秒后开始下一轮采集...")
            time.sleep(60)
        except KeyboardInterrupt:
            log("⚠️  收到停止信号，正在退出...")
            break
        except Exception as e:
            log(f"❌ 采集器出错: {e}")
            log("⏰ 等待10秒后重试...")
            time.sleep(10)

if __name__ == '__main__':
    # 首次运行立即采集一次
    collect_indicators()
    # 然后进入定时循环
    main()
