#!/bin/bash
# 启动加密货币数据监控面板

echo "=================================="
echo "加密货币数据监控面板"
echo "=================================="
echo ""

# 检查credentials.json
if [ ! -f "credentials.json" ]; then
    echo "❌ 错误: 未找到 credentials.json"
    echo ""
    echo "请先完成Google Drive API设置:"
    echo "1. 运行: python3 setup_guide.py"
    echo "2. 按照提示创建 credentials.json"
    echo ""
    exit 1
fi

echo "✅ 找到凭证文件"
echo ""

# 检查依赖
echo "📦 检查Python依赖..."
pip3 install -r requirements.txt -q

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖检查完成"
echo ""

# 启动服务器
echo "🚀 启动服务器..."
echo ""
python3 crypto_server.py
