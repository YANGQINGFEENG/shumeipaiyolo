#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMP280 气压传感器 - 使用 adafruit_bmp280 库
"""

from sensors.base import BaseSensor

try:
    import board
    import adafruit_bmp280
    HAS_BMP = True
except ImportError:
    HAS_BMP = False


class Bmp280Sensor(BaseSensor):
    """BMP280 气压温度传感器"""

    def __init__(self, name: str = "bmp280"):
        super().__init__(name=name, sensor_type="i2c", pin_config={})
        self._sensor = None

    def initialize(self) -> bool:
        if not HAS_BMP:
            self._initialized = True
            return True
        try:
            i2c = board.I2C()
            self._sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)
            self._sensor.sea_level_pressure = 1013.25
            self._initialized = True
            return True
        except Exception as e:
            print(f"[BMP280] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._sensor:
            try:
                temp = self._sensor.temperature
                press = self._sensor.pressure
                alt = self._sensor.altitude
                return {
                    "temperature": round(temp, 2),
                    "pressure": round(press, 2),
                    "altitude": round(alt, 2),
                    "unit_temp": "C",
                    "unit_press": "hPa"
                }
            except Exception as e:
                return {"error": str(e)}
        return {"temperature": 0, "pressure": 0, "altitude": 0}

    def cleanup(self):
        self._sensor = None
        super().cleanup()
