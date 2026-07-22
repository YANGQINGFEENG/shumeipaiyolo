#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LED传感器 / LED Sensor
"""

from sensors.base import BaseSensor

try:
    from gpiozero import PWMLED
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False


class LedSensor(BaseSensor):
    """LED控制"""

    def __init__(self, pin: int = 17, name: str = "led"):
        super().__init__(
            name=name,
            sensor_type="digital",
            pin_config={"pin": pin}
        )
        self.pin = pin
        self._led = None

    def initialize(self) -> bool:
        if not HAS_GPIOZERO:
            print("[LED] gpiozero not available, running in test mode")
            self._initialized = True
            return True

        try:
            self._led = PWMLED(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[LED] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {
            "pin": self.pin,
            "state": self._led.value if self._led else 0,
            "mode": "pwm"
        }

    def set_brightness(self, value: float):
        """设置亮度 (0.0 - 1.0)"""
        if self._led:
            self._led.value = max(0, min(1, value))

    def on(self):
        """点亮"""
        self.set_brightness(1.0)

    def off(self):
        """熄灭"""
        self.set_brightness(0.0)

    def cleanup(self):
        if self._led:
            self._led.close()
        super().cleanup()
