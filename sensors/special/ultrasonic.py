#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超声波传感器 / Ultrasonic Sensor (HC-SR04)
"""

from sensors.base import BaseSensor

try:
    from gpiozero import DistanceSensor
    HAS_GPIOZERO = True
except ImportError:
    HAS_GPIOZERO = False


class UltrasonicSensor(BaseSensor):
    """超声波距离传感器"""

    def __init__(self, trigger: int = 23, echo: int = 24, name: str = "ultrasonic"):
        super().__init__(
            name=name,
            sensor_type="special",
            pin_config={"trigger": trigger, "echo": echo}
        )
        self.trigger = trigger
        self.echo = echo
        self._sensor = None

    def initialize(self) -> bool:
        if not HAS_GPIOZERO:
            print("[Ultrasonic] gpiozero not available, running in test mode")
            self._initialized = True
            return True

        try:
            self._sensor = DistanceSensor(echo=self.echo, trigger=self.trigger)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Ultrasonic] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._sensor:
            distance = self._sensor.distance  # 米
            return {
                "distance": round(distance, 3),
                "unit": "m",
                "distance_cm": round(distance * 100, 1)
            }
        return {"distance": 0, "unit": "m", "distance_cm": 0}

    def cleanup(self):
        if self._sensor:
            self._sensor.close()
        super().cleanup()
