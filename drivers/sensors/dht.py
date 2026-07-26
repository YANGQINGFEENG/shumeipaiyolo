#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DHT11/DHT22 温湿度传感器 - 参考程序案例逻辑，使用 lgpio"""

import time
from datetime import datetime
from typing import Any, Dict
from drivers.sensors.base import BaseSensor, DataQuality

try:
    import lgpio
    HAS_LGPIO = True
except ImportError:
    HAS_LGPIO = False


class DHTSensor(BaseSensor):
    """DHT11/DHT22 温湿度传感器"""

    def __init__(self, sensor_id: str = "dht11", name: str = "温湿度传感器",
                 pin: int = 6, sensor_type: str = "DHT11", config: Dict = None):
        super().__init__(sensor_id, name, sensor_type.lower(), config)
        self.pin = pin
        self.sensor_type = sensor_type.upper()
        self._initialized = False
        self._h = None
        self._last_value = {"temperature": None, "humidity": None}
        self._last_time = None

    def initialize(self) -> bool:
        """初始化传感器"""
        if HAS_LGPIO:
            try:
                self._h = lgpio.gpiochip_open(0)
                if self._h < 0:
                    self.logger.error("lgpio chip open failed")
                    return False
                self._initialized = True
                self.logger.info(f"DHT initialized (lgpio): pin={self.pin}, type={self.sensor_type}")
                return True
            except Exception as e:
                self.logger.error(f"DHT lgpio init error: {e}")
                return False
        else:
            self.logger.warning("No GPIO library available, running in test mode")
            self._initialized = True
            return True

    def _bits_to_byte(self, bits):
        """将8位二进制数据转换为字节"""
        byte = 0
        for bit in bits:
            byte = (byte << 1) | bit
        return byte

    def read(self) -> Dict[str, Any]:
        """读取传感器数据"""
        if not self._initialized:
            return {"value": None, "unit": "", "quality": DataQuality.UNAVAILABLE}

        if HAS_LGPIO and self._h is not None:
            try:
                # 发送开始信号
                lgpio.gpio_claim_output(self._h, self.pin)
                lgpio.gpio_write(self._h, self.pin, 0)
                time.sleep(0.018)
                lgpio.gpio_write(self._h, self.pin, 1)
                time.sleep(0.00002)
                
                # 切换到输入模式
                lgpio.gpio_claim_input(self._h, self.pin)
                
                # 读取响应信号
                timeout = time.time() + 0.01
                while lgpio.gpio_read(self._h, self.pin) == 0:
                    if time.time() > timeout:
                        self.logger.error("DHT response timeout (LOW)")
                        return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                
                timeout = time.time() + 0.01
                while lgpio.gpio_read(self._h, self.pin) == 1:
                    if time.time() > timeout:
                        self.logger.error("DHT response timeout (HIGH)")
                        return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                
                # 读取40位数据
                data = []
                for _ in range(40):
                    timeout = time.time() + 0.01
                    while lgpio.gpio_read(self._h, self.pin) == 0:
                        if time.time() > timeout:
                            self.logger.error("DHT data read timeout")
                            return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                    
                    start_time = time.time()
                    timeout = time.time() + 0.01
                    while lgpio.gpio_read(self._h, self.pin) == 1:
                        if time.time() > timeout:
                            self.logger.error("DHT data read timeout")
                            return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                    
                    duration = time.time() - start_time
                    if duration > 0.000028:
                        data.append(1)
                    else:
                        data.append(0)
                
                # 解析数据
                humidity_high = self._bits_to_byte(data[0:8])
                humidity_low = self._bits_to_byte(data[8:16])
                temp_high = self._bits_to_byte(data[16:24])
                temp_low = self._bits_to_byte(data[24:32])
                checksum = self._bits_to_byte(data[32:40])
                
                # 验证校验和
                if (humidity_high + humidity_low + temp_high + temp_low) & 0xFF != checksum:
                    self.logger.warning("DHT checksum error")
                    return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                
                # 计算温度和湿度
                if self.sensor_type == "DHT11":
                    temperature = temp_high
                    humidity = humidity_high
                else:
                    temperature = (temp_high << 8) + temp_low
                    humidity = (humidity_high << 8) + humidity_low
                    if temperature > 0x8000:
                        temperature = -((temperature ^ 0xFFFF) + 1)
                    temperature /= 10.0
                    humidity /= 10.0
                
                if humidity < 0 or humidity > 100:
                    return {"value": None, "unit": "", "quality": DataQuality.ERROR}
                
                self._last_value = {
                    "temperature": temperature,
                    "humidity": humidity
                }
                self._last_time = datetime.now()

                return {
                    "value": self._last_value,
                    "unit": {"temperature": "°C", "humidity": "%"},
                    "quality": DataQuality.GOOD
                }
            except Exception as e:
                self.logger.error(f"DHT read error: {e}")
                return {"value": None, "unit": "", "quality": DataQuality.ERROR}
        else:
            # 测试模式
            self._last_value = {"temperature": 25.0, "humidity": 50.0}
            self._last_time = datetime.now()
            return {
                "value": self._last_value,
                "unit": {"temperature": "°C", "humidity": "%"},
                "quality": DataQuality.GOOD
            }

    def cleanup(self):
        """释放资源"""
        if HAS_LGPIO and self._h is not None:
            try:
                lgpio.gpio_write(self._h, self.pin, 1)
                lgpio.gpio_free(self._h, self.pin)
                lgpio.gpiochip_close(self._h)
            except:
                pass
        self._initialized = False
