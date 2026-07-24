#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""振动开关传感器"""

from typing import Any, Dict
from drivers.sensors.base import BaseSensor, DataQuality

try:
    from gpiozero import Button
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class VibrationSensor(BaseSensor):
    """振动开关传感器"""

    def __init__(self, sensor_id: str = "vibration", name: str = "振动传感器",
                 pin: int = 12, config: Dict = None):
        super().__init__(sensor_id, name, "vibration", config)
        self.pin = pin
        self._device = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self.logger.warning("gpiozero not available, running in test mode")
            self._initialized = True
            return True
        try:
            self._device = Button(self.pin)
            self._initialized = True
            self.logger.info(f"Vibration sensor initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False

    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": False, "unit": "", "quality": DataQuality.UNAVAILABLE}

        try:
            vibrating = self._device.is_pressed
            self._last_value = vibrating
            return {
                "value": vibrating,
                "unit": "",
                "quality": DataQuality.GOOD
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": DataQuality.ERROR}

    def cleanup(self):
        if self._device:
            self._device.close()
        self._initialized = False
