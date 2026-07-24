#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统配置"""

import os
import yaml


def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


# 默认配置
DEFAULT_CONFIG = {
    "server": {
        "url": "http://192.168.1.22:3000",
        "farm_id": 1
    },
    "device": {
        "gateway_ip": "192.168.1.63",
        "gateway_type": "wifi_sensor",
        "mac": "AA:BB:CC:DD:EE:FF"
    },
    "sensors": {
        "rgb_led": {"red": 19, "green": 17, "blue": 27},
        "relay": {"pin": 16},
        "laser": {"pin": 13},
        "vibration": {"pin": 12},
        "dht": {"pin": 6, "type": "DHT11"},
        "bmp280": {}
    },
    "intervals": {
        "upload": 30,
        "poll": 10
    }
}
