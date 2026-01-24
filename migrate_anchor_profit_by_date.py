#!/usr/bin/env python3
"""
将锚点盈利统计数据从单个大文件拆分为按日期的多个文件
"""
import json
import os
from datetime import datetime
from collections import defaultdict
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def migrate_data():
    """迁移数据到按日期文件"""
    
    source_file = '/home/user/webapp/data/anchor_profit_stats/anchor_profit_stats.jsonl'
    output_dir = '/home/user/webapp/data/anchor_profit_stats'
    
    if not os.path.exists(source_file):
        print(f"❌ 源文件不存在: {source_file}")
        return
    
    print(f"📂 开始迁移数据...")
    print(f"   源文件: {source_file}")
    print(f"   输出目录: {output_dir}")
    
    # 统计信息
    total_records = 0
    date_records = defaultdict(list)
    
    # 读取源文件，按日期分组
    print("\n📖 读取源文件...")
    with open(source_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 10000 == 0:
                print(f"   已处理 {line_num} 行...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                timestamp = data.get('timestamp')
                
                if not timestamp:
                    continue
                
                # 转换为北京时间的日期
                dt = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ)
                date_str = dt.strftime('%Y-%m-%d')
                
                date_records[date_str].append(data)
                total_records += 1
                
            except Exception as e:
                print(f"⚠️  跳过无效记录 (行 {line_num}): {str(e)}")
                continue
    
    print(f"\n✅ 读取完成！共 {total_records} 条记录，分布在 {len(date_records)} 天")
    
    # 写入按日期文件
    print(f"\n💾 写入按日期文件...")
    for date_str in sorted(date_records.keys()):
        output_file = os.path.join(output_dir, f'anchor_profit_{date_str}.jsonl')
        records = date_records[date_str]
        
        # 按时间戳排序
        records.sort(key=lambda x: x.get('timestamp', 0))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"   ✓ {date_str}: {len(records)} 条记录 -> {output_file}")
    
    print(f"\n🎉 迁移完成！")
    print(f"   总记录数: {total_records}")
    print(f"   生成文件数: {len(date_records)}")
    
    # 显示文件大小对比
    source_size = os.path.getsize(source_file) / (1024 * 1024)
    print(f"\n📊 文件大小对比:")
    print(f"   原文件: {source_size:.2f} MB")
    print(f"   按日期文件:")
    
    total_new_size = 0
    for date_str in sorted(date_records.keys())[-7:]:  # 只显示最近7天
        output_file = os.path.join(output_dir, f'anchor_profit_{date_str}.jsonl')
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        total_new_size += file_size
        print(f"      {date_str}: {file_size:.2f} MB ({len(date_records[date_str])} 条)")
    
    print(f"   最近7天总大小: {total_new_size:.2f} MB")
    
    # 建议
    print(f"\n💡 建议:")
    print(f"   1. 验证新文件数据完整性")
    print(f"   2. 备份原文件: mv {source_file} {source_file}.bak")
    print(f"   3. 更新数据采集器，使其写入按日期文件")

if __name__ == '__main__':
    migrate_data()
