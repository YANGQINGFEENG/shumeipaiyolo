#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""心跳服务"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class HeartbeatService:
    """心跳服务"""

    def __init__(self, config: Dict[str, Any] = None):
        self.enabled = config.get("enabled", True) if config else True

    def send_heartbeat(self, sensors: Dict, actuators: Dict) -> bool:
        """发送心跳"""
        if not self.enabled:
            return True

        # 收集状态信息
        sensor_status = {k: v.get_status() for k, v in sensors.items()}
        actuator_status = {k: v.get_status() for k, v in actuators.items()}

        heartbeat_data = {
            "type": "heartbeat",
            "sensors": sensor_status,
            "actuators": actuator_status
        }

        logger.debug(f"Heartbeat: {len(sensors)} sensors, {len(actuators)} actuators")
        return True
