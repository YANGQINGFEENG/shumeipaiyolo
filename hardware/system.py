#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件系统 - 整合所有组件
"""

import time
import json
import logging
import signal
import threading
from typing import Dict, Any, List
from datetime import datetime

from hardware.core import HardwareManager, BaseActuator
from hardware.network import HttpClient, DataReporter, CommandReceiver

logger = logging.getLogger(__name__)


class HardwareSystem:
    """硬件系统主控"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.logger = logging.getLogger("HardwareSystem")
        
        # 初始化硬件管理器
        gateway_ip = config.get("gateway_ip", "192.168.1.63")
        farm_id = config.get("farm_id", 1)
        area = config.get("area", "")
        self.hardware = HardwareManager(gateway_ip, farm_id, area)
        
        # 初始化网络
        server_url = config.get("server_url", "http://192.168.1.22:3000")
        self.http = HttpClient(server_url)
        self.reporter = DataReporter(self.http, gateway_ip, farm_id, area)
        self.receiver = CommandReceiver(self.http, gateway_ip)
        
        # 设置指令处理回调
        self.receiver.set_handler(self._handle_command)
        
        # 统计信息
        self.stats = {
            "report_count": 0,
            "command_count": 0,
            "start_time": None
        }
        
        self.logger.info(f"HardwareSystem initialized: gateway={gateway_ip}")
    
    def register_sensor(self, sensor):
        """注册传感器"""
        self.hardware.register_sensor(sensor)
    
    def register_actuator(self, actuator):
        """注册执行器"""
        self.hardware.register_actuator(actuator)
    
    def _handle_command(self, command: Dict):
        """处理控制指令"""
        try:
            actuator_id = command.get("actuator_id")
            command_id = command.get("command_id")
            cmd = command.get("command")
            control_value = command.get("control_value")
            
            self.logger.info(f"Received command: {actuator_id} -> {cmd}")
            
            # 执行指令
            success = self.hardware.execute_actuator_command(
                actuator_id, cmd, control_value
            )
            
            # 发送回执
            status = "executed" if success else "failed"
            state = "on" if cmd == "on" else "off"
            
            self.reporter.send_ack(
                actuator_id=actuator_id,
                command_id=command_id,
                status=status,
                control_value=control_value,
                state=state
            )
            
            self.stats["command_count"] += 1
            self.logger.info(f"Command {command_id} {status}")
            
        except Exception as e:
            logger.error(f"Handle command error: {e}")
    
    def start(self):
        """启动系统"""
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        # 启动数据上报
        report_interval = self.config.get("report_interval", 30)
        self.reporter.start_periodic_report(self.hardware, report_interval)
        
        # 启动指令轮询
        poll_interval = self.config.get("poll_interval", 2)
        self.receiver.start_polling(poll_interval)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("System started")
        
        # 主循环
        self._main_loop()
    
    def _main_loop(self):
        """主循环"""
        while self.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
    
    def _signal_handler(self, sig, frame):
        """信号处理"""
        self.logger.info("Shutdown signal received")
        self.running = False
    
    def stop(self):
        """停止系统"""
        self.running = False
        self.reporter.stop()
        self.receiver.stop()
        self.hardware.cleanup()
        self.logger.info("System stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "running": self.running,
            "sensors": len(self.hardware.sensors),
            "actuators": len(self.hardware.actuators),
            "stats": self.stats,
            "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None
        }
