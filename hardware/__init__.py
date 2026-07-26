#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件模块 - 智慧农业物联网硬件抽象层
"""

from hardware.core import (
    HardwareManager,
    BaseSensor,
    BaseActuator,
    ControlType,
    DeviceType,
    ControlRange,
    DeviceNode
)

from hardware.sensors import (
    DHTSensor,
    BMP280Sensor,
    VibrationSensor,
    LightSensor,
    SoilMoistureSensor
)

from hardware.actuators import (
    RelayActuator,
    MotorActuator,
    ServoActuator,
    LedActuator,
    ValveActuator
)

from hardware.network import (
    HttpClient,
    WebSocketClient,
    DataReporter,
    CommandReceiver
)

from hardware.system import HardwareSystem

__version__ = "1.0.0"

__all__ = [
    "HardwareManager",
    "BaseSensor",
    "BaseActuator",
    "ControlType",
    "DeviceType",
    "ControlRange",
    "DeviceNode",
    "DHTSensor",
    "BMP280Sensor",
    "VibrationSensor",
    "LightSensor",
    "SoilMoistureSensor",
    "RelayActuator",
    "MotorActuator",
    "ServoActuator",
    "LedActuator",
    "ValveActuator",
    "HttpClient",
    "WebSocketClient",
    "DataReporter",
    "CommandReceiver",
    "HardwareSystem"
]
