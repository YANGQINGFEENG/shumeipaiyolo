import requests
import json
import time

# JupyterLab API
JUPYTER_URL = "http://192.168.1.63:8888"

# 首先获取CSRF token
session = requests.Session()

# 获取JupyterLab的token
try:
    # 获取登录页面
    resp = session.get(f"{JUPYTER_URL}/login", timeout=10)
    print("Login page status:", resp.status_code)

    # 尝试不带token访问API
    resp = session.get(f"{JUPYTER_URL}/api/kernels", timeout=10)
    print("Kernels API status:", resp.status_code)
    print("Response:", resp.text[:500])

except Exception as e:
    print(f"Error: {e}")

# 尝试直接执行命令
print("\n" + "="*60)
print("尝试通过JupyterLab执行环境检测命令")
print("="*60)

# 创建一个简单的HTML页面来执行命令
commands = """
import subprocess
import sys

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)

print("=== System Info ===")
print(run_cmd("uname -a"))
print()
print("=== Python Version ===")
print(run_cmd("python3 --version"))
print()
print("=== Pip Version ===")
print(run_cmd("pip3 --version"))
print()
print("=== Key Packages ===")
print(run_cmd("pip3 list 2>/dev/null | grep -iE 'opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|ultralytics'"))
print()
print("=== OpenCV ===")
print(run_cmd("python3 -c 'import cv2; print(cv2.__version__)' 2>/dev/null || echo 'Not installed'"))
print()
print("=== GPIO ===")
print(run_cmd("python3 -c 'import gpiozero; print(gpiozero.__version__)' 2>/dev/null || echo 'Not available'"))
print()
print("=== Camera ===")
print(run_cmd("python3 -c 'from picamera2 import Picamera2; print(picamera2.__version__)' 2>/dev/null || echo 'Not available'"))
print()
print("=== Disk ===")
print(run_cmd("df -h /"))
print()
print("=== Memory ===")
print(run_cmd("free -h"))
"""

print("\n请在浏览器中打开 JupyterLab:")
print(f"{JUPYTER_URL}/lab")
print("\n然后创建一个新Notebook，运行以下代码:")
print("-" * 60)
print(commands)
print("-" * 60)
