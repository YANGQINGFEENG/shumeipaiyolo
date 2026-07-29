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
            enable_ui: 是否启动触摸屏 UI（已废弃，使用终端界面）
        """
        self.project_root = PROJECT_ROOT
        self.enable_ui = enable_ui  # 保留参数以兼容旧代码，实际不再使用

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

        # 13. WebSocket 状态
        self._websocket_connected = False
        self._websocket_service = None
        
        # 14. 导入 WebSocket 服务（延迟导入避免循环依赖）
        try:
            from services.websocket_service import WebSocketService
            self._websocket_class = WebSocketService
        except ImportError:
            logger.warning("WebSocketService import failed")
            self._websocket_class = None

        # 14. 命令去重（已执行的 command_id，缓存5分钟）
        self._executed_commands = set()
        self._command_lock = threading.Lock()
        
        # 15. 命令队列和线程池（异步执行命令）
        self._command_queue = []
        self._command_queue_lock = threading.Lock()
        self._command_executor = None
        self._command_executor_running = False

        # 16. 设备初始化状态追踪（支持中途加入的设备）
        self._failed_sensors: Dict[str, float] = {}  # sensor_id -> 上次重试时间
        self._failed_actuators: Dict[str, float] = {}  # actuator_id -> 上次重试时间
        self._retry_interval = 10  # 重试间隔（秒）

        # 17. 监听配置变化
        self.config.on_change(self._on_config_changed)

        # 16. 注册信号处理
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
        """初始化所有设备（GPIO/I2C 等）
        
        支持设备中途加入：
        - 初始化失败的设备会被记录到 _failed_sensors/_failed_actuators
        - 后续的数据采集循环会定期重试初始化失败的设备
        """
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
                    self._failed_sensors[sensor_id] = time.time()
            except Exception as e:
                logger.error(f"Sensor {sensor_id} init error: {e}")
                self._failed_sensors[sensor_id] = time.time()

        # 初始化执行器
        for actuator_id, actuator in self.actuators.items():
            try:
                result = actuator.initialize()
                if not result:
                    logger.warning(f"Actuator {actuator_id} initialization failed")
                    self._failed_actuators[actuator_id] = time.time()
            except Exception as e:
                logger.error(f"Actuator {actuator_id} init error: {e}")
                self._failed_actuators[actuator_id] = time.time()

        # 最后初始化 DHT（等待其他 GPIO 稳定）
        if dht_sensors:
            time.sleep(2)
            for sensor in dht_sensors:
                try:
                    result = sensor.initialize()
                    if not result:
                        logger.warning(f"DHT {sensor.sensor_id} initialization failed")
                        self._failed_sensors[sensor.sensor_id] = time.time()
                except Exception as e:
                    logger.error(f"DHT {sensor.sensor_id} init error: {e}")
                    self._failed_sensors[sensor.sensor_id] = time.time()

        # 打印初始化结果统计
        total_sensors = len(self.sensors)
        total_actuators = len(self.actuators)
        failed_sensors = len(self._failed_sensors)
        failed_actuators = len(self._failed_actuators)
        logger.info(f"设备初始化完成: 传感器 {total_sensors - failed_sensors}/{total_sensors} 成功, 执行器 {total_actuators - failed_actuators}/{total_actuators} 成功")
        
        if self._failed_sensors or self._failed_actuators:
            logger.info(f"将每 {self._retry_interval} 秒重试初始化失败的设备...")

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

        # 启动命令异步执行器
        self._start_command_executor()

        # 启动 WebSocket 服务（实时接收服务器推送的命令）
        self._start_websocket_service()

        # 启动 UI（如果启用）
        if self.enable_ui:
            self._start_ui()

        logger.info("System started successfully")

        # 主循环：当没有 UI 时，进入后台运行模式
        # 如果有终端界面（CLI），由调用方负责交互循环
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
        """数据采集与上传循环
        
        支持设备热插拔：
        - 每次采集前检查是否有失败的设备需要重试初始化
        - 设备初始化成功后自动加入数据采集流程
        """
        logger.info("Data collection loop started")
        upload_interval = self._get_upload_interval()
        last_upload = 0
        last_retry = 0

        while self.running:
            try:
                current_time = time.time()
                
                # 定期重试初始化失败的设备（每 retry_interval 秒）
                if current_time - last_retry >= self._retry_interval:
                    self._retry_failed_devices()
                    last_retry = current_time
                
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

    def _retry_failed_devices(self):
        """重试初始化失败的设备
        
        遍历所有失败的传感器和执行器，尝试重新初始化。
        初始化成功的设备会从失败列表中移除，并自动加入数据采集流程。
        """
        if not self._failed_sensors and not self._failed_actuators:
            return  # 没有失败的设备，跳过
        
        now = time.time()
        retry_count = 0
        success_count = 0

        # 重试传感器
        for sensor_id, last_attempt in list(self._failed_sensors.items()):
            if now - last_attempt < self._retry_interval:
                continue  # 未到重试时间
            
            if sensor_id not in self.sensors:
                del self._failed_sensors[sensor_id]
                continue
            
            sensor = self.sensors[sensor_id]
            retry_count += 1
            
            try:
                result = sensor.initialize()
                if result:
                    logger.info(f"[重试] 传感器 {sensor_id} 初始化成功！已加入数据采集")
                    del self._failed_sensors[sensor_id]
                    success_count += 1
                else:
                    self._failed_sensors[sensor_id] = now
            except Exception as e:
                logger.debug(f"[重试] 传感器 {sensor_id} 重试失败: {e}")
                self._failed_sensors[sensor_id] = now

        # 重试执行器
        for actuator_id, last_attempt in list(self._failed_actuators.items()):
            if now - last_attempt < self._retry_interval:
                continue
            
            if actuator_id not in self.actuators:
                del self._failed_actuators[actuator_id]
                continue
            
            actuator = self.actuators[actuator_id]
            retry_count += 1
            
            try:
                result = actuator.initialize()
                if result:
                    logger.info(f"[重试] 执行器 {actuator_id} 初始化成功！已加入数据采集")
                    del self._failed_actuators[actuator_id]
                    success_count += 1
                else:
                    self._failed_actuators[actuator_id] = now
            except Exception as e:
                logger.debug(f"[重试] 执行器 {actuator_id} 重试失败: {e}")
                self._failed_actuators[actuator_id] = now

        # 打印重试结果（仅在有设备被重试时）
        if retry_count > 0:
            remaining = len(self._failed_sensors) + len(self._failed_actuators)
            logger.info(f"[重试] 重试了 {retry_count} 个设备，成功 {success_count} 个，剩余 {remaining} 个待重试")

    def _get_upload_interval(self) -> int:
        """获取上传间隔（动态读取配置）"""
        return self.config.get("upload.interval", 30)

    def _read_sensor_data(self, sensor_id: str, sensor, sensors_mapping: Dict, area: str) -> List[Dict]:
        """读取单个传感器数据（供线程池使用）
        
        Args:
            sensor_id: 传感器ID
            sensor: 传感器实例
            sensors_mapping: 传感器映射配置
            area: 区域名
        
        Returns:
            节点数据列表
        """
        nodes = []
        try:
            logger.debug(f"[采集] 读取传感器: {sensor_id} ({sensor.name})")
            
            # 直接读取（传感器内部已有缓存和超时保护）
            data = sensor.read()
            
            if not data or data.get("value") is None:
                logger.warning(f"[采集] 传感器 {sensor_id} 返回空数据，跳过")
                return nodes

            value = data.get("value")
            quality = data.get("quality", "unknown")

            # WARNING 级别也接受（使用缓存数据）
            if quality not in ["good", "GOOD", "warning", "WARNING"]:
                logger.warning(f"[采集] 传感器 {sensor_id} 数据质量差: {quality}，跳过")
                return nodes

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
        except Exception as e:
            logger.error(f"[采集] 传感器 {sensor_id} 读取错误: {e}")
        
        return nodes

    def _collect_and_upload(self):
        """采集所有传感器数据并上传（并行读取优化）"""
        nodes = []
        sensors_mapping = self.device_mapping.get("sensors", {})
        area = self.config.get("upload.area", "")

        logger.info(f"[采集] 开始采集数据，共 {len(self.sensors)} 个传感器，{len(self.actuators)} 个执行器")

        # 并行读取所有传感器数据（使用线程池）
        if self.sensors:
            import concurrent.futures
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    # 提交所有读取任务
                    futures = {
                        executor.submit(
                            self._read_sensor_data,
                            sensor_id,
                            sensor,
                            sensors_mapping,
                            area
                        ): sensor_id
                        for sensor_id, sensor in self.sensors.items()
                    }

                    # 收集结果
                    for future in concurrent.futures.as_completed(futures):
                        sensor_id = futures[future]
                        try:
                            result_nodes = future.result()
                            nodes.extend(result_nodes)
                        except Exception as e:
                            logger.error(f"[采集] 传感器 {sensor_id} 读取异常: {e}")
            except Exception as e:
                logger.error(f"[采集] 并行读取失败: {e}")
                # 降级为串行读取
                for sensor_id, sensor in self.sensors.items():
                    nodes.extend(self._read_sensor_data(sensor_id, sensor, sensors_mapping, area))

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
        """命令轮询循环 - 定期从服务器获取待执行的控制指令
        
        根据 WebSocket 状态动态调整轮询频率：
        - WebSocket 在线：轮询间隔30秒（仅作兜底）
        - WebSocket 离线：轮询间隔2秒（快速获取命令）
        """
        logger.info("Command poll loop started")
        while self.running:
            try:
                # 更新 WebSocket 连接状态
                self._update_websocket_status()
                
                # 根据 WebSocket 状态动态调整轮询间隔
                poll_interval = 30 if self._websocket_connected else 2
                self._stop_event.wait(timeout=poll_interval)
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

    def _is_command_executed(self, command_id: int) -> bool:
        """检查命令是否已执行过（去重）

        Args:
            command_id: 命令ID

        Returns:
            True表示已执行过，False表示未执行
        """
        with self._command_lock:
            return command_id in self._executed_commands

    def _mark_command_executed(self, command_id: int):
        """标记命令已执行

        Args:
            command_id: 命令ID
        """
        with self._command_lock:
            self._executed_commands.add(command_id)

    def _cleanup_executed_commands(self):
        """清理已过期的命令记录（每5分钟清理一次）"""
        # 当前实现简单，保留所有记录
        # 如需清理，可添加时间戳记录并定期删除过期条目
        pass

    def _execute_single_command(self, cmd: Dict):
        """执行单条控制指令（支持去重，供 WebSocket 和 HTTP 共用）

        Args:
            cmd: 指令数据
        """
        try:
            actuator_node_id = cmd.get("actuator_id", "")
            command = cmd.get("command", "")
            command_id = cmd.get("id", 0)
            control_value = cmd.get("control_value")

            # 命令去重检查
            if self._is_command_executed(command_id):
                logger.debug(f"[命令] 跳过已执行的命令: {command_id}")
                return

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
                return

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
                    
                    # RGB-LED 使用 set_value 方法支持颜色选择和亮度控制
                    # value=0-9: 预设颜色, value=10-100: 白色亮度
                    if hasattr(actuator, "set_value"):
                        success = actuator.set_value(int_value)
                        state = "on" if int_value > 0 else "off"
                    else:
                        logger.warning(f"[命令] 执行器 {actuator_id} 不支持 value 命令")
                except Exception as e:
                    logger.error(f"[命令] 设置控制值失败: {e}")

            if success:
                logger.info(f"[命令] 执行成功: {actuator_id} -> {command}")
                # 标记命令已执行（防止重复）
                self._mark_command_executed(command_id)
                # 使用节点ID发送回执（协议规范要求）
                self.upload.send_ack(actuator_node_id, command_id, "executed", control_value)
            else:
                logger.error(f"[命令] 执行失败: {actuator_id} -> {command}")
                # 标记命令已执行（防止重复）
                self._mark_command_executed(command_id)
                # 使用节点ID发送回执（协议规范要求）
                self.upload.send_ack(actuator_node_id, command_id, "failed", control_value)

        except Exception as e:
            logger.error(f"[命令] 执行指令异常: {e}")

    def _start_command_executor(self):
        """启动命令异步执行器"""
        if self._command_executor_running:
            return
            
        self._command_executor_running = True
        self._command_executor = threading.Thread(
            target=self._command_executor_loop, 
            daemon=True, 
            name="command-executor"
        )
        self._command_executor.start()
        logger.info("Command executor started (async mode)")

    def _stop_command_executor(self):
        """停止命令异步执行器"""
        self._command_executor_running = False
        
    def _command_executor_loop(self):
        """命令执行器主循环 - 异步处理命令队列"""
        while self._command_executor_running:
            try:
                # 从队列中取出命令
                cmd = None
                with self._command_queue_lock:
                    if self._command_queue:
                        cmd = self._command_queue.pop(0)
                
                if cmd:
                    self._execute_single_command(cmd)
                else:
                    # 队列为空，短暂休眠
                    self._stop_event.wait(timeout=0.1)
            except Exception as e:
                logger.error(f"Command executor loop error: {e}")

    def _execute_commands(self, commands: List[Dict]):
        """执行从服务器获取的控制指令列表（异步模式）

        Args:
            commands: 指令列表
        """
        with self._command_queue_lock:
            self._command_queue.extend(commands)
        logger.info(f"[命令] 已加入 {len(commands)} 条命令到执行队列")

    def _execute_single_command_sync(self, cmd: Dict):
        """同步执行单条命令（供特殊场景使用）"""
        self._execute_single_command(cmd)

    def _start_websocket_service(self):
        """启动 WebSocket 服务（实时接收服务器推送的命令）"""
        if self._websocket_class:
            try:
                # 创建 WebSocket 服务，注册命令处理回调
                # 传递配置字典（使用 ConfigManager 的 to_dict() 方法）
                self._websocket_service = self._websocket_class(
                    config=self.config.to_dict(),
                    upload_service=self.upload,
                    command_handler=self._on_websocket_command,
                )
                self._websocket_service.start()
                logger.info("[WebSocket] WebSocket 服务已启动")
            except Exception as e:
                logger.error(f"[WebSocket] 启动失败: {e}")
        else:
            logger.info("[WebSocket] WebSocketService 不可用，跳过启动")

    def _on_websocket_command(self, cmd: Dict):
        """处理 WebSocket 收到的命令

        Args:
            cmd: 命令数据
        """
        logger.info(f"[WebSocket] 收到命令: {cmd}")
        # 使用公共方法执行命令（自动去重）
        self._execute_single_command(cmd)

    def _update_websocket_status(self):
        """更新 WebSocket 连接状态"""
        if self._websocket_service:
            self._websocket_connected = self._websocket_service.is_connected()
        else:
            self._websocket_connected = False

    def _start_ui(self):
        """启动触摸屏 UI"""
        def ui_main():
            try:
                from ui.main_window import MainWindow
                self.ui = MainWindow(app_container=self, fullscreen=True)
                self.ui.run()
            except ImportError as e:
                logger.error(f"UI import error: {e}")
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

        # 停止 WebSocket 服务
        try:
            if self._websocket_service:
                self._websocket_service.stop()
        except Exception:
            pass

        # 停止命令执行器
        try:
            self._stop_command_executor()
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
