#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器基类 / Base Sensor Class

所有传感器的抽象基类，提供统一接口:
- read(): 读取传感器数据
- test(): 自检测试
- cleanup(): 清理资源
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseSensor(ABC):
    """传感器抽象基类"""

    def __init__(self, name: str, sensor_type: str, pin_config: Dict[str, Any]):
        """
        初始化传感器

        Args:
            name: 传感器名称 (如 "ultrasonic", "temperature")
            sensor_type: 传感器类型 (如 "digital", "analog", "i2c", "special")
            pin_config: 引脚配置字典
        """
        self.name = name
        self.sensor_type = sensor_type
        self.pin_config = pin_config
        self._initialized = False
        self._last_reading = None
        self._last_read_time = None
        logger.info(f"Sensor [{name}] created with type={sensor_type}")

    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化传感器硬件

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    def read_raw(self) -> Any:
        """
        读取原始数据 (子类必须实现)

        Returns:
            原始传感器数据
        """
        pass

    def read(self) -> Dict[str, Any]:
        """
        读取传感器数据，返回标准化字典

        Returns:
            包含数据和元信息的字典
        """
        if not self._initialized:
            self.initialize()

        try:
            raw_data = self.read_raw()
            self._last_reading = raw_data
            self._last_read_time = datetime.now()

            return {
                "sensor": self.name,
                "type": self.sensor_type,
                "data": raw_data,
                "timestamp": self._last_read_time.isoformat(),
                "status": "ok"
            }
        except Exception as e:
            logger.error(f"Sensor [{self.name}] read error: {e}")
            return {
                "sensor": self.name,
                "type": self.sensor_type,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def test(self) -> Dict[str, Any]:
        """
        传感器自检

        Returns:
            测试结果字典
        """
        try:
            # 尝试初始化
            if not self._initialized:
                init_ok = self.initialize()
                if not init_ok:
                    return {
                        "sensor": self.name,
                        "status": "fail",
                        "error": "Initialization failed"
                    }

            # 尝试读取
            result = self.read()
            return {
                "sensor": self.name,
                "status": "ok" if result["status"] == "ok" else "fail",
                "last_reading": result.get("data"),
                "error": result.get("error")
            }
        except Exception as e:
            return {
                "sensor": self.name,
                "status": "error",
                "error": str(e)
            }

    def cleanup(self):
        """清理资源"""
        self._initialized = False
        logger.info(f"Sensor [{self.name}] cleaned up")

    @property
    def last_reading(self):
        """获取最后一次读数"""
        return self._last_reading

    @property
    def last_read_time(self):
        """获取最后一次读数时间"""
        return self._last_read_time

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.sensor_type}')>"


class SensorHub:
    """传感器管理器，管理所有传感器实例"""

    def __init__(self):
        self._sensors: Dict[str, BaseSensor] = {}

    def register(self, sensor: BaseSensor):
        """注册传感器"""
        self._sensors[sensor.name] = sensor
        logger.info(f"Sensor [{sensor.name}] registered")

    def get(self, name: str) -> Optional[BaseSensor]:
        """获取传感器"""
        return self._sensors.get(name)

    def list(self) -> list:
        """列出所有传感器"""
        return list(self._sensors.keys())

    def read_all(self) -> Dict[str, Any]:
        """读取所有传感器数据"""
        results = {}
        for name, sensor in self._sensors.items():
            results[name] = sensor.read()
        return results

    def test_all(self) -> Dict[str, Any]:
        """测试所有传感器"""
        results = {}
        for name, sensor in self._sensors.items():
            results[name] = sensor.test()
        return results

    def cleanup_all(self):
        """清理所有传感器"""
        for sensor in self._sensors.values():
            sensor.cleanup()
        logger.info("All sensors cleaned up")
