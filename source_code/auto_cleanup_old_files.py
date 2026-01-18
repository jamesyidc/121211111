#!/usr/bin/env python3
"""
自动清理Google Drive旧文件脚本
业务逻辑：保持文件夹内文件数量在50以下，自动删除旧文件
"""

from datetime import datetime, timedelta
import pytz

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def generate_cleanup_list(keep_hours=4):
    """
    生成需要删除的文件列表
    保留最近N小时的文件，删除更早的文件
    """
    now = datetime.now(BEIJING_TZ)
    cutoff_time = now - timedelta(hours=keep_hours)
    
    files_to_delete = []
    files_to_keep = []
    
    # 生成今天所有可能的文件名
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    current = start_of_day
    
    while current <= now:
        filename = current.strftime("2025-12-06_%H%M.txt")
        
        if current < cutoff_time:
            files_to_delete.append({
                'filename': filename,
                'time': current.strftime('%H:%M')
            })
        else:
            files_to_keep.append({
                'filename': filename,
                'time': current.strftime('%H:%M')
            })
        
        current += timedelta(minutes=10)
    
    return files_to_delete, files_to_keep

print("="*70)
print("Google Drive 文件自动清理方案")
print("="*70)

# 生成清理列表
delete_list, keep_list = generate_cleanup_list(keep_hours=4)

print(f"\n当前时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"\n清理策略: 保留最近4小时的文件")
print(f"\n需要删除的文件: {len(delete_list)} 个")
if delete_list:
    print(f"时间范围: {delete_list[0]['time']} - {delete_list[-1]['time']}")
    print(f"\n删除列表示例（前5个）:")
    for item in delete_list[:5]:
        print(f"  - {item['filename']} ({item['time']})")

print(f"\n需要保留的文件: {len(keep_list)} 个")
if keep_list:
    print(f"时间范围: {keep_list[0]['time']} - {keep_list[-1]['time']}")

print("\n" + "="*70)
print("实施说明:")
print("="*70)
print("""
由于需要Google Drive API认证才能自动删除文件，
当前提供以下解决方案：

方案1：手动删除旧文件
  1. 打开 Google Drive 文件夹
  2. 选择今天早上8点之前的所有文件
  3. 删除这些文件
  4. 这样新文件就能进入前50名被系统访问

方案2：修改采集器逻辑
  - 不从Google Drive读取文件列表
  - 直接根据当前时间推算最新文件名
  - 尝试直接访问该文件
  
方案3：使用Google Drive API（需要配置）
  - 配置OAuth认证
  - 使用API自动删除旧文件
  - 自动化清理流程
""")

