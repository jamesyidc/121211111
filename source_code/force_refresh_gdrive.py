#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
强制刷新Google Drive页面获取最新文件列表
使用多种方法绕过缓存
"""

import requests
import re
import json
from datetime import datetime
import pytz
import time
import random

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(pytz.timezone('Asia/Shanghai'))

def fetch_gdrive_with_force_refresh(folder_id, attempt=1):
    """
    使用多种方法强制刷新Google Drive页面
    """
    beijing_time = get_beijing_time()
    print(f"\n{'='*60}")
    print(f"尝试 #{attempt} - 北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 方法1: 使用不同的随机参数
    timestamp = int(time.time() * 1000)
    random_param = random.randint(1000, 9999)
    
    url = f"https://drive.google.com/drive/folders/{folder_id}?usp=sharing&nocache={timestamp}&rand={random_param}"
    
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/{537 + attempt}.36 (KHTML, like Gecko) Chrome/{120 + attempt}.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
    }
    
    try:
        print(f"请求URL: {url}")
        print(f"User-Agent: {headers['User-Agent'][:50]}...")
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=15)
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应大小: {len(response.text)} bytes")
        
        if response.status_code == 200:
            content = response.text
            
            # 检查响应头中的缓存信息
            cache_control = response.headers.get('Cache-Control', 'N/A')
            etag = response.headers.get('ETag', 'N/A')
            print(f"Cache-Control: {cache_control}")
            print(f"ETag: {etag[:50] if len(etag) > 50 else etag}")
            
            return content
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return None

def extract_files_from_content(content, folder_id):
    """
    从Google Drive页面内容中提取文件列表
    """
    if not content:
        print("❌ 页面内容为空")
        return []
    
    print(f"\n开始解析页面内容...")
    print(f"页面大小: {len(content)} bytes")
    
    # 查找所有可能的文件名模式
    patterns = [
        r'"(2025-\d{2}-\d{2}_\d{4}\.txt)"',  # 基本文件名
        r'\["(2025-\d{2}-\d{2}_\d{4}\.txt)"',  # 数组中的文件名
        r'name\\":\\"(2025-\d{2}-\d{2}_\d{4}\.txt)\\"',  # JSON中的文件名
    ]
    
    all_files = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"模式 '{pattern}' 找到 {len(matches)} 个匹配")
            all_files.update(matches)
    
    if not all_files:
        print("❌ 未找到任何文件名")
        # 输出一些页面内容用于调试
        print("\n页面内容示例（前1000字符）:")
        print(content[:1000])
        return []
    
    print(f"\n✅ 总共找到 {len(all_files)} 个唯一文件")
    
    # 解析文件时间并排序
    file_list = []
    for filename in all_files:
        try:
            # 从文件名中提取时间: 2025-12-03_0821.txt
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
            if match:
                date_str = match.group(1)
                time_str = match.group(2)
                # 转换为datetime
                file_datetime = datetime.strptime(f"{date_str} {time_str[:2]}:{time_str[2:]}", 
                                                 "%Y-%m-%d %H:%M")
                file_list.append({
                    'filename': filename,
                    'datetime': file_datetime,
                    'time_str': f"{time_str[:2]}:{time_str[2:]}"
                })
        except Exception as e:
            print(f"⚠️ 解析文件名失败 {filename}: {str(e)}")
    
    # 按时间排序
    file_list.sort(key=lambda x: x['datetime'], reverse=True)
    
    return file_list

def main():
    """主函数"""
    folder_id = "1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh"
    beijing_time = get_beijing_time()
    
    print("="*60)
    print("Google Drive 强制刷新测试")
    print("="*60)
    print(f"当前北京时间: {beijing_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标文件夹ID: {folder_id}")
    
    # 尝试3次，使用不同的参数
    max_attempts = 3
    latest_file = None
    
    for attempt in range(1, max_attempts + 1):
        print(f"\n{'='*60}")
        print(f"第 {attempt}/{max_attempts} 次尝试")
        print(f"{'='*60}")
        
        # 每次尝试之间等待一小段时间
        if attempt > 1:
            wait_time = 2
            print(f"等待 {wait_time} 秒...")
            time.sleep(wait_time)
        
        # 获取页面内容
        content = fetch_gdrive_with_force_refresh(folder_id, attempt)
        
        if content:
            # 解析文件列表
            file_list = extract_files_from_content(content, folder_id)
            
            if file_list:
                print(f"\n找到 {len(file_list)} 个文件")
                
                # 显示最新的10个文件
                print("\n最新的文件（最多10个）:")
                for i, file_info in enumerate(file_list[:10], 1):
                    print(f"  {i}. {file_info['filename']} (时间: {file_info['time_str']})")
                
                # 获取最新文件
                current_latest = file_list[0]
                
                # 计算时间差
                file_time = current_latest['datetime']
                time_diff = (beijing_time.replace(tzinfo=None) - file_time).total_seconds() / 60
                
                print(f"\n当前最新文件:")
                print(f"  文件名: {current_latest['filename']}")
                print(f"  文件时间: {current_latest['time_str']}")
                print(f"  时间差: {time_diff:.1f} 分钟")
                
                # 如果找到更新的文件，或者这是第一次
                if latest_file is None or current_latest['datetime'] > latest_file['datetime']:
                    latest_file = current_latest
                    print(f"  ✅ 这是目前找到的最新文件")
                    
                    # 如果时间差小于15分钟，认为是新鲜数据
                    if time_diff < 15:
                        print(f"  ✅ 数据较新（<15分钟），停止尝试")
                        break
                    else:
                        print(f"  ⚠️ 数据较旧（{time_diff:.1f}分钟），继续尝试...")
                else:
                    print(f"  ℹ️ 与之前相同，继续尝试...")
    
    # 最终结果
    print(f"\n{'='*60}")
    print("最终结果")
    print(f"{'='*60}")
    
    if latest_file:
        file_time = latest_file['datetime']
        time_diff = (beijing_time.replace(tzinfo=None) - file_time).total_seconds() / 60
        
        print(f"最新文件: {latest_file['filename']}")
        print(f"文件时间: {latest_file['time_str']}")
        print(f"当前时间: {beijing_time.strftime('%H:%M')}")
        print(f"时间差: {time_diff:.1f} 分钟")
        
        if time_diff < 15:
            print(f"✅ 状态: 数据较新")
        else:
            print(f"⚠️ 状态: 数据较旧，可能存在缓存问题")
    else:
        print("❌ 未找到任何文件")

if __name__ == "__main__":
    main()
