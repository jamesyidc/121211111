#!/usr/bin/env python3
"""
批量导入所有历史txt文件到数据库
"""
import os
import re
import sqlite3
import subprocess
from datetime import datetime

def find_all_txt_files():
    """查找所有历史txt文件"""
    txt_files = []
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt')
    
    # 搜索temp_download目录
    temp_dir = '/home/user/webapp/temp_download'
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            match = pattern.match(filename)
            if match:
                filepath = os.path.join(temp_dir, filename)
                txt_files.append({
                    'path': filepath,
                    'filename': filename,
                    'date': match.group(1),
                    'time': match.group(2)
                })
    
    # 搜索2025-12-06目录
    date_dir = '/home/user/webapp/2025-12-06'
    if os.path.exists(date_dir):
        for filename in os.listdir(date_dir):
            match = pattern.match(filename)
            if match:
                filepath = os.path.join(date_dir, filename)
                txt_files.append({
                    'path': filepath,
                    'filename': filename,
                    'date': match.group(1),
                    'time': match.group(2)
                })
    
    # 按日期和时间排序（从早到晚）
    txt_files.sort(key=lambda x: (x['date'], x['time']))
    
    # 去重（相同文件名只保留一个）
    seen_filenames = set()
    unique_files = []
    for f in txt_files:
        if f['filename'] not in seen_filenames:
            seen_filenames.add(f['filename'])
            unique_files.append(f)
    
    return unique_files

def check_file_imported(filename):
    """检查文件是否已导入"""
    try:
        conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM crypto_snapshots WHERE filename = ?', (filename,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except:
        return False

def import_txt_file(filepath, filename):
    """导入单个txt文件"""
    try:
        # 使用原有的collect_and_store.py脚本导入
        result = subprocess.run(
            ['python3', '/home/user/webapp/collect_and_store.py', filepath],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "成功"
        else:
            return False, result.stderr[:100]
    except Exception as e:
        return False, str(e)[:100]

def batch_import():
    """批量导入所有txt文件"""
    print("=" * 80)
    print("📦 批量导入历史txt文件")
    print("=" * 80)
    
    # 查找所有txt文件
    files = find_all_txt_files()
    
    if not files:
        print("❌ 未找到任何txt文件")
        return
    
    print(f"\n✅ 找到 {len(files)} 个txt文件")
    print(f"   时间范围: {files[0]['filename']} 到 {files[-1]['filename']}")
    
    # 统计
    total = len(files)
    imported = 0
    skipped = 0
    failed = 0
    
    print(f"\n开始导入...")
    print("-" * 80)
    
    for i, file_info in enumerate(files, 1):
        filename = file_info['filename']
        filepath = file_info['path']
        
        # 检查是否已导入
        if check_file_imported(filename):
            print(f"[{i:3d}/{total}] ⏭️  已存在: {filename}")
            skipped += 1
            continue
        
        # 导入文件
        success, message = import_txt_file(filepath, filename)
        
        if success:
            print(f"[{i:3d}/{total}] ✅ 导入成功: {filename}")
            imported += 1
        else:
            print(f"[{i:3d}/{total}] ❌ 导入失败: {filename} - {message}")
            failed += 1
    
    print("-" * 80)
    print(f"\n📊 导入统计:")
    print(f"   总文件数: {total}")
    print(f"   ✅ 成功导入: {imported}")
    print(f"   ⏭️  已存在跳过: {skipped}")
    print(f"   ❌ 导入失败: {failed}")
    
    # 查询数据库最终状态
    try:
        conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM crypto_snapshots')
        total_records = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(snapshot_time), MAX(snapshot_time) FROM crypto_snapshots')
        time_range = cursor.fetchone()
        
        conn.close()
        
        print(f"\n📈 数据库状态:")
        print(f"   总快照数: {total_records}")
        if time_range[0] and time_range[1]:
            print(f"   时间范围: {time_range[0]} 到 {time_range[1]}")
            
            # 计算时间跨度
            start = datetime.strptime(time_range[0], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(time_range[1], '%Y-%m-%d %H:%M:%S')
            duration = end - start
            hours = duration.total_seconds() / 3600
            print(f"   时间跨度: {hours:.1f} 小时")
    except Exception as e:
        print(f"   ⚠️  无法查询数据库状态: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 批量导入完成！")
    print("=" * 80)
    print("\n🌐 访问Web界面查看完整24小时趋势图:")
    print("   https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")

if __name__ == '__main__':
    batch_import()
