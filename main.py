#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序 - 传感器数据采集与YOLO检测
"""

import sys
import os
import yaml
import logging
import signal

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sensors.base import SensorHub
from sensors.camera import CameraSensor
from sensors.yolo_detector import YoloDetector
from sensors.digital import LedSensor, ButtonSensor, BuzzerSensor
from sensors.analog import LightSensor, PotentiometerSensor, SoundSensor
from sensors.i2c import Bmp280Sensor, Mpu6050Sensor
from sensors.special import UltrasonicSensor, Ds18b20Sensor, PirSensor, Mfrc522Sensor
from upload.http_uploader import HttpUploader
from upload.mqtt_uploader import MqttUploader
from upload.collector import DataCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_sensors(config: dict) -> SensorHub:
    """初始化所有传感器"""
    hub = SensorHub()
    pins = config.get("pins", {})

    # 数字传感器
    digital = pins.get("digital", {})
    hub.register(LedSensor(pin=digital.get("led", {}).get("red", 17), name="led_red"))
    hub.register(ButtonSensor(pin=digital.get("button", {}).get("pin", 24)))
    hub.register(BuzzerSensor(pin=digital.get("buzzer", {}).get("pin", 22)))

    # 模拟传感器 (通过MCP3008)
    hub.register(LightSensor(channel=0, name="light"))
    hub.register(PotentiometerSensor(channel=1, name="potentiometer"))
    hub.register(SoundSensor(channel=2, name="sound"))

    # I2C传感器
    i2c = pins.get("i2c", {})
    hub.register(Bmp280Sensor(address=i2c.get("bmp280", 0x76)))
    hub.register(Mpu6050Sensor(address=i2c.get("mpu6050", 0x68)))

    # 特殊传感器
    hub.register(UltrasonicSensor(trigger=18, echo=17))
    hub.register(PirSensor(pin=pins.get("pir", {}).get("pin", 17)))

    # DS18B20 (如果启用)
    hub.register(Ds18b20Sensor())

    return hub


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("  Raspberry Pi YOLO Sensor System")
    logger.info("=" * 60)

    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(config_path)
    logger.info("Config loaded")

    # 初始化传感器
    hub = setup_sensors(config)
    logger.info(f"Sensors initialized: {hub.list()}")

    # 初始化摄像头
    camera = CameraSensor()
    camera.initialize()
    logger.info("Camera initialized")

    # 初始化YOLO
    yolo_config = config.get("yolo", {})
    yolo = YoloDetector(
        model_path=yolo_config.get("model", "yolov8n.pt"),
        confidence=yolo_config.get("confidence", 0.5)
    )
    yolo.initialize()
    logger.info("YOLO initialized")

    # 初始化上传器
    upload_config = config.get("upload", {})
    http_config = upload_config.get("http", {})
    mqtt_config = upload_config.get("mqtt", {})

    http_uploader = None
    if http_config.get("server"):
        http_uploader = HttpUploader(
            server=http_config["server"],
            endpoint=http_config.get("endpoint", "/api/data")
        )
        logger.info("HTTP uploader ready")

    mqtt_uploader = None
    if mqtt_config.get("broker"):
        mqtt_uploader = MqttUploader(
            broker=mqtt_config["broker"],
            port=mqtt_config.get("port", 1883),
            topic_prefix=mqtt_config.get("topic_prefix", "raspberrypi/sensors")
        )
        mqtt_uploader.connect()
        logger.info("MQTT uploader ready")

    # 创建数据采集器
    collector = DataCollector(
        hub=hub,
        camera=camera,
        yolo=yolo,
        http_uploader=http_uploader,
        mqtt_uploader=mqtt_uploader
    )

    # 信号处理
    def signal_handler(sig, frame):
        logger.info("Shutting down...")
        collector.stop()
        hub.cleanup_all()
        camera.cleanup()
        yolo.cleanup()
        if mqtt_uploader:
            mqtt_uploader.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 测试传感器
    logger.info("\n--- Sensor Test ---")
    results = hub.test_all()
    for name, result in results.items():
        status = "OK" if result["status"] == "ok" else "FAIL"
        logger.info(f"  {name}: {status}")

    # 开始采集循环
    interval = config.get("collection", {}).get("interval", 60)
    logger.info(f"\nStarting data collection (interval={interval}s)...")
    collector.run_loop(interval=interval)


if __name__ == "__main__":
    main()
