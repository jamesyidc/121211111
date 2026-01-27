#!/usr/bin/env python3
"""
加密货币数据解析器
解析从 TXT 文件读取的数据
"""

from typing import Dict, List, Optional
import re

class CryptoDataParser:
    """加密货币数据解析器"""
    
    @staticmethod
    def parse_txt_content(content: str) -> Optional[Dict]:
        """
        解析 TXT 文件内容
        
        Args:
            content: 文件内容
            
        Returns:
            {
                'stats': {...},  # 统计数据
                'data': [...]    # 币种列表
            }
        """
        try:
            lines = content.strip().split('\n')
            
            # 解析统计数据
            stats = {}
            crypto_list = []
            in_data_section = False
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    continue
                
                # 检查是否进入数据区
                if '[超级列表框_首页开始]' in line:
                    in_data_section = True
                    continue
                
                if '[超级列表框_首页结束]' in line:
                    in_data_section = False
                    continue
                
                # 解析统计标签
                if line.startswith('透明标签_'):
                    CryptoDataParser._parse_stat_line(line, stats)
                    continue
                
                # 解析币种数据
                if in_data_section:
                    crypto_data = CryptoDataParser._parse_crypto_line(line)
                    if crypto_data:
                        crypto_list.append(crypto_data)
            
            # 处理统计数据
            processed_stats = CryptoDataParser._process_stats(stats)
            
            print(f"✅ 解析完成: {len(crypto_list)} 个币种")
            print(f"   急涨: {processed_stats.get('rushUp', 0)}")
            print(f"   急跌: {processed_stats.get('rushDown', 0)}")
            print(f"   状态: {processed_stats.get('status', 'N/A')}")
            
            return {
                'stats': processed_stats,
                'data': crypto_list
            }
            
        except Exception as e:
            print(f"❌ 解析失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _parse_stat_line(line: str, stats: Dict):
        """解析统计行"""
        # 格式：透明标签_急涨总和=急涨：5
        match = re.match(r'透明标签_([^=]+)=(.+)', line)
        if match:
            key = match.group(1)
            value = match.group(2)
            stats[key] = value
    
    @staticmethod
    def _parse_crypto_line(line: str) -> Optional[Dict]:
        """解析币种行"""
        try:
            parts = line.split('|')
            
            if len(parts) < 16:
                return None
            
            return {
                'index': parts[0],              # 序号
                'symbol': parts[1],             # 币名
                'change': parts[2],             # 涨幅
                'rushUp': int(parts[3]) if parts[3] else 0,        # 急涨
                'rushDown': int(parts[4]) if parts[4] else 0,      # 急跌
                'updateTime': parts[5],         # 更新时间
                'highPrice': parts[6],          # 历史高价
                'highTime': parts[7],           # 高价时间
                'decline': parts[8],            # 跌幅
                'change24h': parts[9],          # 24h涨幅
                'col10': parts[10] if len(parts) > 10 else '',
                'col11': parts[11] if len(parts) > 11 else '',
                'col12': parts[12] if len(parts) > 12 else '',
                'rank': parts[13] if len(parts) > 13 else '',              # 排名
                'currentPrice': parts[14] if len(parts) > 14 else '',      # 当前价格
                'ratio1': parts[15] if len(parts) > 15 else '',            # 比率1
                'ratio2': parts[16] if len(parts) > 16 else ''             # 比率2
            }
            
        except Exception as e:
            print(f"⚠️  解析币种行失败: {e}")
            return None
    
    @staticmethod
    def _process_stats(stats: Dict) -> Dict:
        """处理统计数据"""
        processed = {}
        
        # 急涨总和
        if '急涨总和' in stats:
            match = re.search(r'急涨[：:]\s*(\d+)', stats['急涨总和'])
            if match:
                processed['rushUp'] = int(match.group(1))
        
        # 急跌总和
        if '急跌总和' in stats:
            match = re.search(r'急跌[：:]\s*(\d+)', stats['急跌总和'])
            if match:
                processed['rushDown'] = int(match.group(1))
        
        # 状态
        if '五种状态' in stats:
            match = re.search(r'状态[：:]\s*(.+)', stats['五种状态'])
            if match:
                processed['status'] = match.group(1).strip()
        
        # 比值
        if '急涨急跌比值' in stats:
            match = re.search(r'比值[：:]\s*(.+)', stats['急涨急跌比值'])
            if match:
                processed['ratio'] = match.group(1).strip()
        
        # 绿色数量
        if '绿色数量' in stats:
            match = re.search(r'(\d+)', stats['绿色数量'])
            if match:
                processed['greenCount'] = int(match.group(1))
        
        # 百分比
        if '百分比' in stats:
            match = re.search(r'(\d+%)', stats['百分比'])
            if match:
                processed['percentage'] = match.group(1)
        
        # 计次
        if '计次' in stats:
            match = re.search(r'(\d+)', stats['计次'])
            if match:
                processed['count'] = int(match.group(1))
        
        # 差值
        if '差值结果' in stats:
            match = re.search(r'差值[：:]\s*(-?\d+)', stats['差值结果'])
            if match:
                processed['diff'] = int(match.group(1))
        
        return processed


# 测试
if __name__ == '__main__':
    test_content = """透明标签_急涨总和=急涨：5
透明标签_急跌总和=急跌：5
透明标签_五种状态=状态：震荡无序
[超级列表框_首页开始]
1|BTC|-0.14|0|0|2025-12-03 08:21:29|126259.48|2025-10-07|-27.6|5.77|||20|91024.4169|72.6%|111.88%
2|ETH|-0.07|0|0|2025-12-03 08:21:29|4954.59|2025-08-25|-39.46|7.34|||13|2986.73521|61.84%|113.05%
[超级列表框_首页结束]
"""
    
    parser = CryptoDataParser()
    result = parser.parse_txt_content(test_content)
    
    if result:
        print("\n统计数据:", result['stats'])
        print("\n币种数量:", len(result['data']))
        if result['data']:
            print("第一个币种:", result['data'][0])
