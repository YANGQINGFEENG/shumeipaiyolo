#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件核心模块 - 统一硬件抽象层
"""

import time
import json
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ControlType(Enum):
    """控制类型枚举"""
    BOOLEAN = "boolean"  # 布尔值控制 (on/off)
    INTEGER = "integer"  # 整数值控制 (0-100)
    ANGLE = "angle"      # 角度控制 (0-180/360)
    FLOAT = "float"      # 浮点值控制
    STRING = "string"    # 字符串指令


class DeviceType(Enum):
    """设备类型枚举"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"


@dataclass
class ControlRange:
    """控制范围配置"""
    min_value: float = 0
    max_value: float = 100
    step: float = 1
    default: float = 0


@dataclass
class DeviceNode:
    """设备节点"""
    node_id: str
    name: str
    device_type: DeviceType
    type_name: str
    location: str = ""
    area: str = ""
    value: Any = None
    unit: str = ""
    state: str = "off"
    mode: str = "manual"
    control_value: float = 0
    control_type: str = "boolean"
    control_range: ControlRange = field(default_factory=ControlRange)
    firmware_version: str = ""
    signal_strength: int = 100
    battery_level: int = 100
    last_update: datetime = field(default_factory=datetime.now)


class BaseSensor(ABC):
    """传感器基类"""
    
    def __init__(self, node_id: str, name: str, sensor_type: str):
        self.node_id = node_id
        self.name = name
        self.sensor_type = sensor_type
        self._value = None
        self._unit = ""
        self._last_read_time = None
        self.logger = logging.getLogger(f"sensor.{node_id}")
    
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """读取传感器数据"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化传感器"""
        pass
    
    def to_report_dict(self) -> Dict[str, Any]:
        """转换为上报格式"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.sensor_type,
            "value": self._value,
            "unit": self._unit,
            "last_update": self._last_time.isoformat() if self._last_time else None
        }


class BaseActuator(ABC):
    """执行器基类"""
    
    def __init__(self, node_id: str, name: str, actuator_type: str,
                 control_type: str = "boolean", control_range: ControlRange = None):
        self.node_id = node_id
        self.name = name
        self.actuator_type = actuator_type
        self.control_type = control_type
        self.control_range = control_range or ControlRange()
        self._state = "off"
        self._control_value = 0
        self._mode = "manual"
        self._locked = False
        self._last_update = None
        self.logger = logging.getLogger(f"actuator.{node_id}")
    
    @abstractmethod
    def initialize(self) -> bool:
        """初始化执行器"""
        pass
    
    @abstractmethod
    def execute_command(self, command: str, control_value: float = None) -> bool:
        """执行控制命令"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取执行器状态"""
        return {
            "state": self._state,
            "control_value": self._control_value,
            "mode": self._mode,
            "locked": self._locked,
            "last_update": self._last_update.isoformat() if self._last_update else None
        }
    
    def to_report_dict(self) -> Dict[str, Any]:
        """转换为上报格式"""
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.actuator_type,
            "state": self._state,
            "mode": self._mode,
            "control_value": self._control_value,
            "control_type": self.control_type,
            "control_range": {
                "min": self.control_range.min_value,
                "max": self.control_range.max_value,
                "step": self.control_range.step,
                "default": self.control_range.default
            }
        }


class HardwareManager:
    """硬件管理器"""
    
    def __init__(self, gateway_ip: str, farm_id: int = 1, area: str = ""):
        self.gateway_ip = gateway_ip
        self.farm_id = farm_id
        self.area = area
        self.sensors: Dict[str, BaseSensor] = {}
        self.actuators: Dict[str, BaseActuator] = {}
        self.logger = logging.getLogger("hardware")
    
    def register_sensor(self, sensor: BaseSensor):
        """注册传感器"""
        self.sensors[sensor.node_id] = sensor
        self.logger.info(f"Sensor registered: {sensor.node_id}")
    
    def register_actuator(self, actuator: BaseActuator):
        """注册执行器"""
        self.actuators[actuator.node_id] = actuator
        self.logger.info(f"Actuator registered: {actuator.node_id}")
    
    def read_all_sensors(self) -> List[Dict[str, Any]]:
        """读取所有传感器数据"""
        nodes = []
        for sensor in self.sensors.values():
            try:
                data = sensor.read()
                if data.get("value") is not None:
                    nodes.append(sensor.to_report_dict())
            except Exception as e:
                self.logger.error(f"Sensor {sensor.node_id} read error: {e}")
        return nodes
    
    def get_actuator_status(self) -> List[Dict[str, Any]]:
        """获取所有执行器状态"""
        return [act.to_report_dict() for act in self.actuators.values()]
    
    def execute_actuator_command(self, actuator_id: str, command: str,
                                  control_value: float = None) -> bool:
        """执行执行器控制命令"""
        actuator = self.actuators.get(actuator_id)
        if not actuator:
            self.logger.error(f"Actuator not found: {actuator_id}")
            return False
        
        if actuator._locked:
            self.logger.warning(f"Actuator {actuator_id} is locked")
            return False
        
        actuator._locked = True
        try:
            success = actuator.execute_command(command, control_value)
            actuator._last_update = datetime.now()
            return success
        except Exception as e:
            self.logger.error(f"Execute command error: {e}")
            return False
        finally:
            actuator._locked = False
    
    def build_report_payload(self) -> Dict[str, Any]:
        """构建上报数据包"""
        nodes = self.read_all_sensors()
        nodes.extend(self.get_actuator_status())
        
        return {
            "gateway_ip": self.gateway_ip,
            "farm_id": self.farm_id,
            "area": self.area,
            "nodes": nodes
        }
    
    def cleanup(self):
        """清理所有资源"""
        for sensor in self.sensors.values():
            try:
                sensor.cleanup()
            except:
                pass
        for actuator in self.actuators.values():
            try:
                actuator.cleanup()
            except:
                pass
        self.logger.info("All devices cleaned up")
