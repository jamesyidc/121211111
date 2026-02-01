#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
得分整合系统 - 整合两个数据源的做多做空评分
数据源1: 19种币 (https://3000-i42fq2f1mk8544uuc8pew-5c13a017.sandbox.novita.ai)
数据源2: 8种币 (https://3000-itkyuobnbphje7wgo4xbk-c07dda5e.sandbox.novita.ai)
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Tuple
import statistics

class ScoreIntegrationSystem:
    def __init__(self):
        # 数据源配置
        self.source1_base = "https://3000-i42fq2f1mk8544uuc8pew-5c13a017.sandbox.novita.ai"
        self.source2_base = "https://3000-itkyuobnbphje7wgo4xbk-c07dda5e.sandbox.novita.ai"
        self.source2_port = 5011
        
        # 时间范围
        self.time_ranges = ['3m', '1h', '3h', '6h', '12h', '24h']
        self.range_labels = {
            '3m': '3分钟',
            '1h': '1小时',
            '3h': '3小时',
            '6h': '6小时',
            '12h': '12小时',
            '24h': '24小时'
        }
        
        # 币种列表
        self.source1_symbols = [
            # 数据源1的19种币（需要从实际API获取）
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'BNB-USDT-SWAP',
            'XRP-USDT-SWAP', 'ADA-USDT-SWAP', 'DOGE-USDT-SWAP',
            'SOL-USDT-SWAP', 'DOT-USDT-SWAP', 'MATIC-USDT-SWAP',
            'LINK-USDT-SWAP', 'UNI-USDT-SWAP', 'AVAX-USDT-SWAP',
            'ATOM-USDT-SWAP', 'ETC-USDT-SWAP', 'FIL-USDT-SWAP',
            'NEAR-USDT-SWAP', 'AAVE-USDT-SWAP', 'APT-USDT-SWAP',
            'ARB-USDT-SWAP'
        ]
        
        self.source2_symbols = [
            'FIL-USDT-SWAP', 'UNI-USDT-SWAP', 'TAO-USDT-SWAP',
            'CFX-USDT-SWAP', 'BTC-USDT-SWAP', 'HBAR-USDT-SWAP',
            'XLM-USDT-SWAP', 'BCH-USDT-SWAP'
        ]
        
        # 合并所有币种（去重）
        all_symbols_set = set(self.source1_symbols + self.source2_symbols)
        self.all_symbols = sorted(list(all_symbols_set))
        
    def fetch_source2_data(self, symbol: str, time_range: str) -> Dict:
        """
        从数据源2获取数据
        """
        url = f"http://{self.source2_base.split('//')[1].replace('3000-', f'{self.source2_port}-')}/api/depth/history/{symbol}?range={time_range}"
        try:
            response = requests.get(url, timeout=10)
            return response.json()
        except Exception as e:
            print(f"❌ 获取 {symbol} {time_range} 数据失败: {e}")
            return {"success": False}
    
    def calculate_average_scores(self, history_data: List[Dict]) -> Tuple[float, float, float]:
        """
        计算平均做多得分、做空得分和差值
        """
        if not history_data:
            return 0.0, 0.0, 0.0
        
        long_scores = [item['long_score'] for item in history_data if 'long_score' in item]
        short_scores = [item['short_score'] for item in history_data if 'short_score' in item]
        
        if not long_scores or not short_scores:
            return 0.0, 0.0, 0.0
        
        avg_long = statistics.mean(long_scores)
        avg_short = statistics.mean(short_scores)
        avg_diff = avg_long - avg_short
        
        return avg_long, avg_short, avg_diff
    
    def fetch_all_data(self) -> Dict:
        """
        获取所有数据源的所有数据
        """
        print("📊 开始获取所有数据...")
        all_data = {}
        
        # 目前只能从数据源2获取数据
        for symbol in self.source2_symbols:
            print(f"  🔄 获取 {symbol} 数据...")
            symbol_data = {}
            
            for time_range in self.time_ranges:
                data = self.fetch_source2_data(symbol, time_range)
                symbol_data[time_range] = data
            
            all_data[symbol] = symbol_data
        
        print("✅ 数据获取完成")
        return all_data
    
    def generate_statistics(self, all_data: Dict) -> Dict:
        """
        生成统计数据
        返回格式: {
            '3m': {'avg_long': x, 'avg_short': y, 'avg_diff': z},
            '1h': {...},
            ...
        }
        """
        statistics_result = {}
        
        for time_range in self.time_ranges:
            long_scores_all = []
            short_scores_all = []
            diffs_all = []
            
            # 收集所有币种在该时间段的平均得分
            for symbol, symbol_data in all_data.items():
                range_data = symbol_data.get(time_range, {})
                
                if range_data.get('success') and range_data.get('history'):
                    avg_long, avg_short, avg_diff = self.calculate_average_scores(range_data['history'])
                    long_scores_all.append(avg_long)
                    short_scores_all.append(avg_short)
                    diffs_all.append(avg_diff)
            
            # 计算该时间段所有币种的平均值
            if long_scores_all and short_scores_all:
                statistics_result[time_range] = {
                    'avg_long': statistics.mean(long_scores_all),
                    'avg_short': statistics.mean(short_scores_all),
                    'avg_diff': statistics.mean(diffs_all),
                    'coin_count': len(long_scores_all)
                }
            else:
                statistics_result[time_range] = {
                    'avg_long': 0.0,
                    'avg_short': 0.0,
                    'avg_diff': 0.0,
                    'coin_count': 0
                }
        
        return statistics_result
    
    def generate_coin_statistics(self, all_data: Dict) -> Dict:
        """
        生成每个币种的统计数据
        """
        coin_stats = {}
        
        for symbol, symbol_data in all_data.items():
            coin_name = symbol.split('-')[0]
            coin_stats[coin_name] = {}
            
            for time_range in self.time_ranges:
                range_data = symbol_data.get(time_range, {})
                
                if range_data.get('success') and range_data.get('history'):
                    avg_long, avg_short, avg_diff = self.calculate_average_scores(range_data['history'])
                    coin_stats[coin_name][time_range] = {
                        'long': avg_long,
                        'short': avg_short,
                        'diff': avg_diff
                    }
                else:
                    coin_stats[coin_name][time_range] = {
                        'long': 0.0,
                        'short': 0.0,
                        'diff': 0.0
                    }
        
        return coin_stats
    
    def print_statistics_report(self, stats: Dict, coin_stats: Dict):
        """
        打印统计报告
        """
        print("\n" + "="*80)
        print("📊 得分整合系统 - 统计报告")
        print("="*80)
        print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据源: 2个 (数据源1暂不可用)")
        print(f"币种数量: {len(coin_stats)}")
        print("="*80)
        
        # 打印各时间段统计
        print("\n📈 各时间段平均得分统计:")
        print("-"*80)
        print(f"{'时间段':<10} {'平均做多得分':<15} {'平均做空得分':<15} {'平均差值':<15} {'币种数量'}")
        print("-"*80)
        
        for time_range in self.time_ranges:
            stat = stats[time_range]
            label = self.range_labels[time_range]
            trend = "📈 看多" if stat['avg_diff'] > 0 else "📉 看空"
            
            print(f"{label:<8} "
                  f"{stat['avg_long']:>13.2f}   "
                  f"{stat['avg_short']:>13.2f}   "
                  f"{stat['avg_diff']:>+13.2f}   "
                  f"{stat['coin_count']:>6} {trend}")
        
        print("-"*80)
        
        # 打印各币种详细数据
        print("\n💰 各币种详细得分:")
        print("-"*120)
        header = "币种    "
        for time_range in self.time_ranges:
            header += f" {self.range_labels[time_range]:<25}"
        print(header)
        print(" " * 8 + "做多   做空   差值     " * len(self.time_ranges))
        print("-"*120)
        
        for coin_name in sorted(coin_stats.keys()):
            row = f"{coin_name:<6}  "
            for time_range in self.time_ranges:
                data = coin_stats[coin_name][time_range]
                row += f"{data['long']:>5.1f} {data['short']:>5.1f} {data['diff']:>+6.1f}  "
            print(row)
        
        print("-"*120)
        print("\n✅ 报告生成完成\n")

def main():
    """
    主函数
    """
    system = ScoreIntegrationSystem()
    
    # 获取所有数据
    all_data = system.fetch_all_data()
    
    # 生成统计
    stats = system.generate_statistics(all_data)
    coin_stats = system.generate_coin_statistics(all_data)
    
    # 打印报告
    system.print_statistics_report(stats, coin_stats)
    
    # 保存JSON结果
    result = {
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'statistics': stats,
        'coin_statistics': coin_stats
    }
    
    output_file = '/home/user/webapp/score_statistics.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"📄 统计结果已保存到: {output_file}\n")
    
    return result

if __name__ == '__main__':
    main()
