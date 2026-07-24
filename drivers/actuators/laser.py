#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""激光执行器"""

from typing import Dict
from drivers.actuators.base import BaseActuator, ActuatorState

try:
    from gpiozero import OutputDevice
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class LaserActuator(BaseActuator):
    """激光执行器"""

    def __init__(self, actuator_id: str = "laser", name: str = "激光",
                 pin: int = 13, config: Dict = None):
        super().__init__(actuator_id, name, "laser", config)
        self.pin = pin
        self._device = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self.logger.warning("gpiozero not available, running in test mode")
            self._initialized = True
            self._state = ActuatorState.OFF
            return True
        try:
            self._device = OutputDevice(self.pin)
            self._initialized = True
            self._state = ActuatorState.OFF
            self.logger.info(f"Laser initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False

    def turn_on(self) -> bool:
        if self._device:
            try:
                self._device.on()
                self._state = ActuatorState.ON
                self.logger.info("Laser ON")
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
                self.logger.info("Laser OFF")
                return True
            except Exception as e:
                self.logger.error(f"Turn off error: {e}")
                self._state = ActuatorState.ERROR
                return False
        self._state = ActuatorState.OFF
        return True

    def cleanup(self):
        if self._device:
            self._device.close()
        self._initialized = False
