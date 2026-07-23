#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP JSON 数据上传 - 智慧农业物联网平台API
"""

import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class HttpUploader:
    """HTTP JSON数据上传器 - 智慧农业平台"""

    def __init__(
        self,
        server: str,
        report_endpoint: str = "/api/device/report",
        sensor_endpoint: str = "/api/sensors",
        gateway_ip: str = "192.168.1.63",
        gateway_type: str = "wifi_sensor",
        mac: str = "AA:BB:CC:DD:EE:FF",
        farm_id: int = 1,
        timeout: int = 10
    ):
        """
        Args:
            server: 服务器地址 (如 http://localhost:3000)
            report_endpoint: 数据上报端点
            sensor_endpoint: 传感器端点
            gateway_ip: 网关IP地址
            gateway_type: 网关类型
            mac: MAC地址
            farm_id: 基地ID
        """
        self.server = server.rstrip("/")
        self.report_url = f"{self.server}{report_endpoint}"
        self.sensor_url = f"{self.server}{sensor_endpoint}"
        self.gateway_ip = gateway_ip
        self.gateway_type = gateway_type
        self.mac = mac
        self.farm_id = farm_id
        self.timeout = timeout

    def upload_sensor_data(self, sensor_readings: List[Dict[str, Any]]) -> bool:
        """
        上传传感器数据

        Args:
            sensor_readings: 传感器数据列表
                [{"type": "temperature", "value": 25.5, "unit": "°C"}, ...]
        """
        payload = {
            "gateway_ip": self.gateway_ip,
            "gateway_type": self.gateway_type,
            "mac": self.mac,
            "farm_id": self.farm_id,
            "data": sensor_readings
        }

        try:
            resp = requests.post(
                self.report_url,
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

    def upload_from_hub(self, hub_readings: Dict[str, Any]) -> bool:
        """
        从SensorHub读取结果上传

        Args:
            hub_readings: SensorHub.read_all() 的返回值
        """
        data_list = []
        for name, reading in hub_readings.items():
            if reading.get("status") == "ok":
                sensor_data = reading.get("data", {})
                # 映射传感器类型
                sensor_type = self._map_sensor_type(name, sensor_data)
                if sensor_type and "value" in sensor_data:
                    data_list.append({
                        "type": sensor_type,
                        "value": sensor_data["value"],
                        "unit": sensor_data.get("unit", "")
                    })

        if data_list:
            return self.upload_sensor_data(data_list)
        return False

    def _map_sensor_type(self, name: str, data: Dict) -> Optional[str]:
        """映射传感器名称到API类型"""
        type_map = {
            "dht": "temperature",  # DHT有温度和湿度
            "bmp280": "pressure",
            "light": "light",
            "sound": "sound",
        }

        if name == "dht":
            # DHT同时有温度和湿度
            return None  # 需要特殊处理
        elif name == "bmp280":
            return "pressure"
        elif name == "light":
            return "light"
        elif name == "sound":
            return "sound"
        return None

    def upload_dht_data(self, temperature: float, humidity: float) -> bool:
        """上传DHT温湿度数据"""
        data = [
            {"type": "temperature", "value": temperature, "unit": "°C"},
            {"type": "humidity", "value": humidity, "unit": "%"}
        ]
        return self.upload_sensor_data(data)

    def upload_bmp280_data(self, temperature: float, pressure: float) -> bool:
        """上传BMP280数据"""
        data = [
            {"type": "temperature", "value": temperature, "unit": "°C"},
            {"type": "pressure", "value": pressure, "unit": "hPa"}
        ]
        return self.upload_sensor_data(data)

    def upload_all(self, hub_readings: Dict[str, Any]) -> bool:
        """上传所有传感器数据"""
        success = True

        for name, reading in hub_readings.items():
            if reading.get("status") != "ok":
                continue

            sensor_data = reading.get("data", {})

            if name == "dht":
                temp = sensor_data.get("temperature")
                hum = sensor_data.get("humidity")
                if temp is not None and hum is not None:
                    if not self.upload_dht_data(temp, hum):
                        success = False

            elif name == "bmp280":
                temp = sensor_data.get("temperature")
                press = sensor_data.get("pressure")
                if temp is not None and press is not None:
                    if not self.upload_bmp280_data(temp, press):
                        success = False

            elif name == "light":
                lux = sensor_data.get("lux")
                if lux is not None:
                    self.upload_sensor_data([{"type": "light", "value": lux, "unit": "lux"}])

            elif name == "sound":
                level = sensor_data.get("level")
                if level is not None:
                    self.upload_sensor_data([{"type": "sound", "value": level, "unit": "level"}])

        return success
