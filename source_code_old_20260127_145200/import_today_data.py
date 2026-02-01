#!/usr/bin/env python3
"""
导入当天所有txt文件到数据库
按照时间从早到晚顺序导入
"""
import os
import re
import sqlite3
from datetime import datetime
import subprocess

def get_today_txt_files():
    """获取当天的所有txt文件"""
    today = datetime.now().strftime('%Y-%m-%d')
    temp_dir = '/home/user/webapp/temp_download'
    
    if not os.path.exists(temp_dir):
        print(f"❌ 目录不存在: {temp_dir}")
        return []
    
    # 获取所有txt文件
    files = []
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt')
    
    for filename in os.listdir(temp_dir):
        match = pattern.match(filename)
        if match:
            file_date = match.group(1)
            file_time = match.group(2)
            
            # 只处理当天的文件
            if file_date == today:
                filepath = os.path.join(temp_dir, filename)
                files.append({
                    'path': filepath,
                    'filename': filename,
                    'date': file_date,
                    'time': file_time
                })
    
    # 按时间排序（从早到晚）
    files.sort(key=lambda x: x['time'])
    
    return files

def check_file_imported(filename):
    """检查文件是否已经导入"""
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM crypto_snapshots WHERE filename = ?",
            (filename,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        print(f"检查文件状态失败: {e}")
        return False

def import_file(filepath, filename):
    """导入单个文件"""
    try:
        # 调用 collect_and_store.py 的导入功能
        # 这里我们直接读取文件并处理
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用 parse_and_store_data 函数（需要从 collect_and_store.py 导入）
        # 为了简单，这里调用 subprocess
        result = subprocess.run(
            ['python3', '/home/user/webapp/collect_and_store.py', filepath],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            return True, "导入成功"
        else:
            return False, result.stderr[:100] if result.stderr else "导入失败"
    
    except Exception as e:
        return False, str(e)

def main():
    """主函数"""
    print("=" * 70)
    print(" " * 20 + "导入当天所有数据文件")
    print("=" * 70)
    
    # 获取当天的txt文件
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n📅 目标日期: {today}")
    
    files = get_today_txt_files()
    
    if not files:
        print(f"❌ 未找到当天的txt文件")
        return
    
    print(f"✅ 找到 {len(files)} 个文件")
    print("\n📂 文件列表（按时间从早到晚）:")
    for i, file_info in enumerate(files, 1):
        print(f"   {i}. {file_info['filename']} ({file_info['time'][:2]}:{file_info['time'][2:]})")
    
    # 检查哪些文件已导入
    print(f"\n🔍 检查导入状态...")
    to_import = []
    already_imported = []
    
    for file_info in files:
        if check_file_imported(file_info['filename']):
            already_imported.append(file_info)
        else:
            to_import.append(file_info)
    
    if already_imported:
        print(f"\n✓ 已导入: {len(already_imported)} 个文件")
        for file_info in already_imported:
            print(f"   ✓ {file_info['filename']}")
    
    if not to_import:
        print(f"\n✅ 所有文件都已导入，无需重复导入")
        return
    
    print(f"\n📥 需要导入: {len(to_import)} 个文件")
    
    # 确认是否继续
    print(f"\n是否继续导入？ (y/n): ", end='', flush=True)
    response = input().strip().lower()
    
    if response != 'y':
        print("❌ 已取消导入")
        return
    
    # 开始导入
    print(f"\n{'='*70}")
    print(" " * 25 + "开始导入数据")
    print(f"{'='*70}\n")
    
    success_count = 0
    failed_count = 0
    
    for i, file_info in enumerate(to_import, 1):
        filename = file_info['filename']
        filepath = file_info['path']
        
        print(f"[{i}/{len(to_import)}] 导入: {filename} ... ", end='', flush=True)
        
        success, message = import_file(filepath, filename)
        
        if success:
            print(f"✅ 成功")
            success_count += 1
        else:
            print(f"❌ 失败: {message}")
            failed_count += 1
    
    # 总结
    print(f"\n{'='*70}")
    print(" " * 25 + "导入完成")
    print(f"{'='*70}")
    print(f"\n📊 导入统计:")
    print(f"   ✅ 成功: {success_count} 个")
    print(f"   ❌ 失败: {failed_count} 个")
    print(f"   📁 总计: {len(to_import)} 个")
    
    if success_count > 0:
        print(f"\n✅ 数据已导入数据库，可以在Web界面查看")
        print(f"   时间轴顺序: 时间晚的在上，时间早的在下")

if __name__ == '__main__':
    main()
