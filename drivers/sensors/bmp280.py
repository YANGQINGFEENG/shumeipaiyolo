#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BMP280 气压温度传感器"""

from typing import Any, Dict
from drivers.sensors.base import BaseSensor, DataQuality

try:
    import board
    import adafruit_bmp280
    HAS_BMP = True
except ImportError:
    HAS_BMP = False


class BMP280Sensor(BaseSensor):
    """BMP280 气压温度传感器"""

    def __init__(self, sensor_id: str = "bmp280", name: str = "气压传感器",
                 address: int = 0x76, sea_level_pressure: float = 1013.25,
                 config: Dict = None):
        super().__init__(sensor_id, name, "bmp280", config)
        self.address = address
        self.sea_level_pressure = sea_level_pressure
        self._device = None

    def initialize(self) -> bool:
        if not HAS_BMP:
            self.logger.warning("adafruit_bmp280 not available, running in test mode")
            self._initialized = True
            return True
        try:
            i2c = board.I2C()
            self._device = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=self.address)
            self._device.sea_level_pressure = self.sea_level_pressure
            self._initialized = True
            self.logger.info(f"BMP280 initialized: address=0x{self.address:02X}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False

    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": None, "unit": "", "quality": DataQuality.UNAVAILABLE}

        try:
            temp = self._device.temperature
            press = self._device.pressure
            alt = self._device.altitude

            # 数据校验
            if not (-40 <= temp <= 85) or not (300 <= press <= 1100):
                return {"value": None, "unit": "", "quality": DataQuality.ERROR}

            self._last_value = {
                "temperature": round(temp, 2),
                "pressure": round(press, 2),
                "altitude": round(alt, 2)
            }

            return {
                "value": self._last_value,
                "unit": {"temperature": "°C", "pressure": "hPa", "altitude": "m"},
                "quality": DataQuality.GOOD
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": DataQuality.ERROR}

    def cleanup(self):
        self._device = None
        self._initialized = False
