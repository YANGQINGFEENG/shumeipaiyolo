#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""继电器模块"""

from sensors.base import BaseSensor

try:
    from gpiozero import OutputDevice
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class RelaySensor(BaseSensor):
    """继电器模块"""

    def __init__(self, pin: int = 16, name: str = "relay"):
        super().__init__(name=name, sensor_type="digital", pin_config={"pin": pin})
        self.pin = pin
        self._relay = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._relay = OutputDevice(self.pin)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Relay] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"pin": self.pin, "active": self._relay.is_active if self._relay else False}

    def on(self):
        if self._relay:
            self._relay.on()

    def off(self):
        if self._relay:
            self._relay.off()

    def cleanup(self):
        if self._relay:
            self._relay.close()
        super().cleanup()
