#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配置管理器"""

import os
import yaml
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 统一配置加载"""

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
        self.config_dir = config_dir
        self._config = {}
        self._load_all()

    def _load_all(self):
        """加载所有配置文件"""
        config_files = ["settings.yaml", "sensors.yaml", "actuators.yaml"]

        for filename in config_files:
            filepath = os.path.join(self.config_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data:
                        self._config.update(data)
                        logger.info(f"Loaded config: {filename}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_sensors(self) -> list:
        """获取传感器配置列表"""
        return self._config.get("sensors", [])

    def get_actuators(self) -> list:
        """获取执行器配置列表"""
        return self._config.get("actuators", [])

    def reload(self):
        """重新加载配置"""
        self._config.clear()
        self._load_all()
        logger.info("Config reloaded")

    def to_dict(self) -> dict:
        """导出为字典"""
        return self._config.copy()
