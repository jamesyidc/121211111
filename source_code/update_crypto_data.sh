#!/bin/bash
# 更新加密货币数据脚本
# 使用方法：将最新TXT文件内容保存为 latest_data.txt，然后运行此脚本

cd /home/user/webapp

if [ -f "latest_data.txt" ]; then
    echo "📁 发现 latest_data.txt 文件"
    
    # 备份旧数据
    if [ -f "crypto_latest_data.txt" ]; then
        mv crypto_latest_data.txt crypto_latest_data.txt.bak
        echo "✅ 已备份旧数据"
    fi
    
    # 更新数据
    cp latest_data.txt crypto_latest_data.txt
    echo "✅ 数据已更新"
    
    # 显示更新时间
    echo "📅 更新时间: $(date '+%Y-%m-%d %H:%M:%S')"
    
    # 解析并显示统计
    python3 << 'EOF'
from crypto_data_parser import CryptoDataParser

with open('crypto_latest_data.txt', 'r', encoding='utf-8') as f:
    content = f.read()

result = CryptoDataParser.parse_txt_content(content)
if result:
    stats = result['stats']
    print(f"\n📊 数据统计:")
    print(f"   急涨: {stats.get('rushUp', 0)}")
    print(f"   急跌: {stats.get('rushDown', 0)}")
    print(f"   状态: {stats.get('status', 'N/A')}")
    print(f"   币种数量: {len(result['data'])}")
EOF
    
    # 清理临时文件
    rm latest_data.txt
    echo "✅ 已清理临时文件"
    
else
    echo "❌ 未找到 latest_data.txt 文件"
    echo "请将最新的TXT文件内容保存为 latest_data.txt"
    exit 1
fi
