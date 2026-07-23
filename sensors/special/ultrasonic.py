#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超声波传感器 HC-SR04 - 基于 gpiozero.DistanceSensor"""

from sensors.base import BaseSensor

try:
    from gpiozero import DistanceSensor
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class UltrasonicSensor(BaseSensor):
    """超声波距离传感器"""

    def __init__(self, trigger: int = 18, echo: int = 17, name: str = "ultrasonic"):
        super().__init__(name=name, sensor_type="special", pin_config={"trigger": trigger, "echo": echo})
        self.trigger = trigger
        self.echo = echo
        self._sensor = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._sensor = DistanceSensor(echo=self.echo, trigger=self.trigger,
                                          max_distance=3, threshold_distance=0.2)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Ultrasonic] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._sensor:
            distance = self._sensor.distance
            return {"distance_m": round(distance, 4), "distance_cm": round(distance * 100, 1)}
        return {"distance_m": 0, "distance_cm": 0}

    def cleanup(self):
        if self._sensor:
            self._sensor.close()
        super().cleanup()
