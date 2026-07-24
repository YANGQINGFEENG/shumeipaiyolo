#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DHT11/DHT22 温湿度传感器"""

import time
import subprocess
from typing import Any, Dict
from drivers.sensors.base import BaseSensor, DataQuality

try:
    import board
    import adafruit_dht
    HAS_DHT = True
except ImportError:
    HAS_DHT = False


class DHTSensor(BaseSensor):
    """温湿度传感器"""

    def __init__(self, sensor_id: str = "dht", name: str = "温湿度传感器",
                 pin: int = 6, sensor_type: str = "DHT11", config: Dict = None):
        super().__init__(sensor_id, name, "dht", config)
        self.pin = pin
        self.dht_type = sensor_type
        self._device = None
        self._retry_count = 3
        self._retry_delay = 2

    def _get_board_pin(self):
        """获取board引脚"""
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

    def _cleanup_gpio(self):
        """清理GPIO资源"""
        try:
            subprocess.run(["sudo", "pkill", "-9", "-f", "libgpiod"], 
                          capture_output=True, timeout=3)
            time.sleep(0.5)
        except:
            pass

    def initialize(self) -> bool:
        if not HAS_DHT:
            self.logger.warning("adafruit_dht not available, running in test mode")
            self._initialized = True
            return True

        # 尝试初始化，带重试
        for attempt in range(self._retry_count):
            try:
                # 清理可能的GPIO占用
                self._cleanup_gpio()
                time.sleep(0.5)

                pin = self._get_board_pin()
                if self.dht_type.upper() == "DHT22":
                    self._device = adafruit_dht.DHT22(pin)
                else:
                    self._device = adafruit_dht.DHT11(pin)
                self._initialized = True
                self.logger.info(f"DHT initialized: pin={self.pin}, type={self.dht_type}")
                return True
            except Exception as e:
                self.logger.warning(f"Init attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    self._cleanup_gpio()
                    time.sleep(self._retry_delay)

        self.logger.error(f"DHT init failed after {self._retry_count} attempts")
        return False

    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": None, "unit": "", "quality": DataQuality.UNAVAILABLE}

        # 尝试读取，带重试
        for attempt in range(self._retry_count):
            try:
                temp = self._device.temperature
                hum = self._device.humidity

                if temp is None or hum is None:
                    if attempt < self._retry_count - 1:
                        time.sleep(1)
                        continue
                    return {"value": None, "unit": "", "quality": DataQuality.ERROR}

                # 数据校验
                if not (-40 <= temp <= 80) or not (0 <= hum <= 100):
                    return {"value": None, "unit": "", "quality": DataQuality.ERROR}

                self._last_value = {"temperature": round(temp, 2), "humidity": round(hum, 2)}
                self._last_time = __import__("datetime").datetime.now()

                return {
                    "value": self._last_value,
                    "unit": {"temperature": "°C", "humidity": "%"},
                    "quality": DataQuality.GOOD
                }
            except RuntimeError as e:
                self.logger.warning(f"Read attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    time.sleep(1)
                    continue
                return {"value": None, "unit": "", "quality": DataQuality.ERROR}
            except Exception as e:
                self.logger.error(f"Read error: {e}")
                return {"value": None, "unit": "", "quality": DataQuality.ERROR}

        return {"value": None, "unit": "", "quality": DataQuality.ERROR}

    def cleanup(self):
        if self._device:
            try:
                self._device.exit()
            except:
                pass
        self._initialized = False
