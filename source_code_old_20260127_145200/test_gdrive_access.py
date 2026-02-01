#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Google Drive文件夹的不同访问方式
帮助诊断为什么找不到2026-01-18文件夹
"""

import requests
import re
from datetime import datetime
import pytz

# 配置
HOME_DATA_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def test_direct_access():
    """测试1: 直接访问文件夹"""
    print("\n" + "=" * 80)
    print("测试1: 直接访问首页数据文件夹")
    print("=" * 80)
    
    url = f'https://drive.google.com/drive/folders/{HOME_DATA_FOLDER_ID}'
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=15)
        print(f"状态码: {response.status_code}")
        print(f"响应大小: {len(response.text)} 字符")
        
        # 方法1: 查找日期文件夹
        date_pattern = r'"(202[0-9]-[01][0-9]-[0-3][0-9])"'
        dates = re.findall(date_pattern, response.text)
        dates_unique = list(set(dates))
        dates_unique.sort(reverse=True)
        
        if dates_unique:
            print(f"\n✅ 找到 {len(dates_unique)} 个日期:")
            for date in dates_unique[:10]:
                print(f"   {date}")
        else:
            print("\n❌ 未找到日期格式的文件夹")
        
        # 方法2: 查找TXT文件（可能直接在根目录）
        txt_pattern = r'"(202[0-9]-[01][0-9]-[0-3][0-9]_[0-2][0-9][0-5][0-9]\.txt)"'
        txt_files = re.findall(txt_pattern, response.text)
        txt_files_unique = list(set(txt_files))
        txt_files_unique.sort(reverse=True)
        
        if txt_files_unique:
            print(f"\n✅ 找到 {len(txt_files_unique)} 个TXT文件:")
            for txt_file in txt_files_unique[:10]:
                print(f"   {txt_file}")
        else:
            print("\n❌ 未找到日期时间格式的TXT文件")
        
        # 方法3: 查找任何TXT文件
        any_txt_pattern = r'"([^"]+\.txt)"'
        any_txt_files = re.findall(any_txt_pattern, response.text)
        any_txt_files_unique = list(set(any_txt_files))
        
        if any_txt_files_unique:
            print(f"\n📄 找到 {len(any_txt_files_unique)} 个TXT文件（任意名称）:")
            for txt_file in sorted(any_txt_files_unique)[:20]:
                print(f"   {txt_file}")
        
        # 方法4: 查找任何文件夹
        folder_pattern = r'"([^"]+)"[^}]*?"application/vnd\.google-apps\.folder"'
        folders = re.findall(folder_pattern, response.text[:100000])  # 只搜索前100K字符
        
        if folders:
            print(f"\n📁 可能的文件夹（前20个）:")
            for folder in list(set(folders))[:20]:
                if len(folder) < 50:  # 过滤太长的
                    print(f"   {folder}")
        
    except Exception as e:
        print(f"\n❌ 访问失败: {e}")

def test_with_today_folder():
    """测试2: 尝试构造今天的文件夹URL"""
    print("\n" + "=" * 80)
    print("测试2: 尝试今天的日期文件夹")
    print("=" * 80)
    
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    print(f"今天日期: {today}")
    
    # 尝试几个可能的文件夹ID（需要你提供实际的文件夹ID）
    print("\n如果你知道2026-01-18文件夹的实际Google Drive链接，")
    print("请提供给我，格式如：")
    print("https://drive.google.com/drive/folders/FOLDER_ID_HERE")

def test_alternative_patterns():
    """测试3: 尝试其他可能的文件命名模式"""
    print("\n" + "=" * 80)
    print("测试3: 搜索其他可能的文件模式")
    print("=" * 80)
    
    url = f'https://drive.google.com/drive/folders/{HOME_DATA_FOLDER_ID}'
    
    try:
        response = requests.get(url, timeout=15)
        
        # 尝试不同的文件名模式
        patterns = [
            (r'"(20[0-9]{2}-[0-1][0-9]-[0-3][0-9]\.txt)"', "日期.txt"),
            (r'"(20[0-9]{6}_[0-9]{4}\.txt)"', "YYYYMMDD_HHMM.txt"),
            (r'"(20[0-9]{6}\.txt)"', "YYYYMMDD.txt"),
            (r'"([A-Z]{2,5}\.txt)"', "币种.txt (如BTC.txt)"),
        ]
        
        for pattern, desc in patterns:
            matches = re.findall(pattern, response.text)
            if matches:
                print(f"\n✅ 找到 {len(set(matches))} 个 {desc} 文件:")
                for match in sorted(set(matches))[:10]:
                    print(f"   {match}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    print("=" * 80)
    print("🔍 Google Drive 文件夹结构诊断工具")
    print("=" * 80)
    print(f"\n文件夹ID: {HOME_DATA_FOLDER_ID}")
    print(f"链接: https://drive.google.com/drive/folders/{HOME_DATA_FOLDER_ID}")
    
    # 运行所有测试
    test_direct_access()
    test_with_today_folder()
    test_alternative_patterns()
    
    print("\n" + "=" * 80)
    print("💡 建议")
    print("=" * 80)
    print("\n如果上面的测试都找不到文件，可能的原因：")
    print("1. 文件夹需要登录才能访问（权限问题）")
    print("2. Google Drive使用JavaScript动态加载内容")
    print("3. 文件夹结构与预期不同")
    print("\n解决方案：")
    print("1. 将'首页数据'文件夹设为完全公开（任何人都可查看）")
    print("2. 或者提供'2026-01-18'子文件夹的直接链接")
    print("3. 或者使用Google Drive API认证")
    print("4. 或者使用rclone工具")

if __name__ == '__main__':
    main()
