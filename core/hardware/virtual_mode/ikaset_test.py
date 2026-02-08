"""
IKA 旋转搅拌控制程序 - 虚拟调试模式
基于 RS232 通信协议 (NAMUR 指令集) - 仅记录命令不实际发送

通信参数:
- 波特率: 9600
- 数据位: 7
- 校验位: 奇校验 (Odd)
- 停止位: 1
- 流控制: 无
"""

import time

PORT = "COM10"


class MockSerial:
    """[虚拟模式] 模拟串口 - 仅记录命令不实际发送"""
    
    def __init__(self, port='COM10'):
        self.port = port
        self.is_open = True
        
    def close(self):
        self.is_open = False
        print(f"[Virtual] 串口 {self.port} 已关闭")
    
    def write(self, data):
        """记录命令但不实际发送"""
        cmd_str = data.decode('ascii').strip()
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


class StirController:
    """
    IKA 搅拌控制器类（虚拟模式）
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
    
    def _log(self, msg):
        """统一日志输出"""
        if self._logger:
            self._logger(msg)
    
    @staticmethod
    def build_command(cmd: str) -> bytes:
        """
        构建符合IKA协议的命令帧
        格式: 命令 + 空格 + 参数 + CR + LF
        """
        return cmd.encode('ascii') + b'\x0d\x0a'
    
    def _send_raw(self, cmd: str):
        """发送原始命令"""
        if self.ser is None:
            self.ser = MockSerial(self.port)
        
        data = self.build_command(cmd)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(data)
        self.ser.flush()
        
        # 记录命令
        self.commands_log.append(cmd)
        self._log(f"[Virtual] 发送: {cmd}")
    
    def set_speed(self, speed: int) -> bool:
        """
        设置搅拌转速
        
        Args:
            speed: 目标转速 (0-1500 RPM)
        
        Returns:
            是否设置成功
        """
        if not 0 <= speed <= 1500:
            self._log(f"[Virtual] 错误: 转速必须在 0-1500 范围内，当前值: {speed}")
            return False
        
        self._log(f"[Virtual] === 设置搅拌转速为 {speed} RPM ===")
        self._send_raw(f"OUT_SP_4 {speed}")
        self._log("[Virtual] 转速设置已记录")
        return True
    
    def start(self) -> bool:
        """
        启动搅拌马达
        
        Returns:
            是否启动成功
        """
        self._log("[Virtual] === 启动搅拌马达 ===")
        self._send_raw("START_4")
        self._log("[Virtual] 马达启动命令已记录")
        return True
    
    def stop(self) -> bool:
        """
        停止搅拌马达
        
        Returns:
            是否停止成功
        """
        self._log("[Virtual] === 停止搅拌马达 ===")
        self._send_raw("STOP_4")
        self._log("[Virtual] 马达停止命令已记录")
        return True
    
    def control(self, speed: int):
        """
        完整的搅拌控制流程：设置转速并启动
        
        Args:
            speed: 目标转速 (0-1500 RPM)
        """
        if not self.set_speed(speed):
            self._log("[Virtual] 设置转速失败，中止操作")
            return False
        
        time.sleep(0.1)  # 虚拟模式下减少等待时间
        
        if not self.start():
            self._log("[Virtual] 启动马达失败")
            return False
        
        self._log(f"[Virtual] >>> 搅拌已启动，目标转速: {speed} RPM")
        return True
    
    def get_speed(self):
        """发送读取转速指令"""
        self._log("[Virtual] === 发送读取转速指令 ===")
        self._send_raw("IN_PV_4")
        self._log("[Virtual] 读取转速指令已记录")
    
    def get_setpoint(self):
        """发送读取设定转速指令"""
        self._log("[Virtual] === 发送读取设定转速指令 ===")
        self._send_raw("IN_SP_4")
        self._log("[Virtual] 读取设定转速指令已记录")
    
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
