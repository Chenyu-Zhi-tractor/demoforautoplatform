"""
IKA 旋转搅拌控制程序
基于 RS232 通信协议 (NAMUR 指令集)

通信参数:
- 波特率: 9600
- 数据位: 7
- 校验位: 奇校验 (Odd)
- 停止位: 1
- 流控制: 无
"""

import serial
import time

PORT = "COM10"


class StirController:
    """
    IKA 搅拌控制器类
    提供与 PumpController 类似的类接口
    """
    
    def __init__(self, port=PORT):
        """
        初始化搅拌控制器
        
        Args:
            port: 串口号，默认 COM10
        """
        self.port = port
        self.ser = None
        self.commands_log = []
        self._logger = print
        
    def set_logger(self, logger_func):
        """设置日志输出函数"""
        self._logger = logger_func
    
    @staticmethod
    def build_command(cmd: str) -> bytes:
        """
        构建符合IKA协议的命令帧
        格式: 命令 + 空格 + 参数 + CR + LF
        """
        # 命令以 CR (0x0D) LF (0x0A) 终止
        return cmd.encode('ascii') + b'\x0d\x0a'
    
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
                bytesize=7,
                parity='O',
                stopbits=1,
                timeout=2
            )
    
    def _send_raw(self, cmd: str):
        """发送原始命令"""
        self._open_serial()
        
        # 清空缓冲区
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # 发送命令
        data = self.build_command(cmd)
        self.ser.write(data)
        self.ser.flush()
        
        # 记录命令
        self.commands_log.append(cmd)
        
        self._log(f"发送: {cmd}")
        self._log(f"发送HEX: {data.hex().upper()}")
    
    def set_speed(self, speed: int) -> bool:
        """
        设置搅拌转速
        
        Args:
            speed: 目标转速 (0-1500 RPM)
        
        Returns:
            是否设置成功
        """
        if not 0 <= speed <= 1500:
            self._log(f"错误: 转速必须在 0-1500 范围内，当前值: {speed}")
            return False
        
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log(f"\n=== 设置搅拌转速为 {speed} RPM ===")
            self._send_raw(f"OUT_SP_4 {speed}")
            self._log("转速设置已发送")
            return True
        except Exception as e:
            self._log(f"设置转速失败: {e}")
            return False
    
    def start(self) -> bool:
        """
        启动搅拌马达
        
        Returns:
            是否启动成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log("\n=== 启动搅拌马达 ===")
            self._send_raw("START_4")
            self._log("马达启动命令已发送")
            return True
        except Exception as e:
            self._log(f"启动马达失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止搅拌马达
        
        Returns:
            是否停止成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log("\n=== 停止搅拌马达 ===")
            self._send_raw("STOP_4")
            self._log("马达停止命令已发送")
            return True
        except Exception as e:
            self._log(f"停止马达失败: {e}")
            return False
    
    def control(self, speed: int) -> bool:
        """
        完整的搅拌控制流程：设置转速并启动
        
        Args:
            speed: 目标转速 (0-1500 RPM)
        
        Returns:
            是否执行成功
        """
        # 设置转速
        if not self.set_speed(speed):
            self._log("设置转速失败，中止操作")
            return False
        
        time.sleep(0.5)
        
        # 启动马达
        if not self.start():
            self._log("启动马达失败")
            return False
        
        self._log(f">>> 搅拌已启动，目标转速: {speed} RPM")
        return True
    
    def get_speed(self) -> bool:
        """
        发送读取转速指令
        
        Returns:
            是否发送成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log("\n=== 发送读取转速指令 ===")
            self._send_raw("IN_PV_4")
            self._log("读取转速指令已发送")
            return True
        except Exception as e:
            self._log(f"读取转速失败: {e}")
            return False
    
    def get_setpoint(self) -> bool:
        """
        发送读取设定转速指令
        
        Returns:
            是否发送成功
        """
        try:
            self._open_serial()
            time.sleep(0.2)
            self._log("\n=== 发送读取设定转速指令 ===")
            self._send_raw("IN_SP_4")
            self._log("读取设定转速指令已发送")
            return True
        except Exception as e:
            self._log(f"读取设定转速失败: {e}")
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
