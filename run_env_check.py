#!/usr/bin/env python3
"""通过JupyterLab API检测树莓派环境"""
import requests
import time
import json

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
kernel_id = resp.json()["id"]
print(f"Kernel ID: {kernel_id}")

# 等待kernel就绪
for i in range(10):
    time.sleep(2)
    resp = session.get(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
        headers=headers,
        timeout=10)
    state = resp.json().get("execution_state", "unknown")
    print(f"  State: {state}")
    if state == "idle":
        break

# 执行环境检测代码
code = """
import subprocess, os

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)

print("=" * 60)
print("  RASPBERRY PI ENVIRONMENT CHECK")
print("=" * 60)

print("\\n--- System ---")
print("Hostname:", run("hostname"))
print("OS:", run("cat /etc/os-release | grep PRETTY_NAME"))
print("Kernel:", run("uname -r"))
print("Arch:", run("uname -m"))
print("CPU Temp:", run("cat /sys/class/thermal/thermal_zone0/temp"))

print("\\n--- Python ---")
print("Python:", run("python3 --version"))
print("Pip:", run("pip3 --version"))

print("\\n--- Packages ---")
pkgs = run("pip3 list 2>/dev/null")
for line in pkgs.split("\\n"):
    low = line.lower()
    if any(k in low for k in ["opencv", "yolo", "torch", "tensor", "gpio", "picamera", "numpy", "pandas", "flask", "ultralytics", "matplotlib", "pillow"]):
        print(" ", line)

print("\\n--- OpenCV ---")
print(run("python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo NOT_INSTALLED"))

print("\\n--- Ultralytics ---")
print(run("python3 -c 'import ultralytics; print(ultralytics.__version__)' 2>/dev/null || echo NOT_INSTALLED"))

print("\\n--- GPIO ---")
print("gpiozero:", run("python3 -c 'import gpiozero; print(gpiozero.__version__)' 2>/dev/null || echo NOT_AVAILABLE"))
print("RPi.GPIO:", run("python3 -c 'import RPi.GPIO; print(AVAILABLE)' 2>/dev/null || echo NOT_AVAILABLE"))

print("\\n--- Camera ---")
print(run("python3 -c 'from picamera2 import Picamera2; print(picamera2.__version__)' 2>/dev/null || echo NOT_AVAILABLE"))

print("\\n--- Memory ---")
print(run("free -h"))

print("\\n--- Disk ---")
print(run("df -h /"))

print("\\n--- Network ---")
print("IP:", run("hostname -I"))

print("\\n" + "=" * 60)
print("  CHECK COMPLETE")
print("=" * 60)
"""

print("Executing code...")
resp = session.post(f"{JUPYTER_URL}/api/kernels/{kernel_id}/execute",
    json={"code": code, "silent": False},
    headers=headers,
    timeout=10)
print(f"Execute status: {resp.status_code}")

# 等待执行完成
print("Waiting for execution...")
time.sleep(15)

# 清理 - 删除kernel
session.delete(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
    headers=headers,
    timeout=10)
print("Done. Please check JupyterLab for output:")
print(f"{JUPYTER_URL}/lab")
