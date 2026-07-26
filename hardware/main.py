#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件系统启动入口
"""

import sys
import os
import yaml
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.system import HardwareSystem
from hardware.sensors import (
    DHTSensor, BMP280Sensor, VibrationSensor,
    LightSensor, SoilMoistureSensor
)
from hardware.actuators import (
    RelayActuator, MotorActuator, ServoActuator,
    LedActuator, ValveActuator
)


def load_config(config_path: str = None) -> dict:
    """加载配置文件"""
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_sensor(sensor_config: dict):
    """根据配置创建传感器"""
    sensor_type = sensor_config.get("type")
    sensor_id = sensor_config.get("id")
    name = sensor_config.get("name")
    config = sensor_config.get("config", {})
    
    sensor_map = {
        "temperature": lambda: DHTSensor(sensor_id, name, **config),
        "humidity": lambda: DHTSensor(sensor_id, name, **config),
        "pressure": lambda: BMP280Sensor(sensor_id, name, **config),
        "vibration": lambda: VibrationSensor(sensor_id, name, **config),
        "light": lambda: LightSensor(sensor_id, name, **config),
        "soil_moisture": lambda: SoilMoistureSensor(sensor_id, name, **config),
    }
    
    if sensor_type in sensor_map:
        return sensor_map[sensor_type]()
    return None


def create_actuator(actuator_config: dict):
    """根据配置创建执行器"""
    actuator_type = actuator_config.get("type")
    actuator_id = actuator_config.get("id")
    name = actuator_config.get("name")
    config = actuator_config.get("config", {})
    control_type = actuator_config.get("control_type", "boolean")
    control_range_config = actuator_config.get("control_range", {})
    
    from hardware.core import ControlRange
    control_range = ControlRange(
        min_value=control_range_config.get("min", 0),
        max_value=control_range_config.get("max", 100),
        step=control_range_config.get("step", 1),
        default=control_range_config.get("default", 0)
    )
    
    actuator_map = {
        "relay": lambda: RelayActuator(actuator_id, name, **config),
        "motor": lambda: MotorActuator(actuator_id, name, **config),
        "servo": lambda: ServoActuator(actuator_id, name, **config),
        "led": lambda: LedActuator(actuator_id, name, **config),
        "valve": lambda: ValveActuator(actuator_id, name, **config),
    }
    
    if actuator_type in actuator_map:
        return actuator_map[actuator_type]()
    return None


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    print("=" * 60)
    print("  智慧农业物联网硬件系统")
    print("  Smart Agriculture IoT Hardware System")
    print("=" * 60)
    print()
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(config_path)
    print("Config loaded")
    
    # 创建系统
    gateway_config = config.get("gateway", {})
    server_config = config.get("server", {})
    
    system_config = {
        "gateway_ip": gateway_config.get("ip", "192.168.1.63"),
        "farm_id": gateway_config.get("farm_id", 1),
        "area": gateway_config.get("area", ""),
        "server_url": server_config.get("url", "http://192.168.1.22:3000"),
        "report_interval": server_config.get("report_interval", 30),
        "poll_interval": server_config.get("poll_interval", 2)
    }
    
    system = HardwareSystem(system_config)
    print("System initialized")
    
    # 注册传感器
    sensors_config = config.get("sensors", [])
    for sensor_conf in sensors_config:
        sensor = create_sensor(sensor_conf)
        if sensor:
            system.register_sensor(sensor)
            print(f"  Sensor: {sensor_conf['name']} ({sensor_conf['type']})")
    
    # 注册执行器
    actuators_config = config.get("actuators", [])
    for actuator_conf in actuators_config:
        actuator = create_actuator(actuator_conf)
        if actuator:
            system.register_actuator(actuator)
            print(f"  Actuator: {actuator_conf['name']} ({actuator_conf['type']})")
    
    print()
    print(f"Sensors: {len(system.hardware.sensors)}")
    print(f"Actuators: {len(system.hardware.actuators)}")
    print()
    
    # 启动系统
    print("Starting system...")
    system.start()


if __name__ == "__main__":
    main()
