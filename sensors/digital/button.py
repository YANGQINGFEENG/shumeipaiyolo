#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按键传感器 - 基于 gpiozero.Button"""

from sensors.base import BaseSensor

try:
    from gpiozero import Button
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class ButtonSensor(BaseSensor):
    """轻触按键"""

    def __init__(self, pin: int = 24, name: str = "button"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
        self._btn = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._btn = Button(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Button] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"pin": self.pin, "pressed": self._btn.is_pressed if self._btn else False}

    def cleanup(self):
        if self._btn:
            self._btn.close()
        super().cleanup()
