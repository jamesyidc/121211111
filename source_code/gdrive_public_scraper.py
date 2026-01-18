#!/usr/bin/env python3
"""
Google Drive 公开文件夹爬虫
直接通过 HTTP 访问公开链接，无需 API
"""

import requests
import re
from datetime import datetime
from typing import Optional, Tuple, List
import pytz
from bs4 import BeautifulSoup
import json

class GDrivePublicScraper:
    """Google Drive 公开文件夹爬虫"""
    
    def __init__(self, folder_id: str = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'):
        self.folder_id = folder_id
        self.beijing_tz = pytz.timezone('Asia/Shanghai')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
    
    def get_today_folder_name(self) -> str:
        """获取今天的文件夹名称（北京时间）"""
        now = datetime.now(self.beijing_tz)
        return now.strftime('%Y-%m-%d')
    
    def extract_data_from_page(self, html: str) -> List[dict]:
        """从页面中提取文件/文件夹数据"""
        import html as html_module
        
        # 解码 HTML 实体
        html = html_module.unescape(html)
        
        files = []
        
        # Google Drive 数据格式：["文件名","文件ID",...]
        # 多种模式匹配
        patterns = [
            r'\["(20\d{2}-\d{2}-\d{2}[^"]*)",\s*"([a-zA-Z0-9_-]{25,})"\]',  # 日期格式
            r'"(20\d{2}-\d{2}-\d{2}[^"]*)"[^\[]{0,100}"([a-zA-Z0-9_-]{28,})"',  # 宽松匹配
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for name, id_str in matches:
                if name and id_str and len(id_str) >= 28:
                    # 去重
                    if not any(f['name'] == name for f in files):
                        files.append({'name': name, 'id': id_str})
        
        print(f"📂 提取到 {len(files)} 个项目")
        
        if files:
            print("   前5个:")
            for item in files[:5]:
                print(f"     - {item['name'][:50]}")
        
        return files
    
    def find_today_folder_id(self) -> Optional[str]:
        """查找今天日期的文件夹ID"""
        try:
            today = self.get_today_folder_name()
            beijing_now = datetime.now(self.beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
            
            print("="*80)
            print(f"📅 当前北京时间: {beijing_now}")
            print(f"🔍 查找文件夹: {today}")
            print("="*80)
            
            # 访问主文件夹
            url = f'https://drive.google.com/drive/folders/{self.folder_id}'
            print(f"🌐 访问: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 提取文件列表
            files = self.extract_data_from_page(response.text)
            
            # 查找今天的文件夹
            for item in files:
                if item['name'] == today:
                    print(f"✅ 找到今天的文件夹: {today}")
                    print(f"   文件夹ID: {item['id']}")
                    return item['id']
            
            print(f"❌ 未找到文件夹: {today}")
            return None
            
        except Exception as e:
            print(f"❌ 查找文件夹失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def find_latest_txt_in_folder(self, folder_id: str) -> Optional[Tuple[str, str]]:
        """在文件夹中查找最新的 TXT 文件"""
        try:
            url = f'https://drive.google.com/drive/folders/{folder_id}'
            print(f"\n🌐 访问文件夹: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 提取文件列表
            files = self.extract_data_from_page(response.text)
            
            # 筛选 TXT 文件
            txt_files = [f for f in files if f['name'].endswith('.txt')]
            
            print(f"📄 找到 {len(txt_files)} 个 TXT 文件")
            
            if not txt_files:
                return None
            
            # 按文件名排序（时间戳格式会自然排序）
            txt_files.sort(key=lambda x: x['name'], reverse=True)
            
            # 显示前5个
            print("\n最新的文件:")
            for i, f in enumerate(txt_files[:5], 1):
                marker = "🏆" if i == 1 else "  "
                print(f"{marker} {i}. {f['name']}")
            
            latest = txt_files[0]
            print(f"\n✅ 选择最新文件: {latest['name']}")
            
            return (latest['id'], latest['name'])
            
        except Exception as e:
            print(f"❌ 查找TXT文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_file_content(self, file_id: str) -> Optional[str]:
        """下载文件内容"""
        try:
            # Google Drive 直接下载链接
            url = f'https://drive.google.com/uc?export=download&id={file_id}'
            
            print(f"\n📥 下载文件: {file_id[:20]}...")
            
            response = self.session.get(url, timeout=30)
            
            # 如果文件较大，可能需要确认
            if 'download_warning' in response.text or 'virus scan warning' in response.text.lower():
                # 获取确认令牌
                confirm_token = None
                for key, value in response.cookies.items():
                    if key.startswith('download_warning'):
                        confirm_token = value
                        break
                
                if confirm_token:
                    url = f'https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm_token}'
                    response = self.session.get(url, timeout=30)
            
            response.raise_for_status()
            
            # 解码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    content = response.content.decode(encoding)
                    print(f"✅ 成功下载并解码（{encoding}），大小: {len(content)} 字节")
                    return content
                except UnicodeDecodeError:
                    continue
            
            print("❌ 无法解码文件内容")
            return None
            
        except Exception as e:
            print(f"❌ 下载文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_latest_data(self) -> Optional[str]:
        """获取最新的数据文件内容"""
        try:
            # 1. 查找今天的文件夹
            today_folder_id = self.find_today_folder_id()
            
            if not today_folder_id:
                print("❌ 无法找到今天的文件夹")
                return None
            
            # 2. 查找最新的 TXT 文件
            result = self.find_latest_txt_in_folder(today_folder_id)
            
            if not result:
                print("❌ 无法找到TXT文件")
                return None
            
            file_id, filename = result
            
            # 3. 下载文件内容
            content = self.download_file_content(file_id)
            
            if content:
                print("\n" + "="*80)
                print("✅ 成功获取最新数据")
                print("="*80)
                print(f"文件名: {filename}")
                print(f"内容预览（前200字符）:")
                print("-"*80)
                print(content[:200])
                print("-"*80)
            
            return content
            
        except Exception as e:
            print(f"❌ 获取数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None


# 测试
if __name__ == '__main__':
    scraper = GDrivePublicScraper()
    content = scraper.get_latest_data()
    
    if content:
        print("\n✅ 测试成功！")
        
        # 保存到文件
        with open('crypto_latest_data.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 已保存到 crypto_latest_data.txt")
    else:
        print("\n❌ 测试失败")
