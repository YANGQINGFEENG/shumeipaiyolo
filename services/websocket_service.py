#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WebSocket 客户端服务 - 实时接收服务器推送的控制指令

功能：
1. 建立 WebSocket 连接，携带网关IP参数
2. 实时接收服务器推送的命令
3. 发送命令回执（command_ack）
4. 心跳保活（每30秒）
5. 指数退避重连（1s→2s→4s→...→max 30s）
6. WebSocket 断开时通知系统降级为 HTTP 轮询
"""

import json
import logging
import threading
import time
from typing import Dict, Optional, Callable

try:
    from websocket import create_connection, WebSocketException
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

logger = logging.getLogger(__name__)


class WebSocketService:
    """WebSocket 客户端服务"""

    def __init__(self, config: Dict, upload_service, command_handler: Callable = None):
        """初始化 WebSocket 服务

        Args:
            config: 配置字典
            upload_service: 上传服务实例（用于发送 HTTP 回执作为备选）
            command_handler: 命令处理回调函数，接收命令字典作为参数
        """
        self.config = config
        self.upload = upload_service
        self.command_handler = command_handler
        
        # 连接状态
        self._running = False
        self._connected = False
        self._ws = None
        self._thread = None
        self._stop_event = threading.Event()
        
        # 重连参数
        self._reconnect_delay = 1  # 初始重连延迟（秒）
        self._max_reconnect_delay = 30
        self._reconnect_count = 0
        
        # 心跳参数
        self._heartbeat_interval = 30  # 心跳间隔（秒）
        self._last_heartbeat_time = 0
        
        # 连接参数
        self._server_url = self._get_server_url()
        self._gateway_ip = self._get_gateway_ip()

    def _get_server_url(self) -> str:
        """获取服务器地址"""
        url = self.config.get("upload.server_url", "http://localhost:3000")
        # 替换 http/https 为 ws/wss
        if url.startswith("http://"):
            # 替换 http:// 为 ws://，并使用端口 8080（WebSocket端口）
            return url.replace("http://", "ws://").replace(":3000", ":8080")
        elif url.startswith("https://"):
            # 替换 https:// 为 wss://，并使用端口 8080
            return url.replace("https://", "wss://").replace(":3000", ":8080")
        return f"ws://{url}:8080"

    def _get_gateway_ip(self) -> str:
        """获取网关IP"""
        return self.config.get("upload.gateway_ip", "127.0.0.1")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def start(self):
        """启动 WebSocket 服务"""
        if not HAS_WEBSOCKET:
            logger.warning("[WebSocket] websocket-client 库未安装，跳过 WebSocket 连接")
            return
        
        if self._running:
            logger.warning("[WebSocket] 服务已在运行")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="websocket")
        self._thread.start()
        logger.info("[WebSocket] 服务已启动")

    def stop(self):
        """停止 WebSocket 服务"""
        self._running = False
        self._stop_event.set()
        
        # 关闭连接
        if self._ws:
            try:
                self._ws.close()
            except Exception as e:
                logger.error(f"[WebSocket] 关闭连接失败: {e}")
            self._ws = None
        
        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self._connected = False
        logger.info("[WebSocket] 服务已停止")

    def _run(self):
        """WebSocket 主循环"""
        while self._running:
            try:
                # 建立连接
                self._connect()
                
                if self._connected:
                    # 连接成功，重置重连参数
                    self._reconnect_delay = 1
                    self._reconnect_count = 0
                    
                    # 接收消息循环
                    self._receive_loop()
                else:
                    # 连接失败，等待后重试
                    self._wait_reconnect()
            except Exception as e:
                logger.error(f"[WebSocket] 主循环异常: {e}")
                self._connected = False
                self._wait_reconnect()

    def _connect(self):
        """建立 WebSocket 连接"""
        try:
            ws_url = f"{self._server_url}?gateway_ip={self._gateway_ip}"
            logger.info(f"[WebSocket] 正在连接: {ws_url}")
            
            self._ws = create_connection(ws_url, timeout=10)
            self._connected = True
            self._last_heartbeat_time = time.time()
            
            logger.info("[WebSocket] 连接成功")
            
            # 发送欢迎消息响应
            # 等待服务器的 welcome 消息
            try:
                msg = self._ws.recv()
                data = json.loads(msg)
                if data.get("type") == "welcome":
                    logger.info(f"[WebSocket] 收到欢迎消息: {data.get('message', '')}")
            except Exception as e:
                logger.debug(f"[WebSocket] 等待欢迎消息超时或异常: {e}")
            
            # 发送心跳
            self._send_heartbeat()
            
        except WebSocketException as e:
            logger.error(f"[WebSocket] 连接失败: {e}")
            self._connected = False
        except Exception as e:
            logger.error(f"[WebSocket] 连接异常: {e}")
            self._connected = False

    def _receive_loop(self):
        """接收消息循环"""
        while self._running and self._connected:
            try:
                # 设置超时，以便定期检查心跳和退出信号
                self._ws.settimeout(5)
                
                msg = self._ws.recv()
                if not msg:
                    continue
                
                self._process_message(msg)
                
            except WebSocketException as e:
                logger.error(f"[WebSocket] 接收消息失败: {e}")
                self._connected = False
                break
            except Exception as e:
                logger.error(f"[WebSocket] 接收消息异常: {e}")
                # 继续运行，可能是超时等待
                
            # 检查心跳
            self._check_heartbeat()

    def _process_message(self, msg: str):
        """处理收到的消息"""
        try:
            data = json.loads(msg)
            msg_type = data.get("type", "")
            
            if msg_type == "command":
                # 收到控制指令
                cmd_data = data.get("data", {})
                logger.info(f"[WebSocket] 收到命令: {cmd_data}")
                
                # 调用命令处理回调
                if self.command_handler:
                    self.command_handler(cmd_data)
                
            elif msg_type == "heartbeat_ack":
                # 心跳回执
                logger.debug("[WebSocket] 收到心跳回执")
                
            elif msg_type == "welcome":
                # 欢迎消息
                logger.info(f"[WebSocket] 欢迎消息: {data.get('message', '')}")
                
            elif msg_type == "error":
                # 错误消息
                logger.error(f"[WebSocket] 错误: {data.get('message', '')}")
                
            else:
                logger.debug(f"[WebSocket] 未知消息类型: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"[WebSocket] 消息解析失败: {e}, 原始消息: {msg}")
        except Exception as e:
            logger.error(f"[WebSocket] 处理消息异常: {e}")

    def _send_heartbeat(self):
        """发送心跳"""
        try:
            heartbeat_msg = json.dumps({"type": "heartbeat"})
            self._ws.send(heartbeat_msg)
            self._last_heartbeat_time = time.time()
            logger.debug("[WebSocket] 发送心跳")
        except Exception as e:
            logger.error(f"[WebSocket] 发送心跳失败: {e}")

    def _check_heartbeat(self):
        """检查心跳，超时则重连"""
        now = time.time()
        if now - self._last_heartbeat_time > self._heartbeat_interval:
            self._send_heartbeat()

    def _wait_reconnect(self):
        """等待重连"""
        if not self._running:
            return
        
        wait_time = min(self._reconnect_delay, self._max_reconnect_delay)
        logger.info(f"[WebSocket] {wait_time}秒后尝试重连...")
        
        # 等待期间检查停止信号
        if self._stop_event.wait(timeout=wait_time):
            return
        
        # 指数退避
        self._reconnect_delay *= 2
        self._reconnect_count += 1

    def send_command_ack(self, actuator_id: str, command_id: int, 
                        status: str, control_value: float = None):
        """发送命令回执（优先使用 WebSocket，失败则使用 HTTP）

        Args:
            actuator_id: 执行器ID（节点ID）
            command_id: 命令ID
            status: 执行状态（executed/failed）
            control_value: 实际控制值
        """
        if self._connected and self._ws:
            try:
                ack_msg = {
                    "type": "command_ack",
                    "actuator_id": actuator_id,
                    "command_id": command_id,
                    "status": status,
                }
                if control_value is not None:
                    ack_msg["control_value"] = control_value
                
                self._ws.send(json.dumps(ack_msg))
                logger.info(f"[WebSocket] 发送回执: {ack_msg}")
                return True
            except Exception as e:
                logger.error(f"[WebSocket] 发送回执失败，切换到 HTTP: {e}")
        
        # WebSocket 不可用，使用 HTTP 发送回执
        return self._send_ack_via_http(actuator_id, command_id, status, control_value)

    def _send_ack_via_http(self, actuator_id: str, command_id: int, 
                           status: str, control_value: float = None) -> bool:
        """通过 HTTP 发送命令回执

        Args:
            actuator_id: 执行器ID
            command_id: 命令ID
            status: 执行状态
            control_value: 实际控制值

        Returns:
            是否成功
        """
        try:
            if self.upload:
                result = self.upload.send_ack(actuator_id, command_id, status, control_value)
                return result.get("success", False)
        except Exception as e:
            logger.error(f"[WebSocket] HTTP 回执发送失败: {e}")
        return False
