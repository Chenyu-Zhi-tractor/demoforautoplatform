
import serial
import time
port = "COM9"
def xuanzheng_temp_set(tempset: int):
    # 设置目标温度
    T_set = tempset  
    def modbus_crc(data: bytes) -> bytes:
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

    def build_modbus_frame(device_address: int, function_code: int, register_address: int, value: int) -> bytes:
        frame = bytearray([
            device_address,
            function_code,
            (register_address >> 8) & 0xFF,
            register_address & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])
        crc = modbus_crc(frame)
        return frame + crc

    def convert_temperature_to_modbus_value(temperature: float, decimal_points: int = 1) -> int:
        factor = 10 ** decimal_points
        value = int(temperature * factor)
        return value & 0xFFFF

    temperature_value = convert_temperature_to_modbus_value(T_set, decimal_points=1)

    ser = serial.Serial(
        port=port,
        baudrate=9600,
        bytesize=8,
        parity='N',
        stopbits=1,
        timeout=2  # 增加超时时间
    )
    
    # 清空缓冲区
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    print('旋蒸冷却 COM9 已连接') 

    device_address = 0x01
    function_code = 0x06  
    register_address = 0x000B  

    frame = build_modbus_frame(device_address, function_code, register_address, temperature_value)
    print(f"Frame: {frame.hex().upper()}")
    
    # 发送数据并确保发送完成
    ser.write(frame)
    ser.flush()
    
    # 给设备一点处理时间
    time.sleep(0.1)
    
    print(f'旋蒸冷却 COM9 温度设置为{T_set}℃')

    # 读取响应，先等待数据到达
    response = b''
    start_time = time.time()
    while len(response) < 8 and (time.time() - start_time) < 2:
        if ser.in_waiting > 0:
            response += ser.read(ser.in_waiting)
        time.sleep(0.05)
    
    if response:
        print(f"Response: {response.hex().upper()}")
        if len(response) == 8:
            print("命令执行成功")
        else:
            print(f"收到非标准响应长度: {len(response)} 字节")
    else:
        print("Warning: 未收到设备响应")

    # 关闭串口
    ser.close()
    print('旋蒸冷却 COM9 已断开')

xuanzheng_temp_set(-20)
