#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境检测脚本 - 在树莓派上执行"""

import subprocess
import os

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"Error: {e}"

print("=" * 60)
print("       树莓派环境检测报告 / Environment Check Report")
print("=" * 60)

print("\n=== 1. 系统信息 / System Info ===")
print(f"Hostname: {run_cmd('hostname')}")
print(f"OS: {run_cmd('cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2')}")
print(f"Kernel: {run_cmd('uname -r')}")
print(f"Architecture: {run_cmd('uname -m')}")

print("\n=== 2. Python环境 / Python Environment ===")
print(f"Python3: {run_cmd('python3 --version')}")
print(f"Pip3: {run_cmd('pip3 --version | cut -d' ' -f1-2')}")

print("\n=== 3. 关键Python包 / Key Python Packages ===")
packages = run_cmd("pip3 list 2>/dev/null | grep -iE 'opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|fastapi|requests|ultralytics|matplotlib|scipy|pillow'")
if packages:
    print(packages)
else:
    print("未找到匹配的包 / No matching packages found")

print("\n=== 4. OpenCV ===")
print(run_cmd("python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'NOT INSTALLED'"))

print("\n=== 5. YOLO/Ultralytics ===")
print(run_cmd("python3 -c 'import ultralytics; print(ultralytics.__version__)' 2>/dev/null || echo 'NOT INSTALLED'"))

print("\n=== 6. GPIO库 / GPIO Libraries ===")
print(f"RPi.GPIO: {run_cmd('python3 -c 'import RPi.GPIO; print('AVAILABLE')' 2>/dev/null || echo 'NOT AVAILABLE')}")
print(f"gpiozero: {run_cmd('python3 -c 'import gpiozero; print('AVAILABLE')' 2>/dev/null || echo 'NOT AVAILABLE')}")

print("\n=== 7. 摄像头 / Camera ===")
print(run_cmd("python3 -c 'from picamera2 import Picamera2; print(\"picamera2: AVAILABLE\")' 2>/dev/null || echo 'picamera2: NOT AVAILABLE'"))

print("\n=== 8. 硬件信息 / Hardware Info ===")
print(f"CPU Temperature: {run_cmd('cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{print $1/1000}' || echo 'N/A')}")
print(f"Memory: {run_cmd('free -h | awk '/^Mem:/{print $2 \" total, \" $3 \" used\"}')}")
print(f"Disk: {run_cmd('df -h / | awk 'NR==2{print $2 \" total, \" $3 \" used, \" $4 \" available\"}')}'")

print("\n=== 9. 网络 / Network ===")
print(f"IP Address: {run_cmd('hostname -I | awk '{print $1}')}")
print(f"Gateway: {run_cmd('ip route | grep default | awk '{print $3}')}")

print("\n" + "=" * 60)
print("       环境检测完成 / Environment Check Complete")
print("=" * 60)
