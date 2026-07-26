#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""继电器执行器 - 优先使用 lgpio，降级到 RPi.GPIO"""

from typing import Dict
from drivers.actuators.base import BaseActuator, ActuatorState

try:
    import lgpio
    HAS_LGPIO = True
except ImportError:
    HAS_LGPIO = False

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class RelayActuator(BaseActuator):
    """继电器执行器"""

    def __init__(self, actuator_id: str = "relay", name: str = "继电器",
                 pin: int = 16, config: Dict = None):
        super().__init__(actuator_id, name, "relay", config)
        self.pin = pin
        self._initialized = False
        self._state = ActuatorState.OFF
        self._h = None  # lgpio 句柄

    def initialize(self) -> bool:
        if HAS_LGPIO:
            try:
                self._h = lgpio.gpiochip_open(0)
                if self._h < 0:
                    self.logger.error("lgpio chip open failed")
                    return False
                lgpio.gpio_claim_output(self._h, self.pin)
                lgpio.gpio_write(self._h, self.pin, 0)  # 默认关闭
                self._initialized = True
                self._state = ActuatorState.OFF
                self.logger.info(f"Relay initialized (lgpio): pin={self.pin}")
                return True
            except Exception as e:
                self.logger.error(f"Relay lgpio init error: {e}")
                return False
        elif HAS_GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.OUT)
                GPIO.output(self.pin, GPIO.LOW)
                self._initialized = True
                self._state = ActuatorState.OFF
                self.logger.info(f"Relay initialized (RPi.GPIO): pin={self.pin}")
                return True
            except Exception as e:
                self.logger.error(f"Relay RPi.GPIO init error: {e}")
                return False
        else:
            self.logger.warning("No GPIO library available, running in test mode")
            self._initialized = True
            self._state = ActuatorState.OFF
            return True

    def turn_on(self) -> bool:
        if not self._initialized:
            return False
            
        try:
            if HAS_LGPIO:
                lgpio.gpio_write(self._h, self.pin, 1)
            elif HAS_GPIO:
                GPIO.output(self.pin, GPIO.HIGH)
            
            self._state = ActuatorState.ON
            self.logger.info("Relay ON")
            return True
        except Exception as e:
            self.logger.error(f"Relay turn on error: {e}")
            self._state = ActuatorState.ERROR
            return False

    def turn_off(self) -> bool:
        if not self._initialized:
            return False
            
        try:
            if HAS_LGPIO:
                lgpio.gpio_write(self._h, self.pin, 0)
            elif HAS_GPIO:
                GPIO.output(self.pin, GPIO.LOW)
            
            self._state = ActuatorState.OFF
            self.logger.info("Relay OFF")
            return True
        except Exception as e:
            self.logger.error(f"Relay turn off error: {e}")
            self._state = ActuatorState.ERROR
            return False

    def cleanup(self):
        if HAS_LGPIO and self._h is not None:
            try:
                lgpio.gpio_write(self._h, self.pin, 0)
                lgpio.gpio_free(self._h, self.pin)
                lgpio.gpiochip_close(self._h)
            except:
                pass
        elif HAS_GPIO and self._initialized:
            try:
                GPIO.output(self.pin, GPIO.LOW)
                GPIO.setup(self.pin, GPIO.IN)
            except:
                pass
        self._initialized = False
