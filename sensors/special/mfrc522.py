#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RFID MFRC522 读卡器 - 基于 Serial UART"""

import serial
from sensors.base import BaseSensor

try:
    from gpiozero import LED
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class Mfrc522Sensor(BaseSensor):
    """RFID MFRC522读卡器"""

    def __init__(self, enable_pin: int = 17, name: str = "rfid"):
        super().__init__(name=name, sensor_type="special", pin_config={"enable_pin": enable_pin})
        self.enable_pin = enable_pin
        self._enable = None
        self._ser = None

    def initialize(self) -> bool:
        try:
            if HAS_GPIO:
                self._enable = LED(self.enable_pin)
                self._enable.off()

            self._ser = serial.Serial(
                "/dev/ttyAMA0",
                baudrate=2400,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            self._initialized = True
            return True
        except Exception as e:
            print(f"[RFID] Init error: {e}")
            return False

    def _validate_rfid(self, code: bytes) -> str:
        try:
            decoded = code.decode("ascii")
            if decoded[0] == "\n" and decoded[-1] == "\r" and len(decoded) == 12:
                return decoded[1:-1]
        except:
            pass
        return ""

    def read_raw(self) -> dict:
        if self._ser:
            data = self._ser.read(12)
            if data:
                rfid = self._validate_rfid(data)
                if rfid:
                    return {"rfid": rfid, "valid": True}
            return {"rfid": "", "valid": False}
        return {"rfid": "", "valid": False}

    def cleanup(self):
        if self._ser:
            self._ser.close()
        if self._enable:
            self._enable.on()
        super().cleanup()
