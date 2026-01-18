#!/usr/bin/env python3
"""
直接解析txt文件并导入数据库
"""
import os
import re
import sqlite3
from datetime import datetime

def parse_txt_file(filepath):
    """解析txt文件，提取统计数据"""
    try:
        with open(filepath, 'r', encoding='gb18030', errors='ignore') as f:
            content = f.read()
        
        # 提取文件名中的时间
        filename = os.path.basename(filepath)
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
        if not match:
            return None
        
        date_str = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        snapshot_time = f"{date_str} {hour}:{minute}:00"
        
        # 提取统计数据
        data = {
            'snapshot_time': snapshot_time,
            'snapshot_date': date_str,
            'filename': filename
        }
        
        # 急涨/急跌数量
        rush_up_match = re.search(r'急涨.*?=.*?(\d+)', content)
        rush_down_match = re.search(r'急跌.*?=.*?(\d+)', content)
        
        data['rush_up'] = int(rush_up_match.group(1)) if rush_up_match else 0
        data['rush_down'] = int(rush_down_match.group(1)) if rush_down_match else 0
        data['diff'] = data['rush_up'] - data['rush_down']
        
        # 计次
        count_match = re.search(r'计次.*?=.*?(\d+)', content)
        data['count'] = int(count_match.group(1)) if count_match else 0
        
        # 比值
        ratio_match = re.search(r'比值.*?=.*?([\d.]+)', content)
        data['ratio'] = float(ratio_match.group(1)) if ratio_match else 0.0
        
        # 状态
        status_match = re.search(r'状态.*?=.*?([\u4e00-\u9fa5]+)', content)
        data['status'] = status_match.group(1) if status_match else '未知'
        
        # 绿色数量
        green_match = re.search(r'绿色.*?=.*?(\d+)', content)
        data['green_count'] = int(green_match.group(1)) if green_match else 0
        
        # 百分比
        percentage_match = re.search(r'百分比.*?=.*?(\d+)%', content)
        data['percentage'] = f"{percentage_match.group(1)}%" if percentage_match else "0%"
        
        return data
        
    except Exception as e:
        print(f"  ⚠️  解析失败: {e}")
        return None

def insert_snapshot(data):
    """插入快照数据到数据库"""
    try:
        conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute('SELECT id FROM crypto_snapshots WHERE filename = ?', (data['filename'],))
        if cursor.fetchone():
            conn.close()
            return False, "已存在"
        
        # 插入快照
        cursor.execute("""
            INSERT INTO crypto_snapshots (
                snapshot_time, snapshot_date, 
                rush_up, rush_down, diff, count, 
                ratio, status, green_count, percentage, filename
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['snapshot_time'], data['snapshot_date'],
            data['rush_up'], data['rush_down'], data['diff'], data['count'],
            data['ratio'], data['status'], data['green_count'], 
            data['percentage'], data['filename']
        ))
        
        conn.commit()
        conn.close()
        return True, "成功"
        
    except Exception as e:
        return False, str(e)[:100]

def batch_import():
    """批量导入所有txt文件"""
    print("=" * 80)
    print("📦 批量导入历史txt文件 (直接解析模式)")
    print("=" * 80)
    
    # 查找所有txt文件
    txt_files = []
    pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt')
    
    for directory in ['/home/user/webapp/temp_download', '/home/user/webapp/2025-12-06']:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if pattern.match(filename):
                    filepath = os.path.join(directory, filename)
                    txt_files.append(filepath)
    
    # 去重
    txt_files = list(set(txt_files))
    txt_files.sort()
    
    if not txt_files:
        print("❌ 未找到任何txt文件")
        return
    
    print(f"\n✅ 找到 {len(txt_files)} 个txt文件")
    
    # 统计
    total = len(txt_files)
    imported = 0
    skipped = 0
    failed = 0
    
    print(f"\n开始导入...")
    print("-" * 80)
    
    for i, filepath in enumerate(txt_files, 1):
        filename = os.path.basename(filepath)
        
        # 解析文件
        data = parse_txt_file(filepath)
        if not data:
            print(f"[{i:3d}/{total}] ❌ 解析失败: {filename}")
            failed += 1
            continue
        
        # 插入数据库
        success, message = insert_snapshot(data)
        
        if success:
            print(f"[{i:3d}/{total}] ✅ {filename} - 急涨:{data['rush_up']:2d} 急跌:{data['rush_down']:2d} 计次:{data['count']:2d}")
            imported += 1
        elif message == "已存在":
            print(f"[{i:3d}/{total}] ⏭️  {filename} - 已存在")
            skipped += 1
        else:
            print(f"[{i:3d}/{total}] ❌ {filename} - {message}")
            failed += 1
    
    print("-" * 80)
    print(f"\n📊 导入统计:")
    print(f"   总文件数: {total}")
    print(f"   ✅ 成功导入: {imported}")
    print(f"   ⏭️  已存在跳过: {skipped}")
    print(f"   ❌ 失败: {failed}")
    
    # 查询数据库最终状态
    try:
        conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM crypto_snapshots')
        total_records = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(snapshot_time), MAX(snapshot_time) FROM crypto_snapshots')
        time_range = cursor.fetchone()
        
        conn.close()
        
        print(f"\n📈 数据库最终状态:")
        print(f"   总快照数: {total_records}")
        if time_range[0] and time_range[1]:
            print(f"   时间范围: {time_range[0]} 到 {time_range[1]}")
            
            start = datetime.strptime(time_range[0], '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime(time_range[1], '%Y-%m-%d %H:%M:%S')
            duration = end - start
            hours = duration.total_seconds() / 3600
            print(f"   时间跨度: {hours:.1f} 小时")
    except Exception as e:
        print(f"   ⚠️  查询失败: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 批量导入完成！")
    print("=" * 80)
    print("\n🌐 访问Web界面查看完整24小时趋势图:")
    print("   https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")

if __name__ == '__main__':
    batch_import()
