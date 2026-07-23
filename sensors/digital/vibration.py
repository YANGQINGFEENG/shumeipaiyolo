#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""振动开关传感器"""

from sensors.base import BaseSensor

try:
    from gpiozero import Button
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class VibrationSensor(BaseSensor):
    """振动开关传感器"""

    def __init__(self, pin: int = 12, name: str = "vibration"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
        self._sensor = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._sensor = Button(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Vibration] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"pin": self.pin, "vibrating": self._sensor.is_pressed if self._sensor else False}

    def cleanup(self):
        if self._sensor:
            self._sensor.close()
        super().cleanup()
