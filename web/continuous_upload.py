#!/usr/bin/env python3
"""持续数据上传脚本"""
import requests
import json
import time
import random

# 服务器配置
SERVER_URL = "http://192.168.1.22:3000"
GATEWAY_IP = "192.168.1.63"
FARM_ID = 1
UPLOAD_INTERVAL = 30  # 上传间隔(秒)

def upload_sensor_data():
    """上传传感器数据"""
    # 模拟传感器数据 (实际应从硬件读取)
    temp = round(25 + random.uniform(-3, 5), 1)
    humidity = round(60 + random.uniform(-10, 15), 1)
    soil = round(40 + random.uniform(-5, 10), 1)
    light = round(1000 + random.uniform(-200, 400), 0)
    pressure = round(1013 + random.uniform(-3, 3), 1)

    payload = {
        "gateway_ip": GATEWAY_IP,
        "gateway_type": "wifi_sensor",
        "farm_id": FARM_ID,
        "area": "温室1号区域",
        "nodes": [
            {"node_id": "T-1-001", "name": "温度传感器", "type": "temperature", "value": temp, "unit": "°C"},
            {"node_id": "H-1-001", "name": "湿度传感器", "type": "humidity", "value": humidity, "unit": "%"},
            {"node_id": "SM-1-001", "name": "土壤湿度", "type": "soil_moisture", "value": soil, "unit": "%"},
            {"node_id": "L-1-001", "name": "光照传感器", "type": "light", "value": light, "unit": "lux"},
            {"node_id": "P-1-001", "name": "气压传感器", "type": "pressure", "value": pressure, "unit": "hPa"},
        ]
    }

    try:
        resp = requests.post(f"{SERVER_URL}/api/device/report", json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[{time.strftime('%H:%M:%S')}] 上传成功: 温度={temp}°C 湿度={humidity}%")
            return True
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 上传失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 上传错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("  智慧农业数据持续上传")
    print("=" * 50)
    print(f"服务器: {SERVER_URL}")
    print(f"网关IP: {GATEWAY_IP}")
    print(f"上传间隔: {UPLOAD_INTERVAL}秒")
    print("按 Ctrl+C 停止")
    print()

    count = 0
    while True:
        try:
            if upload_sensor_data():
                count += 1
            time.sleep(UPLOAD_INTERVAL)
        except KeyboardInterrupt:
            print(f"\n停止上传，共上传{count}次")
            break
