import subprocess
import time
import sys

def ssh_command(host, user, password, command):
    """Execute SSH command with password authentication"""
    try:
        # Use ssh with -tt to force pseudo-terminal allocation
        proc = subprocess.Popen(
            ["ssh", "-tt", "-o", "StrictHostKeyChecking=no", f"{user}@{host}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send password
        time.sleep(1)
        proc.stdin.write(password + "\n")
        proc.stdin.flush()
        
        # Send command
        time.sleep(1)
        proc.stdin.write(command + "\n")
        proc.stdin.write("exit\n")
        proc.stdin.flush()
        
        # Wait for output
        stdout, stderr = proc.communicate(timeout=30)
        return stdout, stderr
        
    except subprocess.TimeoutExpired:
        proc.kill()
        return "", "Connection timed out"
    except Exception as e:
        return "", str(e)

# Test connection
host = "192.168.1.63"
user = "pi"
password = "pi"

print(f"Connecting to {host} as {user}...")
print("=" * 60)

commands = """
echo "=== System Info ==="
uname -a
echo ""
echo "=== Python Version ==="
python3 --version 2>&1
echo ""
echo "=== Pip Version ==="
pip3 --version 2>&1
echo ""
echo "=== Key Python Packages ==="
pip3 list 2>/dev/null | grep -iE "opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|fastapi|requests|ultralytics" 2>&1
echo ""
echo "=== OpenCV Version ==="
python3 -c "import cv2; print('OpenCV:', cv2.__version__)" 2>&1 || echo "OpenCV not installed"
echo ""
echo "=== GPIO Library ==="
python3 -c "import RPi.GPIO; print('RPi.GPIO available')" 2>&1 || echo "RPi.GPIO not available"
python3 -c "import gpiozero; print('gpiozero available')" 2>&1 || echo "gpiozero not available"
echo ""
echo "=== Camera ==="
python3 -c "from picamera2 import Picamera2; print('picamera2 available')" 2>&1 || echo "picamera2 not available"
echo ""
echo "=== Disk Usage ==="
df -h / 2>&1
echo ""
echo "=== Memory ==="
free -h 2>&1
echo ""
"""

stdout, stderr = ssh_command(host, user, password, commands)

if stdout:
    print(stdout)
if stderr:
    print("STDERR:", stderr)
