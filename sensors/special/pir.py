#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PIR 人体感应传感器 - 基于 gpiozero.MotionSensor"""

from sensors.base import BaseSensor

try:
    from gpiozero import MotionSensor
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class PirSensor(BaseSensor):
    """PIR人体热释电感应"""

    def __init__(self, pin: int = 17, name: str = "pir"):
        super().__init__(name=name, sensor_type="special", pin_config={"pin": pin})
        self.pin = pin
        self._sensor = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._sensor = MotionSensor(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[PIR] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._sensor:
            return {"motion": self._sensor.motion_detected}
        return {"motion": False}

    def cleanup(self):
        if self._sensor:
            self._sensor.close()
        super().cleanup()
