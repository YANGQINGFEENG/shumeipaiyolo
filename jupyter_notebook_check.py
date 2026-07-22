#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过JupyterLab Notebook检测树莓派环境"""

import requests
import json
import time

JUPYTER_URL = "http://192.168.1.63:8888"

# 创建session获取cookie
session = requests.Session()
resp = session.get(f"{JUPYTER_URL}/login", timeout=10)
xsrf = session.cookies.get("_xsrf")
headers = {"X-XSRFToken": xsrf}

# 创建Notebook
notebook = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import subprocess\n",
                "\n",
                "def run_cmd(cmd):\n",
                "    try:\n",
                "        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)\n",
                "        return (result.stdout + result.stderr).strip()\n",
                "    except Exception as e:\n",
                "        return f'Error: {e}'\n",
                "\n",
                "print('=' * 60)\n",
                "print('       树莓派环境检测报告')\n",
                "print('=' * 60)\n",
                "\n",
                "print('\\n=== 1. 系统信息 ===')\n",
                "print(f'Hostname: {run_cmd(\"hostname\")}')\n",
                "print(f'Kernel: {run_cmd(\"uname -r\")}')\n",
                "print(f'Architecture: {run_cmd(\"uname -m\")}')\n",
                "\n",
                "print('\\n=== 2. Python环境 ===')\n",
                "print(f'Python3: {run_cmd(\"python3 --version\")}')\n",
                "print(f'Pip3: {run_cmd(\"pip3 --version\")}')\n",
                "\n",
                "print('\\n=== 3. 关键Python包 ===')\n",
                "pkgs = run_cmd('pip3 list 2>/dev/null | grep -iE opencv,yolo,torch,gpio,picamera,numpy,ultralytics')\n",
                "print(pkgs if pkgs else '未找到匹配的包')\n",
                "\n",
                "print('\\n=== 4. OpenCV ===')\n",
                "print(run_cmd('python3 -c \"import cv2; print(cv2.__version__)\" 2>/dev/null || echo \"NOT INSTALLED\"'))\n",
                "\n",
                "print('\\n=== 5. YOLO/Ultralytics ===')\n",
                "print(run_cmd('python3 -c \"import ultralytics; print(ultralytics.__version__)\" 2>/dev/null || echo \"NOT INSTALLED\"'))\n",
                "\n",
                "print('\\n=== 6. GPIO库 ===')\n",
                "print(run_cmd('python3 -c \"import gpiozero; print(gpiozero.__version__)\" 2>/dev/null || echo \"NOT AVAILABLE\"'))\n",
                "\n",
                "print('\\n=== 7. 摄像头 ===')\n",
                "print(run_cmd('python3 -c \"from picamera2 import Picamera2; print(\\\"AVAILABLE\\\")\" 2>/dev/null || echo \"NOT AVAILABLE\"'))\n",
                "\n",
                "print('\\n=== 8. 硬件信息 ===')\n",
                "print(run_cmd('cat /sys/class/thermal/thermal_zone0/temp | awk \"{print $1/1000 \\\"°C\\\"}\"'))\n",
                "print(run_cmd('free -h | awk /^Mem:/{print $2 \" total, \" $3 \" used\"}'))\n",
                "print(run_cmd('df -h / | awk NR==2{print $2 \" total, \" $3 \" used, \" $4 \" available\"}'))\n",
                "\n",
                "print('\\n=== 9. 网络 ===')\n",
                "print(run_cmd('hostname -I | awk \"{print $1}\"'))\n",
                "\n",
                "print('\\n' + '=' * 60)\n",
                "print('       检测完成')\n",
                "print('=' * 60)"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.11.2"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

# 创建Notebook
print("Creating notebook...")
resp = session.put(f"{JUPYTER_URL}/api/contents/env_check.ipynb",
    json={"content": notebook, "type": "notebook"},
    headers=headers,
    timeout=10)
print(f"Create notebook: {resp.status_code}")

if resp.status_code == 200:
    # 创建kernel执行Notebook
    print("Creating kernel...")
    resp = session.post(f"{JUPYTER_URL}/api/kernels",
        json={"name": "python3"},
        headers=headers,
        timeout=10)
    print(f"Create kernel: {resp.status_code}")

    if resp.status_code == 200:
        kernel = resp.json()
        kernel_id = kernel["id"]
        print(f"Kernel ID: {kernel_id}")

        # 等待kernel启动
        time.sleep(2)

        # 获取Notebook内容
        resp = session.get(f"{JUPYTER_URL}/api/contents/env_check.ipynb",
            headers=headers,
            timeout=10)
        notebook_content = resp.json()["content"]

        # 执行第一个cell
        code = "".join(notebook_content["cells"][0]["source"])

        resp = session.post(f"{JUPYTER_URL}/api/kernels/{kernel_id}/execute",
            json={"code": code, "silent": False},
            headers=headers,
            timeout=10)
        print(f"Execute cell: {resp.status_code}")

        # 等待执行完成
        print("Waiting for execution...")
        time.sleep(10)

        # 获取输出
        resp = session.get(f"{JUPYTER_URL}/api/contents/env_check.ipynb",
            headers=headers,
            timeout=10)
        notebook_content = resp.json()["content"]

        # 打印输出
        for output in notebook_content["cells"][0]["outputs"]:
            if output["output_type"] == "stream":
                for line in output["text"]:
                    print(line, end="")
            elif output["output_type"] == "execute_result":
                for line in output["data"].get("text/plain", []):
                    print(line, end="")

        # 删除kernel
        session.delete(f"{JUPYTER_URL}/api/kernels/{kernel_id}",
            headers=headers,
            timeout=10)
        print("\nKernel deleted")
