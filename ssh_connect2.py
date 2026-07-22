import subprocess
import time

# 尝试不同的密码
passwords = ['pi', 'raspberry', '192.168.1.63', 'password']

for pwd in passwords:
    print(f"\n尝试密码: {pwd}")
    print("-" * 40)

    try:
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
        proc.stdin.write(pwd + '\n')
        proc.stdin.flush()

        # 等待登录完成
        time.sleep(3)

        # 发送一个简单命令测试
        proc.stdin.write('echo "LOGIN_SUCCESS"\n')
        proc.stdin.flush()

        # 等待响应
        time.sleep(2)

        # 发送退出
        proc.stdin.write('exit\n')
        proc.stdin.flush()

        # 读取输出
        stdout, stderr = proc.communicate(timeout=10)

        if 'LOGIN_SUCCESS' in stdout:
            print(f"成功! 密码是: {pwd}")
            print("STDOUT:", stdout)
            break
        else:
            print("登录失败")
            if stderr:
                print("STDERR:", stderr[:200])

    except subprocess.TimeoutExpired:
        proc.kill()
        print("超时")
    except Exception as e:
        print(f"错误: {e}")
