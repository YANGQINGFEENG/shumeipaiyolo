#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统管理器 - 整合传感器、上传、执行器控制
"""

import sys
import os
import time
import signal
import logging
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from system.config import load_config, DEFAULT_CONFIG
from system.hub import create_sensor_hub
from upload.http_uploader import HttpUploader
from sensors.actuator_controller import ActuatorController

logger = logging.getLogger(__name__)


class SystemManager:
    """系统管理器"""

    def __init__(self, config: dict = None):
        self.config = config or DEFAULT_CONFIG
        self.hub = None
        self.uploader = None
        self.actuator_ctrl = None
        self.running = False

        # 统计
        self.stats = {
            "upload_count": 0,
            "poll_count": 0,
            "error_count": 0,
            "start_time": None
        }

    def initialize(self):
        """初始化所有组件"""
        logger.info("初始化系统...")

        # 初始化传感器
        self.hub = create_sensor_hub(self.config)
        logger.info(f"传感器: {self.hub.list()}")

        # 初始化上传器
        server_config = self.config.get("server", {})
        device_config = self.config.get("device", {})
        self.uploader = HttpUploader(
            server=server_config.get("url", "http://192.168.1.22:3000"),
            gateway_ip=device_config.get("gateway_ip", "192.168.1.63"),
            mac=device_config.get("mac", "AA:BB:CC:DD:EE:FF"),
            farm_id=server_config.get("farm_id", 1)
        )

        # 初始化执行器控制器
        self.actuator_ctrl = ActuatorController(
            server=server_config.get("url", "http://192.168.1.22:3000"),
            gateway_ip=device_config.get("gateway_ip", "192.168.1.63"),
            farm_id=server_config.get("farm_id", 1)
        )

        # 注册执行器
        for name in ["relay", "laser", "rgb_led"]:
            device = self.hub.get(name)
            if device:
                self.actuator_ctrl.register_actuator(f"{name}_001", device)

        logger.info("系统初始化完成")

    def start(self):
        """启动系统"""
        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        self.stats["upload_count"] = 0
        self.stats["poll_count"] = 0
        self.stats["error_count"] = 0

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        intervals = self.config.get("intervals", {})
        upload_interval = intervals.get("upload", 30)
        poll_interval = intervals.get("poll", 10)

        logger.info(f"系统启动 - 上传间隔: {upload_interval}s, 轮询间隔: {poll_interval}s")

        last_upload = 0
        last_poll = 0

        while self.running:
            try:
                current_time = time.time()

                # 数据上传
                if current_time - last_upload >= upload_interval:
                    self._upload_data()
                    last_upload = current_time

                # 执行器轮询
                if current_time - last_poll >= poll_interval:
                    self._poll_actuators()
                    last_poll = current_time

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"主循环错误: {e}")
                self.stats["error_count"] += 1
                time.sleep(5)

        self._cleanup()

    def _signal_handler(self, sig, frame):
        """信号处理"""
        logger.info("收到停止信号...")
        self.running = False

    def _upload_data(self):
        """上传传感器数据"""
        try:
            readings = self.hub.read_all()

            # 记录数据
            log_data = {}
            for name, reading in readings.items():
                if reading["status"] == "ok":
                    log_data[name] = reading["data"]

            # 上传
            success = self.uploader.upload_all(readings)
            if success:
                self.stats["upload_count"] += 1
                logger.info(f"上传成功 #{self.stats['upload_count']}: {log_data}")
            else:
                self.stats["error_count"] += 1
                logger.warning("上传失败")

        except Exception as e:
            logger.error(f"上传错误: {e}")
            self.stats["error_count"] += 1

    def _poll_actuators(self):
        """轮询执行器指令"""
        try:
            self.actuator_ctrl.poll_commands()
            self.stats["poll_count"] += 1
        except Exception as e:
            logger.error(f"轮询错误: {e}")
            self.stats["error_count"] += 1

    def _cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        if self.hub:
            self.hub.cleanup_all()

        # 输出统计
        logger.info("=" * 50)
        logger.info("系统运行统计:")
        logger.info(f"  运行时间: {self.stats['start_time']}")
        logger.info(f"  上传次数: {self.stats['upload_count']}")
        logger.info(f"  轮询次数: {self.stats['poll_count']}")
        logger.info(f"  错误次数: {self.stats['error_count']}")
        logger.info("=" * 50)

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "running": self.running,
            "stats": self.stats,
            "sensors": self.hub.list() if self.hub else []
        }

    def stop(self):
        """停止系统"""
        self.running = False
