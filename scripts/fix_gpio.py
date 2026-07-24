#!/usr/bin/env python3
"""
GPIO资源清理脚本
用于解决GPIO busy问题，清理僵尸进程和释放GPIO资源
"""

import subprocess
import sys
import time


def clean_gpio():
    """清理GPIO资源"""
    print("=" * 50)
    print("  GPIO资源清理工具")
    print("=" * 50)
    print()

    # 1. 杀死所有Python进程
    print("1. 清理Python进程...")
    try:
        subprocess.run(["sudo", "pkill", "-9", "-f", "python3"], 
                       capture_output=True, timeout=5)
        print("   ✓ Python进程已清理")
    except Exception as e:
        print(f"   ✗ 清理失败: {e}")

    time.sleep(1)

    # 2. 清理libgpiod僵尸进程
    print("2. 清理libgpiod僵尸进程...")
    try:
        subprocess.run(["sudo", "pkill", "-9", "-f", "libgpiod"], 
                       capture_output=True, timeout=5)
        print("   ✓ libgpiod进程已清理")
    except Exception as e:
        print(f"   ✗ 清理失败: {e}")

    time.sleep(1)

    # 3. 清理gpiomem
    print("3. 清理gpiomem...")
    try:
        result = subprocess.run(["ls", "-la", "/dev/gpiomem*"], 
                               capture_output=True, text=True, timeout=5)
        if result.stdout:
            print(f"   找到: {result.stdout.strip()}")
            subprocess.run(["sudo", "chmod", "666", "/dev/gpiomem"], 
                          capture_output=True, timeout=5)
            print("   ✓ gpiomem权限已更新")
        else:
            print("   未找到gpiomem设备")
    except Exception as e:
        print(f"   ✗ 检查失败: {e}")

    time.sleep(1)

    # 4. 检查剩余进程
    print("4. 检查剩余GPIO进程...")
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        gpio_processes = []
        for line in result.stdout.split("\n"):
            if "gpio" in line.lower() or ("python" in line.lower() and "run.py" not in line):
                gpio_processes.append(line[:80])

        if gpio_processes:
            print(f"   发现 {len(gpio_processes)} 个相关进程:")
            for p in gpio_processes[:5]:
                print(f"   - {p}")
        else:
            print("   ✓ 未发现GPIO占用进程")
    except Exception as e:
        print(f"   ✗ 检查失败: {e}")

    print()
    print("=" * 50)
    print("  清理完成！")
    print("=" * 50)
    print()
    print("现在可以运行: python3 run.py start")


if __name__ == "__main__":
    clean_gpio()
