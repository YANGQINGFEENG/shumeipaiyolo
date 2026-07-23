#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全部传感器测试脚本 - 读取并打印所有传感器数据
"""

import sys
import os
import time

sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor')

from sensors.base import SensorHub
from sensors.digital import (
    RgbLedSensor, RelaySensor, LaserSensor,
    VibrationSensor, DhtSensor
)
from sensors.analog import LightSensor, PotentiometerSensor, SoundSensor
from sensors.i2c import Bmp280Sensor


def main():
    print("=" * 60)
    print("  树莓派传感器数据读取测试")
    print("  Raspberry Pi Sensor Data Test")
    print("=" * 60)
    print()

    hub = SensorHub()

    # 注册传感器 (使用实际硬件引脚)
    print("初始化传感器...")

    # RGB-LED: R=G19, G=G17, B=G27
    hub.register(RgbLedSensor(red=19, green=17, blue=27, name="rgb_led"))

    # 继电器: G16
    hub.register(RelaySensor(pin=16, name="relay"))

    # 激光: G13
    hub.register(LaserSensor(pin=13, name="laser"))

    # 振动开关: G12
    hub.register(VibrationSensor(pin=12, name="vibration"))

    # 温湿度: G6 (DHT11)
    hub.register(DhtSensor(pin=6, sensor_type="DHT11", name="dht"))

    # BMP280 气压: I2C
    hub.register(Bmp280Sensor(name="bmp280"))

    # 模拟传感器 (通过MCP3008)
    hub.register(LightSensor(channel=0, name="light"))
    hub.register(PotentiometerSensor(channel=1, name="potentiometer"))
    hub.register(SoundSensor(channel=2, name="sound"))

    print(f"已注册 {len(hub.list())} 个传感器: {hub.list()}")
    print()

    # 测试所有传感器
    print("=" * 60)
    print("  传感器测试结果")
    print("=" * 60)

    results = hub.test_all()
    for name, result in results.items():
        status = "✓ OK" if result["status"] == "ok" else "✗ FAIL"
        error = f" ({result.get('error', '')})" if result["status"] != "ok" else ""
        print(f"  {name:15} : {status}{error}")

    print()

    # 读取所有传感器数据
    print("=" * 60)
    print("  传感器数据读取")
    print("=" * 60)

    for _ in range(3):
        print(f"\n--- 第{_+1}次读取 ---")
        data = hub.read_all()
        for name, reading in data.items():
            if reading["status"] == "ok":
                sensor_data = reading["data"]
                if name == "rgb_led":
                    print(f"  {name:15} : R={sensor_data.get('red', 0):.3f} G={sensor_data.get('green', 0):.3f} B={sensor_data.get('blue', 0):.3f}")
                elif name == "dht":
                    print(f"  {name:15} : {sensor_data.get('temperature', 'N/A')}°C  {sensor_data.get('humidity', 'N/A')}%")
                elif name == "bmp280":
                    print(f"  {name:15} : {sensor_data.get('temperature', 'N/A')}°C  {sensor_data.get('pressure', 'N/A')} hPa")
                elif name == "light":
                    print(f"  {name:15} : {sensor_data.get('lux', 0)}")
                elif name == "potentiometer":
                    print(f"  {name:15} : {sensor_data.get('percentage', 0):.1f}%")
                elif name == "sound":
                    print(f"  {name:15} : Level {sensor_data.get('level', 0)}")
                elif name == "relay":
                    print(f"  {name:15} : {'ON' if sensor_data.get('active') else 'OFF'}")
                elif name == "laser":
                    print(f"  {name:15} : {'ON' if sensor_data.get('active') else 'OFF'}")
                elif name == "vibration":
                    print(f"  {name:15} : {'VIBRATING' if sensor_data.get('vibrating') else 'STILL'}")
                else:
                    print(f"  {name:15} : {sensor_data}")
            else:
                print(f"  {name:15} : ERROR - {reading.get('error', 'unknown')}")
        time.sleep(2)

    hub.cleanup_all()
    print()
    print("=" * 60)
    print("  测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
