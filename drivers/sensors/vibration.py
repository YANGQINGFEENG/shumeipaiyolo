#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""振动传感器 - 使用 lgpio 实现，参考程序案例逻辑"""

from datetime import datetime
from typing import Any, Dict
from drivers.sensors.base import BaseSensor, DataQuality

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


class VibrationSensor(BaseSensor):
    """振动传感器 - 参考程序案例逻辑"""

    def __init__(self, sensor_id: str = "vibration", name: str = "振动传感器",
                 pin: int = 12, config: Dict = None):
        super().__init__(sensor_id, name, "vibration", config)
        self.pin = pin
        self._initialized = False
        self._h = None  # lgpio 句柄

    def initialize(self) -> bool:
        """初始化传感器（参考程序案例：使用上拉电阻）"""
        if HAS_LGPIO:
            try:
                self._h = lgpio.gpiochip_open(0)
                if self._h < 0:
                    self.logger.error("lgpio chip open failed")
                    return False
                # 使用上拉电阻，振动时引脚变低
                lgpio.gpio_claim_input(self._h, self.pin, 2)  # 2 = LGPIO_PULL_UP
                self._initialized = True
                self.logger.info(f"Vibration sensor initialized (lgpio): pin={self.pin}")
                return True
            except Exception as e:
                self.logger.error(f"Vibration lgpio init error: {e}")
                return False
        elif HAS_GPIO:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self._initialized = True
                self.logger.info(f"Vibration sensor initialized (RPi.GPIO): pin={self.pin}")
                return True
            except Exception as e:
                self.logger.error(f"Vibration RPi.GPIO init error: {e}")
                return False
        else:
            self.logger.warning("No GPIO library available, running in test mode")
            self._initialized = True
            return True

    def read(self) -> Dict[str, Any]:
        """读取振动状态（参考程序案例：振动时引脚变低）"""
        if not self._initialized:
            return {"value": None, "unit": "", "quality": DataQuality.UNAVAILABLE}

        try:
            vibrating = False
            
            if HAS_LGPIO and self._h is not None:
                # 振动传感器触发时，引脚变低
                vibrating = lgpio.gpio_read(self._h, self.pin) == 0
            elif HAS_GPIO:
                vibrating = GPIO.input(self.pin) == GPIO.LOW
            
            self._last_value = vibrating
            self._last_time = datetime.now()

            return {
                "value": vibrating,
                "unit": "",
                "quality": DataQuality.GOOD
            }
        except Exception as e:
            self.logger.error(f"Vibration read error: {e}")
            return {"value": None, "unit": "", "quality": DataQuality.ERROR}

    def cleanup(self):
        """释放资源"""
        if HAS_LGPIO and self._h is not None:
            try:
                lgpio.gpio_free(self._h, self.pin)
                lgpio.gpiochip_close(self._h)
            except:
                pass
        elif HAS_GPIO and self._initialized:
            try:
                GPIO.setup(self.pin, GPIO.IN)
            except:
                pass
        self._initialized = False
