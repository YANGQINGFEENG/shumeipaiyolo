#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据采集与上传管理器"""

import time
import json
import logging
from typing import Dict, Any, Optional

from sensors.base import SensorHub
from sensors.camera import CameraSensor
from sensors.yolo_detector import YoloDetector
from upload.http_uploader import HttpUploader
from upload.mqtt_uploader import MqttUploader

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集与上传管理器"""

    def __init__(
        self,
        hub: SensorHub,
        camera: Optional[CameraSensor] = None,
        yolo: Optional[YoloDetector] = None,
        http_uploader: Optional[HttpUploader] = None,
        mqtt_uploader: Optional[MqttUploader] = None
    ):
        self.hub = hub
        self.camera = camera
        self.yolo = yolo
        self.http = http_uploader
        self.mqtt = mqtt_uploader
        self._running = False

    def collect_once(self) -> Dict[str, Any]:
        """采集一次数据"""
        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "device": "raspberrypi",
            "sensors": self.hub.read_all()
        }

        # YOLO检测
        if self.yolo and self.camera:
            yolo_result = self.yolo.detect_camera(self.camera)
            data["yolo"] = yolo_result

        return data

    def upload_once(self) -> bool:
        """采集并上传一次数据"""
        data = self.collect_once()
        success = True

        if self.http:
            if not self.http.upload(data):
                success = False
                logger.error("HTTP upload failed")

        if self.mqtt:
            if not self.mqtt.publish_all(data["sensors"]):
                success = False
                logger.error("MQTT publish failed")

        return success

    def run_loop(self, interval: int = 60):
        """持续采集上传"""
        self._running = True
        logger.info(f"Starting collection loop, interval={interval}s")

        while self._running:
            try:
                self.upload_once()
                time.sleep(interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Collection error: {e}")
                time.sleep(5)

        self._running = False
        logger.info("Collection loop stopped")

    def stop(self):
        """停止采集"""
        self._running = False
