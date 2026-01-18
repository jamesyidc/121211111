#!/usr/bin/env python3
"""
公开 Google Drive 文件夹读取器
不需要 API 凭据，直接通过公开链接访问
"""

import requests
import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import pytz
from bs4 import BeautifulSoup

class PublicGDriveReader:
    """公开 Google Drive 文件夹读取器"""
    
    def __init__(self, folder_id: str = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'):
        """
        初始化读取器
        
        Args:
            folder_id: Google Drive 公开文件夹 ID
        """
        self.folder_id = folder_id
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_today_folder_name(self) -> str:
        """获取今天的文件夹名称（北京时间）"""
        now = datetime.now(self.beijing_tz)
        return now.strftime('%Y-%m-%d')
    
    def list_folder_contents(self, folder_id: str) -> List[Dict]:
        """
        列出文件夹内容
        
        Args:
            folder_id: 文件夹 ID
            
        Returns:
            文件列表
        """
        try:
            # 使用 Google Drive 的公开文件夹查看 URL
            url = f'https://drive.google.com/drive/folders/{folder_id}'
            
            print(f"🔍 正在访问: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 从页面 HTML 中提取文件列表
            # Google Drive 公开文件夹的数据通常在 JavaScript 变量中
            html = response.text
            
            # 查找文件数据（通常在 window['_DRIVE_ivd'] 或类似变量中）
            files = []
            
            # 尝试匹配文件名模式
            # 格式：2025-12-02_2238.txt
            pattern = r'(\d{4}-\d{2}-\d{2}_\d{4}\.txt)'
            matches = re.findall(pattern, html)
            
            if matches:
                # 去重
                unique_files = list(set(matches))
                print(f"✅ 找到 {len(unique_files)} 个 TXT 文件")
                
                for filename in unique_files:
                    files.append({
                        'name': filename,
                        'id': None  # 公开访问不需要 ID
                    })
                
                return files
            else:
                print("⚠️  未找到时间戳格式的 TXT 文件")
                return []
                
        except Exception as e:
            print(f"❌ 列出文件夹内容失败: {e}")
            return []
    
    def find_latest_txt_in_folder(self, folder_id: str) -> Optional[str]:
        """
        在文件夹中查找最新的 TXT 文件
        
        Args:
            folder_id: 文件夹 ID
            
        Returns:
            最新文件名
        """
        files = self.list_folder_contents(folder_id)
        
        if not files:
            return None
        
        # 按文件名排序（时间戳格式会自然排序）
        timestamped_files = []
        
        for file in files:
            filename = file['name']
            # 提取时间戳：2025-12-02_2238.txt
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                timestamp_str = f"{date_str} {time_str[:2]}:{time_str[2:]}"
                timestamped_files.append((filename, timestamp_str))
        
        if timestamped_files:
            # 按时间戳降序排序
            timestamped_files.sort(key=lambda x: x[1], reverse=True)
            latest_file = timestamped_files[0][0]
            latest_time = timestamped_files[0][1]
            
            print(f"✅ 最新文件: {latest_file}")
            print(f"   时间戳: {latest_time}")
            
            return latest_file
        
        return None
    
    def download_file_by_name(self, folder_id: str, filename: str) -> Optional[str]:
        """
        通过文件名下载文件内容
        
        Args:
            folder_id: 文件夹 ID
            filename: 文件名
            
        Returns:
            文件内容
        """
        try:
            # 方法1: 尝试直接构造下载链接（如果知道文件ID）
            # 方法2: 爬取文件夹页面获取下载链接
            
            # 这里我们使用另一种方法：通过文件夹页面获取文件ID
            folder_url = f'https://drive.google.com/drive/folders/{folder_id}'
            
            print(f"🔍 查找文件: {filename}")
            
            response = self.session.get(folder_url, timeout=30)
            response.raise_for_status()
            
            html = response.text
            
            # 尝试提取文件ID（Google Drive的文件ID通常是33个字符）
            # 查找包含文件名和ID的模式
            pattern = rf'\["({filename})"[^\]]*?"([a-zA-Z0-9_-]{{25,}})"'
            match = re.search(pattern, html)
            
            if match:
                file_id = match.group(2)
                print(f"✅ 找到文件ID: {file_id[:20]}...")
                
                # 下载文件
                download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
                
                print(f"📥 正在下载: {download_url}")
                
                response = self.session.get(download_url, timeout=30)
                response.raise_for_status()
                
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                    try:
                        content = response.content.decode(encoding)
                        print(f"✅ 成功解码（{encoding}），内容长度: {len(content)} 字节")
                        return content
                    except UnicodeDecodeError:
                        continue
                
                print("❌ 无法解码文件内容")
                return None
            else:
                print(f"❌ 未找到文件ID: {filename}")
                return None
                
        except Exception as e:
            print(f"❌ 下载文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def read_latest_signal_txt(self) -> Optional[Dict]:
        """
        读取今天文件夹中最新的信号 TXT 文件
        
        Returns:
            解析后的信号数据字典
        """
        try:
            # 1. 获取今天的日期（北京时间）
            today = self.get_today_folder_name()
            beijing_now = datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            print("="*80)
            print(f"📅 当前北京时间: {beijing_now}")
            print(f"🔍 查找日期文件夹: {today}")
            print("="*80)
            
            # 2. 构造今天文件夹的 URL
            # 注意：公开文件夹的子文件夹也需要是公开的
            # 我们需要先列出主文件夹，找到今天的子文件夹ID
            
            # 由于公开访问限制，我们直接尝试访问主文件夹
            # 并查找今天日期的文件
            
            # 3. 查找最新的 TXT 文件
            latest_file = self.find_latest_txt_in_folder(self.folder_id)
            
            if not latest_file:
                print("❌ 未找到最新的 TXT 文件")
                return None
            
            # 4. 下载文件内容
            content = self.download_file_by_name(self.folder_id, latest_file)
            
            if not content:
                print("❌ 下载文件内容失败")
                return None
            
            # 5. 解析内容
            print("\n" + "="*80)
            print("📄 文件内容:")
            print("="*80)
            print(content)
            print("="*80)
            
            return self._parse_signal_data(content)
            
        except Exception as e:
            print(f"❌ 读取信号数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_signal_data(self, content: str) -> Optional[Dict]:
        """
        解析信号数据
        
        格式：做空信号|变化|做多信号|变化|时间
        示例：146|0|0|0|2025-12-02 22:38:00
        """
        try:
            parts = content.strip().split('|')
            
            if len(parts) < 5:
                print(f"❌ 数据格式错误，期望5个字段，实际得到 {len(parts)} 个")
                return None
            
            result = {
                'short': int(parts[0]),
                'short_change': int(parts[1]),
                'long': int(parts[2]),
                'long_change': int(parts[3]),
                'update_time': parts[4]
            }
            
            print("\n✅ 解析成功:")
            print(f"   🔴 做空信号: {result['short']}")
            print(f"      变化: {result['short_change']:+d}")
            print(f"   🟢 做多信号: {result['long']}")
            print(f"      变化: {result['long_change']:+d}")
            print(f"   📅 更新时间: {result['update_time']}")
            
            return result
            
        except Exception as e:
            print(f"❌ 解析数据失败: {e}")
            return None


if __name__ == '__main__':
    # 测试
    reader = PublicGDriveReader()
    data = reader.read_latest_signal_txt()
    
    if data:
        print("\n" + "="*80)
        print("✅ 测试成功！")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("❌ 测试失败")
        print("="*80)
