#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.base import SensorHub
from sensors.digital.led import LedSensor
from sensors.special.ultrasonic import UltrasonicSensor
from sensors.i2c.bmp280 import Bmp280Sensor


class TestLedSensor:
    """LED传感器测试"""

    def test_init(self):
        sensor = LedSensor(pin=17)
        assert sensor.name == "led"
        assert sensor.sensor_type == "digital"

    def test_initialize(self):
        sensor = LedSensor(pin=17)
        result = sensor.initialize()
        assert result == True

    def test_read(self):
        sensor = LedSensor(pin=17)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "data" in data

    def test_set_brightness(self):
        sensor = LedSensor(pin=17)
        sensor.initialize()
        sensor.set_brightness(0.5)
        assert sensor.last_reading is not None

    def test_cleanup(self):
        sensor = LedSensor(pin=17)
        sensor.initialize()
        sensor.cleanup()
        assert sensor._initialized == False


class TestUltrasonicSensor:
    """超声波传感器测试"""

    def test_init(self):
        sensor = UltrasonicSensor(trigger=23, echo=24)
        assert sensor.name == "ultrasonic"
        assert sensor.sensor_type == "special"

    def test_initialize(self):
        sensor = UltrasonicSensor(trigger=23, echo=24)
        result = sensor.initialize()
        assert result == True

    def test_read(self):
        sensor = UltrasonicSensor(trigger=23, echo=24)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "distance" in data["data"]

    def test_read_range(self):
        sensor = UltrasonicSensor(trigger=23, echo=24)
        sensor.initialize()
        data = sensor.read()
        if data["status"] == "ok":
            distance = data["data"]["distance"]
            assert 0 <= distance <= 4.0  # HC-SR04有效范围0-4米


class TestBmp280Sensor:
    """BMP280传感器测试"""

    def test_init(self):
        sensor = Bmp280Sensor(address=0x76)
        assert sensor.name == "bmp280"
        assert sensor.sensor_type == "i2c"

    def test_initialize(self):
        sensor = Bmp280Sensor(address=0x76)
        result = sensor.initialize()
        assert result == True

    def test_read(self):
        sensor = Bmp280Sensor(address=0x76)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "temperature" in data["data"]
        assert "pressure" in data["data"]

    def test_temperature_range(self):
        sensor = Bmp280Sensor(address=0x76)
        sensor.initialize()
        data = sensor.read()
        if data["status"] == "ok":
            temp = data["data"]["temperature"]
            assert -40 <= temp <= 85  # BMP280有效范围

    def test_pressure_range(self):
        sensor = Bmp280Sensor(address=0x76)
        sensor.initialize()
        data = sensor.read()
        if data["status"] == "ok":
            press = data["data"]["pressure"]
            assert 300 <= press <= 1100  # BMP280有效范围 (hPa)


class TestSensorHub:
    """传感器管理器测试"""

    def test_register(self):
        hub = SensorHub()
        sensor = LedSensor(pin=17)
        hub.register(sensor)
        assert "led" in hub.list()

    def test_get(self):
        hub = SensorHub()
        sensor = LedSensor(pin=17)
        hub.register(sensor)
        assert hub.get("led") is sensor

    def test_read_all(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        hub.register(UltrasonicSensor(trigger=23, echo=24))
        results = hub.read_all()
        assert "led" in results
        assert "ultrasonic" in results

    def test_test_all(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        results = hub.test_all()
        assert "led" in results
        assert results["led"]["status"] in ["ok", "fail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
