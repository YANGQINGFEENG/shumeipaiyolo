#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧农业物联网系统 - 启动入口

用法:
    python3 run.py start      # 启动系统
    python3 run.py test       # 运行测试
    python3 run.py sensors    # 读取传感器
    python3 run.py status     # 查看状态
    python3 run.py actuator   # 测试执行器
"""

import sys
import os
import argparse
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_manager import ConfigManager
from core.logger import setup_logger


def load_sensors(config):
    """根据配置加载传感器"""
    from drivers.sensors.dht import DHTSensor
    from drivers.sensors.bmp280 import BMP280Sensor
    from drivers.sensors.vibration import VibrationSensor

    sensor_map = {
        "dht": DHTSensor,
        "bmp280": BMP280Sensor,
        "vibration": VibrationSensor,
    }

    sensors = []
    for sensor_conf in config.get_sensors():
        if not sensor_conf.get("enabled", True):
            continue

        sensor_type = sensor_conf.get("type")
        if sensor_type in sensor_map:
            sensor_class = sensor_map[sensor_type]
            sensor = sensor_class(
                sensor_id=sensor_conf["id"],
                name=sensor_conf.get("name", sensor_conf["id"]),
                **sensor_conf.get("config", {})
            )
            sensors.append(sensor)

    return sensors


def load_actuators(config):
    """根据配置加载执行器"""
    from drivers.actuators.relay import RelayActuator
    from drivers.actuators.laser import LaserActuator
    from drivers.actuators.rgb_led import RGBLEDActuator

    actuator_map = {
        "relay": RelayActuator,
        "laser": LaserActuator,
        "rgb_led": RGBLEDActuator,
    }

    actuators = []
    for actuator_conf in config.get_actuators():
        if not actuator_conf.get("enabled", True):
            continue

        actuator_type = actuator_conf.get("type")
        if actuator_type in actuator_map:
            actuator_class = actuator_map[actuator_type]
            actuator = actuator_class(
                actuator_id=actuator_conf["id"],
                name=actuator_conf.get("name", actuator_conf["id"]),
                **actuator_conf.get("config", {})
            )
            actuators.append(actuator)

    return actuators


def cmd_start(args):
    """启动系统"""
    from app.system import System

    config = ConfigManager()
    system = System()

    # 加载设备
    for sensor in load_sensors(config):
        system.register_sensor(sensor)
    for actuator in load_actuators(config):
        system.register_actuator(actuator)

    system.start()


def cmd_test(args):
    """测试传感器和执行器"""
    from app.system import System

    config = ConfigManager()
    system = System()

    print("=" * 50)
    print("  设备测试")
    print("=" * 50)

    # 测试传感器
    print("\n--- 传感器测试 ---")
    for sensor in load_sensors(config):
        sensor.initialize()
        result = sensor.read()
        status = "✓" if result.get("quality") == "good" else "✗"
        print(f"  {status} {sensor.name}: {result.get('value')}")
        sensor.cleanup()

    # 测试执行器
    print("\n--- 执行器测试 ---")
    for actuator in load_actuators(config):
        actuator.initialize()
        print(f"  ✓ {actuator.name}: initialized")
        actuator.cleanup()

    print("\n" + "=" * 50)


def cmd_sensors(args):
    """读取传感器数据"""
    from app.system import System
    import json

    config = ConfigManager()
    system = System()

    print("读取传感器数据:")
    for sensor in load_sensors(config):
        sensor.initialize()
        data = sensor.read()
        print(f"  {sensor.name}: {json.dumps(data, ensure_ascii=False)}")
        sensor.cleanup()


def cmd_actuator(args):
    """测试执行器控制"""
    import time
    from app.system import System

    config = ConfigManager()
    system = System()

    print("执行器控制测试:")
    for actuator in load_actuators(config):
        actuator.initialize()
        print(f"  {actuator.name}: ON")
        actuator.turn_on()
        time.sleep(1)
        print(f"  {actuator.name}: OFF")
        actuator.turn_off()
        actuator.cleanup()


def main():
    parser = argparse.ArgumentParser(description="智慧农业物联网系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("start", help="启动系统")
    subparsers.add_parser("test", help="测试设备")
    subparsers.add_parser("sensors", help="读取传感器")
    subparsers.add_parser("actuator", help="测试执行器")

    args = parser.parse_args()

    commands = {
        "start": cmd_start,
        "test": cmd_test,
        "sensors": cmd_sensors,
        "actuator": cmd_actuator,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
