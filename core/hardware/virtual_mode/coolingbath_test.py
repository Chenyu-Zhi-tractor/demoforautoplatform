"""
低温恒温冷却浴控制程序 - 虚拟调试模式
基于 MODBUS RTU 通信协议 - 仅记录命令不实际发送
"""

import time

PORT = "COM9"

class MockSerial:
    """[虚拟模式] 模拟串口 - 仅记录命令不实际发送"""
    
    def __init__(self, port='COM9'):
        self.port = port
        self.is_open = True
        self.in_waiting = 0
        
    def close(self):
        self.is_open = False
        print(f"[Virtual] 串口 {self.port} 已关闭")
    
    def write(self, data):
        """记录命令但不实际发送"""
        pass # 实际打印逻辑主要在 Controller 里做，MockSerial 只需要存在即可
    
    def flush(self):
        pass
    
    def reset_input_buffer(self):
        pass
    
    def reset_output_buffer(self):
        pass
    
    def read(self, size):
        return b''

class CoolingBathController:
    """
    冷却浴控制器类 (虚拟模式)
    提供与 CoolingBathController 真实的类接口
    """

    def __init__(self, port=PORT):
        """
        初始化冷却浴控制器
        
        Args:
            port: 串口号，默认 COM9
        """
        self.port = port
        self.ser = None
        self.commands_log = []
        self._logger = print  # 默认使用 print 作为日志输出

    def set_logger(self, logger_func):
        """设置日志输出函数"""
        self._logger = logger_func

    def _log(self, msg):
        """统一日志输出"""
        if self._logger:
            self._logger(msg)

    def _open_serial(self):
        """打开串口连接"""
        if self.ser is None:
            self.ser = MockSerial(self.port)
            self._log(f"[Virtual] 冷却浴串口 {self.port} 已连接")

    def close(self):
        """关闭串口连接"""
        if self.ser:
            self.ser.close()
            self._log(f"[Virtual] 冷却浴串口 {self.port} 已断开")

    @staticmethod
    def _calculate_crc(data: bytes) -> bytes:
        """计算 Modbus CRC16 校验码"""
        crc = 0xFFFF
        for pos in data:
            crc ^= pos
            for _ in range(8):
                if (crc & 0x0001) != 0:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, byteorder='little')

    def _build_frame(self, device_address: int, function_code: int, register_address: int, value: int) -> bytes:
        """构建 Modbus RTU 数据帧"""
        frame = bytearray([
            device_address,
            function_code,
            (register_address >> 8) & 0xFF,
            register_address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])
        crc = self._calculate_crc(frame)
        return frame + crc

    def _send_recv(self, frame: bytes) -> bytes:
        """发送数据帧并接收模拟响应"""
        self._open_serial()
        
        # 记录发送日志
        cmd_hex = frame.hex().upper()
        self.commands_log.append(f"TX: {cmd_hex}")
        self._log(f"[Virtual] 发送HEX: {cmd_hex}")
        
        # 模拟响应 (Modbus 写单寄存器成功时，通常回显发送的报文)
        response = frame 
        resp_hex = response.hex().upper()
        self.commands_log.append(f"RX: {resp_hex}")
        self._log(f"[Virtual] 接收HEX (模拟): {resp_hex}")
        
        # 模拟网络延迟
        time.sleep(0.05)
        return response

    def set_temperature(self, temp: float) -> bool:
        """
        设置冷却浴目标温度
        
        Args:
            temp: 目标温度 (摄氏度)
            
        Returns:
            bool: 是否执行成功
        """
        try:
            # 转换温度值: 乘以 10 (保留1位小数)
            val_int = int(temp * 10)
            val_u16 = val_int & 0xFFFF
            
            # 构造帧: 地址 0x01, 功能码 0x06 (写单个寄存器), 寄存器 0x000B (设定温度)
            device_address = 0x01
            function_code = 0x06
            register_address = 0x000B
            
            frame = self._build_frame(device_address, function_code, register_address, val_u16)
            
            self._log(f"[Virtual] 正在设置温度为: {temp}℃")
            response = self._send_recv(frame)
            
            # 简单校验响应长度
            if len(response) == 8:
                self._log(f"[Virtual] 设置温度成功: {temp}℃")
                return True
            else:
                self._log(f"[Virtual] 设置失败，响应异常")
                return False
                
        except Exception as e:
            self._log(f"[Virtual] Error: {e}")
            return False

if __name__ == "__main__":
    # 简单测试
    controller = CoolingBathController(port="COM9")
    try:
        controller.set_temperature(-20)
    finally:
        controller.close()
