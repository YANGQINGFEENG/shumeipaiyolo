#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器测试套件
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.base import SensorHub
from sensors.digital import LedSensor, ButtonSensor, BuzzerSensor
from sensors.analog import LightSensor, PotentiometerSensor, SoundSensor
from sensors.i2c import Bmp280Sensor, Mpu6050Sensor
from sensors.special import UltrasonicSensor, Ds18b20Sensor, PirSensor


class TestLedSensor:
    def test_init(self):
        sensor = LedSensor(pin=17)
        assert sensor.name == "led_red"
        assert sensor.sensor_type == "digital"

    def test_initialize(self):
        sensor = LedSensor(pin=17)
        assert sensor.initialize() == True

    def test_read(self):
        sensor = LedSensor(pin=17)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "data" in data

    def test_brightness(self):
        sensor = LedSensor(pin=17)
        sensor.initialize()
        sensor.set_brightness(0.5)
        assert sensor.last_reading is not None


class TestUltrasonicSensor:
    def test_init(self):
        sensor = UltrasonicSensor(trigger=18, echo=17)
        assert sensor.name == "ultrasonic"

    def test_initialize(self):
        sensor = UltrasonicSensor(trigger=18, echo=17)
        assert sensor.initialize() == True

    def test_read(self):
        sensor = UltrasonicSensor(trigger=18, echo=17)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "distance_m" in data["data"]

    def test_read_range(self):
        sensor = UltrasonicSensor(trigger=18, echo=17)
        sensor.initialize()
        data = sensor.read()
        if data["status"] == "ok":
            dist = data["data"]["distance_m"]
            assert 0 <= dist <= 3.0


class TestBmp280Sensor:
    def test_init(self):
        sensor = Bmp280Sensor(address=0x76)
        assert sensor.name == "bmp280"
        assert sensor.sensor_type == "i2c"

    def test_initialize(self):
        sensor = Bmp280Sensor(address=0x76)
        assert sensor.initialize() == True

    def test_read(self):
        sensor = Bmp280Sensor(address=0x76)
        sensor.initialize()
        data = sensor.read()
        assert data["status"] == "ok"
        assert "temperature" in data["data"]
        assert "pressure" in data["data"]


class TestSensorHub:
    def test_register_and_list(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        hub.register(UltrasonicSensor(trigger=18, echo=17))
        assert "led_red" in hub.list()
        assert "ultrasonic" in hub.list()

    def test_get(self):
        hub = SensorHub()
        sensor = LedSensor(pin=17)
        hub.register(sensor)
        assert hub.get("led_red") is sensor

    def test_read_all(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        hub.register(UltrasonicSensor(trigger=18, echo=17))
        results = hub.read_all()
        assert "led_red" in results
        assert "ultrasonic" in results

    def test_test_all(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        results = hub.test_all()
        assert "led_red" in results
        assert results["led_red"]["status"] in ["ok", "fail"]

    def test_cleanup(self):
        hub = SensorHub()
        hub.register(LedSensor(pin=17))
        hub.cleanup_all()
        assert hub.get("led_red")._initialized == False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
