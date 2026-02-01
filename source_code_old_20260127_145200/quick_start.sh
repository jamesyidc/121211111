#!/bin/bash
# 快速开始脚本

echo "=================================="
echo "Google Drive 文件查找器 - 快速开始"
echo "=================================="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

echo "✅ Python3 已安装: $(python3 --version)"
echo ""

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 未找到pip3，请先安装pip"
    exit 1
fi

echo "✅ pip3 已安装"
echo ""

# 安装依赖
echo "📦 正在安装Python依赖包..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo ""
echo "✅ 依赖安装完成"
echo ""

# 运行设置向导
echo "🚀 运行设置向导..."
python3 setup_guide.py

echo ""
echo "=================================="
echo "快速开始完成"
echo "=================================="
