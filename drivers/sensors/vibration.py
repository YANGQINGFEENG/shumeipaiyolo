#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""振动开关传感器"""

import subprocess
import time
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
        self._retry_count = 3
        self._retry_delay = 1

    def _cleanup_gpio(self):
        """清理GPIO资源"""
        try:
            subprocess.run(["sudo", "pkill", "-9", "-f", "libgpiod"], 
                          capture_output=True, timeout=3)
            time.sleep(0.3)
        except:
            pass

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self.logger.warning("gpiozero not available, running in test mode")
            self._initialized = True
            return True

        for attempt in range(self._retry_count):
            try:
                self._cleanup_gpio()
                time.sleep(0.3)
                self._device = Button(self.pin)
                self._initialized = True
                self.logger.info(f"Vibration sensor initialized: pin={self.pin}")
                return True
            except Exception as e:
                self.logger.warning(f"Init attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    self._cleanup_gpio()
                    time.sleep(self._retry_delay)

        self.logger.error(f"Vibration init failed after {self._retry_count} attempts")
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
            try:
                self._device.close()
            except:
                pass
        self._initialized = False
