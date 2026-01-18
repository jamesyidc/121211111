#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动导入TXT文件到数据库
用于Google Drive自动更新不可用时的临时方案
"""

import os
import sys
import sqlite3
import re
from datetime import datetime
import pytz

# 配置
DB_PATH = '/home/user/webapp/databases/crypto_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def parse_txt_filename(filename):
    """解析TXT文件名，提取日期和时间"""
    # 格式: 2026-01-18_1630.txt
    match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
    if not match:
        return None
    
    date_part = match.group(1)
    time_part = match.group(2)
    
    # 转换为完整时间
    snapshot_time = f"{date_part} {time_part[:2]}:{time_part[2:]}:00"
    return snapshot_time

def check_if_imported(snapshot_time):
    """检查是否已导入"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM crypto_snapshots 
            WHERE snapshot_time = ?
        """, (snapshot_time,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return False

def import_txt_file(file_path):
    """导入单个TXT文件"""
    try:
        filename = os.path.basename(file_path)
        print(f"\n📄 处理文件: {filename}")
        
        # 解析文件名
        snapshot_time = parse_txt_filename(filename)
        if not snapshot_time:
            print(f"   ❌ 文件名格式错误，应为: YYYY-MM-DD_HHMM.txt")
            return False
        
        print(f"   时间: {snapshot_time}")
        
        # 检查是否已导入
        if check_if_imported(snapshot_time):
            print(f"   ⚠️ 已存在，跳过")
            return False
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print(f"   ❌ 文件内容为空")
            return False
        
        print(f"   内容大小: {len(content)} 字节")
        
        # 插入数据库
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO crypto_snapshots (snapshot_time, data_content, source)
            VALUES (?, ?, 'manual_import')
        """, (snapshot_time, content))
        
        conn.commit()
        conn.close()
        
        print(f"   ✅ 导入成功")
        return True
        
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def import_directory(directory):
    """批量导入目录中的所有TXT文件"""
    print("=" * 80)
    print("📁 批量导入TXT文件")
    print("=" * 80)
    print(f"\n目录: {directory}")
    
    if not os.path.exists(directory):
        print(f"❌ 目录不存在")
        return
    
    # 查找所有TXT文件
    txt_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt') and re.match(r'\d{4}-\d{2}-\d{2}_\d{4}\.txt', filename):
            txt_files.append(filename)
    
    txt_files.sort()
    
    print(f"\n找到 {len(txt_files)} 个TXT文件")
    
    if not txt_files:
        print("没有找到符合格式的TXT文件")
        return
    
    # 逐个导入
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for filename in txt_files:
        file_path = os.path.join(directory, filename)
        result = import_txt_file(file_path)
        
        if result:
            success_count += 1
        elif check_if_imported(parse_txt_filename(filename)):
            skip_count += 1
        else:
            fail_count += 1
    
    # 统计
    print("\n" + "=" * 80)
    print("📊 导入统计")
    print("=" * 80)
    print(f"✅ 成功导入: {success_count} 个")
    print(f"⚠️ 已存在跳过: {skip_count} 个")
    print(f"❌ 导入失败: {fail_count} 个")
    print(f"📁 总计文件: {len(txt_files)} 个")

def main():
    """主函数"""
    print("=" * 80)
    print("🔧 手动导入TXT文件工具")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  单个文件: python3 manual_import_txt.py /path/to/2026-01-18_1630.txt")
        print("  批量导入: python3 manual_import_txt.py /path/to/directory/")
        print("\n示例:")
        print("  python3 manual_import_txt.py /home/user/webapp/temp/2026-01-18_1630.txt")
        print("  python3 manual_import_txt.py /home/user/webapp/temp/")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if os.path.isfile(path):
        # 单个文件
        import_txt_file(path)
    elif os.path.isdir(path):
        # 目录
        import_directory(path)
    else:
        print(f"❌ 路径不存在: {path}")
        sys.exit(1)

if __name__ == '__main__':
    main()
