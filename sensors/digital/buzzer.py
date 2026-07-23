#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蜂鸣器 - 基于 gpiozero"""

from sensors.base import BaseSensor

try:
    from gpiozero import Buzzer
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class BuzzerSensor(BaseSensor):
    """蜂鸣器"""

    def __init__(self, pin: int = 22, name: str = "buzzer"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
        self._buzzer = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._buzzer = Buzzer(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Buzzer] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"pin": self.pin, "active": self._buzzer.is_active if self._buzzer else False}

    def on(self):
        if self._buzzer:
            self._buzzer.on()

    def off(self):
        if self._buzzer:
            self._buzzer.off()

    def cleanup(self):
        if self._buzzer:
            self._buzzer.close()
        super().cleanup()
