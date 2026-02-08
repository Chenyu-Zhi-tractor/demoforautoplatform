"""
低温恒温冷却浴控制程序
基于 MODBUS RTU 通信协议

通信参数:
- 波特率: 9600
- 数据位: 8
- 校验位: 无校验 (None)
- 停止位: 1
- 流控制: 无
"""

import serial
import time

PORT = "COM9"

class CoolingBathController:
    """
    冷却浴控制器类
    提供与 PumpController/StirController 类似的类接口
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
        if self.ser is None or not self.ser.is_open:
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=9600,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    timeout=2
                )
                self._log(f"冷却浴串口 {self.port} 已连接")
            except Exception as e:
                self._log(f"无法打开串口 {self.port}: {e}")
                raise

    def close(self):
        """关闭串口连接"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                pass
            self._log(f"冷却浴串口 {self.port} 已断开")

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
        """发送数据帧并接收响应"""
        self._open_serial()
        
        # 清空缓冲区
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        
        # 发送数据
        self.ser.write(frame)
        self.ser.flush()
        
        # 记录发送日志
        cmd_hex = frame.hex().upper()
        self.commands_log.append(f"TX: {cmd_hex}")
        self._log(f"发送HEX: {cmd_hex}")
        
        # 接收响应 (Modbus 写单寄存器响应通常也是 8 字节)
        # 给设备一点处理时间
        time.sleep(0.1)
        
        response = b''
        start_time = time.time()
        # 简单等待策略，直到读够字节或超时
        expected_len = 8 # 写指令通常回显发送的内容
        
        while len(response) < expected_len and (time.time() - start_time) < 2:
            if self.ser.in_waiting > 0:
                response += self.ser.read(self.ser.in_waiting)
            time.sleep(0.05)
            
        if response:
            resp_hex = response.hex().upper()
            self.commands_log.append(f"RX: {resp_hex}")
            self._log(f"接收HEX: {resp_hex}")
            return response
        else:
            self._log("Warning: 未收到设备响应")
            return b''

    def set_temperature(self, temp: float) -> bool:
        """
        设置冷却浴目标温度
        
        Args:
            temp: 目标温度 (摄氏度)
            
        Returns:
            bool: 是否执行成功 (已收到合法响应)
        """
        try:
            # 转换温度值: 乘以 10 (保留1位小数)
            val_int = int(temp * 10)
            # 处理负数 (Modbus通常使用补码，但在 Python 中 int 转 bytes 需要注意掩码)
            val_u16 = val_int & 0xFFFF
            
            # 构造帧: 地址 0x01, 功能码 0x06 (写单个寄存器), 寄存器 0x000B (设定温度)
            device_address = 0x01
            function_code = 0x06
            register_address = 0x000B
            
            frame = self._build_frame(device_address, function_code, register_address, val_u16)
            
            self._log(f"正在设置温度为: {temp}℃")
            response = self._send_recv(frame)
            
            # 简单校验响应长度
            if len(response) == 8:
                # 严格来说应该校验 CRC 和回显内容，这里暂只校验长度
                self._log(f"设置温度成功: {temp}℃")
                return True
            else:
                self._log(f"设置失败，响应异常 (长度 {len(response)})")
                return False
                
        except Exception as e:
            self._log(f"设置温度过程中发生错误: {e}")
            import traceback
            self._log(traceback.format_exc())
            return False

if __name__ == "__main__":
    # 简单测试
    controller = CoolingBathController(port="COM9")
    try:
        controller.set_temperature(-20)
    finally:
        controller.close()
