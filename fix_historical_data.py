#!/usr/bin/env python3
"""
历史数据字段修复脚本

问题：
旧解析器使用了错误的字段映射：
- rush_up 保存的实际是 speed（涨速）
- rush_down 保存的实际是 rush_up（急涨次数）
- count 保存的实际是 rush_down（急跌次数）

修复方案：
将历史数据的字段重新映射为正确的值
"""

import json
import os
from datetime import datetime

def fix_historical_data():
    """修复历史数据的字段映射"""
    
    input_file = '/home/user/webapp/data/gdrive_jsonl/crypto_snapshots.jsonl'
    output_file = '/home/user/webapp/data/gdrive_jsonl/crypto_snapshots_fixed.jsonl'
    backup_file = '/home/user/webapp/data/gdrive_jsonl/crypto_snapshots_backup.jsonl'
    
    # 备份原文件
    print(f"📦 备份原文件...")
    os.system(f'cp {input_file} {backup_file}')
    print(f"✅ 备份完成: {backup_file}")
    
    # 统计
    total = 0
    fixed = 0
    skipped = 0
    
    print(f"\n🔧 开始修复数据...")
    
    with open(input_file, 'r') as fin, open(output_file, 'w') as fout:
        for line in fin:
            total += 1
            
            try:
                data = json.loads(line.strip())
                
                # 检查是否需要修复（没有speed字段的记录）
                if data.get('speed') is None and data.get('rush_up') is not None:
                    # 旧数据字段映射（错误的）
                    old_rush_up = data.get('rush_up')      # 实际是涨速
                    old_rush_down = data.get('rush_down')  # 实际是急涨次数
                    old_count = data.get('count')          # 实际是急跌次数
                    
                    # 修正为正确的字段映射
                    data['speed'] = old_rush_up           # 涨速
                    data['rush_up'] = old_rush_down       # 急涨次数
                    data['rush_down'] = old_count         # 急跌次数
                    data['count'] = old_count             # 向后兼容
                    
                    # 重新计算diff和status
                    rush_up_new = data['rush_up'] or 0
                    rush_down_new = data['rush_down'] or 0
                    data['diff'] = rush_up_new - rush_down_new
                    
                    if data['diff'] > 0:
                        data['status'] = '急涨'
                    elif data['diff'] < 0:
                        data['status'] = '急跌'
                    else:
                        data['status'] = '平稳'
                    
                    fixed += 1
                    
                    # 每1000条打印一次进度
                    if fixed % 1000 == 0:
                        print(f"  已修复: {fixed} 条")
                else:
                    skipped += 1
                
                # 写入修复后的数据
                fout.write(json.dumps(data, ensure_ascii=False) + '\n')
                
            except Exception as e:
                print(f"⚠️  解析失败 (行{total}): {e}")
                # 保留原始行
                fout.write(line)
    
    print(f"\n✅ 修复完成!")
    print(f"  总记录数: {total}")
    print(f"  已修复: {fixed}")
    print(f"  跳过: {skipped}")
    
    # 替换原文件
    print(f"\n🔄 替换原文件...")
    os.system(f'mv {output_file} {input_file}')
    print(f"✅ 完成！原文件已更新")
    print(f"   备份保存在: {backup_file}")

if __name__ == '__main__':
    print("=" * 80)
    print("历史数据字段修复脚本")
    print("=" * 80)
    print()
    print("⚠️  警告：此脚本会修改历史数据！")
    print("   - 会自动备份原文件")
    print("   - 修复字段映射错误")
    print()
    
    response = input("确认继续？(yes/no): ")
    if response.lower() == 'yes':
        fix_historical_data()
    else:
        print("❌ 取消操作")
