#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""光敏传感器 - 基于 MCP3008 ADC"""

from sensors.base import BaseSensor

try:
    from gpiozero import MCP3008
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


class LightSensor(BaseSensor):
    """光敏电阻传感器 (通过MCP3008)"""

    def __init__(self, channel: int = 0, name: str = "light"):
        super().__init__(name=name, sensor_type="analog", pin_config={"channel": channel})
        self.channel = channel
        self._adc = None

    def initialize(self) -> bool:
        if not HAS_GPIO:
            self._initialized = True
            return True
        try:
            self._adc = MCP3008(channel=self.channel)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[Light] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        if self._adc:
            raw = self._adc.value
            lux = int(raw * 255)
            return {"raw": round(raw, 4), "lux": lux, "unit": "0-255"}
        return {"raw": 0, "lux": 0}

    def cleanup(self):
        if self._adc:
            self._adc.close()
        super().cleanup()
