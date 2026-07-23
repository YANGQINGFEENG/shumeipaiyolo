#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据上传到智慧农业平台
"""

import sys
import os
import time
import requests

sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor')

from sensors.base import SensorHub
from sensors.digital import RgbLedSensor, RelaySensor, LaserSensor, VibrationSensor, DhtSensor
from sensors.i2c import Bmp280Sensor
from upload.http_uploader import HttpUploader


def main():
    print("=" * 60)
    print("  传感器数据上传测试")
    print("  Smart Agriculture Platform Upload Test")
    print("=" * 60)
    print()

    # 配置
    API_SERVER = "http://26.162.225.180:3000"
    GATEWAY_IP = "192.168.1.63"
    MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"
    FARM_ID = 1

    # 初始化上传器
    uploader = HttpUploader(
        server=API_SERVER,
        gateway_ip=GATEWAY_IP,
        mac=MAC_ADDRESS,
        farm_id=FARM_ID
    )
    print(f"API服务器: {API_SERVER}")
    print(f"网关IP: {GATEWAY_IP}")
    print()

    # 测试API连接
    print("--- 测试API连接 ---")
    try:
        resp = requests.get(f"{API_SERVER}/api/farms", timeout=5)
        if resp.status_code == 200:
            print("✓ API连接成功")
        else:
            print(f"✗ API返回状态码: {resp.status_code}")
    except Exception as e:
        print(f"✗ API连接失败: {e}")
        print("请确保服务器已启动")
        return

    print()

    # 初始化传感器
    print("--- 初始化传感器 ---")
    hub = SensorHub()
    hub.register(RgbLedSensor(red=19, green=17, blue=27, name="rgb_led"))
    hub.register(RelaySensor(pin=16, name="relay"))
    hub.register(LaserSensor(pin=13, name="laser"))
    hub.register(VibrationSensor(pin=12, name="vibration"))
    hub.register(DhtSensor(pin=6, sensor_type="DHT11", name="dht"))
    hub.register(Bmp280Sensor(name="bmp280"))
    print(f"已注册 {len(hub.list())} 个传感器")
    print()

    # 读取并上传数据
    print("--- 读取传感器数据 ---")
    readings = hub.read_all()

    # 显示读取结果
    for name, reading in readings.items():
        if reading["status"] == "ok":
            data = reading["data"]
            if name == "dht":
                print(f"  {name:15} : 温度={data.get('temperature', 'N/A')}°C  湿度={data.get('humidity', 'N/A')}%")
            elif name == "bmp280":
                print(f"  {name:15} : 温度={data.get('temperature', 'N/A')}°C  气压={data.get('pressure', 'N/A')} hPa")
            elif name == "vibration":
                print(f"  {name:15} : {'振动中' if data.get('vibrating') else '静止'}")
            else:
                print(f"  {name:15} : {data}")

    print()

    # 上传数据
    print("--- 上传数据到平台 ---")

    # 上传DHT数据
    dht_reading = readings.get("dht", {})
    if dht_reading.get("status") == "ok":
        temp = dht_reading["data"].get("temperature")
        hum = dht_reading["data"].get("humidity")
        if temp is not None and hum is not None:
            print(f"  上传DHT数据: 温度={temp}°C, 湿度={hum}%")
            success = uploader.upload_dht_data(temp, hum)
            print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")

    # 上传BMP280数据
    bmp_reading = readings.get("bmp280", {})
    if bmp_reading.get("status") == "ok":
        temp = bmp_reading["data"].get("temperature")
        press = bmp_reading["data"].get("pressure")
        if temp is not None and press is not None:
            print(f"  上传BMP280数据: 温度={temp}°C, 气压={press} hPa")
            success = uploader.upload_bmp280_data(temp, press)
            print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")

    hub.cleanup_all()
    print()
    print("=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
