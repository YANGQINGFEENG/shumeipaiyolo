#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器实现
"""

import time
import logging
from typing import Any, Dict
from hardware.core import BaseActuator, ControlRange

logger = logging.getLogger(__name__)


class RelayActuator(BaseActuator):
    """继电器执行器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 16):
        super().__init__(
            node_id=node_id,
            name=name,
            actuator_type="relay",
            control_type="boolean",
            control_range=ControlRange(min_value=0, max_value=1, step=1, default=0)
        )
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import OutputDevice
            self._device = OutputDevice(self.pin)
            self.logger.info(f"Relay initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def execute_command(self, command: str, control_value: float = None) -> bool:
        try:
            if command == "on":
                if self._device:
                    self._device.on()
                self._state = "on"
                self._control_value = 1
            elif command == "off":
                if self._device:
                    self._device.off()
                self._state = "off"
                self._control_value = 0
            else:
                return False
            
            self._last_update = datetime.now()
            self.logger.info(f"Relay {command}")
            return True
        except Exception as e:
            self.logger.error(f"Execute error: {e}")
            return False
    
    def cleanup(self):
        if self._device:
            self._device.close()


class MotorActuator(BaseActuator):
    """电机执行器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 18):
        super().__init__(
            node_id=node_id,
            name=name,
            actuator_type="motor",
            control_type="integer",
            control_range=ControlRange(min_value=0, max_value=100, step=5, default=0)
        )
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import PWMOutputDevice
            self._device = PWMOutputDevice(self.pin)
            self.logger.info(f"Motor initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def execute_command(self, command: str, control_value: float = None) -> bool:
        try:
            if command == "on":
                speed = control_value if control_value is not None else 100
                if self._device:
                    self._device.value = speed / 100.0
                self._state = "on"
                self._control_value = speed
            elif command == "off":
                if self._device:
                    self._device.value = 0
                self._state = "off"
                self._control_value = 0
            elif command == "value":
                if control_value is not None:
                    if self._device:
                        self._device.value = control_value / 100.0
                    self._control_value = control_value
                    self._state = "on" if control_value > 0 else "off"
                else:
                    return False
            else:
                return False
            
            self._last_update = datetime.now()
            self.logger.info(f"Motor: command={command}, value={self._control_value}")
            return True
        except Exception as e:
            self.logger.error(f"Execute error: {e}")
            return False
    
    def cleanup(self):
        if self._device:
            self._device.close()


class ServoActuator(BaseActuator):
    """舵机执行器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 23):
        super().__init__(
            node_id=node_id,
            name=name,
            actuator_type="servo",
            control_type="angle",
            control_range=ControlRange(min_value=0, max_value=180, step=1, default=90)
        )
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import Servo
            self._device = Servo(self.pin, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
            self.logger.info(f"Servo initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def execute_command(self, command: str, control_value: float = None) -> bool:
        try:
            if command == "value" and control_value is not None:
                angle = max(0, min(180, control_value))
                if self._device:
                    self._device.value = (angle - 90) / 90.0
                self._control_value = angle
                self._state = "on"
            elif command == "on":
                if self._device:
                    self._device.value = 0
                self._control_value = 90
                self._state = "on"
            elif command == "off":
                if self._device:
                    self._device.value = 0
                self._control_value = 0
                self._state = "off"
            else:
                return False
            
            self._last_update = datetime.now()
            self.logger.info(f"Servo: angle={self._control_value}")
            return True
        except Exception as e:
            self.logger.error(f"Execute error: {e}")
            return False
    
    def cleanup(self):
        if self._device:
            self._device.close()


class LedActuator(BaseActuator):
    """LED执行器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 24):
        super().__init__(
            node_id=node_id,
            name=name,
            actuator_type="led",
            control_type="boolean",
            control_range=ControlRange(min_value=0, max_value=1, step=1, default=0)
        )
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import LED
            self._device = LED(self.pin)
            self.logger.info(f"LED initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def execute_command(self, command: str, control_value: float = None) -> bool:
        try:
            if command == "on":
                if self._device:
                    self._device.on()
                self._state = "on"
                self._control_value = 1
            elif command == "off":
                if self._device:
                    self._device.off()
                self._state = "off"
                self._control_value = 0
            else:
                return False
            
            self._last_update = datetime.now()
            self.logger.info(f"LED {command}")
            return True
        except Exception as e:
            self.logger.error(f"Execute error: {e}")
            return False
    
    def cleanup(self):
        if self._device:
            self._device.close()


class ValveActuator(BaseActuator):
    """电磁阀执行器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 25):
        super().__init__(
            node_id=node_id,
            name=name,
            actuator_type="valve",
            control_type="boolean",
            control_range=ControlRange(min_value=0, max_value=1, step=1, default=0)
        )
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import OutputDevice
            self._device = OutputDevice(self.pin)
            self.logger.info(f"Valve initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def execute_command(self, command: str, control_value: float = None) -> bool:
        try:
            if command == "on":
                if self._device:
                    self._device.on()
                self._state = "on"
                self._control_value = 1
            elif command == "off":
                if self._device:
                    self._device.off()
                self._state = "off"
                self._control_value = 0
            else:
                return False
            
            self._last_update = datetime.now()
            self.logger.info(f"Valve {command}")
            return True
        except Exception as e:
            self.logger.error(f"Execute error: {e}")
            return False
    
    def cleanup(self):
        if self._device:
            self._device.close()
