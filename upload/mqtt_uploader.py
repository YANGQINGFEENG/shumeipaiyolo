#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT 数据发布
"""

import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False


class MqttUploader:
    """MQTT数据发布器"""

    def __init__(
        self,
        broker: str,
        port: int = 1883,
        topic_prefix: str = "raspberrypi/sensors",
        username: str = None,
        password: str = None,
        qos: int = 1
    ):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.qos = qos
        self._client = None

        if not HAS_MQTT:
            logger.warning("paho-mqtt not installed, MQTT uploader disabled")
            return

        self._client = mqtt.Client()
        if username:
            self._client.username_pw_set(username, password)

    def connect(self) -> bool:
        """连接MQTT Broker"""
        if not self._client:
            return False

        try:
            self._client.connect(self.broker, self.port, 60)
            self._client.loop_start()
            logger.info(f"MQTT connected to {self.broker}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False

    def publish(self, topic: str, data: Any) -> bool:
        """
        发布消息

        Args:
            topic: 主题 (会自动添加前缀)
            data: 数据 (会自动序列化为JSON)
        """
        if not self._client:
            return False

        full_topic = f"{self.topic_prefix}/{topic}"
        payload = json.dumps(data) if isinstance(data, dict) else str(data)

        try:
            result = self._client.publish(full_topic, payload, qos=self.qos)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published to {full_topic}")
                return True
            else:
                logger.error(f"Publish failed: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    def publish_sensor(self, sensor_name: str, data: Dict[str, Any]) -> bool:
        """发布传感器数据"""
        return self.publish(sensor_name, {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "data": data
        })

    def publish_all(self, readings: Dict[str, Any]) -> bool:
        """发布所有传感器数据"""
        return self.publish("all", {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sensors": readings
        })

    def disconnect(self):
        """断开连接"""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            logger.info("MQTT disconnected")
