#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""激光模块"""

from sensors.base import BaseSensor

try:
    from gpiozero import OutputDevice
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class LaserSensor(BaseSensor):
    """激光模块"""

    def __init__(self, pin: int = 13, name: str = "laser"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
        self._laser = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._laser = OutputDevice(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Laser] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"pin": self.pin, "active": self._laser.is_active if self._laser else False}

    def on(self):
        if self._laser:
            self._laser.on()

    def off(self):
        if self._laser:
            self._laser.off()

    def cleanup(self):
        if self._laser:
            self._laser.close()
        super().cleanup()
