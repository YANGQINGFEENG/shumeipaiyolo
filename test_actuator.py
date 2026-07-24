#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器控制测试 - 清理GPIO后测试
"""

import sys
import os
import time
import subprocess

sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor')

# 清理GPIO资源
print("清理GPIO资源...")
subprocess.run(["sudo", "pkill", "-f", "gpio"], capture_output=True)
subprocess.run(["sudo", "fuser", "-k", "/dev/gpiomem"], capture_output=True)
time.sleep(1)

from sensors.digital import RelaySensor, LaserSensor, RgbLedSensor


def main():
    print("=" * 60)
    print("  执行器控制测试")
    print("  Actuator Control Test")
    print("=" * 60)
    print()

    # 初始化执行器
    print("初始化执行器...")
    relay = RelaySensor(pin=16, name="relay")
    laser = LaserSensor(pin=13, name="laser")
    rgb_led = RgbLedSensor(red=19, green=17, blue=27, name="rgb_led")

    # 尝试初始化
    relay_ok = relay.initialize()
    laser_ok = laser.initialize()
    rgb_ok = rgb_led.initialize()

    print(f"  继电器 (G16): {'✓ OK' if relay_ok else '✗ FAIL'}")
    print(f"  激光 (G13): {'✓ OK' if laser_ok else '✗ FAIL'}")
    print(f"  RGB-LED: {'✓ OK' if rgb_ok else '✗ FAIL'}")
    print()

    # 测试RGB-LED (不依赖硬件初始化)
    print("--- RGB-LED 测试 (模拟) ---")
    colors = [
        ("红色", (1.0, 0.0, 0.0)),
        ("绿色", (0.0, 1.0, 0.0)),
        ("蓝色", (0.0, 0.0, 1.0)),
        ("白色", (1.0, 1.0, 1.0)),
        ("关闭", (0.0, 0.0, 0.0)),
    ]
    for name, (r, g, b) in colors:
        print(f"  设置颜色: {name}")
        if rgb_ok:
            rgb_led.set_color(r, g, b)
        time.sleep(0.5)
    print()

    # 测试继电器
    if relay_ok:
        print("--- 继电器测试 ---")
        print("  ON...")
        relay.on()
        time.sleep(0.5)
        data = relay.read()
        print(f"  状态: {'ON' if data['data']['active'] else 'OFF'}")

        print("  OFF...")
        relay.off()
        time.sleep(0.5)
        data = relay.read()
        print(f"  状态: {'ON' if data['data']['active'] else 'OFF'}")
        print()
    else:
        print("--- 继电器: 跳过 (GPIO不可用) ---")
        print()

    # 测试激光
    if laser_ok:
        print("--- 激光测试 ---")
        print("  ON...")
        laser.on()
        time.sleep(0.5)
        data = laser.read()
        print(f"  状态: {'ON' if data['data']['active'] else 'OFF'}")

        print("  OFF...")
        laser.off()
        time.sleep(0.5)
        data = laser.read()
        print(f"  状态: {'ON' if data['data']['active'] else 'OFF'}")
        print()
    else:
        print("--- 激光: 跳过 (GPIO不可用) ---")
        print()

    # 清理
    if relay_ok:
        relay.cleanup()
    if laser_ok:
        laser.cleanup()
    if rgb_ok:
        rgb_led.cleanup()

    print("=" * 60)
    print("  测试完成!")
    print("=" * 60)
    print()
    print("提示: 如果GPIO不可用，请先运行以下命令清理:")
    print("  sudo pkill -f gpio")
    print("  sudo fuser -k /dev/gpiomem")


if __name__ == "__main__":
    main()
