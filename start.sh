#!/bin/bash
# MiniJEV 快速开始脚本

set -e

echo "========================================"
echo "MiniJEV 快速开始"
echo "========================================"
echo ""

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
    echo "错误: 需要 Python 3.10+，当前版本: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python版本: $PYTHON_VERSION"

# 检查依赖
echo ""
echo "检查依赖..."
python3 -c "import json, re, time, logging" 2>/dev/null && echo "  ✅ 标准库已安装" || echo "  ⚠️ 请安装标准库"

# 运行演示
echo ""
echo "========================================"
echo "运行MiniJEV演示..."
echo "========================================"
echo ""

python3 demo.py

echo ""
echo "========================================"
echo "演示完成！"
echo "========================================"
echo ""
echo "下一步:"
echo "  1. 查看 README.md 了解更多用法"
echo "  2. 接入你自己的LLM API"
echo "  3. 自定义few-shot示例提升准确率"
echo ""
