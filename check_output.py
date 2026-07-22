#!/usr/bin/env python3
import requests
import time

JUPYTER_URL = "http://192.168.1.63:8888"

session = requests.Session()
resp = session.get(f"{JUPYTER_URL}/login", timeout=10)
xsrf = session.cookies.get("_xsrf")
headers = {"X-XSRFToken": xsrf}

# 创建kernel
print("Creating kernel...")
resp = session.post(f"{JUPYTER_URL}/api/kernels",
    json={"name": "python3"},
    headers=headers,
    timeout=10)
print(f"Kernel status: {resp.status_code}")

if resp.status_code == 200:
    kernel = resp.json()
    kernel_id = kernel["id"]
    print(f"Kernel ID: {kernel_id}")

    time.sleep(3)

    # 执行简单的测试命令
    code = 'print("HELLO_FROM_PI")'
    resp = session.post(f"{JUPYTER_URL}/api/kernels/{kernel_id}/execute",
        json={"code": code, "silent": False},
        headers=headers,
        timeout=10)
    print(f"Execute: {resp.status_code}")

    time.sleep(5)

    # 获取kernelspecs
    resp = session.get(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
        headers=headers,
        timeout=10)
    print(f"Kernel info: {resp.json().get('last_activity', 'unknown')}")

    # 删除kernel
    session.delete(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
        headers=headers,
        timeout=10)
else:
    print("Error:", resp.text[:300])
