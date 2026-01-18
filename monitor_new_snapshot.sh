#!/bin/bash
echo "🔍 开始监控新快照..."
echo "当前最新快照:"

# 获取当前最新快照时间
CURRENT=$(tail -1 data/gdrive_jsonl/crypto_snapshots.jsonl 2>/dev/null | python3 -c "import json, sys; print(json.load(sys.stdin).get('snapshot_time', 'N/A'))" 2>/dev/null)
echo "  时间: $CURRENT"

# 统计当前快照的币种数
COUNT=$(grep "\"snapshot_time\": \"$CURRENT\"" data/gdrive_jsonl/crypto_snapshots.jsonl 2>/dev/null | wc -l)
echo "  币种数: $COUNT"

echo ""
echo "⏳ 每30秒检查一次..."
echo "按Ctrl+C停止监控"
echo ""

while true; do
    sleep 30
    
    # 获取最新快照时间
    NEW=$(tail -1 data/gdrive_jsonl/crypto_snapshots.jsonl 2>/dev/null | python3 -c "import json, sys; print(json.load(sys.stdin).get('snapshot_time', 'N/A'))" 2>/dev/null)
    
    # 如果有新快照
    if [ "$NEW" != "$CURRENT" ]; then
        NEW_COUNT=$(grep "\"snapshot_time\": \"$NEW\"" data/gdrive_jsonl/crypto_snapshots.jsonl 2>/dev/null | wc -l)
        echo "🎉 检测到新快照!"
        echo "  时间: $NEW"
        echo "  币种数: $NEW_COUNT"
        
        if [ "$NEW_COUNT" -ge 25 ]; then
            echo "  ✅ 币种数量正常 (≥25)"
        else
            echo "  ⚠️  币种数量偏少 (<25)"
        fi
        
        CURRENT=$NEW
        echo ""
    else
        echo "⏳ $(date '+%H:%M:%S') - 等待新快照... (当前: $CURRENT, $COUNT个币种)"
    fi
done
