#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统主控 - 整合所有模块，统一调度"""

import os
import sys
import time
import signal
import logging
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config_manager import ConfigManager
from core.event_bus import EventBus, Event, EventTypes, event_bus
from core.logger import setup_logger
from services.upload_service import UploadService
from services.cache_service import CacheService
from services.heartbeat_service import HeartbeatService
from ota.manager import OTAManager
from scanner.device_scanner import DeviceScanner

logger = logging.getLogger(__name__)


class System:
    """系统主控 - 整合所有模块

    负责初始化、调度、协调各模块工作：
    - 配置管理（热加载）
    - 日志系统
    - 缓存服务
    - 上传服务（与服务器通信）
    - 心跳服务（设备状态上报）
    - OTA 升级（自动检查、备份、回滚）
    - 设备扫描（自动发现）
    - 传感器/执行器驱动
    - 数据采集与上传循环
    """

    VERSION = "2.0.0"

    def __init__(self, config_dir: str = None, enable_ui: bool = False):
        """初始化系统

        Args:
            config_dir: 配置目录路径
            enable_ui: 是否启动触摸屏 UI
        """
        self.project_root = PROJECT_ROOT
        self.enable_ui = enable_ui

        # 1. 初始化配置管理器
        self.config = ConfigManager(config_dir)

        # 2. 初始化日志系统
        log_level = self.config.get("system.log_level", "INFO")
        log_file = self.config.get("system.log_file", "logs/system.log")
        setup_logger("smart_farm", log_file, log_level)
        # 同时配置根日志
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        logger.info("=" * 60)
        logger.info(f"智慧农业硬件系统 v{self.VERSION} 启动中...")
        logger.info(f"项目路径: {self.project_root}")
        logger.info(f"配置目录: {self.config.config_dir}")
        logger.info("=" * 60)

        # 3. 初始化事件总线
        self.event_bus = event_bus

        # 4. 初始化缓存服务
        cache_path = self.config.get("cache.db_path", "data/cache.db")
        self.cache = CacheService(cache_path)

        # 5. 初始化上传服务
        self.upload = UploadService(self.config, self.cache)

        # 6. 初始化心跳服务
        self.heartbeat = HeartbeatService(self.config, self.upload)

        # 7. 初始化 OTA 管理器
        self.ota_manager = OTAManager(self.config, self.project_root)
        # 设置重启回调
        self.ota_manager.set_restart_callback(self._restart_service)

        # 8. 初始化设备扫描器
        scanner_config = self.config.get("scanner", {})
        self.scanner = DeviceScanner(scanner_config)

        # 9. 设备注册表
        self.sensors: Dict[str, Any] = {}
        self.actuators: Dict[str, Any] = {}

        # 10. 设备 ID 映射（传感器ID -> 服务器节点ID/类型）
        self.device_mapping = self.config.get("device_mapping", {}) or {}

        # 11. 运行时状态
        self.running = False
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._main_thread: Optional[threading.Thread] = None

        # 12. UI 引用（延迟初始化）
        self.ui = None
        self._ui_thread: Optional[threading.Thread] = None

        # 13. 监听配置变化
        self.config.on_change(self._on_config_changed)

        # 14. 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("System initialized")

    def _on_config_changed(self, changed_files: List[str]):
        """配置变更回调 - 通知各模块重新加载"""
        logger.info(f"Config changed: {changed_files}, notifying modules")
        # 发布事件
        self.event_bus.publish(Event(
            event_type=EventTypes.SYSTEM_START,
            source="system",
            data={"changed_files": changed_files}
        ))

    def load_devices(self):
        """加载所有已配置的传感器和执行器"""
        self._load_sensors()
        self._load_actuators()
        logger.info(f"Loaded {len(self.sensors)} sensors, {len(self.actuators)} actuators")

    def _load_sensors(self):
        """加载传感器驱动"""
        sensor_map = self._get_sensor_driver_map()

        for sensor_conf in self.config.get_sensors():
            if not sensor_conf.get("enabled", True):
                continue
            sensor_type = sensor_conf.get("type")
            sensor_class = sensor_map.get(sensor_type)
            if not sensor_class:
                logger.warning(f"Unknown sensor type: {sensor_type}, skip")
                continue

            try:
                sensor = sensor_class(
                    sensor_id=sensor_conf["id"],
                    name=sensor_conf.get("name", sensor_conf["id"]),
                    config=sensor_conf.get("config", {}),
                    **(sensor_conf.get("config") or {}),
                )
                self.register_sensor(sensor)
            except Exception as e:
                logger.error(f"Load sensor {sensor_conf.get('id')} failed: {e}")

    def _load_actuators(self):
        """加载执行器驱动"""
        actuator_map = self._get_actuator_driver_map()

        for actuator_conf in self.config.get_actuators():
            if not actuator_conf.get("enabled", True):
                continue
            actuator_type = actuator_conf.get("type")
            actuator_class = actuator_map.get(actuator_type)
            if not actuator_class:
                logger.warning(f"Unknown actuator type: {actuator_type}, skip")
                continue

            try:
                actuator = actuator_class(
                    actuator_id=actuator_conf["id"],
                    name=actuator_conf.get("name", actuator_conf["id"]),
                    config=actuator_conf.get("config", {}),
                    **(actuator_conf.get("config") or {}),
                )
                self.register_actuator(actuator)
            except Exception as e:
                logger.error(f"Load actuator {actuator_conf.get('id')} failed: {e}")

    def _get_sensor_driver_map(self) -> Dict[str, type]:
        """获取传感器类型->驱动类映射"""
        from drivers.sensors.dht import DHTSensor
        from drivers.sensors.bmp280 import BMP280Sensor
        from drivers.sensors.vibration import VibrationSensor

        return {
            "dht": DHTSensor,
            "bmp280": BMP280Sensor,
            "vibration": VibrationSensor,
        }

    def _get_actuator_driver_map(self) -> Dict[str, type]:
        """获取执行器类型->驱动类映射"""
        from drivers.actuators.relay import RelayActuator
        from drivers.actuators.laser import LaserActuator
        from drivers.actuators.rgb_led import RGBLEDActuator

        return {
            "relay": RelayActuator,
            "laser": LaserActuator,
            "rgb_led": RGBLEDActuator,
        }

    def register_sensor(self, sensor):
        """注册传感器"""
        self.sensors[sensor.sensor_id] = sensor
        logger.info(f"Sensor registered: {sensor.sensor_id}")

    def register_actuator(self, actuator):
        """注册执行器"""
        self.actuators[actuator.actuator_id] = actuator
        logger.info(f"Actuator registered: {actuator.actuator_id}")

    def initialize_devices(self):
        """初始化所有设备（GPIO/I2C 等）"""
        # DHT 类传感器最后初始化（避免 GPIO 冲突）
        dht_sensors = []
        for sensor_id, sensor in self.sensors.items():
            if sensor.sensor_type == "dht":
                dht_sensors.append(sensor)
                continue
            try:
                result = sensor.initialize()
                if not result:
                    logger.warning(f"Sensor {sensor_id} initialization failed")
            except Exception as e:
                logger.error(f"Sensor {sensor_id} init error: {e}")

        # 初始化执行器
        for actuator_id, actuator in self.actuators.items():
            try:
                result = actuator.initialize()
                if not result:
                    logger.warning(f"Actuator {actuator_id} initialization failed")
            except Exception as e:
                logger.error(f"Actuator {actuator_id} init error: {e}")

        # 最后初始化 DHT（等待其他 GPIO 稳定）
        if dht_sensors:
            time.sleep(2)
            for sensor in dht_sensors:
                try:
                    result = sensor.initialize()
                    if not result:
                        logger.warning(f"DHT {sensor.sensor_id} initialization failed")
                except Exception as e:
                    logger.error(f"DHT {sensor.sensor_id} init error: {e}")

    def start(self):
        """启动系统"""
        if self.running:
            logger.warning("System already running")
            return
        self.running = True
        self._stop_event.clear()

        logger.info("System starting...")

        # 发布系统启动事件
        self.event_bus.publish(Event(
            event_type=EventTypes.SYSTEM_START,
            source="system",
            data={"version": self.VERSION}
        ))

        # 加载并初始化设备
        self.load_devices()
        self.initialize_devices()

        # 启动配置热加载监控
        self.config.start_watching(interval=5.0)

        # 启动心跳服务
        self.heartbeat.start(
            sensors_provider=lambda: self.sensors,
            actuators_provider=lambda: self.actuators,
        )

        # 启动 OTA 自动检查
        if self.config.get("ota.auto_check_enabled", False):
            self.ota_manager.start_auto_check()

        # 启动数据采集与上传线程
        data_thread = threading.Thread(target=self._data_loop, daemon=True, name="data-collector")
        data_thread.start()
        self._threads.append(data_thread)

        # 启动缓存重传线程
        cache_thread = threading.Thread(target=self._cache_retry_loop, daemon=True, name="cache-retry")
        cache_thread.start()
        self._threads.append(cache_thread)

        # 启动命令轮询线程（从服务器获取待执行的控制指令）
        command_thread = threading.Thread(target=self._command_poll_loop, daemon=True, name="command-poll")
        command_thread.start()
        self._threads.append(command_thread)

        # 启动 UI（如果启用）
        if self.enable_ui:
            self._start_ui()

        logger.info("System started successfully")

        # 主循环（仅在有 UI 时不需要）
        if not self.enable_ui:
            self._main_loop()

    def _main_loop(self):
        """主循环（命令行模式）"""
        logger.info("Entering main loop (Ctrl+C to stop)")
        try:
            while self.running:
                self._stop_event.wait(timeout=1)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received")
        finally:
            self.stop()

    def _data_loop(self):
        """数据采集与上传循环"""
        logger.info("Data collection loop started")
        upload_interval = self._get_upload_interval()
        last_upload = 0

        while self.running:
            try:
                current_time = time.time()
                if current_time - last_upload >= upload_interval:
                    self._collect_and_upload()
                    last_upload = current_time
                # 短暂休眠，便于响应停止
                self._stop_event.wait(timeout=1)
                # 动态获取间隔（支持配置热加载）
                upload_interval = self._get_upload_interval()
            except Exception as e:
                logger.error(f"Data loop error: {e}")
                self.event_bus.publish(Event(
                    event_type=EventTypes.SYSTEM_ERROR,
                    source="data_loop",
                    data={"error": str(e)}
                ))
                self._stop_event.wait(timeout=5)

    def _get_upload_interval(self) -> int:
        """获取上传间隔（动态读取配置）"""
        return self.config.get("upload.interval", 30)

    def _collect_and_upload(self):
        """采集所有传感器数据并上传"""
        nodes = []
        sensors_mapping = self.device_mapping.get("sensors", {})
        area = self.config.get("upload.area", "")

        logger.info(f"[采集] 开始采集数据，共 {len(self.sensors)} 个传感器，{len(self.actuators)} 个执行器")

        # 采集传感器数据（按协议规范格式）
        for sensor_id, sensor in self.sensors.items():
            try:
                logger.debug(f"[采集] 读取传感器: {sensor_id} ({sensor.name})")

                # 使用线程超时读取，避免单个传感器卡死
                result = [None]

                def read_sensor():
                    result[0] = sensor.read()

                thread = threading.Thread(target=read_sensor, daemon=True)
                thread.start()
                thread.join(timeout=10)

                if thread.is_alive():
                    logger.warning(f"[采集] 传感器 {sensor_id} 读取超时（10秒），跳过")
                    continue

                data = result[0]
                if not data or data.get("value") is None:
                    logger.warning(f"[采集] 传感器 {sensor_id} 返回空数据，跳过")
                    continue

                value = data.get("value")
                quality = data.get("quality", "unknown")

                if quality != "good" and quality != "GOOD":
                    logger.warning(f"[采集] 传感器 {sensor_id} 数据质量差: {quality}，跳过")
                    continue

                logger.info(f"[采集] 传感器 {sensor_id} 数据: {value} {data.get('unit', '')}")

                # 处理多值传感器（如 DHT11 同时返回温度和湿度）
                if isinstance(value, dict):
                    for key, val in value.items():
                        map_key = f"{sensor_id}_{key}"
                        mapping = sensors_mapping.get(map_key, {})
                        node_id = mapping.get("node_id", f"{sensor_id}_{key}")
                        api_type = mapping.get("type", key)
                        name = mapping.get("name", f"{sensor.name}_{key}")
                        location = mapping.get("location", "")
                        unit = data.get("unit", {})
                        if isinstance(unit, dict):
                            unit = unit.get(key, "")
                        nodes.append({
                            "node_id": node_id,
                            "type": api_type,
                            "name": name,
                            "value": val,
                            "unit": unit,
                            "location": location,
                            "area": area,
                        })
                        logger.debug(f"[采集]   -> 节点: {node_id} = {val} {unit}")
                else:
                    mapping = sensors_mapping.get(sensor_id, {})
                    node_id = mapping.get("node_id", sensor_id)
                    api_type = mapping.get("type", sensor.sensor_type)
                    name = mapping.get("name", sensor.name)
                    location = mapping.get("location", "")
                    unit = data.get("unit", "")
                    nodes.append({
                        "node_id": node_id,
                        "type": api_type,
                        "name": name,
                        "value": value,
                        "unit": unit,
                        "location": location,
                        "area": area,
                    })
                    logger.debug(f"[采集]   -> 节点: {node_id} = {value} {unit}")
            except Exception as e:
                logger.error(f"[采集] 传感器 {sensor_id} 读取错误: {e}")

        # 采集执行器状态（按协议规范格式）
        logger.info(f"[采集] 采集执行器状态，共 {len(self.actuators)} 个执行器")
        actuators_mapping = self.device_mapping.get("actuators", {})
        area = self.config.get("upload.area", "")
        for actuator_id, actuator in self.actuators.items():
            try:
                mapping = actuators_mapping.get(actuator_id, {})
                node_id = mapping.get("node_id", actuator_id)
                api_type = mapping.get("type", actuator.actuator_type)
                name = mapping.get("name", actuator.name)

                # 获取执行器状态
                state = "off"
                if hasattr(actuator, "_state"):
                    state = actuator._state.value if hasattr(actuator._state, "value") else str(actuator._state)
                    if state == "unknown":
                        state = "off"

                # 获取控制参数（按协议规范）
                control_value = 0
                control_type = "boolean"  # 默认布尔控制
                control_min = 0
                control_max = 0
                control_step = 0
                control_default = 0

                # 根据执行器类型设置控制参数
                if actuator.actuator_type in ["rgb_led", "motor", "fan", "heater"]:
                    control_type = "integer"
                    control_min = 0
                    control_max = 100
                    control_step = 1
                    control_default = 0

                location = mapping.get("location", "")

                nodes.append({
                    "node_id": node_id,
                    "type": api_type,
                    "name": name,
                    "state": state,
                    "mode": "manual",
                    "control_value": control_value,
                    "control_type": control_type,
                    "control_min": control_min,
                    "control_max": control_max,
                    "control_step": control_step,
                    "control_default": control_default,
                    "location": location,
                    "area": area,
                })
                logger.info(f"[采集] 执行器 {actuator_id} 状态: {state}")
            except Exception as e:
                logger.error(f"Actuator {actuator_id} status error: {e}")

        # 上传
        if nodes:
            try:
                logger.info(f"[上传] 准备上传 {len(nodes)} 个设备节点")
                success = self.upload.upload_batch(nodes)
                if success:
                    logger.info(f"[上传] 上传成功，共 {len(nodes)} 个设备节点")
                    self.event_bus.publish(Event(
                        event_type=EventTypes.UPLOAD_SUCCESS,
                        source="upload",
                        data={"count": len(nodes)}
                    ))
                else:
                    logger.error(f"[上传] 上传失败，共 {len(nodes)} 个设备节点")
                    self.event_bus.publish(Event(
                        event_type=EventTypes.UPLOAD_FAILED,
                        source="upload",
                        data={"count": len(nodes)}
                    ))
            except Exception as e:
                logger.error(f"[上传] 上传异常: {e}")
        else:
            logger.info(f"[上传] 没有可上传的设备节点")

    def _cache_retry_loop(self):
        """缓存重传循环 - 网络恢复后重传缓存的数据"""
        logger.info("Cache retry loop started")
        while self.running:
            try:
                self._stop_event.wait(timeout=60)  # 每 60 秒重试一次
                if not self.running:
                    break
                uploaded = self.upload.upload_cached_data()
                if uploaded > 0:
                    logger.info(f"Retry uploaded {uploaded} cached records")
            except Exception as e:
                logger.error(f"Cache retry error: {e}")

    def _command_poll_loop(self):
        """命令轮询循环 - 定期从服务器获取待执行的控制指令"""
        logger.info("Command poll loop started")
        while self.running:
            try:
                self._stop_event.wait(timeout=10)  # 每 10 秒轮询一次
                if not self.running:
                    break

                # 从服务器获取待执行命令（使用映射后的节点ID）
                actuator_ids = []
                actuators_mapping = self.device_mapping.get("actuators", {})
                for actuator_id in self.actuators.keys():
                    mapping = actuators_mapping.get(actuator_id, {})
                    node_id = mapping.get("node_id", actuator_id)
                    actuator_ids.append(node_id)
                
                commands = self.upload.fetch_pending_commands(actuator_ids)
                if commands:
                    self._execute_commands(commands)
            except Exception as e:
                logger.error(f"Command poll error: {e}")

    def _execute_commands(self, commands: List[Dict]):
        """执行从服务器获取的控制指令

        Args:
            commands: 指令列表
        """
        for cmd in commands:
            try:
                actuator_node_id = cmd.get("actuator_id", "")
                command = cmd.get("command", "")
                command_id = cmd.get("id", 0)
                control_value = cmd.get("control_value")

                # 反向映射：从节点ID找到原始执行器ID
                actuator_id = actuator_node_id
                actuators_mapping = self.device_mapping.get("actuators", {})
                for orig_id, mapping in actuators_mapping.items():
                    if mapping.get("node_id") == actuator_node_id:
                        actuator_id = orig_id
                        break

                logger.info(f"[命令] 硬件端查询指令 - 执行器: {actuator_id}, 指令: {command}, 控制值: {control_value}, 命令ID: {command_id}")

                # 查找执行器
                actuator = self.actuators.get(actuator_id)
                if not actuator:
                    logger.warning(f"[命令] 未找到执行器: {actuator_id} (节点ID: {actuator_node_id})")
                    # 发送失败回执（使用节点ID）
                    self.upload.send_ack(actuator_node_id, command_id, "failed")
                    continue

                # 执行命令
                success = False
                state = "off"

                if command == "on":
                    success = actuator.turn_on()
                    state = "on"
                elif command == "off":
                    success = actuator.turn_off()
                    state = "off"
                elif command == "value" and control_value is not None:
                    # 设置控制值（仅支持整数类型）
                    try:
                        # 将控制值转换为整数（服务器可能返回字符串如 '0.00'）
                        int_value = int(float(control_value))
                        
                        # RGB-LED 需要特殊处理颜色值
                        if actuator.actuator_type == "rgb_led":
                            r, g, b = [int_value / 100] * 3
                            actuator.set_color(r, g, b)
                            success = True
                            state = "on"
                        elif hasattr(actuator, "set_value"):
                            success = actuator.set_value(int_value)
                            state = "on"
                        else:
                            logger.warning(f"[命令] 执行器 {actuator_id} 不支持 value 命令")
                    except Exception as e:
                        logger.error(f"[命令] 设置控制值失败: {e}")

                if success:
                    logger.info(f"[命令] 执行成功: {actuator_id} -> {command}")
                    # 使用节点ID发送回执（协议规范要求）
                    self.upload.send_ack(actuator_node_id, command_id, "executed", control_value)
                else:
                    logger.error(f"[命令] 执行失败: {actuator_id} -> {command}")
                    # 使用节点ID发送回执（协议规范要求）
                    self.upload.send_ack(actuator_node_id, command_id, "failed", control_value)

            except Exception as e:
                logger.error(f"[命令] 执行指令异常: {e}")

    def _start_ui(self):
        """启动触摸屏 UI"""
        def ui_main():
            try:
                from ui.main_window import MainWindow
                self.ui = MainWindow(app_container=self, fullscreen=True)
                self.ui.run()
            except Exception as e:
                logger.error(f"UI error: {e}")

        self._ui_thread = threading.Thread(target=ui_main, daemon=True, name="ui")
        self._ui_thread.start()
        logger.info("UI started in separate thread")

    def _restart_service(self):
        """重启服务（OTA 升级成功后调用）"""
        logger.info("Restarting service after OTA update...")
        try:
            self.stop()
        except Exception:
            pass
        # 通过重启主进程来加载新代码
        # 注意：这里使用 os.execv 重启当前进程
        time.sleep(1)
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def _signal_handler(self, sig, frame):
        """信号处理"""
        logger.info(f"Received signal {sig}, shutting down...")
        self.running = False
        self._stop_event.set()

    def stop(self):
        """停止系统"""
        if not self.running:
            return
        logger.info("System stopping...")
        self.running = False
        self._stop_event.set()

        # 停止配置监控
        try:
            self.config.stop_watching()
        except Exception:
            pass

        # 停止心跳
        try:
            self.heartbeat.stop()
        except Exception:
            pass

        # 停止 OTA 自动检查
        try:
            self.ota_manager.stop_auto_check()
        except Exception:
            pass

        # 等待线程结束
        for thread in self._threads:
            try:
                if thread.is_alive():
                    thread.join(timeout=5)
            except Exception:
                pass

        # 清理设备
        for sensor in self.sensors.values():
            try:
                sensor.cleanup()
            except Exception:
                pass

        for actuator in self.actuators.values():
            try:
                actuator.cleanup()
            except Exception:
                pass

        # 发布停止事件
        self.event_bus.publish(Event(
            event_type=EventTypes.SYSTEM_STOP,
            source="system"
        ))

        logger.info("System stopped")

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "version": self.VERSION,
            "running": self.running,
            "project_root": self.project_root,
            "uptime": self._get_uptime(),
            "sensors": {k: self._safe_get_status(v) for k, v in self.sensors.items()},
            "actuators": {k: self._safe_get_status(v) for k, v in self.actuators.items()},
            "upload": self.upload.get_status() if self.upload else None,
            "heartbeat": self.heartbeat.get_status() if self.heartbeat else None,
            "ota": self.ota_manager.get_status() if self.ota_manager else None,
            "cache_count": self.cache.get_count() if self.cache else 0,
        }

    def _safe_get_status(self, device) -> Dict[str, Any]:
        """安全获取设备状态"""
        try:
            return device.get_status()
        except Exception as e:
            return {"error": str(e)}

    def _get_uptime(self) -> Optional[str]:
        """获取运行时长"""
        # 简单实现：返回 None，实际可记录启动时间
        return None

    def scan_devices(self):
        """执行设备扫描"""
        return self.scanner.scan_all()
