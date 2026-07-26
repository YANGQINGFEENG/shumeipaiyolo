#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RGB-LED 执行器 - 优先使用 lgpio，降级到 RPi.GPIO"""

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


class RGBLEDActuator(BaseActuator):
    """RGB-LED 执行器"""

    def __init__(self, actuator_id: str = "rgb_led", name: str = "RGB-LED",
                 red: int = 19, green: int = 17, blue: int = 27,
                 config: Dict = None):
        super().__init__(actuator_id, name, "rgb_led", config)
        self.red_pin = red
        self.green_pin = green
        self.blue_pin = blue
        self._initialized = False
        self._state = ActuatorState.OFF
        self._h = None  # lgpio 句柄
        # RPi.GPIO PWM 对象
        self._red_pwm = None
        self._green_pwm = None
        self._blue_pwm = None

    def initialize(self) -> bool:
        if HAS_LGPIO:
            try:
                self._h = lgpio.gpiochip_open(0)
                if self._h < 0:
                    self.logger.error("lgpio chip open failed")
                    return False
                
                # 设置为输出模式（使用简单开关控制，不使用 PWM）
                lgpio.gpio_claim_output(self._h, self.red_pin)
                lgpio.gpio_claim_output(self._h, self.green_pin)
                lgpio.gpio_claim_output(self._h, self.blue_pin)
                
                # 初始化为关闭状态
                lgpio.gpio_write(self._h, self.red_pin, 0)
                lgpio.gpio_write(self._h, self.green_pin, 0)
                lgpio.gpio_write(self._h, self.blue_pin, 0)
                
                self._initialized = True
                self._state = ActuatorState.OFF
                self.logger.info(f"RGB-LED initialized (lgpio): R={self.red_pin}, G={self.green_pin}, B={self.blue_pin}")
                return True
            except Exception as e:
                self.logger.error(f"RGB-LED lgpio init error: {e}")
                return False
        elif HAS_GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.red_pin, GPIO.OUT)
                GPIO.setup(self.green_pin, GPIO.OUT)
                GPIO.setup(self.blue_pin, GPIO.OUT)
                
                # 创建 PWM 对象（频率 100Hz）
                self._red_pwm = GPIO.PWM(self.red_pin, 100)
                self._green_pwm = GPIO.PWM(self.green_pin, 100)
                self._blue_pwm = GPIO.PWM(self.blue_pin, 100)
                
                # 初始化为关闭状态
                self._red_pwm.start(0)
                self._green_pwm.start(0)
                self._blue_pwm.start(0)
                
                self._initialized = True
                self._state = ActuatorState.OFF
                self.logger.info(f"RGB-LED initialized (RPi.GPIO): R={self.red_pin}, G={self.green_pin}, B={self.blue_pin}")
                return True
            except Exception as e:
                self.logger.error(f"RGB-LED RPi.GPIO init error: {e}")
                return False
        else:
            self.logger.warning("No GPIO library available, running in test mode")
            self._initialized = True
            self._state = ActuatorState.OFF
            return True

    def set_color(self, r: float, g: float, b: float):
        """设置颜色 (0.0-1.0)"""
        if not self._initialized:
            return
            
        try:
            # 简单开关控制：阈值 > 0.5 为亮，否则为灭
            r_on = 1 if r > 0.5 else 0
            g_on = 1 if g > 0.5 else 0
            b_on = 1 if b > 0.5 else 0
            
            if HAS_LGPIO:
                lgpio.gpio_write(self._h, self.red_pin, r_on)
                lgpio.gpio_write(self._h, self.green_pin, g_on)
                lgpio.gpio_write(self._h, self.blue_pin, b_on)
            elif HAS_GPIO:
                self._red_pwm.ChangeDutyCycle(int(max(0.0, min(1.0, r)) * 100))
                self._green_pwm.ChangeDutyCycle(int(max(0.0, min(1.0, g)) * 100))
                self._blue_pwm.ChangeDutyCycle(int(max(0.0, min(1.0, b)) * 100))
        except Exception as e:
            self.logger.error(f"RGB-LED set color error: {e}")

    def turn_on(self) -> bool:
        """打开 (白色)"""
        try:
            self.set_color(1.0, 1.0, 1.0)
            self._state = ActuatorState.ON
            self.logger.info("RGB-LED ON (white)")
            return True
        except Exception as e:
            self.logger.error(f"RGB-LED turn on error: {e}")
            self._state = ActuatorState.ERROR
            return False

    def turn_off(self) -> bool:
        """关闭 (熄灭所有颜色)"""
        try:
            self.set_color(0.0, 0.0, 0.0)
            self._state = ActuatorState.OFF
            self.logger.info("RGB-LED OFF")
            return True
        except Exception as e:
            self.logger.error(f"RGB-LED turn off error: {e}")
            self._state = ActuatorState.ERROR
            return False

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
        if HAS_LGPIO and self._h is not None:
            try:
                lgpio.gpio_write(self._h, self.red_pin, 0)
                lgpio.gpio_write(self._h, self.green_pin, 0)
                lgpio.gpio_write(self._h, self.blue_pin, 0)
                lgpio.gpio_free(self._h, self.red_pin)
                lgpio.gpio_free(self._h, self.green_pin)
                lgpio.gpio_free(self._h, self.blue_pin)
                lgpio.gpiochip_close(self._h)
            except:
                pass
        elif HAS_GPIO and self._initialized:
            try:
                self.set_color(0.0, 0.0, 0.0)
                self._red_pwm.stop()
                self._green_pwm.stop()
                self._blue_pwm.stop()
                GPIO.setup(self.red_pin, GPIO.IN)
                GPIO.setup(self.green_pin, GPIO.IN)
                GPIO.setup(self.blue_pin, GPIO.IN)
            except:
                pass
        self._initialized = False
