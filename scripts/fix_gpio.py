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

    # 1. 杀死占用GPIO的Python进程
    print("1. 查找并杀死占用GPIO的进程...")
    try:
        # 查找占用gpiochip0的进程
        result = subprocess.run(["sudo", "lsof", "/dev/gpiochip0"], 
                               capture_output=True, text=True, timeout=5)
        if result.stdout:
            # 提取PID
            pids = set()
            for line in result.stdout.strip().split("\n")[1:]:  # 跳过标题
                parts = line.split()
                if len(parts) >= 2:
                    pids.add(parts[1])
            
            for pid in pids:
                print(f"   杀死进程 PID: {pid}")
                subprocess.run(["sudo", "kill", "-9", pid], 
                              capture_output=True, timeout=5)
            print(f"   ✓ 已杀死 {len(pids)} 个进程")
        else:
            print("   ✓ 未发现占用进程")
    except Exception as e:
        print(f"   ✗ 查找失败: {e}")

    time.sleep(1)

    # 2. 杀死所有Python进程
    print("2. 清理所有Python进程...")
    try:
        subprocess.run(["sudo", "pkill", "-9", "-f", "python3"], 
                       capture_output=True, timeout=5)
        print("   ✓ Python进程已清理")
    except Exception as e:
        print(f"   ✗ 清理失败: {e}")

    time.sleep(1)

    # 3. 清理libgpiod僵尸进程
    print("3. 清理libgpiod僵尸进程...")
    try:
        subprocess.run(["sudo", "pkill", "-9", "-f", "libgpiod"], 
                       capture_output=True, timeout=5)
        print("   ✓ libgpiod进程已清理")
    except Exception as e:
        print(f"   ✗ 清理失败: {e}")

    time.sleep(1)

    # 4. 清理gpiomem
    print("4. 清理gpiomem...")
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

    # 5. 验证GPIO状态
    print("5. 验证GPIO状态...")
    try:
        result = subprocess.run(["sudo", "lsof", "/dev/gpiochip0"], 
                               capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            print(f"   ⚠ 仍有进程占用GPIO:")
            for line in result.stdout.strip().split("\n")[:5]:
                print(f"   {line[:70]}")
        else:
            print("   ✓ GPIO已释放")
    except Exception as e:
        print(f"   ✗ 验证失败: {e}")

    print()
    print("=" * 50)
    print("  清理完成！")
    print("=" * 50)
    print()
    print("现在可以运行: python3 run.py start")


if __name__ == "__main__":
    clean_gpio()
