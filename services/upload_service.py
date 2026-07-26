#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据上传服务 - 支持配置服务器地址、上传时间、设备过滤"""

import requests
import time
import logging
import json
import threading
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from core.config_manager import ConfigManager
from services.cache_service import CacheService

logger = logging.getLogger(__name__)


class UploadService:
    """数据上传服务 - 匹配智慧农业平台 API

    支持通过 ConfigManager 动态配置：
    - 上传服务器地址 (upload.server_url)
    - 上传时间间隔 (upload.interval)
    - 上传设备过滤 (upload.upload_filter)
    - 网关标识 (upload.gateway_ip, upload.farm_id)
    """

    def __init__(self, config: ConfigManager, cache_service: CacheService = None):
        """初始化上传服务

        Args:
            config: 配置管理器
            cache_service: 本地缓存服务（用于离线缓存）
        """
        self.config = config
        self.cache = cache_service
        self._lock = threading.Lock()

        # 运行时状态
        self._running = False
        self._last_upload_time: Optional[datetime] = None
        self._last_upload_status: Optional[str] = None
        self._last_upload_count: int = 0
        self._upload_fail_count: int = 0
        self._thread: Optional[threading.Thread] = None

        # 监听配置变化，运行时重新加载
        self.config.on_change(self._on_config_changed)
        logger.info("UploadService initialized")

    def _on_config_changed(self, changed_files: List[str]):
        """配置变更回调 - 重新读取上传配置"""
        if any(f in changed_files for f in ["settings.yaml"]):
            logger.info("Upload config changed, will reload on next upload")

    def _get_server_url(self) -> str:
        """获取服务器URL（动态读取）"""
        return self.config.get("upload.server_url", "http://192.168.1.22:3000").rstrip("/")

    def _get_gateway_ip(self) -> str:
        """获取网关IP（动态读取）"""
        return self.config.get("upload.gateway_ip", "192.168.1.63")

    def _get_farm_id(self) -> int:
        """获取农场ID（动态读取）"""
        return self.config.get("upload.farm_id", 1)

    def _get_area(self) -> str:
        """获取区域名（动态读取）"""
        return self.config.get("upload.area", "")

    def _get_gateway_type(self) -> str:
        """获取网关类型（动态读取）"""
        return self.config.get("upload.gateway_type", "wifi_sensor")

    def _get_mac(self) -> str:
        """获取网关MAC地址（动态读取或自动获取）"""
        mac = self.config.get("upload.mac", "")
        if not mac:
            # 自动获取MAC地址
            try:
                import uuid
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
                self.config.set("upload.mac", mac)
            except:
                mac = ""
        return mac

    def _get_upload_filter(self) -> Dict[str, Any]:
        """获取上传过滤配置

        Returns:
            过滤配置：
                {
                    "mode": "all" | "whitelist" | "blacklist",
                    "device_ids": [...],
                    "device_types": [...]
                }
        """
        return self.config.get("upload.upload_filter", {"mode": "all", "device_ids": [], "device_types": []})

    def _get_timeout(self) -> int:
        """获取请求超时"""
        return self.config.get("upload.timeout", 10)

    def _get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.config.get("upload.max_retries", 3)

    def _get_retry_delay(self) -> int:
        """获取重试延迟"""
        return self.config.get("upload.retry_delay", 5)

    def _should_upload_device(self, device_id: str, device_type: str) -> bool:
        """根据过滤配置判断设备是否需要上传

        Args:
            device_id: 设备ID
            device_type: 设备类型

        Returns:
            是否需要上传
        """
        filter_config = self._get_upload_filter()
        mode = filter_config.get("mode", "all")

        if mode == "all":
            # 默认上传所有设备
            return True
        elif mode == "whitelist":
            # 白名单模式：仅上传列表中的设备
            allowed_ids = set(filter_config.get("device_ids", []))
            allowed_types = set(filter_config.get("device_types", []))
            return device_id in allowed_ids or device_type in allowed_types
        elif mode == "blacklist":
            # 黑名单模式：排除列表中的设备
            blocked_ids = set(filter_config.get("device_ids", []))
            blocked_types = set(filter_config.get("device_types", []))
            return device_id not in blocked_ids and device_type not in blocked_types
        return True

    def filter_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据配置过滤要上传的设备节点

        Args:
            nodes: 原始节点列表

        Returns:
            过滤后的节点列表
        """
        filtered = []
        for node in nodes:
            node_id = node.get("node_id", "")
            node_type = node.get("type", "")
            if self._should_upload_device(node_id, node_type):
                filtered.append(node)
        if len(filtered) != len(nodes):
            logger.info(f"Upload filter: {len(nodes)} -> {len(filtered)} devices")
        return filtered

    def upload_sensor_data(self, node_id: str, sensor_type: str,
                           value: float, unit: str = "", **kwargs) -> bool:
        """上传单个传感器数据

        Args:
            node_id: 设备节点ID
            sensor_type: 传感器类型
            value: 数值
            unit: 单位
        """
        if not self._should_upload_device(node_id, sensor_type):
            return True
        node = {"node_id": node_id, "type": sensor_type, "value": value, "unit": unit}
        node.update(kwargs)
        return self._upload_nodes([node])

    def upload_actuator_state(self, node_id: str, actuator_type: str,
                              state: str, mode: str = "manual", **kwargs) -> bool:
        """上传执行器状态

        Args:
            node_id: 设备节点ID
            actuator_type: 执行器类型
            state: 状态 (on/off)
            mode: 控制模式 (auto/manual)
        """
        if not self._should_upload_device(node_id, actuator_type):
            return True
        node = {"node_id": node_id, "type": actuator_type, "state": state, "mode": mode}
        node.update(kwargs)
        return self._upload_nodes([node])

    def upload_batch(self, readings: List[Dict[str, Any]]) -> bool:
        """批量上传数据

        Args:
            readings: 数据列表
        """
        filtered = self.filter_nodes(readings)
        return self._upload_nodes(filtered)

    def _upload_nodes(self, nodes: List[Dict[str, Any]]) -> bool:
        """上传节点数据到服务器

        POST /api/device/report
        """
        if not nodes:
            logger.info("[上传] 没有需要上传的设备节点")
            return True

        # 打印要上传的设备列表
        node_summary = []
        for n in nodes:
            node_summary.append(f"{n.get('node_id', '?')}({n.get('type', '?')})")
        logger.info(f"[上传] 准备上传 {len(nodes)} 个设备节点: {', '.join(node_summary)}")

        payload = {
            "gateway_ip": self._get_gateway_ip(),
            "gateway_type": self._get_gateway_type(),
            "mac": self._get_mac(),
            "farm_id": self._get_farm_id(),
            "area": self._get_area(),
            "nodes": nodes,
        }

        success = self._send_with_retry(payload)

        if not success and self.cache:
            # 缓存到本地，待网络恢复后重传
            for node in nodes:
                self.cache.cache_data(node.get("type", "unknown"), node)
            logger.warning(f"[上传] 上传失败，已缓存 {len(nodes)} 条记录到本地")
        elif not success:
            logger.error(f"[上传] 上传失败，未启用本地缓存")

        # 更新状态
        with self._lock:
            self._last_upload_time = datetime.now()
            self._last_upload_status = "success" if success else "failed"
            self._last_upload_count = len(nodes)
            if success:
                self._upload_fail_count = 0
                logger.info(f"[上传] 成功上传 {len(nodes)} 个设备节点")
            else:
                self._upload_fail_count += 1
                logger.error(f"[上传] 上传失败，共 {len(nodes)} 个设备节点，连续失败 {self._upload_fail_count} 次")

        return success

    def _send_with_retry(self, payload: Dict) -> bool:
        """带重试的发送"""
        server_url = self._get_server_url()
        timeout = self._get_timeout()
        max_retries = self._get_max_retries()
        retry_delay = self._get_retry_delay()
        node_count = len(payload.get("nodes", []))

        logger.info(f"[上传] 服务器地址: {server_url}/api/device/report")
        logger.info(f"[上传] 请求超时: {timeout}秒, 最大重试: {max_retries}次, 重试延迟: {retry_delay}秒")

        for attempt in range(max_retries):
            try:
                logger.info(f"[上传] 第 {attempt + 1}/{max_retries} 次尝试...")
                resp = requests.post(
                    f"{server_url}/api/device/report",
                    json=payload,
                    timeout=timeout,
                )

                if resp.status_code in [200, 201]:
                    try:
                        result = resp.json()
                        msg = result.get("message", "上传成功")
                        total = result.get("total_nodes", node_count)
                        logger.info(f"[上传] HTTP {resp.status_code} - {msg}，处理 {total} 个节点")
                    except Exception:
                        logger.info(f"[上传] HTTP {resp.status_code} - 上传成功（无JSON响应）")
                    return True
                else:
                    error_detail = resp.text[:300] if resp.text else "空响应"
                    logger.error(f"[上传] HTTP {resp.status_code} - 服务器拒绝: {error_detail}")
                    logger.error(f"[上传] 失败原因: 服务器返回非200状态码")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"[上传] 第 {attempt + 1} 次尝试失败 - 网络连接错误: {e}")
                logger.error(f"[上传] 失败原因: 无法连接到服务器 {server_url}，请检查网络和服务器地址")
            except requests.exceptions.Timeout:
                logger.error(f"[上传] 第 {attempt + 1} 次尝试失败 - 请求超时（{timeout}秒）")
                logger.error(f"[上传] 失败原因: 服务器响应太慢或网络不稳定")
            except requests.exceptions.SSLError as e:
                logger.error(f"[上传] 第 {attempt + 1} 次尝试失败 - SSL/TLS 错误: {e}")
                logger.error(f"[上传] 失败原因: SSL证书验证失败，请检查HTTPS配置")
            except Exception as e:
                logger.error(f"[上传] 第 {attempt + 1} 次尝试失败 - 未知错误: {e}")
                import traceback
                logger.error(f"[上传] 错误堆栈:\n{traceback.format_exc()}")

            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                logger.info(f"[上传] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

        logger.error(f"[上传] 全部 {max_retries} 次尝试均失败")
        logger.error(f"[上传] 排查建议:")
        logger.error(f"        1. 检查服务器地址: {server_url} 是否正确")
        logger.error(f"        2. 检查树莓派网络是否正常（ping {server_url.split('://')[1].split(':')[0]}）")
        logger.error(f"        3. 检查服务器是否运行且 API 接口可用")
        logger.error(f"        4. 检查防火墙是否允许访问服务器端口")
        return False

    def upload_cached_data(self) -> int:
        """上传缓存的未上传数据

        Returns:
            本次成功上传的记录数
        """
        if not self.cache:
            return 0

        pending = self.cache.get_pending_data(limit=50)
        if not pending:
            return 0

        nodes = []
        ids = []
        for item in pending:
            nodes.append(item["data"])
            ids.append(item["id"])

        if self._upload_nodes(nodes):
            self.cache.mark_uploaded(ids)
            logger.info(f"Uploaded {len(ids)} cached records")
            return len(ids)
        return 0

    def send_ack(self, actuator_id: str, command_id: int, status: str,
                 control_value: float = None) -> Dict:
        """发送控制指令回执

        按协议规范：PATCH /api/actuators/{actuator_id}/commands

        Args:
            actuator_id: 执行器ID
            command_id: 指令ID
            status: 执行状态 (executed/failed)
            control_value: 实际控制值（数值控制必填）
        """
        payload = {
            "command_id": command_id,
            "status": status,
        }
        if control_value is not None:
            payload["control_value"] = control_value

        try:
            server_url = self._get_server_url()
            resp = requests.patch(
                f"{server_url}/api/actuators/{actuator_id}/commands",
                json=payload,
                timeout=self._get_timeout(),
            )
            return resp.json()
        except Exception as e:
            logger.error(f"Send ack error: {e}")
            return {"success": False, "error": str(e)}

    def fetch_pending_commands(self, actuator_ids: List[str] = None) -> List[Dict]:
        """从服务器拉取待执行的控制指令

        按协议规范：GET /api/actuators/{actuator_id}/commands

        Args:
            actuator_ids: 执行器ID列表，如果为空则不查询

        Returns:
            待执行指令列表
        """
        commands = []
        if not actuator_ids:
            return commands

        try:
            server_url = self._get_server_url()
            timeout = self._get_timeout()

            # 逐个查询每个执行器的待执行指令
            for actuator_id in actuator_ids:
                try:
                    resp = requests.get(
                        f"{server_url}/api/actuators/{actuator_id}/commands",
                        timeout=timeout,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        if result.get("success") and result.get("data"):
                            commands.append(result["data"])
                except Exception as e:
                    logger.error(f"Fetch command for {actuator_id} error: {e}")

            if commands:
                logger.info(f"[命令] 获取到 {len(commands)} 条待执行指令")
        except Exception as e:
            logger.error(f"Fetch commands error: {e}")

        return commands

    def get_status(self) -> Dict[str, Any]:
        """获取上传服务状态"""
        with self._lock:
            return {
                "running": self._running,
                "server_url": self._get_server_url(),
                "gateway_ip": self._get_gateway_ip(),
                "farm_id": self._get_farm_id(),
                "interval": self.config.get("upload.interval", 30),
                "last_upload_time": self._last_upload_time.isoformat() if self._last_upload_time else None,
                "last_upload_status": self._last_upload_status,
                "last_upload_count": self._last_upload_count,
                "fail_count": self._upload_fail_count,
                "filter": self._get_upload_filter(),
                "cache_count": self.cache.get_count() if self.cache else 0,
            }
