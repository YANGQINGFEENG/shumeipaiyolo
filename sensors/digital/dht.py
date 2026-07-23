#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""温湿度传感器 DHT11/DHT22 - 基于 adafruit_dht"""

import time
from sensors.base import BaseSensor

try:
    import board
    import adafruit_dht
    HAS_DHT = True
except ImportError:
    HAS_DHT = False


class DhtSensor(BaseSensor):
    """温湿度传感器"""

    def __init__(self, pin: int = 6, sensor_type: str = "DHT11", name: str = "dht"):
        """
        Args:
            pin: GPIO引脚号
            sensor_type: "DHT11" 或 "DHT22"
        """
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin, "sensor_type": sensor_type})
        self.pin = pin
        self.sensor_type_str = sensor_type
        self._sensor = None

    def _get_board_pin(self):
        """获取 board 引脚对象"""
        pin_map = {
            0: board.D0, 1: board.D1, 2: board.D2, 3: board.D3,
            4: board.D4, 5: board.D5, 6: board.D6, 7: board.D7,
            8: board.D8, 9: board.D9, 10: board.D10, 11: board.D11,
            12: board.D12, 13: board.D13, 14: board.D14, 15: board.D15,
            16: board.D16, 17: board.D17, 18: board.D18, 19: board.D19,
            20: board.D20, 21: board.D21, 22: board.D22, 23: board.D23,
            24: board.D24, 25: board.D25, 26: board.D26, 27: board.D27,
        }
        return pin_map.get(self.pin, board.D6)

    def initialize(self) -> bool:
        if not HAS_DHT:
            self._initialized = True
            return True
        try:
            pin = self._get_board_pin()
            if self.sensor_type_str.upper() == "DHT22":
                self._sensor = adafruit_dht.DHT22(pin)
            else:
                self._sensor = adafruit_dht.DHT11(pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[DHT] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._sensor:
            try:
                temp = self._sensor.temperature
                hum = self._sensor.humidity
                if temp is not None and hum is not None:
                    return {
                        "temperature": round(temp, 2),
                        "humidity": round(hum, 2),
                        "unit_temp": "C",
                        "unit_hum": "%"
                    }
                else:
                    return {"temperature": None, "humidity": None, "error": "No data"}
            except RuntimeError as e:
                return {"error": str(e)}
            except Exception as e:
                return {"error": str(e)}
        return {"temperature": None, "humidity": None}

    def cleanup(self):
        if self._sensor:
            try:
                self._sensor.exit()
            except:
                pass
        super().cleanup()
