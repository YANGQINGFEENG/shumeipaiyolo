#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP JSON 数据上传
"""

import json
import time
import logging
import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HttpUploader:
    """HTTP JSON数据上传器"""

    def __init__(self, server: str, endpoint: str = "/api/data", timeout: int = 10):
        """
        Args:
            server: 服务器地址 (如 http://192.168.1.100:8080)
            endpoint: API端点
            timeout: 请求超时时间
        """
        self.server = server.rstrip("/")
        self.endpoint = endpoint
        self.timeout = timeout
        self.url = f"{self.server}{self.endpoint}"

    def upload(self, data: Dict[str, Any]) -> bool:
        """
        上传数据

        Args:
            data: 要上传的数据字典

        Returns:
            是否成功
        """
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "device": "raspberrypi",
            "data": data
        }

        try:
            resp = requests.post(
                self.url,
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code in [200, 201]:
                logger.info(f"Upload success: {resp.status_code}")
                return True
            else:
                logger.error(f"Upload failed: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False

    def upload_sensor_data(self, sensor_readings: Dict[str, Any]) -> bool:
        """上传传感器数据"""
        return self.upload({"sensors": sensor_readings})

    def upload_yolo_results(self, detections: list, image_path: str = None) -> bool:
        """上传YOLO检测结果"""
        data = {
            "yolo": {
                "detections": detections,
                "count": len(detections),
                "image_path": image_path
            }
        }
        return self.upload(data)

    def upload_full(self, sensors: Dict[str, Any], yolo: Dict[str, Any] = None) -> bool:
        """上传完整数据"""
        data = {"sensors": sensors}
        if yolo:
            data["yolo"] = yolo
        return self.upload(data)
