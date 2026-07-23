#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YOLO目标检测模块 - 基于 ultralytics"""

import time
import json
from sensors.base import BaseSensor

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False


class YoloDetector(BaseSensor):
    """YOLO目标检测"""

    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.5, name: str = "yolo"):
        super().__init__(name=name, sensor_type="ai", pin_config={"model": model_path, "confidence": confidence})
        self.model_path = model_path
        self.confidence = confidence
        self._model = None

    def initialize(self) -> bool:
        if not HAS_YOLO:
            self._initialized = True
            return True
        try:
            self._model = YOLO(self.model_path)
            self._initialized = True
            return True
        except Exception as e:
            print(f"[YOLO] Init error: {e}")
            return False

    def read_raw(self) -> dict:
        return {"model": self.model_path, "confidence": self.confidence, "ready": self._model is not None}

    def detect(self, image_path: str) -> dict:
        """检测图片中的目标"""
        if not self._model:
            return {"error": "Model not initialized"}

        try:
            results = self._model(image_path, conf=self.confidence)
            detections = []
            for r in results:
                for box in r.boxes:
                    detections.append({
                        "class": r.names[int(box.cls)],
                        "confidence": round(float(box.conf), 4),
                        "bbox": box.xyxy.tolist()
                    })
            return {"detections": detections, "count": len(detections), "image": image_path}
        except Exception as e:
            return {"error": str(e)}

    def detect_camera(self, camera=None) -> dict:
        """从摄像头实时检测"""
        if camera:
            image_path = camera.capture("/tmp/yolo_input.jpg")
            if image_path:
                return self.detect(image_path)
        return {"error": "No camera or capture failed"}

    def cleanup(self):
        self._model = None
        super().cleanup()
