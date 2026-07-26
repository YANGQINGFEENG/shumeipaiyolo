#!/usr/bin/env python3
from pi_deploy import PiDeploy
import base64

d = PiDeploy()

# 删除错误的目录并重新创建文件
code = """
import os
import shutil

path = '/home/pi/makerobo_code/yolo_sensor/install.sh'
if os.path.isdir(path):
    shutil.rmtree(path)
    print('Deleted directory: install.sh')
"""
d.run_code(code)

# 重新上传install.sh
import time
time.sleep(1)

content = '''#!/bin/bash
# 智慧农业物联网系统安装脚本

echo "=========================================="
echo "  智慧农业物联网系统安装"
echo "=========================================="
echo

# 安装依赖
echo "安装依赖..."
pip3 install --break-system-packages -r requirements.txt

# 创建必要目录
echo "创建目录..."
mkdir -p logs data

echo
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo
echo "使用方法:"
echo "  python3 hardware/main.py    # 启动硬件系统"
echo
'''

content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
code = f"""
import base64
content = base64.b64decode('{content_b64}').decode('utf-8')
with open('/home/pi/makerobo_code/yolo_sensor/install.sh', 'w') as f:
    f.write(content)
import os
os.chmod('/home/pi/makerobo_code/yolo_sensor/install.sh', 0o755)
print('OK')
"""
d.run_code(code)
print('Deployed')
