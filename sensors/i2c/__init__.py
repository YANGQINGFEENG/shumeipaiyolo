#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""I2C传感器"""
from .bmp280 import Bmp280Sensor
from .mpu6050 import Mpu6050Sensor

__all__ = ["Bmp280Sensor", "Mpu6050Sensor"]
