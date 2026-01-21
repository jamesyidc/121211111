#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
27币涨跌幅追踪系统
- 1分钟周期连续追踪
- 每天0点0分重置基准价
- 计算涨跌幅并求和
- 数据独立保存
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class CoinChangeTracker:
    def __init__(self):
        """初始化27币涨跌幅追踪器"""
        # 数据目录
        self.data_dir = PROJECT_ROOT / 'data' / 'coin_change_tracker'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 27个主流币种（永续合约）
        self.symbols = [
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP',
            'BNB-USDT-SWAP', 'SOL-USDT-SWAP', 'LTC-USDT-SWAP',
            'DOGE-USDT-SWAP', 'SUI-USDT-SWAP', 'TRX-USDT-SWAP',
            'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
            'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP',
            'LINK-USDT-SWAP', 'CRO-USDT-SWAP', 'DOT-USDT-SWAP',
            'AAVE-USDT-SWAP', 'UNI-USDT-SWAP', 'NEAR-USDT-SWAP',
            'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
            'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
        ]
        
        # 基准价格（每天0点重置）
        self.baseline_prices = {}
        self.baseline_date = None
        
        # OKX API
        self.okx_base_url = 'https://www.okx.com'
        
        print(f"✅ 27币涨跌幅追踪系统初始化完成")
        print(f"📁 数据目录: {self.data_dir}")
        print(f"📊 追踪币种数: {len(self.symbols)}")
    
    def get_beijing_time(self):
        """获取北京时间"""
        return datetime.now(timezone(timedelta(hours=8)))
    
    def get_current_date_str(self):
        """获取当前日期字符串（YYYYMMDD）"""
        return self.get_beijing_time().strftime('%Y%m%d')
    
    def get_data_file_path(self, date_str=None):
        """获取数据文件路径"""
        if date_str is None:
            date_str = self.get_current_date_str()
        return self.data_dir / f'coin_change_{date_str}.jsonl'
    
    def fetch_current_prices(self):
        """从OKX获取当前币价"""
        try:
            url = f'{self.okx_base_url}/api/v5/market/tickers?instType=SWAP'
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') != '0':
                print(f"❌ 获取行情失败: {data.get('msg')}")
                return None
            
            prices = {}
            for ticker in data.get('data', []):
                inst_id = ticker.get('instId')
                if inst_id in self.symbols:
                    prices[inst_id] = float(ticker.get('last', 0))
            
            return prices
            
        except Exception as e:
            print(f"❌ 获取币价异常: {str(e)}")
            return None
    
    def check_and_reset_baseline(self):
        """检查是否需要重置基准价（每天0点）"""
        current_time = self.get_beijing_time()
        current_date = current_time.strftime('%Y%m%d')
        
        # 如果是新的一天，或者基准价为空，则重置
        if self.baseline_date != current_date or not self.baseline_prices:
            print(f"\n🔄 检测到新的一天: {current_date}，重置基准价")
            
            # 获取当前价格作为基准价
            current_prices = self.fetch_current_prices()
            if current_prices:
                self.baseline_prices = current_prices
                self.baseline_date = current_date
                
                # 保存基准价到文件
                baseline_file = self.data_dir / f'baseline_{current_date}.json'
                with open(baseline_file, 'w') as f:
                    json.dump({
                        'date': current_date,
                        'timestamp': current_time.isoformat(),
                        'prices': self.baseline_prices
                    }, f, indent=2)
                
                print(f"✅ 基准价已重置并保存: {baseline_file}")
                print(f"📊 基准价数量: {len(self.baseline_prices)}")
                return True
            else:
                print(f"❌ 获取基准价失败")
                return False
        
        return True
    
    def calculate_changes(self, current_prices):
        """计算涨跌幅"""
        changes = {}
        
        for symbol in self.symbols:
            baseline_price = self.baseline_prices.get(symbol)
            current_price = current_prices.get(symbol)
            
            if baseline_price and current_price and baseline_price > 0:
                change_pct = ((current_price - baseline_price) / baseline_price) * 100
                changes[symbol] = {
                    'baseline_price': baseline_price,
                    'current_price': current_price,
                    'change_pct': round(change_pct, 2)
                }
            else:
                changes[symbol] = {
                    'baseline_price': baseline_price or 0,
                    'current_price': current_price or 0,
                    'change_pct': 0,
                    'error': 'price_missing'
                }
        
        return changes
    
    def save_record(self, changes, total_change):
        """保存追踪记录"""
        beijing_time = self.get_beijing_time()
        date_str = beijing_time.strftime('%Y%m%d')
        
        record = {
            'timestamp': beijing_time.isoformat(),
            'timestamp_unix': int(beijing_time.timestamp()),
            'date': date_str,
            'time': beijing_time.strftime('%H:%M:%S'),
            'baseline_date': self.baseline_date,
            'total_change': round(total_change, 2),
            'valid_count': len([c for c in changes.values() if 'error' not in c]),
            'changes': changes
        }
        
        # 保存到JSONL文件
        data_file = self.get_data_file_path(date_str)
        with open(data_file, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return record
    
    def run_once(self):
        """执行一次追踪"""
        try:
            # 检查并重置基准价
            if not self.check_and_reset_baseline():
                return None
            
            # 获取当前价格
            current_prices = self.fetch_current_prices()
            if not current_prices:
                print(f"❌ 获取当前价格失败")
                return None
            
            # 计算涨跌幅
            changes = self.calculate_changes(current_prices)
            
            # 计算总涨跌幅
            total_change = sum([
                c['change_pct'] 
                for c in changes.values() 
                if 'error' not in c
            ])
            
            # 保存记录
            record = self.save_record(changes, total_change)
            
            # 打印结果
            beijing_time = self.get_beijing_time()
            valid_count = len([c for c in changes.values() if 'error' not in c])
            
            print(f"\n⏰ {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
            print(f"📊 27币涨跌幅之和: {total_change:+.2f}%")
            print(f"✅ 有效币种数: {valid_count}/{len(self.symbols)}")
            
            # 显示涨幅最大和最小的3个币种
            valid_changes = {k: v for k, v in changes.items() if 'error' not in v}
            sorted_changes = sorted(valid_changes.items(), key=lambda x: x[1]['change_pct'], reverse=True)
            
            if sorted_changes:
                print(f"\n📈 涨幅前3:")
                for symbol, data in sorted_changes[:3]:
                    coin_name = symbol.replace('-USDT-SWAP', '')
                    print(f"   {coin_name}: {data['change_pct']:+.2f}% (${data['current_price']:.4f})")
                
                print(f"\n📉 跌幅前3:")
                for symbol, data in sorted_changes[-3:]:
                    coin_name = symbol.replace('-USDT-SWAP', '')
                    print(f"   {coin_name}: {data['change_pct']:+.2f}% (${data['current_price']:.4f})")
            
            return record
            
        except Exception as e:
            print(f"❌ 执行追踪异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_loop(self):
        """持续运行（1分钟周期）"""
        print(f"\n🚀 开始27币涨跌幅持续追踪")
        print(f"⏱️  追踪周期: 1分钟")
        print(f"🔄 基准价重置: 每天0点0分")
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        while True:
            try:
                # 执行一次追踪
                self.run_once()
                
                # 等待到下一分钟的0秒
                now = self.get_beijing_time()
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                sleep_seconds = (next_minute - now).total_seconds()
                
                print(f"\n💤 等待 {sleep_seconds:.1f} 秒到下一分钟...")
                time.sleep(sleep_seconds)
                
            except KeyboardInterrupt:
                print(f"\n\n⚠️  收到中断信号，停止追踪")
                break
            except Exception as e:
                print(f"\n❌ 循环异常: {str(e)}")
                time.sleep(60)  # 发生异常时等待1分钟后重试

def main():
    """主函数"""
    tracker = CoinChangeTracker()
    tracker.run_loop()

if __name__ == '__main__':
    main()
