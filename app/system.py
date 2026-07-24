#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统主控 - 匹配新API格式"""

import time
import signal
import logging
import threading
from typing import Dict, Any
from datetime import datetime

from core.event_bus import EventBus, Event, EventTypes
from core.config_manager import ConfigManager
from core.logger import setup_logger
from drivers.sensors.base import BaseSensor
from drivers.actuators.base import BaseActuator
from services.upload_service import UploadService
from services.cache_service import CacheService
from services.heartbeat_service import HeartbeatService

logger = logging.getLogger(__name__)


class System:
    """系统主控"""

    def __init__(self, config_path: str = None):
        self.config = ConfigManager(config_path)
        self.event_bus = EventBus()
        self.running = False

        # 初始化日志
        log_level = self.config.get("system.log_level", "INFO")
        log_file = self.config.get("system.log_file", "logs/system.log")
        setup_logger("smart_farm", log_file, log_level)

        # 初始化服务
        cache_path = self.config.get("cache.db_path", "data/cache.db")
        self.cache = CacheService(cache_path)
        self.upload = UploadService(self.config.get("upload", {}), self.cache)
        self.heartbeat = HeartbeatService(self.config.get("heartbeat", {}))

        # 设备注册表
        self.sensors: Dict[str, BaseSensor] = {}
        self.actuators: Dict[str, BaseActuator] = {}

        # 设备映射 (sensor_id -> node_id)
        self.device_mapping = self.config.get("device_mapping", {})

        # 线程
        self._threads = []

        print(f"[DEBUG] Device mapping loaded: {self.device_mapping}")
        logger.info("System initialized")

    def register_sensor(self, sensor: BaseSensor):
        """注册传感器"""
        self.sensors[sensor.sensor_id] = sensor
        logger.info(f"Sensor registered: {sensor.sensor_id}")

    def register_actuator(self, actuator: BaseActuator):
        """注册执行器"""
        self.actuators[actuator.actuator_id] = actuator
        logger.info(f"Actuator registered: {actuator.actuator_id}")

    def start(self):
        """启动系统"""
        self.running = True
        logger.info("System starting...")

        # 初始化设备
        for sensor in self.sensors.values():
            sensor.initialize()
        for actuator in self.actuators.values():
            actuator.initialize()

        # 启动服务线程
        self._start_threads()

        # 注册信号
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("System started")
        self._main_loop()

    def _start_threads(self):
        """启动后台线程"""
        upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
        upload_thread.start()
        self._threads.append(upload_thread)

        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        self._threads.append(heartbeat_thread)

    def _main_loop(self):
        """主循环"""
        upload_interval = self.config.get("upload.interval", 30)
        last_upload = 0

        while self.running:
            current_time = time.time()

            if current_time - last_upload >= upload_interval:
                self._collect_and_upload()
                last_upload = current_time

            time.sleep(0.1)

    def _collect_and_upload(self):
        """采集并上传数据"""
        nodes = []
        sensors_mapping = self.device_mapping.get("sensors", {})
        print(f"[DEBUG] sensors_mapping: {sensors_mapping}")

        for sensor_id, sensor in self.sensors.items():
            try:
                data = sensor.read()
                print(f"[DEBUG] Sensor {sensor_id} raw data: {data}")

                if data and data.get("value") is not None:
                    value = data.get("value")

                    # 处理多值传感器 (如DHT11有温度和湿度)
                    if isinstance(value, dict):
                        for key, val in value.items():
                            # 根据值的key查找映射
                            map_key = f"{sensor_id}_{key}"
                            mapping = sensors_mapping.get(map_key, {})
                            node_id = mapping.get("node_id", f"{sensor_id}_{key}")
                            api_type = mapping.get("type", key)
                            name = mapping.get("name", f"{sensor.name}_{key}")
                            unit = data.get("unit", {})
                            if isinstance(unit, dict):
                                unit = unit.get(key, "")

                            print(f"[DEBUG] Mapped: {map_key} -> node_id={node_id}, type={api_type}")
                            nodes.append({
                                "node_id": node_id,
                                "type": api_type,
                                "name": name,
                                "value": val,
                                "unit": unit
                            })
                    else:
                        # 单值传感器
                        mapping = sensors_mapping.get(sensor_id, {})
                        node_id = mapping.get("node_id", sensor_id)
                        api_type = mapping.get("type", sensor.sensor_type)
                        name = mapping.get("name", sensor.name)
                        unit = data.get("unit", "")

                        print(f"[DEBUG] Mapped: {sensor_id} -> node_id={node_id}, type={api_type}")
                        nodes.append({
                            "node_id": node_id,
                            "type": api_type,
                            "name": name,
                            "value": value,
                            "unit": unit
                        })
            except Exception as e:
                logger.error(f"Sensor {sensor_id} read error: {e}")

        # 上传执行器状态
        actuators_mapping = self.device_mapping.get("actuators", {})
        print(f"[DEBUG] actuators_mapping: {actuators_mapping}")
        for actuator_id, actuator in self.actuators.items():
            try:
                mapping = actuators_mapping.get(actuator_id, {})
                node_id = mapping.get("node_id", actuator_id)
                api_type = mapping.get("type", actuator.actuator_type)
                name = mapping.get("name", actuator.name)
                state = actuator._state.value if hasattr(actuator._state, 'value') else "off"
                if state == "unknown":
                    state = "off"

                print(f"[DEBUG] Actuator {actuator_id}: mapping={mapping}, node_id={node_id}, type={api_type}, state={state}")
                nodes.append({
                    "node_id": node_id,
                    "type": api_type,
                    "name": name,
                    "state": state,
                    "mode": "auto"
                })
            except Exception as e:
                logger.error(f"Actuator {actuator_id} status error: {e}")

        if nodes:
            self.upload.upload_batch(nodes)
            logger.info(f"Uploaded {len(nodes)} nodes")

    def _upload_loop(self):
        """上传线程"""
        while self.running:
            try:
                self.upload.upload_cached_data()
            except Exception as e:
                logger.error(f"Upload loop error: {e}")
            time.sleep(60)

    def _heartbeat_loop(self):
        """心跳线程"""
        while self.running:
            try:
                self.heartbeat.send_heartbeat(self.sensors, self.actuators)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            time.sleep(30)

    def _signal_handler(self, sig, frame):
        """信号处理"""
        logger.info("Shutdown signal received")
        self.running = False

    def stop(self):
        """停止系统"""
        self.running = False
        logger.info("System stopping...")

        for sensor in self.sensors.values():
            sensor.cleanup()
        for actuator in self.actuators.values():
            actuator.cleanup()

        logger.info("System stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "running": self.running,
            "sensors": {k: v.get_status() for k, v in self.sensors.items()},
            "actuators": {k: v.get_status() for k, v in self.actuators.items()},
            "cache_count": self.cache.get_count()
        }
