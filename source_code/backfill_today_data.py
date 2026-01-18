#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据补全工具
按时间顺序抓取并补全今天所有的Google Drive TXT文件
"""

import os
import sys
import sqlite3
import requests
import re
from datetime import datetime
import pytz
import time

# 配置
PARENT_FOLDER_ID = '1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DB_PATH = '/home/user/webapp/crypto_data.db'

def get_all_txt_files_today():
    """获取今天所有的TXT文件列表"""
    try:
        current_time = datetime.now(BEIJING_TZ)
        folder_name = current_time.strftime('%Y-%m-%d')
        
        print("=" * 80)
        print(f"📅 目标日期: {folder_name}")
        print("=" * 80)
        
        # 获取父文件夹
        parent_url = f'https://drive.google.com/drive/folders/{PARENT_FOLDER_ID}'
        print(f"🔍 正在访问Google Drive...")
        response = requests.get(parent_url, timeout=15)
        
        # 查找今天的文件夹ID
        pattern = r'"' + re.escape(folder_name) + r'".*?"id":"([^"]+)"'
        match = re.search(pattern, response.text)
        
        if not match:
            print(f"❌ 未找到文件夹: {folder_name}")
            return []
        
        folder_id = match.group(1)
        print(f"✓ 找到文件夹ID: {folder_id}")
        
        # 获取文件夹内容
        folder_url = f'https://drive.google.com/drive/folders/{folder_id}'
        folder_response = requests.get(folder_url, timeout=15)
        
        # 查找所有TXT文件
        txt_pattern = r'"(' + re.escape(folder_name) + r'_\d{4})\.txt".*?"id":"([^"]+)"'
        txt_files = re.findall(txt_pattern, folder_response.text)
        
        if not txt_files:
            print("❌ 未找到TXT文件")
            return []
        
        # 按时间排序（从早到晚）
        sorted_files = sorted(txt_files, key=lambda x: x[0])
        
        print(f"\n✓ 找到 {len(sorted_files)} 个TXT文件:")
        
        file_list = []
        for filename, file_id in sorted_files:
            download_url = f'https://drive.google.com/uc?id={file_id}&export=download'
            
            # 从文件名提取时间 (例: 2025-12-09_1246)
            time_part = filename.split('_')[1]
            time_str = f"{time_part[:2]}:{time_part[2:]}"
            
            file_info = {
                'filename': f'{filename}.txt',
                'file_id': file_id,
                'download_url': download_url,
                'time': time_str,
                'sort_key': filename
            }
            file_list.append(file_info)
            print(f"  {len(file_list)}. {filename}.txt (时间: {time_str})")
        
        return file_list
        
    except Exception as e:
        print(f"❌ 获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_if_imported(filename):
    """检查文件是否已导入"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 从文件名提取时间
        date_part, time_part = filename.replace('.txt', '').split('_')
        snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
        
        cursor.execute("""
            SELECT COUNT(*) FROM crypto_snapshots
            WHERE snapshot_time = ?
        """, (snapshot_time,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception as e:
        print(f"❌ 检查导入状态失败: {e}")
        return False

def download_and_import(file_info, index, total):
    """下载并导入TXT文件"""
    try:
        filename = file_info['filename']
        download_url = file_info['download_url']
        time_str = file_info['time']
        
        print(f"\n[{index}/{total}] 处理: {filename} (时间: {time_str})")
        
        # 下载文件
        print(f"  ⬇️  正在下载...")
        response = requests.get(download_url, timeout=30)
        response.raise_for_status()
        
        # 保存到临时文件
        temp_file = f'/tmp/{filename}'
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        print(f"  ✓ 下载完成 ({len(response.content)} 字节)")
        
        # 转换编码为UTF-8
        temp_utf8_file = f'/tmp/{filename.replace(".txt", "_utf8.txt")}'
        result = os.system(f'iconv -f GBK -t UTF-8 "{temp_file}" > "{temp_utf8_file}" 2>/dev/null')
        
        if result != 0:
            print(f"  ⚠️  编码转换警告，尝试直接导入...")
            temp_utf8_file = temp_file
        
        # 使用manual_txt_import.py导入
        print(f"  📥 正在导入数据库...")
        import_cmd = f'cd /home/user/webapp && python3 manual_txt_import.py "{temp_utf8_file}" 2>&1'
        import_result = os.popen(import_cmd).read()
        
        # 检查导入结果
        if '成功' in import_result or 'success' in import_result.lower():
            print(f"  ✓ 导入成功!")
            # 清理临时文件
            try:
                os.remove(temp_file)
                if temp_utf8_file != temp_file:
                    os.remove(temp_utf8_file)
            except:
                pass
            return True
        else:
            print(f"  ❌ 导入失败!")
            print(f"  错误信息: {import_result[:200]}")
            return False
            
    except Exception as e:
        print(f"  ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_existing_snapshots_today():
    """获取今天已有的快照记录"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = datetime.now(BEIJING_TZ)
        today = current_time.strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT snapshot_time, rush_up, rush_down, count, status
            FROM crypto_snapshots
            WHERE date(snapshot_time) = ?
            ORDER BY snapshot_time ASC
        """, (today,))
        
        records = cursor.fetchall()
        conn.close()
        
        return records
        
    except Exception as e:
        print(f"❌ 查询现有记录失败: {e}")
        return []

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🔧 历史数据补全工具")
    print("=" * 80)
    
    current_time = datetime.now(BEIJING_TZ)
    print(f"⏰ 当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    
    # 查看当前数据库记录
    print("\n📊 当前数据库记录:")
    print("-" * 80)
    existing_records = get_existing_snapshots_today()
    if existing_records:
        for i, record in enumerate(existing_records, 1):
            print(f"  {i}. {record[0]} - 急涨:{record[1]}, 急跌:{record[2]}, 计次:{record[3]}, {record[4]}")
        print(f"\n✓ 共 {len(existing_records)} 条记录")
    else:
        print("  ⚠️  今天还没有数据记录")
    
    # 获取Google Drive中的所有文件
    print("\n" + "=" * 80)
    all_files = get_all_txt_files_today()
    
    if not all_files:
        print("\n❌ 无法获取文件列表，请检查网络连接")
        return
    
    # 分类：已导入 vs 需要补全
    print("\n" + "=" * 80)
    print("📋 文件分类:")
    print("-" * 80)
    
    imported_files = []
    missing_files = []
    
    for file_info in all_files:
        filename = file_info['filename']
        if check_if_imported(filename):
            imported_files.append(file_info)
        else:
            missing_files.append(file_info)
    
    print(f"✓ 已导入: {len(imported_files)} 个文件")
    if imported_files:
        for f in imported_files[:5]:
            print(f"    - {f['filename']} (时间: {f['time']})")
        if len(imported_files) > 5:
            print(f"    ... 还有 {len(imported_files) - 5} 个文件")
    
    print(f"\n⚠️  缺失: {len(missing_files)} 个文件需要补全")
    if missing_files:
        for f in missing_files:
            print(f"    - {f['filename']} (时间: {f['time']})")
    
    # 如果没有需要补全的文件
    if not missing_files:
        print("\n" + "=" * 80)
        print("✅ 所有数据已完整，无需补全!")
        print("=" * 80)
        return
    
    # 确认是否执行补全
    print("\n" + "=" * 80)
    print(f"📥 准备补全 {len(missing_files)} 个文件")
    print("=" * 80)
    
    response = input("\n是否开始补全? (输入 'yes' 确认，其他键取消): ")
    if response.lower() not in ['yes', 'y', '是']:
        print("\n❌ 已取消补全操作")
        return
    
    # 开始补全
    print("\n" + "=" * 80)
    print("🚀 开始数据补全...")
    print("=" * 80)
    
    success_count = 0
    fail_count = 0
    
    for i, file_info in enumerate(missing_files, 1):
        result = download_and_import(file_info, i, len(missing_files))
        
        if result:
            success_count += 1
        else:
            fail_count += 1
        
        # 避免请求过快
        if i < len(missing_files):
            time.sleep(2)
    
    # 完成总结
    print("\n" + "=" * 80)
    print("📊 补全完成!")
    print("=" * 80)
    print(f"✓ 成功: {success_count} 个文件")
    print(f"✗ 失败: {fail_count} 个文件")
    print(f"📈 总共: {len(missing_files)} 个文件")
    
    # 显示更新后的记录
    print("\n" + "=" * 80)
    print("📊 更新后的数据库记录:")
    print("-" * 80)
    updated_records = get_existing_snapshots_today()
    if updated_records:
        for i, record in enumerate(updated_records, 1):
            print(f"  {i}. {record[0]} - 急涨:{record[1]}, 急跌:{record[2]}, 计次:{record[3]}, {record[4]}")
        print(f"\n✓ 共 {len(updated_records)} 条记录 (增加了 {len(updated_records) - len(existing_records)} 条)")
    
    print("\n" + "=" * 80)
    print("✅ 数据补全完成!")
    print("=" * 80)
    print(f"\n💡 提示: 访问查询页面查看完整数据")
    print(f"🔗 https://5000-iypypqmz2wvn9dmtq7ewn-583b4d74.sandbox.novita.ai/query")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
