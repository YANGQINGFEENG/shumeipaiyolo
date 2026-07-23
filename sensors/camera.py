#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""摄像头模块 - 基于 picamera2"""

import time
from sensors.base import BaseSensor

try:
    from picamera2 import Picamera2
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False


class CameraSensor(BaseSensor):
    """树莓派摄像头"""

    def __init__(self, name: str = "camera"):
        super().__init__(name=name, sensor_type="camera", pin_config={})
        self._camera = None

    def initialize(self) -> bool:
        if not HAS_CAMERA:
            self._initialized = True
            return True
        try:
            self._camera = Picamera2()
            config = self._camera.create_still_configuration()
            self._camera.configure(config)
            self._camera.start()
            time.sleep(2)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Camera] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"status": "ready" if self._camera else "not_initialized"}

    def capture(self, filepath: str = "/tmp/capture.jpg") -> str:
        """拍照并保存"""
        if self._camera:
            self._camera.capture_file(filepath)
            return filepath
        return ""

    def capture_bytes(self) -> bytes:
        """拍照并返回字节数据"""
        if self._camera:
            return self._camera.capture_array()
        return b""

    def cleanup(self):
        if self._camera:
            self._camera.stop()
            self._camera.close()
        super().cleanup()
