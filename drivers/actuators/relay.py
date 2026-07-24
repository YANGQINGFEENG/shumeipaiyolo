#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""继电器执行器"""

import subprocess
import time
from typing import Dict
from drivers.actuators.base import BaseActuator, ActuatorState

try:
    from gpiozero import OutputDevice
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class RelayActuator(BaseActuator):
    """继电器执行器"""

    def __init__(self, actuator_id: str = "relay", name: str = "继电器",
                 pin: int = 16, config: Dict = None):
        super().__init__(actuator_id, name, "relay", config)
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
            self._state = ActuatorState.OFF
            return True

        for attempt in range(self._retry_count):
            try:
                self._cleanup_gpio()
                time.sleep(0.3)
                self._device = OutputDevice(self.pin)
                self._initialized = True
                self._state = ActuatorState.OFF
                self.logger.info(f"Relay initialized: pin={self.pin}")
                return True
            except Exception as e:
                self.logger.warning(f"Init attempt {attempt + 1} failed: {e}")
                if attempt < self._retry_count - 1:
                    self._cleanup_gpio()
                    time.sleep(self._retry_delay)

        self.logger.error(f"Relay init failed after {self._retry_count} attempts")
        return False

    def turn_on(self) -> bool:
        if self._device:
            try:
                self._device.on()
                self._state = ActuatorState.ON
                self.logger.info("Relay ON")
                return True
            except Exception as e:
                self.logger.error(f"Turn on error: {e}")
                self._state = ActuatorState.ERROR
                return False
        self._state = ActuatorState.ON
        return True

    def turn_off(self) -> bool:
        if self._device:
            try:
                self._device.off()
                self._state = ActuatorState.OFF
                self.logger.info("Relay OFF")
                return True
            except Exception as e:
                self.logger.error(f"Turn off error: {e}")
                self._state = ActuatorState.ERROR
                return False
        self._state = ActuatorState.OFF
        return True

    def cleanup(self):
        if self._device:
            try:
                self._device.close()
            except:
                pass
        self._initialized = False
