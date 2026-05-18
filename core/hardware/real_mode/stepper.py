"""
Arduino Mega 2560 步进电机控制程序
基于串口通信协议

通信参数:
- 波特率: 9600
- 数据位: 8
- 校验位: 无
- 停止位: 1
- 流控制: 无

命令格式:
- S:xxx - 设置速度
- M:xxx - 相对移动（步数）
- A:xxx - 绝对移动（位置）
- Z    - 设为零点
"""

import serial
import time
import sys

PORT = "COM9"  # 默认端口，需要根据实际调整


class StepperController:
    """
    Arduino 步进电机控制器类
    提供与泵控制器类似的类接口
    """

    def __init__(self, port=PORT):
        """
        初始化步进电机控制器

        Args:
            port: 串口号，默认 COM9
        """
        self.port = port
        self.ser = None
        self.commands_log = []
        self._logger = print

    def set_logger(self, logger_func):
        """设置日志输出函数"""
        self._logger = logger_func

    def _log(self, msg):
        """统一日志输出"""
        if self._logger:
            self._logger(msg)

    def _open_serial(self):
        """打开串口连接"""
        if self.ser is None or not self.ser.is_open:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=9600,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=1
            )
            time.sleep(2)  # 等待Arduino重启复位
            self.ser.reset_input_buffer()

    def _send_command(self, cmd_str, wait_for_done=False):
        """
        发送命令

        Args:
            cmd_str: 命令字符串
            wait_for_done: 是否等待电机运动完成
        """
        if not self.ser.is_open:
            return False

        # 清空缓冲区
        self.ser.reset_input_buffer()

        full_cmd = f"{cmd_str}\n"
        self.ser.write(full_cmd.encode('utf-8'))

        # 记录命令
        self.commands_log.append(cmd_str)
        self._log(f"发送: {cmd_str}")

        # 读取确认回复
        try:
            ack = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if ack:
                self._log(f"[Arduino ACK]: {ack}")
        except Exception as e:
            self._log(f"读取ACK错误: {e}")

        # 等待完成信号
        if wait_for_done:
            self._log("  -> 等待运动完成...")
            while True:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line == "Done":
                    self._log("  -> 运动完成!")
                    break
                elif line:
                    self._log(f"[Arduino Log]: {line}")

        return True

    def set_speed(self, speed: int) -> bool:
        """
        设置电机速度

        Args:
            speed: 目标速度

        Returns:
            是否设置成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log(f"\n=== 设置电机速度为 {speed} ===")
            result = self._send_command(f"S:{speed}", wait_for_done=False)
            self._log("速度设置已发送")
            return result
        except Exception as e:
            self._log(f"设置速度失败: {e}")
            return False

    def move(self, steps: int) -> bool:
        """
        相对移动

        Args:
            steps: 移动步数（正数为正转，负数为反转）

        Returns:
            是否发送成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log(f"\n=== 相对移动 {steps} 步 ===")
            result = self._send_command(f"M:{steps}", wait_for_done=True)
            self._log("移动命令已发送")
            return result
        except Exception as e:
            self._log(f"移动失败: {e}")
            return False

    def move_to(self, position: int) -> bool:
        """
        绝对移动

        Args:
            position: 目标位置

        Returns:
            是否发送成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log(f"\n=== 移动到位置 {position} ===")
            result = self._send_command(f"A:{position}", wait_for_done=True)
            self._log("绝对移动命令已发送")
            return result
        except Exception as e:
            self._log(f"移动失败: {e}")
            return False

    def set_zero(self) -> bool:
        """
        将当前位置设为零点

        Returns:
            是否设置成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log("\n=== 设为零点 ===")
            result = self._send_command("Z", wait_for_done=False)
            self._log("零点设置已发送")
            return result
        except Exception as e:
            self._log(f"设置零点失败: {e}")
            return False

    def get_commands_log(self):
        """获取命令日志"""
        return self.commands_log.copy()

    def close(self):
        """关闭串口连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log("串口已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
