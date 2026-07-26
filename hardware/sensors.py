#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传感器实现
"""

import time
import logging
from typing import Any, Dict
from hardware.core import BaseSensor

logger = logging.getLogger(__name__)


class DHTSensor(BaseSensor):
    """DHT11/DHT22 温湿度传感器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 6, sensor_type: str = "DHT11"):
        super().__init__(node_id, name, "temperature")
        self.pin = pin
        self.dht_type = sensor_type
        self._device = None
    
    def initialize(self) -> bool:
        try:
            import board
            import adafruit_dht
            
            if self.dht_type.upper() == "DHT22":
                self._device = adafruit_dht.DHT22(getattr(board, f"D{self.pin}"))
            else:
                self._device = adafruit_dht.DHT11(getattr(board, f"D{self.pin}"))
            
            self.logger.info(f"DHT initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": None, "unit": "", "quality": "unavailable"}
        
        try:
            temp = self._device.temperature
            hum = self._device.humidity
            
            if temp is None or hum is None:
                return {"value": None, "unit": "", "quality": "error"}
            
            self._value = {"temperature": round(temp, 2), "humidity": round(hum, 2)}
            self._unit = "°C/%"
            self._last_time = datetime.now()
            
            return {
                "value": self._value,
                "unit": self._unit,
                "quality": "good"
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": "error"}


class BMP280Sensor(BaseSensor):
    """BMP280 气压温度传感器"""
    
    def __init__(self, node_id: str, name: str, address: int = 0x76):
        super().__init__(node_id, name, "pressure")
        self.address = address
        self._device = None
    
    def initialize(self) -> bool:
        try:
            import board
            import adafruit_bmp280
            
            i2c = board.I2C()
            self._device = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=self.address)
            self._device.sea_level_pressure = 1013.25
            
            self.logger.info(f"BMP280 initialized: address=0x{self.address:02X}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": None, "unit": "", "quality": "unavailable"}
        
        try:
            temp = self._device.temperature
            press = self._device.pressure
            alt = self._device.altitude
            
            self._value = {
                "temperature": round(temp, 2),
                "pressure": round(press, 2),
                "altitude": round(alt, 2)
            }
            self._unit = "°C/hPa/m"
            self._last_time = datetime.now()
            
            return {
                "value": self._value,
                "unit": self._unit,
                "quality": "good"
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": "error"}


class VibrationSensor(BaseSensor):
    """振动传感器"""
    
    def __init__(self, node_id: str, name: str, pin: int = 12):
        super().__init__(node_id, name, "vibration")
        self.pin = pin
        self._device = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import Button
            self._device = Button(self.pin)
            self.logger.info(f"Vibration sensor initialized: pin={self.pin}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        if not self._device:
            return {"value": False, "unit": "", "quality": "unavailable"}
        
        try:
            vibrating = self._device.is_pressed
            self._value = vibrating
            self._unit = ""
            self._last_time = datetime.now()
            
            return {
                "value": vibrating,
                "unit": self._unit,
                "quality": "good"
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": "error"}


class LightSensor(BaseSensor):
    """光照传感器"""
    
    def __init__(self, node_id: str, name: str, channel: int = 0):
        super().__init__(node_id, name, "light")
        self.channel = channel
        self._adc = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import MCP3008
            self._adc = MCP3008(channel=self.channel)
            self.logger.info(f"Light sensor initialized: channel={self.channel}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        if not self._adc:
            return {"value": None, "unit": "", "quality": "unavailable"}
        
        try:
            raw = self._adc.value
            lux = int(raw * 1000)
            self._value = lux
            self._unit = "lux"
            self._last_time = datetime.now()
            
            return {
                "value": lux,
                "unit": "lux",
                "quality": "good"
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": "error"}


class SoilMoistureSensor(BaseSensor):
    """土壤湿度传感器"""
    
    def __init__(self, node_id: str, name: str, channel: int = 1):
        super().__init__(node_id, name, "soil_moisture")
        self.channel = channel
        self._adc = None
    
    def initialize(self) -> bool:
        try:
            from gpiozero import MCP3008
            self._adc = MCP3008(channel=self.channel)
            self.logger.info(f"Soil moisture sensor initialized: channel={self.channel}")
            return True
        except Exception as e:
            self.logger.error(f"Init error: {e}")
            return False
    
    def read(self) -> Dict[str, Any]:
        if not self._adc:
            return {"value": None, "unit": "", "quality": "unavailable"}
        
        try:
            raw = self._adc.value
            moisture = int(raw * 100)
            self._value = moisture
            self._unit = "%"
            self._last_time = datetime.now()
            
            return {
                "value": moisture,
                "unit": "%",
                "quality": "good"
            }
        except Exception as e:
            self.logger.error(f"Read error: {e}")
            return {"value": None, "unit": "", "quality": "error"}
