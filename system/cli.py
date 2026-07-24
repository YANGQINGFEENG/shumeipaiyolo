#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统命令行接口

用法:
    python3 -m system start      # 启动系统
    python3 -m system stop       # 停止系统
    python3 -m system status     # 查看状态
    python3 -m system test       # 运行测试
    python3 -m system sensors    # 读取传感器
    python3 -m system actuator   # 测试执行器
"""

import sys
import os
import argparse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def cmd_start(args):
    """启动系统"""
    from system.manager import SystemManager
    from system.config import load_config

    config = load_config()
    manager = SystemManager(config)
    manager.initialize()
    manager.start()


def cmd_stop(args):
    """停止系统"""
    import subprocess
    result = subprocess.run(["pkill", "-f", "system.manager"], capture_output=True, text=True)
    if result.returncode == 0:
        print("系统已停止")
    else:
        print("系统未运行")


def cmd_status(args):
    """查看状态"""
    import requests
    config = load_config()
    server = config.get("server", {}).get("url", "http://192.168.1.22:3000")

    try:
        resp = requests.get(f"{server}/api/farms", timeout=5)
        if resp.status_code == 200:
            print(f"✓ API服务器连接正常: {server}")
        else:
            print(f"✗ API服务器返回: {resp.status_code}")
    except Exception as e:
        print(f"✗ API服务器连接失败: {e}")


def cmd_test(args):
    """运行测试"""
    from system.config import load_config
    from system.hub import create_sensor_hub

    config = load_config()
    hub = create_sensor_hub(config)

    print("传感器测试:")
    results = hub.test_all()
    for name, result in results.items():
        status = "✓" if result["status"] == "ok" else "✗"
        print(f"  {status} {name}")

    hub.cleanup_all()


def cmd_sensors(args):
    """读取传感器数据"""
    from system.config import load_config
    from system.hub import create_sensor_hub
    import json

    config = load_config()
    hub = create_sensor_hub(config)

    readings = hub.read_all()
    print(json.dumps(readings, indent=2, default=str))

    hub.cleanup_all()


def cmd_actuator(args):
    """测试执行器"""
    from system.config import load_config
    from system.hub import create_sensor_hub

    config = load_config()
    hub = create_sensor_hub(config)

    print("执行器测试:")
    for name in ["relay", "laser", "rgb_led"]:
        device = hub.get(name)
        if device:
            device.initialize()
            print(f"  {name}: OK")
            device.cleanup()
        else:
            print(f"  {name}: 未配置")


def main():
    parser = argparse.ArgumentParser(description="智慧农业物联网系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("start", help="启动系统")
    subparsers.add_parser("stop", help="停止系统")
    subparsers.add_parser("status", help="查看状态")
    subparsers.add_parser("test", help="运行测试")
    subparsers.add_parser("sensors", help="读取传感器")
    subparsers.add_parser("actuator", help="测试执行器")

    args = parser.parse_args()

    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
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
