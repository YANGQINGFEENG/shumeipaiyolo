#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据上传服务"""

import requests
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class UploadService:
    """数据上传服务"""

    def __init__(self, config: Dict[str, Any], cache_service=None):
        self.server_url = config.get("server_url", "http://192.168.1.22:3000")
        self.gateway_ip = config.get("gateway_ip", "192.168.1.63")
        self.mac = config.get("mac", "AA:BB:CC:DD:EE:FF")
        self.farm_id = config.get("farm_id", 1)
        self.timeout = config.get("timeout", 10)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 5)
        self.cache = cache_service

    def upload_batch(self, readings: List[Dict[str, Any]]) -> bool:
        """批量上传数据"""
        if not readings:
            return True

        payload = {
            "gateway_ip": self.gateway_ip,
            "gateway_type": "wifi_sensor",
            "mac": self.mac,
            "farm_id": self.farm_id,
            "data": readings
        }

        success = self._send_with_retry(payload)

        if not success and self.cache:
            for reading in readings:
                self.cache.cache_data(reading.get("type", "unknown"), reading)
            logger.warning(f"Cached {len(readings)} records due to upload failure")

        return success

    def upload_single(self, sensor_id: str, data: Dict[str, Any]) -> bool:
        """上传单个传感器数据"""
        readings = [{"type": sensor_id, "value": data.get("value"), "unit": data.get("unit", "")}]
        return self.upload_batch(readings)

    def _send_with_retry(self, payload: Dict) -> bool:
        """带重试的发送"""
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(
                    f"{self.server_url}/api/device/report",
                    json=payload,
                    timeout=self.timeout
                )
                if resp.status_code in [200, 201]:
                    logger.info(f"Upload success")
                    return True
                logger.warning(f"Upload failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"Upload error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        return False

    def upload_cached_data(self):
        """上传缓存的未上传数据"""
        if not self.cache:
            return

        pending = self.cache.get_pending_data(limit=50)
        if not pending:
            return

        readings = []
        ids = []
        for item in pending:
            readings.append(item["data"])
            ids.append(item["id"])

        if self.upload_batch(readings):
            self.cache.mark_uploaded(ids)
            logger.info(f"Uploaded {len(ids)} cached records")
