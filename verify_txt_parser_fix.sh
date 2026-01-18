#!/bin/bash
# TXT解析器修复验证脚本

echo "=================================="
echo "TXT解析器字段修复验证"
echo "=================================="
echo ""

echo "📊 检查最新数据..."
echo ""

# 获取最新快照时间
LATEST_TIME=$(tail -1 /home/user/webapp/data/gdrive_jsonl/crypto_snapshots.jsonl | python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
print(data.get('snapshot_time', 'N/A'))
")

echo "最新快照时间: $LATEST_TIME"
echo ""

# 检查最新5条记录的字段完整性
echo "检查最新5条记录的字段完整性:"
echo "-----------------------------------"

tail -5 /home/user/webapp/data/gdrive_jsonl/crypto_snapshots.jsonl | python3 << 'PYEOF'
import json
import sys

fields_to_check = [
    'current_price',
    'high_price',
    'high_time',
    'drop_from_high',
    'update_time',
    'ranking'
]

for i, line in enumerate(sys.stdin, 1):
    data = json.loads(line.strip())
    inst_id = data.get('inst_id', 'N/A')
    
    print(f"\n{i}. {inst_id}")
    
    all_ok = True
    for field in fields_to_check:
        value = data.get(field)
        status = "✅" if value is not None else "❌"
        
        if value is None:
            all_ok = False
            print(f"   {field}: {status} None")
        else:
            # 格式化显示
            if field in ['current_price', 'high_price']:
                print(f"   {field}: {status} {value:.2f}")
            elif field == 'drop_from_high':
                print(f"   {field}: {status} {value:.2f}%")
            else:
                print(f"   {field}: {status} {value}")
    
    if all_ok:
        print(f"   ✅ 所有字段完整!")
    else:
        print(f"   ❌ 存在空字段")
PYEOF

echo ""
echo "=================================="
echo "验证完成"
echo "=================================="
echo ""
echo "如果看到 ❌，说明数据还是旧的"
echo "如果看到 ✅，说明修复已生效！"
echo ""
