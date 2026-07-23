#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""温湿度传感器 DHT11/DHT22"""

from sensors.base import BaseSensor

try:
    import adafruit_dht
    import board
    HAS_DHT = True
except ImportError:
    HAS_DHT = False


class DhtSensor(BaseSensor):
    """温湿度传感器"""

    def __init__(self, pin: int = 6, name: str = "dht"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
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
            self._sensor = adafruit_dht.DHT22(self._get_board_pin())
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
                return {
                    "temperature": round(temp, 2) if temp else None,
                    "humidity": round(hum, 2) if hum else None,
                    "unit_temp": "C",
                    "unit_hum": "%"
                }
            except Exception as e:
                return {"error": str(e)}
        return {"temperature": 0, "humidity": 0}

    def cleanup(self):
        if self._sensor:
            self._sensor.exit()
        super().cleanup()
