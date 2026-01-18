#!/usr/bin/env python3
"""
简单的公开 Google Drive 文件读取器
通过下载页面直接获取文件内容，无需 API 认证
"""

import requests
import re
from datetime import datetime
from typing import Optional, List, Dict
import pytz

class SimpleGDriveReader:
    """简单的 Google Drive 公开文件夹读取器"""
    
    def __init__(self):
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        # 你的公开文件夹 ID
        self.base_folder_id = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_today_folder_name(self) -> str:
        """获取今天的文件夹名称（北京时间，格式：YYYY-MM-DD）"""
        now = datetime.now(self.beijing_tz)
        return now.strftime('%Y-%m-%d')
    
    def download_file_direct(self, file_id: str) -> Optional[str]:
        """
        直接下载 Google Drive 文件（公开访问）
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件内容（字符串）
        """
        try:
            # Google Drive 直接下载链接
            url = f'https://drive.google.com/uc?export=download&id={file_id}'
            
            print(f"📥 下载文件: {url}")
            
            response = self.session.get(url, timeout=30)
            
            # 如果文件较大，Google 会返回确认页面
            if 'virus scan warning' in response.text.lower() or 'download anyway' in response.text.lower():
                # 需要确认下载
                confirm_token = None
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        confirm_token = value
                        break
                
                if confirm_token:
                    url = f'https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}'
                    response = self.session.get(url, timeout=30)
            
            response.raise_for_status()
            
            # 尝试多种编码解码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    content = response.content.decode(encoding)
                    print(f"✅ 成功解码（{encoding}），内容长度: {len(content)} 字节")
                    return content.strip()
                except UnicodeDecodeError:
                    continue
            
            print("❌ 无法解码文件内容")
            return None
            
        except Exception as e:
            print(f"❌ 下载文件失败: {e}")
            return None
    
    def read_txt_by_file_id(self, file_id: str) -> Optional[List[Dict]]:
        """
        通过文件ID读取TXT并解析为币种数据列表
        
        Args:
            file_id: Google Drive 文件ID
            
        Returns:
            币种数据列表
        """
        try:
            content = self.download_file_direct(file_id)
            
            if not content:
                return None
            
            print(f"\n📄 文件内容预览（前200字符）:")
            print("-" * 80)
            print(content[:200])
            print("-" * 80)
            
            return self.parse_crypto_data(content)
            
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return None
    
    def parse_crypto_data(self, content: str) -> List[Dict]:
        """
        解析加密货币数据
        
        TXT 格式（每行一个币种）：
        序号|币名|涨幅|急涨|急跌|更新时间|历史高价|高价时间|跌幅|24h涨幅|其他字段...
        
        Args:
            content: 文件内容
            
        Returns:
            币种数据列表
        """
        try:
            lines = content.strip().split('\n')
            crypto_list = []
            
            print(f"\n🔍 解析数据，共 {len(lines)} 行")
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 按 | 分割
                parts = line.split('|')
                
                if len(parts) < 10:
                    print(f"⚠️  第 {i+1} 行数据不完整，跳过")
                    continue
                
                try:
                    crypto_data = {
                        'index': parts[0],                    # 序号
                        'symbol': parts[1],                   # 币名
                        'change': parts[2],                   # 涨幅
                        'rushUp': parts[3],                   # 急涨
                        'rushDown': parts[4],                 # 急跌
                        'updateTime': parts[5],               # 更新时间
                        'highPrice': parts[6],                # 历史高价
                        'highTime': parts[7],                 # 高价时间
                        'decline': parts[8],                  # 跌幅
                        'change24h': parts[9],                # 24h涨幅
                    }
                    
                    # 可选字段
                    if len(parts) > 10:
                        crypto_data['col10'] = parts[10] if len(parts) > 10 else ''
                        crypto_data['col11'] = parts[11] if len(parts) > 11 else ''
                        crypto_data['col12'] = parts[12] if len(parts) > 12 else ''
                        crypto_data['rank'] = parts[13] if len(parts) > 13 else ''
                        crypto_data['currentPrice'] = parts[14] if len(parts) > 14 else ''
                        crypto_data['ratio1'] = parts[15] if len(parts) > 15 else ''
                        crypto_data['ratio2'] = parts[16] if len(parts) > 16 else ''
                    
                    crypto_list.append(crypto_data)
                    
                except Exception as e:
                    print(f"⚠️  第 {i+1} 行解析失败: {e}")
                    continue
            
            print(f"✅ 成功解析 {len(crypto_list)} 个币种")
            
            if crypto_list:
                print(f"\n前3个币种:")
                for crypto in crypto_list[:3]:
                    print(f"  {crypto['index']:>2s}. {crypto['symbol']:6s} 涨幅:{crypto['change']:>6s} "
                          f"急涨:{crypto['rushUp']} 急跌:{crypto['rushDown']} "
                          f"更新:{crypto['updateTime']}")
            
            return crypto_list
            
        except Exception as e:
            print(f"❌ 解析数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []


# 测试函数
def test_reader():
    """测试读取器"""
    reader = SimpleGDriveReader()
    
    print("="*80)
    print("测试 Google Drive 文件读取")
    print("="*80)
    
    # 测试文件ID（你需要提供一个实际的文件ID）
    # 格式：https://drive.google.com/file/d/FILE_ID/view
    test_file_id = input("\n请输入测试文件ID（或按Enter跳过）: ").strip()
    
    if test_file_id:
        data = reader.read_txt_by_file_id(test_file_id)
        
        if data:
            print("\n✅ 测试成功！")
            print(f"读取到 {len(data)} 个币种数据")
        else:
            print("\n❌ 测试失败")
    else:
        print("跳过测试")


if __name__ == '__main__':
    test_reader()
