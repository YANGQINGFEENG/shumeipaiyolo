#!/usr/bin/env python3
"""通过JupyterLab WebSocket终端检测树莓派环境"""
import requests
import json
import time
import re

JUPYTER_URL = "http://192.168.1.63:8888"

session = requests.Session()
session.get(f"{JUPYTER_URL}/login", timeout=10)
xsrf = session.cookies.get("_xsrf")
headers = {"X-XSRFToken": xsrf}

# 创建终端
resp = session.post(f"{JUPYTER_URL}/api/terminals", headers=headers, timeout=10)
term = resp.json()["name"]
print(f"Terminal: {term}")

import websocket

ws_url = f"ws://192.168.1.63:8888/terminals/websocket/{term}"
ws = websocket.create_connection(ws_url, timeout=10)
print("Connected")

time.sleep(1)
ws.recv()  # 消耗初始输出

# 发送一个简单命令
ws.send(json.dumps(["execute", "uname -a"]))
time.sleep(3)

# 读取输出
all_output = ""
while True:
    try:
        ws.settimeout(1)
        data = ws.recv()
        all_output += data
    except:
        break

ws.close()

# 解析JSON输出
for line in all_output.split("\n"):
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
        if msg[0] == "stdout":
            content = msg[1]
            # 清理ANSI转义
            clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", content)
            clean = re.sub(r"\x1b\]0;[^\x07]*\x07", "", clean)
            clean = clean.replace("\r", "")
            for l in clean.split("\n"):
                l = l.strip()
                if l and "$" not in l and ">>>" not in l:
                    print(l)
    except (json.JSONDecodeError, IndexError):
        pass
