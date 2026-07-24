#!/usr/bin/env python3
"""完整部署所有修复"""
from pi_deploy import PiDeploy
import base64

d = PiDeploy()

# 所有需要更新的文件
files = {
    "config/settings.yaml": open("config/settings.yaml", "r", encoding="utf-8").read(),
    "services/upload_service.py": open("services/upload_service.py", "r", encoding="utf-8").read(),
    "app/system.py": open("app/system.py", "r", encoding="utf-8").read(),
}

print("部署更新文件...")

for filepath, content in files.items():
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    code = f"""
import base64
content = base64.b64decode('{content_b64}').decode('utf-8')
with open('/home/pi/makerobo_code/yolo_sensor/{filepath}', 'w') as f:
    f.write(content)
print('OK')
"""
    d.run_code(code)
    print(f"  {filepath}: OK")

# 清理GPIO
print("\n清理GPIO...")
d.run_code("""
import subprocess
subprocess.run(['sudo', 'pkill', '-9', '-f', 'python'], capture_output=True)
print('GPIO cleaned')
""")

print("\n部署完成!")
print("\n请在树莓派运行:")
print("  cd /home/pi/makerobo_code/yolo_sensor")
print("  python3 run.py start")
