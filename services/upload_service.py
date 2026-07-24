#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据上传服务 - 匹配新API格式"""

import requests
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UploadService:
    """数据上传服务 - 匹配智慧农业平台API"""

    def __init__(self, config: Dict[str, Any], cache_service=None):
        self.server_url = config.get("server_url", "http://192.168.1.22:3000")
        self.gateway_id = config.get("gateway_id", 1)
        self.farm_id = config.get("farm_id", 1)
        self.timeout = config.get("timeout", 10)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 5)
        self.cache = cache_service

    def upload_sensor_data(self, node_id: str, sensor_type: str,
                           value: float, unit: str = "", **kwargs) -> bool:
        """
        上传单个传感器数据

        Args:
            node_id: 设备节点ID (如 "T-1-001")
            sensor_type: 传感器类型 (如 "temperature")
            value: 数值
            unit: 单位
        """
        node = {
            "node_id": node_id,
            "type": sensor_type,
            "value": value,
            "unit": unit
        }
        node.update(kwargs)
        return self._upload_nodes([node])

    def upload_actuator_state(self, node_id: str, actuator_type: str,
                              state: str, mode: str = "manual", **kwargs) -> bool:
        """
        上传执行器状态

        Args:
            node_id: 设备节点ID (如 "VL-1-001")
            actuator_type: 执行器类型 (如 "valve")
            state: 状态 (on/off)
            mode: 控制模式 (auto/manual)
        """
        node = {
            "node_id": node_id,
            "type": actuator_type,
            "state": state,
            "mode": mode
        }
        node.update(kwargs)
        return self._upload_nodes([node])

    def upload_batch(self, readings: List[Dict[str, Any]]) -> bool:
        """
        批量上传数据

        Args:
            readings: 数据列表
        """
        return self._upload_nodes(readings)

    def _upload_nodes(self, nodes: List[Dict[str, Any]]) -> bool:
        """
        上传节点数据到服务器

        POST /api/device/report
        {
            "gateway_id": 1,
            "farm_id": 1,
            "nodes": [...]
        }
        """
        if not nodes:
            return True

        payload = {
            "gateway_id": self.gateway_id,
            "farm_id": self.farm_id,
            "nodes": nodes
        }

        success = self._send_with_retry(payload)

        if not success and self.cache:
            for node in nodes:
                self.cache.cache_data(node.get("type", "unknown"), node)
            logger.warning(f"Cached {len(nodes)} records due to upload failure")

        return success

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
                    result = resp.json()
                    logger.info(f"Upload success: {result.get('message', '')}")
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

        nodes = []
        ids = []
        for item in pending:
            nodes.append(item["data"])
            ids.append(item["id"])

        if self._upload_nodes(nodes):
            self.cache.mark_uploaded(ids)
            logger.info(f"Uploaded {len(ids)} cached records")
