#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RGB-LED 执行器"""

from typing import Dict
from drivers.actuators.base import BaseActuator, ActuatorState

try:
    from gpiozero import RGBLED
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class RGBLEDActuator(BaseActuator):
    """RGB-LED 执行器"""

    def __init__(self, actuator_id: str = "rgb_led", name: str = "RGB-LED",
                 red: int = 19, green: int = 17, blue: int = 27,
                 config: Dict = None):
        super().__init__(actuator_id, name, "rgb_led", config)
        self.red_pin = red
        self.green_pin = green
        self.blue_pin = blue
        self._device = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self.logger.warning("gpiozero not available, running in test mode")
            self._initialized = True
            self._state = ActuatorState.OFF
            return True
        try:
            self._device = RGBLED(red=self.red_pin, green=self.green_pin, blue=self.blue_pin)
            self._initialized = True
            self._state = ActuatorState.OFF
            self.logger.info(f"RGB-LED initialized: R={self.red_pin}, G={self.green_pin}, B={self.blue_pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False

    def set_color(self, r: float, g: float, b: float):
        """设置颜色 (0.0-1.0)"""
        if self._device:
            self._device.red = max(0.0, min(1.0, r))
            self._device.green = max(0.0, min(1.0, g))
            self._device.blue = max(0.0, min(1.0, b))

    def turn_on(self) -> bool:
        """打开 (白色)"""
        return self.set_color(1.0, 1.0, 1.0) or True

    def turn_off(self) -> bool:
        """关闭"""
        if self._device:
            self._device.close()
        self._state = ActuatorState.OFF
        return True

    def execute_command(self, command: str) -> bool:
        """执行控制命令，支持颜色设置"""
        command = command.lower().strip()

        color_map = {
            "red": (1.0, 0.0, 0.0),
            "green": (0.0, 1.0, 0.0),
            "blue": (0.0, 0.0, 1.0),
            "white": (1.0, 1.0, 1.0),
            "yellow": (1.0, 1.0, 0.0),
            "cyan": (0.0, 1.0, 1.0),
            "magenta": (1.0, 0.0, 1.0),
        }

        if command in color_map:
            r, g, b = color_map[command]
            self.set_color(r, g, b)
            self._state = ActuatorState.ON
            self.logger.info(f"RGB-LED color: {command}")
            return True
        elif command == "on":
            return self.turn_on()
        elif command == "off":
            return self.turn_off()
        else:
            return super().execute_command(command)

    def cleanup(self):
        if self._device:
            self._device.close()
        self._initialized = False
