#!/usr/bin/env python3
"""传感器数据上传测试"""
import requests
import json
import time

# 服务器配置
SERVER_URL = "http://192.168.1.22:3000"
GATEWAY_IP = "192.168.1.63"
FARM_ID = 1

def upload_sensor_data():
    """上传传感器数据"""
    payload = {
        "gateway_ip": GATEWAY_IP,
        "gateway_type": "wifi_sensor",
        "farm_id": FARM_ID,
        "area": "温室1号区域",
        "nodes": [
            {
                "node_id": "T-1-001",
                "name": "空气温度传感器",
                "type": "temperature",
                "value": 26.5,
                "unit": "°C",
                "location": "温室中部"
            },
            {
                "node_id": "H-1-001",
                "name": "空气湿度传感器",
                "type": "humidity",
                "value": 65.2,
                "unit": "%",
                "location": "温室中部"
            }
        ]
    }

    try:
        resp = requests.post(f"{SERVER_URL}/api/device/report", json=payload, timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.json()}")
        return resp.status_code == 200
    except Exception as e:
        print(f"上传失败: {e}")
        return False

if __name__ == "__main__":
    print("测试数据上传...")
    for i in range(3):
        print(f"\n第{i+1}次上传:")
        upload_sensor_data()
        time.sleep(2)
    print("\n测试完成!")
