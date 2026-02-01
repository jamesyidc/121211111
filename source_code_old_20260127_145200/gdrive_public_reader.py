#!/usr/bin/env python3
"""
Google Drive 公开文件夹读取器
直接使用公开分享链接访问，不需要认证
"""
import requests
import re
import json
from datetime import datetime
from typing import List, Dict, Optional

class GDrivePublicReader:
    """Google Drive 公开文件夹读取器"""
    
    def __init__(self, folder_id: str):
        self.folder_id = folder_id
        self.base_url = "https://drive.google.com/drive/folders/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_folder_content(self, folder_id: str = None) -> str:
        """获取文件夹内容的HTML"""
        if folder_id is None:
            folder_id = self.folder_id
        
        url = f"{self.base_url}{folder_id}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    
    def extract_items(self, html_content: str, pattern: str) -> List[str]:
        """从HTML中提取匹配的项目"""
        matches = re.findall(pattern, html_content)
        # 如果匹配结果是元组列表，取第一个元素
        if matches and isinstance(matches[0], tuple):
            matches = [m[0] if isinstance(m, tuple) else m for m in matches]
        return list(set(matches))  # 去重
    
    def find_date_folders(self, folder_id: str = None) -> List[str]:
        """查找日期格式的文件夹（YYYY-MM-DD）"""
        html = self.get_folder_content(folder_id)
        
        # 匹配日期格式 YYYY-MM-DD
        date_pattern = r'\b(20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))\b'
        dates = self.extract_items(html, date_pattern)
        
        # 验证日期有效性
        valid_dates = []
        for date_str in dates:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                valid_dates.append(date_str)
            except ValueError:
                continue
        
        return sorted(valid_dates, reverse=True)
    
    def find_date_folder_id(self, target_date: str, folder_id: str = None) -> Optional[str]:
        """查找指定日期文件夹的ID"""
        html = self.get_folder_content(folder_id)
        
        # 在HTML中查找包含目标日期的部分，然后提取ID
        # Google Drive 的文件夹ID格式: data-id="FOLDER_ID"
        pattern = f'{target_date}.*?data-id=["\']([^"\']+)["\']'
        matches = re.findall(pattern, html, re.DOTALL)
        
        if matches:
            return matches[0]
        
        # 备用方案：搜索所有ID，然后逐个测试
        id_pattern = r'data-id=["\']([a-zA-Z0-9_-]{28,})["\']'
        all_ids = self.extract_items(html, id_pattern)
        
        for folder_id_candidate in all_ids:
            try:
                sub_html = self.get_folder_content(folder_id_candidate)
                # 检查这个文件夹的标题是否包含目标日期
                if target_date in sub_html:
                    return folder_id_candidate
            except:
                continue
        
        return None
    
    def find_txt_files(self, date_folder_id: str) -> List[Dict]:
        """查找指定文件夹中的TXT文件"""
        html = self.get_folder_content(date_folder_id)
        
        # 匹配 YYYY-MM-DD_HHMM.txt 格式的文件
        pattern = r'(20\d{2}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])_\d{4}\.txt)'
        txt_files = self.extract_items(html, pattern)
        
        # 提取文件ID
        files_info = []
        for filename in txt_files:
            # 尝试找到文件ID
            file_pattern = f'{re.escape(filename)}.*?data-id=["\']([^"\']+)["\']'
            matches = re.findall(file_pattern, html, re.DOTALL)
            
            if matches:
                file_id = matches[0]
                download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
                
                files_info.append({
                    'filename': filename,
                    'file_id': file_id,
                    'download_url': download_url
                })
        
        # 按文件名排序（最新的在前）
        files_info.sort(key=lambda x: x['filename'], reverse=True)
        
        return files_info
    
    def get_latest_txt_file(self, target_date: str = None) -> Optional[Dict]:
        """获取指定日期（或今天）最新的TXT文件"""
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"📅 查找日期: {target_date}")
        
        # 1. 先查找日期文件夹
        print(f"🔍 在文件夹 {self.folder_id} 中查找日期文件夹...")
        date_folders = self.find_date_folders()
        
        if not date_folders:
            print("❌ 未找到任何日期文件夹")
            return None
        
        print(f"✅ 找到 {len(date_folders)} 个日期文件夹")
        print(f"   最新的5个: {date_folders[:5]}")
        
        if target_date not in date_folders:
            print(f"❌ 未找到 {target_date} 文件夹")
            print(f"   最新可用日期: {date_folders[0]}")
            return None
        
        # 2. 查找该日期文件夹的ID
        print(f"🔍 查找 {target_date} 文件夹的ID...")
        date_folder_id = self.find_date_folder_id(target_date)
        
        if not date_folder_id:
            print(f"❌ 无法获取 {target_date} 文件夹的ID")
            return None
        
        print(f"✅ 找到文件夹ID: {date_folder_id}")
        
        # 3. 列出该文件夹中的TXT文件
        print(f"📄 列出 {target_date} 中的TXT文件...")
        txt_files = self.find_txt_files(date_folder_id)
        
        if not txt_files:
            print(f"❌ 在 {target_date} 文件夹中未找到TXT文件")
            return None
        
        print(f"✅ 找到 {len(txt_files)} 个TXT文件")
        print(f"   最新的: {txt_files[0]['filename']}")
        
        return txt_files[0]


def test_reader():
    """测试读取器"""
    print("=" * 60)
    print("🧪 测试 Google Drive 公开文件夹读取器")
    print("=" * 60)
    
    # 使用"首页数据"文件夹ID
    folder_id = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
    reader = GDrivePublicReader(folder_id)
    
    # 测试1: 列出所有日期文件夹
    print("\n📋 测试1: 列出日期文件夹")
    print("-" * 60)
    date_folders = reader.find_date_folders()
    print(f"找到 {len(date_folders)} 个日期文件夹")
    print(f"最新的10个:")
    for date in date_folders[:10]:
        print(f"  📁 {date}")
    
    # 测试2: 查找今天的文件
    print("\n📋 测试2: 查找今天的最新TXT文件")
    print("-" * 60)
    today = datetime.now().strftime('%Y-%m-%d')
    latest_file = reader.get_latest_txt_file(today)
    
    if latest_file:
        print("\n✅ 成功找到文件!")
        print(f"   文件名: {latest_file['filename']}")
        print(f"   文件ID: {latest_file['file_id']}")
        print(f"   下载链接: {latest_file['download_url']}")
    else:
        print(f"\n⚠️  今天({today})还没有数据")
        print("   尝试获取最新可用日期的文件...")
        
        if date_folders:
            latest_date = date_folders[0]
            latest_file = reader.get_latest_txt_file(latest_date)
            
            if latest_file:
                print(f"\n✅ 找到最新文件 ({latest_date}):")
                print(f"   文件名: {latest_file['filename']}")
                print(f"   文件ID: {latest_file['file_id']}")
                print(f"   下载链接: {latest_file['download_url']}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)


if __name__ == '__main__':
    test_reader()
