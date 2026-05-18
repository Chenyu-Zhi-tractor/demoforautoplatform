import serial
import time

# ==================== 配置参数 ====================
COM_PORT = 'COM3'           # 你的 Arduino 端口
BAUD_RATE = 115200
STEPS_PER_REVOLUTION = 400  # 一圈脉冲数

# ==================== 串口连接 ====================
def connect_arduino():
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=2)
    time.sleep(2)
    ser.flushInput()
    ser.flushOutput()
    ser.write(b'\n')
    
    print("Waiting for Arduino to be ready...")
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()
            if line == "READY":
                print("Arduino is ready!\n")
                break
    return ser

def send_cmd(cmd_str):
    """发送指令并等待完成"""
    print(f"[Python] {cmd_str}")
    ser.write((cmd_str + '\n').encode())
    
    start_time = time.time()
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()
            print(f"[Arduino] {line}")
            if line == "DONE":
                break
            elif line.startswith("ERROR"):
                print("!!! Arduino error !!!")
                break
        if time.time() - start_time > 30:
            print("!!! Timeout !!!")
            break
        time.sleep(0.01)

# ==================== 电机控制类 ====================
class Motor:
    def __init__(self, name):
        self.name = name.upper()  # STIR 或 SWITCH
    
    def set_speed_us(self, pulse_delay_us):
        """设置脉冲间隔（微秒）"""
        send_cmd(f"{self.name} S{pulse_delay_us}")
    
    def set_speed_rps(self, rps):
        """设置转速（圈/秒）"""
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        print(f"{self.name} 转速 {rps} 圈/秒 -> {pulse_delay_us} us")
        self.set_speed_us(pulse_delay_us)
    
    def rotate_steps(self, steps):
        """旋转指定步数"""
        send_cmd(f"{self.name} G{steps}")
    
    def rotate_revolutions(self, revs):
        """旋转指定圈数"""
        steps = int(revs * STEPS_PER_REVOLUTION)
        print(f"\n>>> {self.name} 旋转 {revs} 圈 ({steps} 步)")
        self.rotate_steps(steps)
    
    def rotate_seconds(self, seconds, pulse_delay_us=None):
        """旋转指定时长"""
        if pulse_delay_us is not None:
            self.set_speed_us(pulse_delay_us)
            time.sleep(0.1)
        # 需要知道当前速度才能计算，这里简化为直接调用
        print(f">>> {self.name} 旋转 {seconds} 秒")
        # 注意：这里需要你传入当前速度，或者从 Arduino 查询
        # 简化起见，建议用 rotate_revolutions

# ==================== 双电机同步控制 ====================
class DualMotors:
    @staticmethod
    def set_speed_us(pulse_delay_us):
        """同时设置两个电机的速度"""
        send_cmd(f"BOTH S{pulse_delay_us}")
    
    @staticmethod
    def set_speed_rps(rps):
        """同时设置两个电机的转速（圈/秒）"""
        pulse_delay_us = int(1_000_000 / (rps * STEPS_PER_REVOLUTION * 2))
        print(f"两电机转速 {rps} 圈/秒 -> {pulse_delay_us} us")
        DualMotors.set_speed_us(pulse_delay_us)
    
    @staticmethod
    def rotate_steps(steps):
        """两电机同时旋转指定步数"""
        send_cmd(f"BOTH G{steps}")
    
    @staticmethod
    def rotate_revolutions(revs):
        """两电机同时旋转指定圈数"""
        steps = int(revs * STEPS_PER_REVOLUTION)
        print(f"\n>>> 两电机同时旋转 {revs} 圈 ({steps} 步)")
        DualMotors.rotate_steps(steps)

# ==================== 主程序 ====================
ser = connect_arduino()

# 创建两个电机对象
stir = Motor("STIR")
switch = Motor("SWITCH")

# ==================== 使用示例 ====================
print("=" * 50)
print("双电机控制示例")
print("=" * 50)

# # 示例1：分别控制
# print("\n【搅拌电机】设置转速 2 圈/秒，转 5 圈")
# stir.set_speed_rps(2)
# stir.rotate_revolutions(5)

# time.sleep(5)

print("\n【切换电机】设置转速 1 圈/秒，转 0.25 圈")
switch.set_speed_rps(1)
switch.rotate_revolutions(0.25)



# # 示例2：搅拌电机单独慢转
# print("\n【搅拌电机】以 1000us 速度转 400 步")
# stir.set_speed_us(1000)
# stir.rotate_steps(400)

# 示例3：两电机同步
# print("\n【同步】两电机同时转 1 圈")
# DualMotors.set_speed_rps(1)
# DualMotors.rotate_revolutions(1)

# # 示例4：分别以不同速度转
# print("\n【分别控制】搅拌快转，切换慢转")
# stir.set_speed_us(200)
# switch.set_speed_us(1000)
# stir.rotate_revolutions(3)
# switch.rotate_revolutions(1)

ser.close()
print("\n--- 控制结束 ---")