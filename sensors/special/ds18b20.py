#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DS18B20 温度传感器 - 基于 Linux 1-Wire sysfs"""

import os
import glob
from sensors.base import BaseSensor


class Ds18b20Sensor(BaseSensor):
    """DS18B20 1-Wire温度传感器"""

    def __init__(self, name: str = "ds18b20"):
        super().__init__(name=name, sensor_type="special", pin_config={"bus": "w1"})
        self._device_folder = None

    def initialize(self) -> bool:
        try:
            # 加载内核模块
            os.system("modprobe w1-gpio")
            os.system("modprobe w1-therm")

            # 查找DS18B20设备
            base_dir = "/sys/bus/w1/devices/"
            devices = glob.glob(base_dir + "28*")
            if devices:
                self._device_folder = devices[0]
                self._initialized = True
                return True
            else:
                print("[DS18B20] No device found")
                return False
        except Exception as e:
            print(f"[DS18B20] Init error: {e}")
            return False

    def _read_temp_raw(self) -> str:
        if self._device_folder:
            with open(self._device_folder + "/w1_slave", "r") as f:
                return f.readlines()
        return []

    def read_raw(self) -> dict:
        lines = self._read_temp_raw()
        if len(lines) >= 2:
            # 等待数据有效
            while lines[0].strip()[-3:] != "YES":
                import time
                time.sleep(0.2)
                lines = self._read_temp_raw()

            # 解析温度
            pos = lines[1].find("t=")
            if pos != -1:
                temp_string = lines[1][pos + 2:]
                temp_c = float(temp_string) / 1000.0
                return {"temperature": round(temp_c, 2), "unit": "C"}
        return {"temperature": 0, "unit": "C"}

    def cleanup(self):
        super().cleanup()
