#!/usr/bin/env python3
"""
虚拟币系统监控 - Google Drive数据读取模块（增强版）
支持自动从 Google Drive 读取最新数据，失败时回退到演示数据
"""

import re
from datetime import datetime
import pytz
from typing import Dict, Optional
import urllib.request
import urllib.parse

# 尝试导入 Google Drive 读取器
try:
    from gdrive_reader import GDriveReader
    GDRIVE_AVAILABLE = True
except ImportError:
    GDRIVE_AVAILABLE = False
    print("⚠️  Google Drive 读取器未安装，将使用演示数据")

class MonitorDataReader:
    def __init__(self):
        """初始化数据读取器"""
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        # Google Drive共享文件夹ID
        self.folder_id = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
        
        # 初始化 Google Drive 读取器（如果可用）
        self.gdrive_reader = None
        if GDRIVE_AVAILABLE:
            try:
                self.gdrive_reader = GDriveReader(self.folder_id)
                print("✅ Google Drive 读取器已初始化")
            except Exception as e:
                print(f"⚠️  初始化 Google Drive 读取器失败: {e}")
    
    def get_today_folder_url(self) -> str:
        """获取今天日期的文件夹名称（北京时间）"""
        now = datetime.now(self.beijing_tz)
        today = now.strftime('%Y-%m-%d')
        return today
    
    def read_signal_data(self, content: str) -> Optional[Dict]:
        """
        解析信号.txt内容
        格式: 146|0|0|0|2025-12-02 22:05:39
        字段: 做空信号|变化|做多信号|变化|时间
        注意：
        - parts[0] = 做空信号 (Short signal) -> 映射为 'short'
        - parts[2] = 做多信号 (Long signal) -> 映射为 'long'
        """
        try:
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                # 解析数据行
                parts = line.split('|')
                if len(parts) >= 5:
                    return {
                        'short': parts[0].strip(),        # 做空信号
                        'short_change': parts[1].strip(), # 做空变化
                        'long': parts[2].strip(),         # 做多信号
                        'long_change': parts[3].strip(),  # 做多变化
                        'update_time': parts[4].strip()   # 更新时间
                    }
            
            return None
        except Exception as e:
            print(f"❌ 解析信号数据失败: {e}")
            return None
    
    def read_panic_data(self, content: str) -> Optional[Dict]:
        """
        解析恐慌清洗.txt内容
        格式: 10.77-绿|5-多头主升区间-99305-2.26-92.18-2025-12-02 20:58:50
        字段: 恐慌清洗指标|趋势评级-市场区间-24h爆仓人数-24h爆仓金额-全网持仓量-时间
        """
        try:
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                # 解析数据行
                parts = line.split('|')
                if len(parts) >= 2:
                    # 第一部分: 恐慌清洗指标
                    panic_indicator = parts[0].strip()
                    
                    # 第二部分: 其他数据（用-分隔）
                    # 格式: 5-多头主升区间-99305-2.26-92.18-2025-12-02 20:58:50
                    other_data = parts[1].strip()
                    
                    # 使用正则表达式提取最后的时间部分
                    import re
                    time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})$', other_data)
                    if time_match:
                        update_time = time_match.group(1)
                        # 去掉时间后的剩余部分
                        data_without_time = other_data[:time_match.start()].rstrip('-')
                        
                        # 分割剩余数据
                        other_parts = data_without_time.split('-')
                        
                        if len(other_parts) >= 5:
                            return {
                                'panic_indicator': panic_indicator,
                                'trend_rating': other_parts[0].strip(),
                                'market_zone': other_parts[1].strip(),
                                'liquidation_24h_count': other_parts[2].strip(),
                                'liquidation_24h_amount': other_parts[3].strip(),
                                'total_position': other_parts[4].strip(),
                                'update_time': update_time
                            }
            
            return None
        except Exception as e:
            print(f"❌ 解析恐慌清洗数据失败: {e}")
            return None
    
    def get_signal_data(self) -> Dict:
        """
        获取信号数据（优先从 Google Drive 读取，失败时使用演示数据）
        
        Returns:
            信号数据字典
        """
        # 1. 尝试从 Google Drive 读取
        if self.gdrive_reader:
            try:
                data = self.gdrive_reader.read_signal_txt()
                if data:
                    print("✅ 从 Google Drive 读取信号数据成功")
                    return data
            except Exception as e:
                print(f"⚠️  从 Google Drive 读取信号数据失败: {e}")
        
        # 2. 回退到演示数据
        print("ℹ️  使用演示信号数据")
        return self.get_demo_signal_data()
    
    def get_panic_data(self) -> Dict:
        """
        获取恐慌清洗数据（优先从 Google Drive 读取，失败时使用演示数据）
        
        Returns:
            恐慌清洗数据字典
        """
        # 1. 尝试从 Google Drive 读取
        if self.gdrive_reader:
            try:
                data = self.gdrive_reader.read_panic_txt()
                if data:
                    print("✅ 从 Google Drive 读取恐慌清洗数据成功")
                    return data
            except Exception as e:
                print(f"⚠️  从 Google Drive 读取恐慌清洗数据失败: {e}")
        
        # 2. 回退到演示数据
        print("ℹ️  使用演示恐慌清洗数据")
        return self.get_demo_panic_data()
    
    def get_demo_signal_data(self) -> Dict:
        """
        获取演示信号数据
        注意：字段对应关系
        - short = 做空信号（红色）
        - long = 做多信号（绿色）
        
        根据实际TXT文件: 146|0|0|0|2025-12-02 22:05:39
        """
        now = datetime.now(self.beijing_tz)
        return {
            'short': '146',        # 做空信号
            'short_change': '0',   # 做空变化
            'long': '0',           # 做多信号
            'long_change': '0',    # 做多变化
            'update_time': now.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_demo_panic_data(self) -> Dict:
        """
        获取演示恐慌清洗数据
        根据实际数据格式更新：2025-12-02 21:17:28
        """
        now = datetime.now(self.beijing_tz)
        return {
            'panic_indicator': '10.68-绿',          # 恐慌清洗指标
            'trend_rating': '5',                     # 趋势评级
            'market_zone': '多头洗盘空间',           # 市场区间
            'liquidation_24h_count': '126259',       # 24h爆仓人数
            'liquidation_24h_amount': '2.88',        # 24h爆仓金额（亿美元）
            'total_position': '92.27',               # 全网持仓量（亿美元）
            'update_time': now.strftime('%Y-%m-%d %H:%M:%S')
        }

if __name__ == '__main__':
    reader = MonitorDataReader()
    
    print("测试数据解析:")
    print("\n1. 信号数据:")
    signal_content = "126|0|0|0|2025-12-02 20:56:01"
    signal_data = reader.read_signal_data(signal_content)
    print(signal_data)
    
    print("\n2. 恐慌清洗数据:")
    panic_content = "10.77-绿|5-多头主升区间-99305-2.26-92.18-2025-12-02 20:58:50"
    panic_data = reader.read_panic_data(panic_content)
    print(panic_data)
