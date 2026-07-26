#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络通信模块 - 数据上报和指令接收
"""

import time
import json
import logging
import requests
import websocket
import threading
from typing import Any, Dict, List, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class HttpClient:
    """HTTP客户端"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
    
    def post(self, endpoint: str, data: Dict) -> Dict:
        """发送POST请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.post(url, json=data, timeout=self.timeout)
            return resp.json()
        except Exception as e:
            logger.error(f"POST {endpoint} error: {e}")
            return {"success": False, "error": str(e)}
    
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """发送GET请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            return resp.json()
        except Exception as e:
            logger.error(f"GET {endpoint} error: {e}")
            return {"success": False, "error": str(e)}


class WebSocketClient:
    """WebSocket客户端"""
    
    def __init__(self, url: str):
        self.url = url
        self.ws = None
        self._connected = False
        self._handlers = {}
        self._reconnect = True
        self._thread = None
    
    def connect(self):
        """连接WebSocket服务器"""
        try:
            self.ws = websocket.WebSocketApp(
                self.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self._thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self._thread.start()
            time.sleep(1)
        except Exception as e:
            logger.error(f"WebSocket connect error: {e}")
    
    def _on_open(self, ws):
        """连接成功回调"""
        self._connected = True
        logger.info("WebSocket connected")
    
    def _on_message(self, ws, message):
        """收到消息回调"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            
            if msg_type in self._handlers:
                self._handlers[msg_type](data)
            else:
                logger.debug(f"Unhandled message type: {msg_type}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    def _on_error(self, ws, error):
        """错误回调"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """关闭回调"""
        self._connected = False
        logger.info("WebSocket disconnected")
        
        if self._reconnect:
            logger.info("Reconnecting in 5 seconds...")
            time.sleep(5)
            self.connect()
    
    def send(self, data: Dict):
        """发送消息"""
        if self.ws and self._connected:
            try:
                self.ws.send(json.dumps(data))
            except Exception as e:
                logger.error(f"Send error: {e}")
    
    def on(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self._handlers[message_type] = handler
    
    def close(self):
        """关闭连接"""
        self._reconnect = False
        if self.ws:
            self.ws.close()


class DataReporter:
    """数据上报器"""
    
    def __init__(self, http_client: HttpClient, gateway_ip: str,
                 farm_id: int = 1, area: str = ""):
        self.http = http_client
        self.gateway_ip = gateway_ip
        self.farm_id = farm_id
        self.area = area
        self._running = False
        self._thread = None
    
    def report(self, nodes: List[Dict[str, Any]]) -> Dict:
        """上报数据"""
        payload = {
            "gateway_ip": self.gateway_ip,
            "farm_id": self.farm_id,
            "area": self.area,
            "nodes": nodes
        }
        
        return self.http.post("/api/device/report", payload)
    
    def report_once(self, hardware_manager) -> Dict:
        """上报一次数据"""
        payload = hardware_manager.build_report_payload()
        return self.report(payload.get("nodes", []))
    
    def start_periodic_report(self, hardware_manager, interval: int = 30):
        """启动周期性上报"""
        self._running = True
        
        def report_loop():
            while self._running:
                try:
                    self.report_once(hardware_manager)
                    logger.info(f"Data reported (interval={interval}s)")
                except Exception as e:
                    logger.error(f"Report error: {e}")
                time.sleep(interval)
        
        self._thread = threading.Thread(target=report_loop, daemon=True)
        self._thread.start()
        logger.info(f"Periodic report started (interval={interval}s)")
    
    def stop(self):
        """停止周期性上报"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def send_ack(self, actuator_id: str, command_id: int, status: str,
                 control_value: float = None, state: str = None) -> Dict:
        """发送回执确认"""
        payload = {
            "gateway_ip": self.gateway_ip,
            "actuator_id": actuator_id,
            "command_id": command_id,
            "status": status
        }
        if control_value is not None:
            payload["control_value"] = control_value
        if state is not None:
            payload["state"] = state
        
        return self.http.post("/api/device/ack", payload)


class CommandReceiver:
    """指令接收器 - 轮询模式"""
    
    def __init__(self, http_client: HttpClient, gateway_ip: str):
        self.http = http_client
        self.gateway_ip = gateway_ip
        self._running = False
        self._thread = None
        self._command_handler = None
    
    def set_handler(self, handler: Callable):
        """设置指令处理回调"""
        self._command_handler = handler
    
    def poll_commands(self) -> List[Dict]:
        """轮询待执行指令"""
        result = self.http.get("/api/device/ack", {"gateway_ip": self.gateway_ip})
        if result.get("success"):
            return result.get("data", [])
        return []
    
    def start_polling(self, interval: int = 2):
        """启动轮询"""
        self._running = True
        
        def poll_loop():
            while self._running:
                try:
                    commands = self.poll_commands()
                    for cmd in commands:
                        if self._command_handler:
                            self._command_handler(cmd)
                except Exception as e:
                    logger.error(f"Poll error: {e}")
                time.sleep(interval)
        
        self._thread = threading.Thread(target=poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"Command polling started (interval={interval}s)")
    
    def stop(self):
        """停止轮询"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
