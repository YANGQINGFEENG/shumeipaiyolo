import subprocess
import sys
import time

# Try using ssh with expect-like behavior
# First, let's try to use the Windows SSH client with a different approach

def run_ssh():
    """Try to run SSH command"""
    host = "192.168.1.63"
    user = "pi"
    password = "pi"

    print(f"Connecting to {host} as {user}...")
    print("Note: You may need to enter the password manually if prompted.")
    print("=" * 60)

    # Simple approach - just run ssh and let user handle password
    cmd = f'ssh -o StrictHostKeyChecking=no {user}@{host} "uname -a && python3 --version && pip3 list 2>/dev/null | grep -iE \\"opencv|yolo|torch|gpio\\" && python3 -c \\"import cv2; print(\\'OpenCV:\\', cv2.__version__)\\" 2>/dev/null && df -h / && free -h"'

    print(f"Running: {cmd}")
    print("=" * 60)

    # Run the command
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

    print("STDOUT:")
    print(result.stdout)

    if result.stderr:
        print("STDERR (may include password prompt):")
        print(result.stderr)

    return result.returncode

if __name__ == "__main__":
    try:
        exit_code = run_ssh()
        sys.exit(exit_code)
    except subprocess.TimeoutExpired:
        print("\nConnection timed out. SSH may require password authentication.")
        print("\nPlease try manually:")
        print("  ssh pi@192.168.1.63")
        print("  Password: pi")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
