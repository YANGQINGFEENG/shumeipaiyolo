#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过JupyterLab终端检测树莓派环境"""

import requests
import json
import time
import re

JUPYTER_URL = "http://192.168.1.63:8888"

# 创建session获取cookie
session = requests.Session()
resp = session.get(f"{JUPYTER_URL}/login", timeout=10)
xsrf = session.cookies.get("_xsrf")
headers = {"X-XSRFToken": xsrf}

# 创建终端
resp = session.post(f"{JUPYTER_URL}/api/terminals", headers=headers, timeout=10)
terminal_name = resp.json()["name"]
print(f"Terminal created: {terminal_name}")

# 通过WebSocket发送命令
import websocket

ws_url = f"ws://192.168.1.63:8888/terminals/websocket/{terminal_name}"
ws = websocket.create_connection(ws_url, timeout=10)
print("WebSocket connected")

# 等待初始输出
time.sleep(1)
output = ws.recv()

# 发送环境检测命令
commands = [
    "echo === System Info ===",
    "uname -a",
    "echo === Python Version ===",
    "python3 --version",
    "echo === Key Packages ===",
    "pip3 list 2>/dev/null | grep -iE opencv,yolo,torch,gpio,picamera,numpy,ultralytics",
    "echo === OpenCV ===",
    "python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo Not installed",
    "echo === GPIO ===",
    "python3 -c 'import gpiozero; print(gpiozero.__version__)' 2>/dev/null || echo Not available",
    "echo === Camera ===",
    "python3 -c 'from picamera2 import Picamera2; print(picamera2.__version__)' 2>/dev/null || echo Not available",
    "echo === Disk ===",
    "df -h /",
    "echo === Memory ===",
    "free -h",
    "exit"
]

for cmd in commands:
    ws.send(json.dumps(["execute", cmd]))
    time.sleep(0.5)

# 读取所有输出
time.sleep(3)
all_output = ""
while True:
    try:
        ws.settimeout(2)
        data = ws.recv()
        all_output += data
    except:
        break

ws.close()

# 解析输出
lines = all_output.split("\r\n")
for line in lines:
    line = line.strip()
    # 跳过空行、命令回显和提示符
    if line and ">>>" not in line and "$" not in line[:3]:
        # 移除可能的转义字符
        clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
        if clean:
            print(clean)
