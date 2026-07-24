#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""传感器管理器"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sensors.base import SensorHub
from sensors.digital import (
    RgbLedSensor, RelaySensor, LaserSensor,
    VibrationSensor, DhtSensor
)
from sensors.i2c import Bmp280Sensor

logger = logging.getLogger(__name__)


def create_sensor_hub(config: dict) -> SensorHub:
    """根据配置创建传感器管理器"""
    hub = SensorHub()
    sensors_config = config.get("sensors", {})

    # RGB-LED
    if "rgb_led" in sensors_config:
        cfg = sensors_config["rgb_led"]
        hub.register(RgbLedSensor(
            red=cfg.get("red", 19),
            green=cfg.get("green", 17),
            blue=cfg.get("blue", 27),
            name="rgb_led"
        ))

    # 继电器
    if "relay" in sensors_config:
        cfg = sensors_config["relay"]
        hub.register(RelaySensor(pin=cfg.get("pin", 16), name="relay"))

    # 激光
    if "laser" in sensors_config:
        cfg = sensors_config["laser"]
        hub.register(LaserSensor(pin=cfg.get("pin", 13), name="laser"))

    # 振动开关
    if "vibration" in sensors_config:
        cfg = sensors_config["vibration"]
        hub.register(VibrationSensor(pin=cfg.get("pin", 12), name="vibration"))

    # 温湿度
    if "dht" in sensors_config:
        cfg = sensors_config["dht"]
        hub.register(DhtSensor(
            pin=cfg.get("pin", 6),
            sensor_type=cfg.get("type", "DHT11"),
            name="dht"
        ))

    # BMP280
    if "bmp280" in sensors_config:
        hub.register(Bmp280Sensor(name="bmp280"))

    return hub
