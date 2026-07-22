import subprocess
import time

# 创建SSH进程
proc = subprocess.Popen(
    ['ssh', '-tt', '-o', 'StrictHostKeyChecking=no', 'pi@192.168.1.63'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待密码提示
time.sleep(2)

# 发送密码
proc.stdin.write('pi\n')
proc.stdin.flush()

# 等待登录完成
time.sleep(2)

# 执行命令
commands = [
    'uname -a',
    'python3 --version',
    'pip3 list 2>/dev/null | grep -iE "opencv|yolo|torch|gpio|picamera" || echo "no packages found"',
    'python3 -c "import cv2; print(\'OpenCV:\', cv2.__version__)" 2>/dev/null || echo "OpenCV not installed"',
    'python3 -c "import gpiozero; print(\'gpiozero: Available\')" 2>/dev/null || echo "gpiozero not available"',
    'df -h /',
    'free -h',
    'exit'
]

for cmd in commands:
    proc.stdin.write(cmd + '\n')
    proc.stdin.flush()
    time.sleep(0.5)

# 读取输出
stdout, stderr = proc.communicate(timeout=30)
print('STDOUT:')
print(stdout)
if stderr:
    print('STDERR:')
    print(stderr)
