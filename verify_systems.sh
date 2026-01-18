#!/bin/bash

echo "=========================================="
echo "🔍 系统状态验证脚本"
echo "=========================================="
echo ""

# 1. 检查PM2进程
echo "📊 1. PM2进程状态:"
pm2 list | grep -E "flask-app|sar-jsonl-collector"
echo ""

# 2. 检查最新SAR数据
echo "📊 2. SAR最新数据 (AAVE):"
tail -3 /home/user/webapp/data/sar_jsonl/AAVE.jsonl | jq -r '[.beijing_time, .position, .sequence, .close] | @tsv' | while IFS=$'\t' read time pos seq price; do
  echo "   $time | $pos #$seq | 价格: $price"
done
echo ""

# 3. 测试SAR API
echo "📊 3. SAR API测试:"
curl -s "http://localhost:5000/api/sar-slope/current-cycle/AAVE" | jq '{
  current_position: .current_status.position, 
  current_sequence: .current_status.sequence,
  last_update: .current_status.last_update,
  total_records: .total_sequences
}'
echo ""

# 4. 测试历史极值API
echo "📊 4. 历史极值API测试:"
curl -s "http://localhost:5000/api/anchor-system/profit-records?trade_mode=real" | jq '{
  success, 
  total, 
  data_source,
  latest_record: .records[0] | {inst_id, pos_side, record_type, profit_rate}
}'
echo ""

# 5. 检查JSONL文件大小
echo "📊 5. JSONL文件状态:"
echo "   SAR数据文件:"
ls -lh /home/user/webapp/data/sar_jsonl/*.jsonl | wc -l | xargs echo "     - 文件数量:"
du -sh /home/user/webapp/data/sar_jsonl/ | awk '{print "     - 总大小: " $1}'
echo "   历史极值文件:"
ls -lh /home/user/webapp/data/extreme_jsonl/*.jsonl 2>/dev/null | while read perm links owner group size rest; do
  echo "     - $(echo $rest | awk '{print $NF}' | xargs basename): $size"
done
echo ""

# 6. 检查采集器日志
echo "📊 6. 采集器最新状态:"
tail -5 /home/user/webapp/logs/sar_jsonl_collector.log | grep "本次采集完成" | tail -1
echo ""

echo "=========================================="
echo "✅ 验证完成！"
echo "=========================================="
