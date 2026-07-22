#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BMP280 气压传感器 / BMP280 Barometric Pressure Sensor
"""

from sensors.base import BaseSensor

try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False


class Bmp280Sensor(BaseSensor):
    """BMP280 气压温度传感器"""

    # BMP280寄存器地址
    REG_ID = 0xD0
    REG_CTRL_MEAS = 0xF4
    REG_CONFIG = 0xF5
    REG_PRESS_MSB = 0xF7
    REG_TEMP_MSB = 0xFA

    def __init__(self, address: int = 0x76, name: str = "bmp280"):
        super().__init__(
            name=name,
            sensor_type="i2c",
            pin_config={"address": address}
        )
        self.address = address
        self._bus = None

    def initialize(self) -> bool:
        if not HAS_SMBUS:
            print("[BMP280] smbus not available, running in test mode")
            self._initialized = True
            return True

        try:
            self._bus = smbus2.SMBus(1)
            # 验证芯片ID
            chip_id = self._bus.read_byte_data(self.address, self.REG_ID)
            if chip_id != 0x58:
                print(f"[BMP280] Invalid chip ID: {chip_id}")
                return False

            # 配置
            self._bus.write_byte_data(self.address, self.REG_CTRL_MEAS, 0x27)
            self._bus.write_byte_data(self.address, self.REG_CONFIG, 0xA0)

            self._initialized = True
            return True
        except Exception as e:
            print(f"[BMP280] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if not self._bus:
            return {"temperature": 25.0, "pressure": 1013.25, "unit_temp": "C", "unit_press": "hPa"}

        try:
            # 读取原始数据
            data = self._bus.read_i2c_block_data(self.address, self.REG_PRESS_MSB, 6)

            # 解析温度
            raw_temp = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
            temp = raw_temp / 5120.0

            # 解析气压
            raw_press = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
            press = raw_press / 256.0 / 100.0

            return {
                "temperature": round(temp, 2),
                "pressure": round(press, 2),
                "unit_temp": "C",
                "unit_press": "hPa"
            }
        except Exception as e:
            return {"error": str(e)}

    def cleanup(self):
        if self._bus:
            self._bus.close()
        super().cleanup()
