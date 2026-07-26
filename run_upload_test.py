#!/usr/bin/env python3
from pi_deploy import PiDeploy

d = PiDeploy()
r = d.run_code("import sys; sys.path.insert(0, '/home/pi/makerobo_code/yolo_sensor/web'); from upload_test import upload_sensor_data; upload_sensor_data()")
print(r.get("stdout", r.get("error", "")))
