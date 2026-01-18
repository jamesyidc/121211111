#!/usr/bin/env python3
"""
修复版TXT文件导入脚本 - snapshot_time只存储时间部分
"""
import os
import re
import sqlite3
from datetime import datetime

def parse_txt_file(filepath):
    """解析txt文件，提取统计数据"""
    try:
        # 尝试多种编码
        content = None
        for encoding in ['utf-8', 'gb18030', 'gbk']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                    break
            except:
                continue
        
        if content is None:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        # 提取文件名中的时间
        filename = os.path.basename(filepath)
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
        if not match:
            return None
        
        date_str = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        
        # snapshot_time 只存储时间部分 HH:MM:SS
        snapshot_time = f"{hour}:{minute}:00"
        
        # 提取统计数据
        data = {
            'snapshot_time': snapshot_time,  # 只有时间
            'snapshot_date': date_str,       # 只有日期
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

def main():
    """主函数"""
    import sys
    import glob
    
    # 获取所有txt文件
    if len(sys.argv) > 1:
        # 指定文件
        txt_files = [sys.argv[1]]
    else:
        # 扫描所有txt文件
        txt_files = sorted(glob.glob('*.txt'))
        txt_files = [f for f in txt_files if re.match(r'\d{4}-\d{2}-\d{2}_\d{4}\.txt', f)]
    
    print('='*80)
    print('📦 TXT文件导入 (修复版 - snapshot_time仅存储时间)')
    print('='*80)
    print(f'\n✅ 找到 {len(txt_files)} 个txt文件\n')
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    print('开始导入...')
    print('-'*80)
    
    for i, filepath in enumerate(txt_files, 1):
        filename = os.path.basename(filepath)
        
        # 解析文件
        data = parse_txt_file(filepath)
        if not data:
            print(f'[{i:3d}/{len(txt_files)}] ❌ {filename} - 解析失败')
            fail_count += 1
            continue
        
        # 插入数据库
        success, msg = insert_snapshot(data)
        
        if success:
            print(f'[{i:3d}/{len(txt_files)}] ✅ {filename} - 急涨: {data["rush_up"]} 急跌: {data["rush_down"]} 计次: {data["count"]}')
            success_count += 1
        elif msg == "已存在":
            print(f'[{i:3d}/{len(txt_files)}] ⏭️  {filename} - 已存在')
            skip_count += 1
        else:
            print(f'[{i:3d}/{len(txt_files)}] ❌ {filename} - {msg}')
            fail_count += 1
    
    print('-'*80)
    print(f'\n📊 导入统计:')
    print(f'   总文件数: {len(txt_files)}')
    print(f'   ✅ 成功导入: {success_count}')
    print(f'   ⏭️  已存在跳过: {skip_count}')
    print(f'   ❌ 失败: {fail_count}')
    
    # 数据库统计
    conn = sqlite3.connect('/home/user/webapp/crypto_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM crypto_snapshots')
    total = cursor.fetchone()[0]
    cursor.execute('SELECT MIN(snapshot_date), MIN(snapshot_time), MAX(snapshot_date), MAX(snapshot_time) FROM crypto_snapshots')
    min_date, min_time, max_date, max_time = cursor.fetchone()
    conn.close()
    
    print(f'\n📈 数据库最终状态:')
    print(f'   总快照数: {total}')
    if min_date:
        print(f'   时间范围: {min_date} {min_time} 到 {max_date} {max_time}')
    
    print('\n' + '='*80)
    print('✅ 批量导入完成！')
    print('='*80)

if __name__ == '__main__':
    main()
