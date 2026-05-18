"""
Arduino Mega 2560 步进电机控制程序 - 虚拟调试模式
基于串口通信协议 - 仅记录命令不实际发送

命令格式:
- S:xxx - 设置速度
- M:xxx - 相对移动（步数）
- A:xxx - 绝对移动（位置）
- Z    - 设为零点
"""

import time

PORT = "COM13"


class MockSerial:
    """[虚拟模式] 模拟串口 - 仅记录命令不实际发送"""

    def __init__(self, port='COM13'):
        self.port = port
        self.is_open = True

    def close(self):
        self.is_open = False
        print(f"[Virtual] 串口 {self.port} 已关闭")

    def write(self, data):
        """记录命令但不实际发送"""
        cmd_str = data.decode('utf-8').strip()
        print(f"[Virtual] 记录命令: {cmd_str}")

    def flush(self):
        """模拟刷新缓冲区"""
        pass

    def reset_input_buffer(self):
        """模拟清空输入缓冲区"""
        pass

    def reset_output_buffer(self):
        """模拟清空输出缓冲区"""
        pass

    def readline(self):
        """模拟读取回复"""
        return b"Ready\n"


class StepperController:
    """
    Arduino 步进电机控制器类（虚拟模式）
    提供与真实控制器相同的接口，但不实际发送命令
    """

    def __init__(self, port=PORT):
        """
        初始化步进电机控制器

        Args:
            port: 串口号，默认 COM13
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

    def _send_command(self, cmd_str, wait_for_done=False):
        """
        发送命令（虚拟模式 - 仅记录）

        Args:
            cmd_str: 命令字符串
            wait_for_done: 是否模拟等待完成
        """
        if self.ser is None:
            self.ser = MockSerial(self.port)

        # 记录命令
        self.commands_log.append(cmd_str)
        self._log(f"[Virtual] 发送: {cmd_str}")

        # 模拟Arduino回复
        time.sleep(0.05)  # 虚拟模式下减少等待时间

        if cmd_str.startswith("M:") or cmd_str.startswith("A:"):
            self._log("[Virtual] [Arduino ACK]: Move: xxx")
            if wait_for_done:
                self._log("[Virtual]   -> 等待运动完成...")
                time.sleep(0.1)
                self._log("[Virtual]   -> 运动完成!")
                self._log("[Arduino Log]: Done")

        return True

    def set_speed(self, speed: int) -> bool:
        """
        设置电机速度（虚拟模式）

        Args:
            speed: 目标速度

        Returns:
            是否设置成功
        """
        self._log(f"[Virtual] === 设置电机速度为 {speed} ===")
        self._send_command(f"S:{speed}", wait_for_done=False)
        self._log("[Virtual] 速度设置已记录")
        return True

    def move(self, steps: int) -> bool:
        """
        相对移动（虚拟模式）

        Args:
            steps: 移动步数（正数为正转，负数为反转）

        Returns:
            是否发送成功
        """
        self._log(f"[Virtual] === 相对移动 {steps} 步 ===")
        self._send_command(f"M:{steps}", wait_for_done=True)
        self._log("[Virtual] 移动命令已记录")
        return True

    def move_to(self, position: int) -> bool:
        """
        绝对移动（虚拟模式）

        Args:
            position: 目标位置

        Returns:
            是否发送成功
        """
        self._log(f"[Virtual] === 移动到位置 {position} ===")
        self._send_command(f"A:{position}", wait_for_done=True)
        self._log("[Virtual] 绝对移动命令已记录")
        return True

    def set_zero(self) -> bool:
        """
        将当前位置设为零点（虚拟模式）

        Returns:
            是否设置成功
        """
        self._log("[Virtual] === 设为零点 ===")
        self._send_command("Z", wait_for_done=False)
        self._log("[Virtual] 零点设置已记录")
        return True

    def get_commands_log(self):
        """获取命令日志"""
        return self.commands_log.copy()

    def close(self):
        """关闭串口连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log("[Virtual] 串口已关闭")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
