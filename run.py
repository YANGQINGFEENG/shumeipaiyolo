#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智慧农业物联网系统 - 启动脚本

用法:
    python3 run.py start      # 启动系统
    python3 run.py test       # 运行测试
    python3 run.py sensors    # 读取传感器
    python3 run.py status     # 查看状态
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system.cli import main

if __name__ == "__main__":
    main()
