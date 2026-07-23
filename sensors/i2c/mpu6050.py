#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MPU6050 陀螺仪加速度传感器 - 基于 mpu6050-raspberrypi"""

from sensors.base import BaseSensor

try:
    import mpu6050
    HAS_MPU = True
except ImportError:
    HAS_MPU = False


class Mpu6050Sensor(BaseSensor):
    """MPU6050 6轴陀螺仪加速度传感器"""

    def __init__(self, address: int = 0x68, name: str = "mpu6050"):
        super().__init__(name=name, sensor_type="i2c", pin_config={"address": address})
        self.address = address
        self._device = None

    def initialize(self) -> bool:
        if not HAS_MPU:
            self._initialized = True
            return True
        try:
            self._device = mpu6050.mpu6050(self.address)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[MPU6050] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._device:
            accel = self._device.get_accel_data()
            gyro = self._device.get_gyro_data()
            temp = self._device.get_temp()
            return {
                "accelerometer": {"x": round(accel["x"], 4), "y": round(accel["y"], 4), "z": round(accel["z"], 4)},
                "gyroscope": {"x": round(gyro["x"], 4), "y": round(gyro["y"], 4), "z": round(gyro["z"], 4)},
                "temperature": round(temp, 2)
            }
        return {"accelerometer": {"x": 0, "y": 0, "z": 0}, "gyroscope": {"x": 0, "y": 0, "z": 0}, "temperature": 0}

    def get_acceleration(self) -> dict:
        if self._device:
            return self._device.get_accel_data()
        return {"x": 0, "y": 0, "z": 0}

    def get_gyroscope(self) -> dict:
        if self._device:
            return self._device.get_gyro_data()
        return {"x": 0, "y": 0, "z": 0}

    def get_temperature(self) -> float:
        if self._device:
            return self._device.get_temp()
        return 0.0

    def cleanup(self):
        super().cleanup()
