import subprocess
import sys
import os

# SSH connection details
HOST = "192.168.1.63"
USER = "pi"
PASSWORD = "pi"

# Commands to run on Raspberry Pi
COMMANDS = """
echo "=========================================="
echo "       RASPBERRY PI ENVIRONMENT CHECK"
echo "=========================================="
echo ""

echo "=== 1. System Information ==="
echo "Hostname: $(hostname)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

echo "=== 2. Python Environment ==="
echo "Python3: $(python3 --version 2>&1)"
echo "Pip3: $(pip3 --version 2>&1 | cut -d' ' -f1-2)"
echo ""

echo "=== 3. Key Python Packages ==="
pip3 list 2>/dev/null | grep -iE "opencv|yolo|torch|tensorflow|gpio|picamera|numpy|pandas|flask|fastapi|requests|ultralytics|matplotlib|scipy|pillow" || echo "No matching packages found"
echo ""

echo "=== 4. OpenCV ==="
python3 -c "import cv2; print('OpenCV Version:', cv2.__version__)" 2>&1 || echo "OpenCV: NOT INSTALLED"
echo ""

echo "=== 5. YOLO/Ultralytics ==="
python3 -c "import ultralytics; print('Ultralytics Version:', ultralytics.__version__)" 2>&1 || echo "Ultralytics: NOT INSTALLED"
echo ""

echo "=== 6. GPIO Libraries ==="
python3 -c "import RPi.GPIO; print('RPi.GPIO: AVAILABLE')" 2>&1 || echo "RPi.GPIO: NOT AVAILABLE"
python3 -c "import gpiozero; print('gpiozero: AVAILABLE')" 2>&1 || echo "gpiozero: NOT AVAILABLE"
echo ""

echo "=== 7. Camera ==="
python3 -c "from picamera2 import Picamera2; print('picamera2: AVAILABLE')" 2>&1 || echo "picamera2: NOT AVAILABLE"
echo ""

echo "=== 8. Hardware Info ==="
echo "CPU Temperature: $(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{print $1/1000 "°C"}' || echo 'N/A')"
echo "Memory: $(free -h | awk '/^Mem:/{print $2 " total, " $3 " used"}')"
echo "Disk: $(df -h / | awk 'NR==2{print $2 " total, " $3 " used, " $4 " available"}')"
echo ""

echo "=== 9. Network ==="
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "Gateway: $(ip route | grep default | awk '{print $3}')"
echo ""

echo "=========================================="
echo "       ENVIRONMENT CHECK COMPLETE"
echo "=========================================="
"""

def run_ssh_command():
    """Run SSH command using subprocess"""
    try:
        # Create SSH command
        ssh_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "PubkeyAuthentication=no",
            f"{USER}@{HOST}",
            COMMANDS
        ]

        print(f"Connecting to {HOST} as {USER}...")
        print("=" * 60)

        # Run SSH command
        # Note: This will prompt for password interactively
        # We'll use expect-like behavior
        proc = subprocess.Popen(
            ssh_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Send password when prompted
        # Wait a bit for the password prompt
        import time
        time.sleep(2)

        # Send password
        proc.stdin.write(PASSWORD + "\n")
        proc.stdin.flush()

        # Wait for command to complete
        stdout, stderr = proc.communicate(timeout=60)

        if stdout:
            print(stdout)
        if stderr:
            # Filter out SSH warnings
            for line in stderr.split('\n'):
                if "Warning:" not in line and line.strip():
                    print(f"STDERR: {line}")

        return proc.returncode

    except subprocess.TimeoutExpired:
        proc.kill()
        print("ERROR: Connection timed out")
        return -1
    except Exception as e:
        print(f"ERROR: {e}")
        return -1

if __name__ == "__main__":
    exit_code = run_ssh_command()
    sys.exit(exit_code if exit_code else 0)
