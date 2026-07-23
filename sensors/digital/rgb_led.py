#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RGB-LED 模块 - 共阴 RGB LED"""

from sensors.base import BaseSensor

try:
    from gpiozero import RGBLED
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class RgbLedSensor(BaseSensor):
    """RGB LED 模块 (共阴)"""

    def __init__(self, red: int = 19, green: int = 17, blue: int = 27, name: str = "rgb_led"):
        super().__init__(name=name, sensor_type="digital",
                         pin_config={"red": red, "green": green, "blue": blue})
        self.red_pin = red
        self.green_pin = green
        self.blue_pin = blue
        self._led = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._led = RGBLED(red=self.red_pin, green=self.green_pin, blue=self.blue_pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[RGB-LED] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._led:
            return {
                "red": round(self._led.red, 4),
                "green": round(self._led.green, 4),
                "blue": round(self._led.blue, 4)
            }
        return {"red": 0, "green": 0, "blue": 0}

    def set_color(self, r: float, g: float, b: float):
        """设置颜色 (0.0-1.0)"""
        if self._led:
            self._led.red = max(0.0, min(1.0, r))
            self._led.green = max(0.0, min(1.0, g))
            self._led.blue = max(0.0, min(1.0, b))

    def on(self, r: float = 1.0, g: float = 1.0, b: float = 1.0):
        self.set_color(r, g, b)

    def off(self):
        if self._led:
            self._led.close()

    def cleanup(self):
        if self._led:
            self._led.close()
        super().cleanup()
