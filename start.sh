#!/bin/bash
# 智慧农业物联网系统启动脚本
# 自动清理GPIO并启动系统

echo "=========================================="
echo "  智慧农业物联网系统启动"
echo "=========================================="
echo

# 1. 清理GPIO占用
echo "1. 清理GPIO占用进程..."

# 杀死占用gpiochip0的进程
GPIO_PIDS=$(sudo lsof /dev/gpiochip0 2>/dev/null | awk 'NR>1 {print $2}' | sort -u)
if [ -n "$GPIO_PIDS" ]; then
    echo "   发现占用GPIO的进程: $GPIO_PIDS"
    for pid in $GPIO_PIDS; do
        echo "   杀死进程 PID: $pid"
        sudo kill -9 $pid 2>/dev/null
    done
    echo "   ✓ GPIO占用进程已清理"
else
    echo "   ✓ 未发现GPIO占用进程"
fi

# 杀死所有Python进程
echo "   清理Python进程..."
sudo pkill -9 -f python3 2>/dev/null
sleep 1

# 杀死libgpiod僵尸进程
echo "   清理libgpiod进程..."
sudo pkill -9 -f libgpiod 2>/dev/null
sleep 1

# 2. 验证GPIO状态
echo "2. 验证GPIO状态..."
GPIO_STATUS=$(sudo lsof /dev/gpiochip0 2>/dev/null)
if [ -z "$GPIO_STATUS" ]; then
    echo "   ✓ GPIO已释放"
else
    echo "   ⚠ 仍有进程占用GPIO:"
    echo "$GPIO_STATUS" | head -3
fi

echo

# 3. 启动系统
echo "3. 启动系统..."
cd /home/pi/makerobo_code/yolo_sensor
python3 run.py start
