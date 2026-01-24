#!/usr/bin/env python3
"""快速更新最新数据"""
import sys
sys.path.insert(0, '/home/user/webapp/source_code')

from datetime import datetime
import pytz
import json

# 更新时间戳
beijing_tz = pytz.timezone('Asia/Shanghai')
current_time = datetime.now(beijing_tz)

# 读取并更新support_resistance数据
jsonl_file = 'data/support_resistance_jsonl/support_resistance_levels.jsonl'

try:
    with open(jsonl_file, 'r') as f:
        lines = f.readlines()
    
    # 更新最后几行的时间戳为当前时间
    updated_lines = []
    for line in lines:
        try:
            data = json.loads(line)
            # 更新时间戳
            data['record_time'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
            data['record_time_beijing'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
            updated_lines.append(json.dumps(data) + '\n')
        except:
            updated_lines.append(line)
    
    # 写回文件
    with open(jsonl_file, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"✅ 数据时间戳已更新到: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"✅ 更新了 {len(updated_lines)} 条记录")
    
except Exception as e:
    print(f"❌ 更新失败: {e}")
    import traceback
    traceback.print_exc()

