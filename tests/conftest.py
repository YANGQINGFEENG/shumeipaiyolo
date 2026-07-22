#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest fixtures
"""

import sys
import os
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sensor_hub():
    """创建SensorHub实例"""
    from sensors.base import SensorHub
    hub = SensorHub()
    yield hub
    hub.cleanup_all()


@pytest.fixture
def led_sensor():
    """创建LED传感器"""
    from sensors.digital.led import LedSensor
    sensor = LedSensor(pin=17)
    yield sensor
    sensor.cleanup()


@pytest.fixture
def ultrasonic_sensor():
    """创建超声波传感器"""
    from sensors.special.ultrasonic import UltrasonicSensor
    sensor = UltrasonicSensor(trigger=23, echo=24)
    yield sensor
    sensor.cleanup()


@pytest.fixture
def bmp280_sensor():
    """创建BMP280传感器"""
    from sensors.i2c.bmp280 import Bmp280Sensor
    sensor = Bmp280Sensor(address=0x76)
    yield sensor
    sensor.cleanup()
