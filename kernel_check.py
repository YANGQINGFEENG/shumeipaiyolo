#!/usr/bin/env python3
"""通过JupyterLab Kernel WebSocket执行环境检测"""
import requests
import json
import time
import re
import select
import threading
import websocket

JUPYTER_URL = "http://192.168.1.63:8888"

session = requests.Session()
session.get(f"{JUPYTER_URL}/login", timeout=10)
xsrf = session.cookies.get("_xsrf")
headers = {"X-XSRFToken": xsrf}

# 创建kernel
resp = session.post(f"{JUPYTER_URL}/api/kernels",
    json={"name": "python3"},
    headers=headers, timeout=10)
kernel_id = resp.json()["id"]
print(f"Kernel: {kernel_id}")

time.sleep(5)  # 等待kernel完全启动

# 检查kernel状态
resp = session.get(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
    headers=headers, timeout=10)
state = resp.json()["execution_state"]
print(f"State: {state}")

if state != "idle":
    print("Kernel not ready, waiting more...")
    time.sleep(10)

# 连接kernel WebSocket
ws_url = f"ws://192.168.1.63:8888/api/kernels/{kernel_id}/channels"
ws = websocket.create_connection(ws_url, timeout=10)
print("Kernel WS connected")

time.sleep(1)

# 消耗初始消息
while True:
    try:
        ws.settimeout(1)
        ws.recv()
    except:
        break

# 环境检测代码
code = r"""
import subprocess, sys

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)

print("=" * 60)
print("  RASPBERRY PI ENVIRONMENT CHECK")
print("=" * 60)

print("\n--- System ---")
print("Hostname:", run("hostname"))
print("Kernel:", run("uname -r"))
print("Arch:", run("uname -m"))

print("\n--- Python ---")
print("Python:", run("python3 --version"))
print("Pip:", run("pip3 --version"))

print("\n--- Key Packages ---")
pkgs = run("pip3 list 2>/dev/null")
for line in pkgs.split("\n"):
    low = line.lower()
    if any(k in low for k in ["opencv", "yolo", "torch", "gpio", "picamera", "numpy", "ultralytics"]):
        print(" ", line)

print("\n--- OpenCV ---")
print(run("python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo NOT_INSTALLED"))

print("\n--- Ultralytics ---")
print(run("python3 -c 'import ultralytics; print(ultralytics.__version__)' 2>/dev/null || echo NOT_INSTALLED"))

print("\n--- GPIO ---")
print("gpiozero:", run("python3 -c 'import gpiozero; print(gpiozero.__version__)' 2>/dev/null || echo NOT_AVAILABLE"))
print("RPi.GPIO:", run("python3 -c 'import RPi.GPIO; print(AVAILABLE)' 2>/dev/null || echo NOT_AVAILABLE"))

print("\n--- Camera ---")
print("picamera2:", run("python3 -c 'from picamera2 import Picamera2; print(picamera2.__version__)' 2>/dev/null || echo NOT_AVAILABLE"))

print("\n--- Memory ---")
print(run("free -h"))

print("\n--- Disk ---")
print(run("df -h /"))

print("\n--- Network ---")
print("IP:", run("hostname -I"))

print("\n" + "=" * 60)
print("  CHECK COMPLETE")
print("=" * 60)
"""

# 发送execute_request
msg_id = "env_check_001"
execute_msg = {
    "header": {
        "msg_id": msg_id,
        "msg_type": "execute_request",
        "username": "pi",
        "session": "env_session",
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "version": "5.3"
    },
    "parent_header": {},
    "metadata": {},
    "content": {
        "code": code,
        "silent": False,
        "store_history": False,
        "user_expressions": {},
        "allow_stdin": False
    }
}

ws.send(json.dumps(execute_msg))
print("Code sent, waiting for execution...")

# 读取所有响应
all_output = []
start_time = time.time()
got_reply = False

while time.time() - start_time < 30:
    try:
        ws.settimeout(2)
        data = ws.recv()
        msg = json.loads(data)
        msg_type = msg.get("msg_type", "")

        if msg_type == "stream":
            content = msg.get("content", {})
            text = content.get("text", "")
            all_output.append(text)
        elif msg_type == "execute_result":
            content = msg.get("content", {})
            data_dict = content.get("data", {})
            text = data_dict.get("text/plain", "")
            all_output.append(text)
        elif msg_type == "error":
            content = msg.get("content", {})
            traceback = content.get("traceback", [])
            for tb in traceback:
                clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", tb)
                all_output.append(clean)
        elif msg_type == "status":
            content = msg.get("content", {})
            if content.get("execution_state") == "idle":
                got_reply = True
                break
    except:
        continue

ws.close()

# 清理并输出结果
result = "".join(all_output)
clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", result)
clean = re.sub(r"\x1b\]0;[^\x07]*\x07", "", clean)

print("\n" + "=" * 60)
print("  ENVIRONMENT CHECK RESULTS")
print("=" * 60)
print(clean)

# 清理kernel
session.delete(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
    headers=headers, timeout=10)
print("\nKernel deleted.")
