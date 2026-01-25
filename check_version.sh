#!/bin/bash
echo "=== 检查所有路由返回的版本 ==="
echo ""
echo "1. 旧路由 (v1):"
curl -s "http://127.0.0.1:5000/escape-signal-history" | grep -o "v[0-9]\.[0-9]-[0-9]*" | head -1
echo ""
echo "2. 新路由 (v2):"
curl -s "http://127.0.0.1:5000/escape-signal-history-v2" | grep -o "v[0-9]\.[0-9]-[0-9]*" | head -1
echo ""
echo "3. 外网访问v2:"
curl -s "https://5000-iz51witudb16wj96d1wvr-a402f90a.sandbox.novita.ai/escape-signal-history-v2" | grep -o "v[0-9]\.[0-9]-[0-9]*" | head -1
echo ""
echo "4. 模板文件版本:"
grep -o "v[0-9]\.[0-9]-[0-9]*-[a-z]*" source_code/templates/escape_signal_history.html | head -1
