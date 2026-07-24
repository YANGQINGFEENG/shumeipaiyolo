#!/bin/bash
# 智慧农业物联网系统 - 安装脚本

set -e

echo "=========================================="
echo "  智慧农业物联网系统安装"
echo "=========================================="
echo

# 检查Python版本
echo "检查Python版本..."
python3 --version || { echo "错误: 需要Python3"; exit 1; }

# 安装依赖
echo "安装依赖..."
pip3 install -r requirements.txt

# 创建必要目录
echo "创建目录..."
mkdir -p logs data

# 设置权限
chmod +x run.py

echo
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo
echo "使用方法:"
echo "  python3 run.py start    # 启动系统"
echo "  python3 run.py test     # 测试设备"
echo "  python3 run.py sensors  # 读取传感器"
echo
