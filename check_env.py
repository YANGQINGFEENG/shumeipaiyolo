import subprocess
import sys

# SSH commands to run on Raspberry Pi
commands = """
echo "=== System Info ==="
uname -a
echo ""

echo "=== Python Version ==="
python3 --version
echo ""

echo "=== Pip Version ==="
pip3 --version
echo ""

echo "=== Key Python Packages ==="
pip3 list 2>/dev/null | grep -iE "opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|fastapi|requests|ultralytics"
echo ""

echo "=== OpenCV Version ==="
python3 -c "import cv2; print('OpenCV:', cv2.__version__)" 2>/dev/null || echo "OpenCV not installed"
echo ""

echo "=== GPIO Library ==="
python3 -c "import RPi.GPIO; print('RPi.GPIO available')" 2>/dev/null || echo "RPi.GPIO not available"
python3 -c "import gpiozero; print('gpiozero available')" 2>/dev/null || echo "gpiozero not available"
echo ""

echo "=== Camera ==="
python3 -c "from picamera2 import Picamera2; print('picamera2 available')" 2>/dev/null || echo "picamera2 not available"
echo ""

echo "=== Disk Usage ==="
df -h /
echo ""

echo "=== Memory ==="
free -h
echo ""

echo "=== CPU Info ==="
cat /proc/cpuinfo | head -20
echo ""

echo "=== Network Config ==="
hostname -I
echo ""
"""

print("Connecting to Raspberry Pi at 192.168.1.63...")
print("Username: pi")
print("=" * 60)

try:
    # Try using ssh with password via stdin
    proc = subprocess.Popen(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "PubkeyAuthentication=no", 
         "pi@192.168.1.63", commands],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(timeout=30)
    
    if stdout:
        print(stdout)
    if stderr:
        print("STDERR:", stderr)
        
except subprocess.TimeoutExpired:
    print("Connection timed out. The SSH may require password authentication.")
    proc.kill()
except Exception as e:
    print(f"Error: {e}")
