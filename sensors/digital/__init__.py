#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数字传感器"""
from .led import LedSensor
from .button import ButtonSensor
from .buzzer import BuzzerSensor
from .rgb_led import RgbLedSensor
from .relay import RelaySensor
from .laser import LaserSensor
from .vibration import VibrationSensor
from .dht import DhtSensor

__all__ = [
    "LedSensor", "ButtonSensor", "BuzzerSensor",
    "RgbLedSensor", "RelaySensor", "LaserSensor",
    "VibrationSensor", "DhtSensor"
]
