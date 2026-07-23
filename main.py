#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续传感器数据采集与上传
在树莓派终端运行: python3 main.py
"""

import sys
import os
import time
import signal
import logging

sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor')

from sensors.base import SensorHub
from sensors.digital import RgbLedSensor, RelaySensor, LaserSensor, VibrationSensor, DhtSensor
from sensors.i2c import Bmp280Sensor
from upload.http_uploader import HttpUploader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/home/pi/makerobo_code/yolo_sensor/logs/upload.log")
    ]
)
logger = logging.getLogger(__name__)

# 配置
API_SERVER = "http://192.168.1.22:3000"
GATEWAY_IP = "192.168.1.63"
MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"
FARM_ID = 1
UPLOAD_INTERVAL = 30  # 上传间隔（秒）

# 全局变量
running = True


def signal_handler(sig, frame):
    """信号处理，优雅退出"""
    global running
    logger.info("收到退出信号，正在停止...")
    running = False


def main():
    global running

    print("=" * 60)
    print("  智慧农业传感器数据持续上传")
    print("  Smart Agriculture Continuous Upload")
    print("=" * 60)
    print()

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建日志目录
    os.makedirs("/home/pi/makerobo_code/yolo_sensor/logs", exist_ok=True)

    # 初始化传感器
    logger.info("初始化传感器...")
    hub = SensorHub()
    hub.register(RgbLedSensor(red=19, green=17, blue=27, name="rgb_led"))
    hub.register(RelaySensor(pin=16, name="relay"))
    hub.register(LaserSensor(pin=13, name="laser"))
    hub.register(VibrationSensor(pin=12, name="vibration"))
    hub.register(DhtSensor(pin=6, sensor_type="DHT11", name="dht"))
    hub.register(Bmp280Sensor(name="bmp280"))
    logger.info(f"已注册 {len(hub.list())} 个传感器: {hub.list()}")

    # 初始化上传器
    logger.info("初始化上传器...")
    uploader = HttpUploader(
        server=API_SERVER,
        gateway_ip=GATEWAY_IP,
        mac=MAC_ADDRESS,
        farm_id=FARM_ID
    )

    # 测试API连接
    import requests
    try:
        resp = requests.get(f"{API_SERVER}/api/farms", timeout=5)
        if resp.status_code == 200:
            logger.info("✓ API服务器连接成功")
        else:
            logger.warning(f"API返回状态码: {resp.status_code}")
    except Exception as e:
        logger.error(f"✗ API服务器连接失败: {e}")
        logger.info("将继续尝试连接...")

    print()
    logger.info(f"开始持续上传，间隔 {UPLOAD_INTERVAL} 秒")
    logger.info("按 Ctrl+C 停止")
    print()

    # 持续上传循环
    upload_count = 0
    error_count = 0

    while running:
        try:
            # 读取传感器数据
            readings = hub.read_all()

            # 显示读取结果
            logger.info("--- 读取传感器数据 ---")
            for name, reading in readings.items():
                if reading["status"] == "ok":
                    data = reading["data"]
                    if name == "dht":
                        logger.info(f"  {name}: 温度={data.get('temperature', 'N/A')}°C 湿度={data.get('humidity', 'N/A')}%")
                    elif name == "bmp280":
                        logger.info(f"  {name}: 温度={data.get('temperature', 'N/A')}°C 气压={data.get('pressure', 'N/A')}hPa")
                    elif name == "vibration":
                        logger.info(f"  {name}: {'振动' if data.get('vibrating') else '静止'}")
                    else:
                        logger.info(f"  {name}: {data}")

            # 上传数据
            logger.info("--- 上传数据 ---")
            success = uploader.upload_all(readings)

            if success:
                upload_count += 1
                logger.info(f"✓ 上传成功 (累计: {upload_count})")
            else:
                error_count += 1
                logger.warning(f"✗ 上传失败 (错误: {error_count})")

            # 等待下一次上传
            logger.info(f"等待 {UPLOAD_INTERVAL} 秒...")
            print()

            # 分段等待，以便响应退出信号
            for _ in range(UPLOAD_INTERVAL):
                if not running:
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"循环错误: {e}")
            error_count += 1
            time.sleep(5)

    # 清理
    logger.info("正在清理资源...")
    hub.cleanup_all()

    print()
    logger.info("=" * 60)
    logger.info(f"  运行结束")
    logger.info(f"  上传次数: {upload_count}")
    logger.info(f"  错误次数: {error_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
