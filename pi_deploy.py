#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pi_deploy.py - 远程部署执行工具
通过JupyterLab API与树莓派通信，实现远程代码执行、文件管理、测试运行

用法:
    python pi_deploy.py status          # 查看树莓派状态
    python pi_deploy.py run <script>    # 执行远程脚本
    python pi_deploy.py upload <file>   # 上传文件
    python pi_deploy.py download <file> # 下载文件
    python pi_deploy.py test [name]     # 运行传感器测试
    python pi_deploy.py yolo <image>    # YOLO检测
    python pi_deploy.py backup          # Git备份
    python pi_deploy.py shell           # 交互式Shell
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
import websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("pi_deploy")

# 默认配置
DEFAULT_JUPYTER_URL = "http://192.168.1.63:8888"
DEFAULT_PROJECT_DIR = "/home/pi/yolo_sensor"


class PiDeploy:
    """树莓派远程部署工具"""

    def __init__(self, jupyter_url: str = DEFAULT_JUPYTER_URL):
        self.jupyter_url = jupyter_url
        self.session = requests.Session()
        self._authenticated = False

    def _authenticate(self):
        """认证JupyterLab"""
        if self._authenticated:
            return

        try:
            self.session.get(f"{self.jupyter_url}/login", timeout=10)
            xsrf = self.session.cookies.get("_xsrf")
            if xsrf:
                self.session.headers["X-XSRFToken"] = xsrf
            self._authenticated = True
            logger.info("JupyterLab authenticated")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def execute_code(self, code: str, timeout: int = 30) -> dict:
        """
        通过Kernel WebSocket执行代码

        Args:
            code: Python代码
            timeout: 超时时间(秒)

        Returns:
            {"stdout": ..., "stderr": ..., "error": ...}
        """
        self._authenticate()

        # 创建kernel
        resp = self.session.post(
            f"{self.jupyter_url}/api/kernels",
            json={"name": "python3"},
            timeout=10
        )
        if resp.status_code != 201:
            return {"error": f"Failed to create kernel: {resp.text}"}

        kernel_id = resp.json()["id"]
        logger.info(f"Kernel created: {kernel_id}")

        # 等待kernel启动
        time.sleep(5)

        try:
            # 连接WebSocket
            ws_url = f"ws://{self.jupyter_url.replace('http://', '')}/api/kernels/{kernel_id}/channels"
            ws = websocket.create_connection(ws_url, timeout=10)
            logger.info("WebSocket connected")

            time.sleep(1)
            # 消耗初始消息
            while True:
                try:
                    ws.settimeout(0.5)
                    ws.recv()
                except:
                    break

            # 发送执行请求
            msg = {
                "header": {
                    "msg_id": f"deploy_{int(time.time())}",
                    "msg_type": "execute_request",
                    "username": "pi",
                    "session": "deploy_session",
                    "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "version": "5.3"
                },
                "parent_header": {},
                "metadata": {},
                "content": {
                    "code": code,
                    "silent": False,
                    "store_history": False,
                    "user_expressions": {},
                    "allow_stdin": False
                }
            }
            ws.send(json.dumps(msg))
            logger.info("Code sent, waiting for execution...")

            # 收集输出
            stdout_lines = []
            stderr_lines = []
            traceback_lines = []
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    ws.settimeout(2)
                    data = ws.recv()
                    msg = json.loads(data)
                    msg_type = msg.get("msg_type", "")

                    if msg_type == "stream":
                        content = msg.get("content", {})
                        text = content.get("text", "")
                        name = content.get("name", "")
                        if name == "stderr":
                            stderr_lines.append(text)
                        else:
                            stdout_lines.append(text)
                    elif msg_type == "execute_result":
                        content = msg.get("content", {})
                        data_dict = content.get("data", {})
                        text = data_dict.get("text/plain", "")
                        stdout_lines.append(text)
                    elif msg_type == "error":
                        content = msg.get("content", {})
                        traceback_lines.extend(content.get("traceback", []))
                    elif msg_type == "status":
                        content = msg.get("content", {})
                        if content.get("execution_state") == "idle":
                            break
                except:
                    continue

            ws.close()

            return {
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "traceback": traceback_lines
            }

        except Exception as e:
            return {"error": str(e)}
        finally:
            # 删除kernel
            try:
                self.session.delete(
                    f"{self.jupyter_url}/api/kernels/{kernel_id}",
                    timeout=5
                )
            except:
                pass

    def upload_file(self, local_path: str, remote_path: str = None) -> bool:
        """上传文件到树莓派"""
        self._authenticate()

        if remote_path is None:
            remote_path = os.path.basename(local_path)

        # 读取文件内容
        with open(local_path, "rb") as f:
            content = f.read()

        # 上传到JupyterLab
        import base64
        content_b64 = base64.b64encode(content).decode("utf-8")

        # 确定文件类型
        if local_path.endswith(".ipynb"):
            file_type = "notebook"
            body = json.loads(content)
        else:
            file_type = "file"
            body = {
                "content": content_b64,
                "encoding": "base64",
                "type": "file",
                "format": "base64"
            }

        resp = self.session.put(
            f"{self.jupyter_url}/api/contents/{remote_path}",
            json=body,
            timeout=30
        )

        if resp.status_code in [200, 201]:
            logger.info(f"File uploaded: {local_path} -> {remote_path}")
            return True
        else:
            logger.error(f"Upload failed: {resp.text}")
            return False

    def download_file(self, remote_path: str, local_path: str = None) -> bool:
        """从树莓派下载文件"""
        self._authenticate()

        if local_path is None:
            local_path = os.path.basename(remote_path)

        resp = self.session.get(
            f"{self.jupyter_url}/api/contents/{remote_path}",
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("content", "")

            with open(local_path, "w", encoding="utf-8") as f:
                if isinstance(content, list):
                    f.writelines(content)
                else:
                    f.write(str(content))

            logger.info(f"File downloaded: {remote_path} -> {local_path}")
            return True
        else:
            logger.error(f"Download failed: {resp.text}")
            return False

    def run_script(self, script_path: str) -> dict:
        """执行远程脚本"""
        with open(script_path, "r", encoding="utf-8") as f:
            code = f.read()

        logger.info(f"Executing script: {script_path}")
        return self.execute_code(code, timeout=60)

    def run_code(self, code: str) -> dict:
        """执行代码"""
        logger.info("Executing code...")
        return self.execute_code(code, timeout=30)

    def test_sensors(self, sensor_name: str = None) -> dict:
        """运行传感器测试"""
        code = """
import sys
sys.path.insert(0, '/home/pi/yolo_sensor')

from sensors.base import SensorHub
import json

hub = SensorHub()

# 动态加载传感器
sensor_modules = {
    "led": "sensors.digital.led",
    "buzzer": "sensors.digital.buzzer",
    "ultrasonic": "sensors.special.ultrasonic",
    "bmp280": "sensors.i2c.bmp280",
    "mpu6050": "sensors.i2c.mpu6050",
    "pir": "sensors.special.pir",
    "ds18b20": "sensors.special.ds18b20",
}

for name, module_path in sensor_modules.items():
    try:
        import importlib
        mod = importlib.import_module(module_path)
        sensor_cls = getattr(mod, name.capitalize() + 'Sensor')
        hub.register(sensor_cls())
    except Exception as e:
        print(f"Failed to load {name}: {e}")

# 测试所有传感器
if {sensor_name is not None}:
    result = hub.get("{sensor_name or ''}").test() if hub.get("{sensor_name or ''}") else {{"status": "not_found"}}
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    results = hub.test_all()
    print(json.dumps(results, indent=2, ensure_ascii=False))

hub.cleanup_all()
""".replace("{sensor_name is not None}", str(sensor_name is not None)) \
  .replace("{sensor_name or ''}", sensor_name or "")

        return self.execute_code(code, timeout=30)

    def run_yolo(self, image_source: str = "camera") -> dict:
        """运行YOLO检测"""
        if image_source == "camera":
            code = """
from ultralytics import YOLO
from picamera2 import Picamera2
import json
import time

# 拍照
picam2 = Picamera2()
picam2.start()
time.sleep(2)
picam2.capture_file("/tmp/yolo_input.jpg")
picam2.stop()

# 检测
model = YOLO("/home/pi/yolo_sensor/models/yolov8n.pt")
results = model("/tmp/yolo_input.jpg")

output = []
for r in results:
    for box in r.boxes:
        output.append({
            "class": r.names[int(box.cls)],
            "confidence": float(box.conf),
            "bbox": box.xyxy.tolist()
        })

print(json.dumps({"detections": output, "count": len(output)}, indent=2))
"""
        else:
            code = f"""
from ultralytics import YOLO
import json

model = YOLO("/home/pi/yolo_sensor/models/yolov8n.pt")
results = model("{image_source}")

output = []
for r in results:
    for box in r.boxes:
        output.append({{
            "class": r.names[int(box.cls)],
            "confidence": float(box.conf),
            "bbox": box.xyxy.tolist()
        }})

print(json.dumps({{"detections": output, "count": len(output)}}, indent=2))
"""

        return self.execute_code(code, timeout=60)

    def git_backup(self, message: str = None) -> dict:
        """Git备份"""
        if message is None:
            message = f"Auto backup {time.strftime('%Y-%m-%d %H:%M:%S')}"

        code = f"""
import subprocess
import os

os.chdir('/home/pi/yolo_sensor')

# 初始化Git (如果需要)
if not os.path.exists('.git'):
    subprocess.run(['git', 'init'], check=True)
    subprocess.run(['git', 'config', 'user.email', 'pi@raspberrypi'], check=True)
    subprocess.run(['git', 'config', 'user.name', 'Pi'], check=True)

# 添加和提交
subprocess.run(['git', 'add', '.'], check=True)
result = subprocess.run(
    ['git', 'commit', '-m', '[auto] {message}'],
    capture_output=True, text=True
)

if result.returncode == 0:
    print(f"Backup successful: {{result.stdout}}")
else:
    print(f"Nothing to commit or error: {{result.stderr}}")

# 显示最近提交
result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
print("Recent commits:")
print(result.stdout)
"""

        return self.execute_code(code, timeout=15)

    def get_status(self) -> dict:
        """获取树莓派状态"""
        code = """
import subprocess
import json

status = {}

# 系统信息
result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
status['system'] = result.stdout.strip()

# Python版本
result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
status['python'] = result.stdout.strip()

# 内存
result = subprocess.run(['free', '-h'], capture_output=True, text=True)
status['memory'] = result.stdout.strip()

# 磁盘
result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
status['disk'] = result.stdout.strip()

# 温度
try:
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        temp = int(f.read().strip()) / 1000
        status['temperature'] = f"{temp:.1f}°C"
except:
    status['temperature'] = "N/A"

# 网络
result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
status['ip'] = result.stdout.strip()

print(json.dumps(status, indent=2, ensure_ascii=False))
"""

        return self.execute_code(code, timeout=10)


def main():
    parser = argparse.ArgumentParser(description="树莓派远程部署工具")
    parser.add_argument("--url", default=DEFAULT_JUPYTER_URL, help="JupyterLab URL")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # status
    subparsers.add_parser("status", help="查看树莓派状态")

    # run
    run_parser = subparsers.add_parser("run", help="执行脚本")
    run_parser.add_argument("script", help="脚本路径")

    # upload
    upload_parser = subparsers.add_parser("upload", help="上传文件")
    upload_parser.add_argument("file", help="本地文件路径")
    upload_parser.add_argument("-r", "--remote", help="远程路径")

    # download
    download_parser = subparsers.add_parser("download", help="下载文件")
    download_parser.add_argument("file", help="远程文件路径")
    download_parser.add_argument("-l", "--local", help="本地路径")

    # test
    test_parser = subparsers.add_parser("test", help="运行传感器测试")
    test_parser.add_argument("sensor", nargs="?", help="传感器名称")

    # yolo
    yolo_parser = subparsers.add_parser("yolo", help="YOLO检测")
    yolo_parser.add_argument("image", nargs="?", default="camera", help="图片路径或camera")

    # backup
    backup_parser = subparsers.add_parser("backup", help="Git备份")
    backup_parser.add_argument("-m", "--message", help="提交信息")

    # shell
    subparsers.add_parser("shell", help="交互式代码执行")

    args = parser.parse_args()
    deploy = PiDeploy(args.url)

    if args.command == "status":
        result = deploy.get_status()
        print(result.get("stdout", result.get("error", "Unknown error")))

    elif args.command == "run":
        result = deploy.run_script(args.script)
        print(result.get("stdout", ""))
        if result.get("stderr"):
            print("STDERR:", result["stderr"], file=sys.stderr)
        if result.get("traceback"):
            for tb in result["traceback"]:
                print(tb, file=sys.stderr)

    elif args.command == "upload":
        deploy.upload_file(args.file, args.remote)

    elif args.command == "download":
        deploy.download_file(args.file, args.local)

    elif args.command == "test":
        result = deploy.test_sensors(args.sensor)
        print(result.get("stdout", result.get("error", "Unknown error")))

    elif args.command == "yolo":
        result = deploy.run_yolo(args.image)
        print(result.get("stdout", result.get("error", "Unknown error")))

    elif args.command == "backup":
        result = deploy.git_backup(args.message)
        print(result.get("stdout", result.get("error", "Unknown error")))

    elif args.command == "shell":
        print("Interactive shell (type 'exit' to quit):")
        while True:
            try:
                code = input(">>> ")
                if code.strip() == "exit":
                    break
                result = deploy.run_code(code)
                if result.get("stdout"):
                    print(result["stdout"])
                if result.get("error"):
                    print(f"Error: {result['error']}")
            except KeyboardInterrupt:
                print()
            except EOFError:
                break

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
