#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行器控制器 - 接收服务器指令控制执行器
"""

import time
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ActuatorController:
    """执行器控制器"""

    def __init__(
        self,
        server: str,
        gateway_ip: str,
        farm_id: int = 1,
        poll_interval: int = 10
    ):
        """
        Args:
            server: API服务器地址
            gateway_ip: 网关IP
            farm_id: 基地ID
            poll_interval: 轮询间隔（秒）
        """
        self.server = server.rstrip("/")
        self.gateway_ip = gateway_ip
        self.farm_id = farm_id
        self.poll_interval = poll_interval
        self.actuators = {}  # {api_id: local_device}
        self._last_poll = 0

    def register_actuator(self, api_id: str, local_device):
        """
        注册执行器

        Args:
            api_id: 服务器上的执行器ID
            local_device: 本地执行器设备对象 (需要有 on/off 方法)
        """
        self.actuators[api_id] = local_device
        logger.info(f"Actuator registered: {api_id}")

    def poll_commands(self) -> bool:
        """
        轮询服务器获取控制指令

        Returns:
            是否有新指令
        """
        try:
            # 获取网关的执行器列表
            resp = requests.get(
                f"{self.server}/api/gateways",
                params={"farm_id": self.farm_id},
                timeout=5
            )

            if resp.status_code != 200:
                logger.warning(f"Failed to get gateways: {resp.status_code}")
                return False

            data = resp.json()
            if not data.get("success"):
                return False

            # 查找本机网关
            gateways = data.get("data", [])
            for gw in gateways:
                if gw.get("ip_address") == self.gateway_ip:
                    # 处理网关下的节点
                    nodes = gw.get("nodes", [])
                    for node in nodes:
                        self._process_node_command(node)
                    return True

            return False

        except Exception as e:
            logger.error(f"Poll error: {e}")
            return False

    def _process_node_command(self, node: Dict[str, Any]):
        """处理节点指令"""
        node_id = node.get("node_id")
        status = node.get("status")

        if node_id in self.actuators:
            device = self.actuators[node_id]
            # 根据状态控制执行器
            if status == "online":
                # 可以添加更复杂的指令解析
                pass

    def send_status(self, api_id: str, state: str) -> bool:
        """
        向服务器报告执行器状态

        Args:
            api_id: 执行器ID
            state: 状态 (on/off)
        """
        try:
            resp = requests.patch(
                f"{self.server}/api/actuators/{api_id}",
                json={
                    "state": state,
                    "mode": "auto",
                    "trigger_source": "device"
                },
                timeout=5
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Status report error: {e}")
            return False

    def control_actuator(self, api_id: str, command: str) -> bool:
        """
        执行控制指令

        Args:
            api_id: 执行器ID
            command: 指令 (on/off)
        """
        if api_id not in self.actuators:
            logger.warning(f"Unknown actuator: {api_id}")
            return False

        device = self.actuators[api_id]
        try:
            if command == "on":
                device.on()
            elif command == "off":
                device.off()
            else:
                logger.warning(f"Unknown command: {command}")
                return False

            # 向服务器报告状态
            self.send_status(api_id, command)
            logger.info(f"Actuator {api_id}: {command}")
            return True

        except Exception as e:
            logger.error(f"Control error: {e}")
            return False
