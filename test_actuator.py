#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器控制测试 - 模拟服务器下发控制指令
"""

import sys
import os
import time

sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor')

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

    relay.initialize()
    laser.initialize()
    rgb_led.initialize()

    print("✓ 继电器 (G16)")
    print("✓ 激光 (G13)")
    print("✓ RGB-LED (R=19, G=17, B=27)")
    print()

    # 测试控制
    try:
        # 测试1: 继电器开关
        print("--- 测试1: 继电器控制 ---")
        print("继电器 ON...")
        relay.on()
        time.sleep(1)
        print(f"  状态: {'ON' if relay.read()['data']['active'] else 'OFF'}")

        print("继电器 OFF...")
        relay.off()
        time.sleep(1)
        print(f"  状态: {'ON' if relay.read()['data']['active'] else 'OFF'}")
        print()

        # 测试2: 激光开关
        print("--- 测试2: 激光控制 ---")
        print("激光 ON...")
        laser.on()
        time.sleep(1)
        print(f"  状态: {'ON' if laser.read()['data']['active'] else 'OFF'}")

        print("激光 OFF...")
        laser.off()
        time.sleep(1)
        print(f"  状态: {'ON' if laser.read()['data']['active'] else 'OFF'}")
        print()

        # 测试3: RGB-LED颜色
        print("--- 测试3: RGB-LED颜色控制 ---")

        print("红色...")
        rgb_led.set_color(1.0, 0.0, 0.0)
        time.sleep(1)

        print("绿色...")
        rgb_led.set_color(0.0, 1.0, 0.0)
        time.sleep(1)

        print("蓝色...")
        rgb_led.set_color(0.0, 0.0, 1.0)
        time.sleep(1)

        print("白色...")
        rgb_led.set_color(1.0, 1.0, 1.0)
        time.sleep(1)

        print("关闭...")
        rgb_led.set_color(0.0, 0.0, 0.0)
        time.sleep(1)
        print()

        # 测试4: 组合控制
        print("--- 测试4: 组合控制序列 ---")
        for i in range(3):
            print(f"  第{i+1}轮: 继电器ON + 激光ON + 红色LED")
            relay.on()
            laser.on()
            rgb_led.set_color(1.0, 0.0, 0.0)
            time.sleep(0.5)

            print(f"  第{i+1}轮: 继电器OFF + 激光OFF + 绿色LED")
            relay.off()
            laser.off()
            rgb_led.set_color(0.0, 1.0, 0.0)
            time.sleep(0.5)

        # 最终关闭
        relay.off()
        laser.off()
        rgb_led.set_color(0.0, 0.0, 0.0)

        print()
        print("=" * 60)
        print("  所有测试完成!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        relay.cleanup()
        laser.cleanup()
        rgb_led.cleanup()
        print("执行器已清理")


if __name__ == "__main__":
    main()
