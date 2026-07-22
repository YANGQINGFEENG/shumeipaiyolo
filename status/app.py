#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单状态页面 / Simple Status Page
"""

import json
import time
import os
import sys
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# 模拟数据 (实际部署时从传感器读取)
def get_system_status():
    """获取系统状态"""
    try:
        import subprocess
        temp = subprocess.run(
            ["cat", "/sys/class/thermal/thermal_zone0/temp"],
            capture_output=True, text=True, timeout=5
        )
        temp_val = int(temp.stdout.strip()) / 1000 if temp.stdout.strip() else 0
    except:
        temp_val = 0

    try:
        import subprocess
        mem = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = mem.stdout.strip().split("\n")
        parts = lines[1].split()
        mem_total = int(parts[1])
        mem_used = int(parts[2])
    except:
        mem_total = 0
        mem_used = 0

    return {
        "temperature": round(temp_val, 1),
        "memory_total": mem_total,
        "memory_used": mem_used,
        "memory_percent": round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0,
        "uptime": time.strftime("%H:%M:%S")
    }


def get_sensor_status():
    """获取传感器状态"""
    # 从最近的日志文件读取
    return {
        "ultrasonic": {"status": "ok", "last_value": "1.23m", "time": "16:30:00"},
        "bmp280": {"status": "ok", "last_value": "25.6°C", "time": "16:30:00"},
        "led": {"status": "ok", "last_value": "ON", "time": "16:29:55"},
        "camera": {"status": "ok", "last_value": "Ready", "time": "16:29:50"}
    }


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """API: 获取状态"""
    return jsonify({
        "system": get_system_status(),
        "sensors": get_sensor_status(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route("/api/sensors")
def api_sensors():
    """API: 获取传感器数据"""
    return jsonify(get_sensor_status())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
