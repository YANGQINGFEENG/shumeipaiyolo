#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模拟传感器"""
from .light import LightSensor
from .potentiometer import PotentiometerSensor
from .sound import SoundSensor

__all__ = ["LightSensor", "PotentiometerSensor", "SoundSensor"]
