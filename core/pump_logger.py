import os
from datetime import datetime
from core.hardware.parse_cmd import parse_cmd

class PumpLogger:
    """
    负责泵执行过程的日志记录
    """
    def __init__(self, log_path, enable_stdout=False):
        self.log_path = log_path
        self.log_file = None
        self.enable_stdout = enable_stdout

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
             import traceback
             self.log_critical_error(str(exc_val), traceback.format_exc())
        self.close()

    def open(self):
        """打开日志文件"""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self.log_file = open(self.log_path, 'w', encoding='utf-8')

    def close(self):
        """关闭日志文件"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def write(self, line=""):
        """写入单行日志"""
        if self.log_file:
            self.log_file.write(line + '\n')
            self.log_file.flush()
        if self.enable_stdout:
            print(line)

    def log_header(self, task_count):
        self.write("=" * 70)
        self.write(" " * 20 + "泵执行详细日志")
        self.write("=" * 70)
        self.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.write(f"任务数量: {task_count}")
        self.write("")

    def log_system_action(self, action):
        self.write(f"【系统】{action}...")

    def log_config_summary(self, config_data):
        self.write("-" * 70)
        self.write("【配置概览】")
        self.write("-" * 70)
        settings = config_data.get('settings', {})
        self.write(f"泵数量: {settings.get('pump_count', 4)}")
        self.write(f"端口/泵: {settings.get('port_count', 8)}")
        self.write(f"液体: {len(config_data.get('liquids', []))} 种")
        self.write(f"容器: {len(config_data.get('containers', []))} 个")
        self.write(f"连接: {len(config_data.get('connections', []))} 条")
        self.write("")

    def log_task_start(self, index, total, task):
        self.write("=" * 70)
        self.write(f"【任务 {index}/{total}】")
        self.write("=" * 70)
        self.write(f"")
        
        # 根据任务类型打印不同头部信息
        task_type = task.get('type', 'transfer')
        
        if task_type == 'transfer':
            self.write(f"  任务类型: 🧪 液体转移")
            self.write(f"  移液内容: {task.get('source')} → {task.get('destination')}")
            self.write(f"  移液体积: {task.get('volume')} mL")
        elif task_type == 'switch':
            # 未来扩展示例：如果是开关任务，日志格式会自动调整，不影响上面的移液格式
            self.write(f"  任务类型: 🔌 开关控制")
            self.write(f"  设备名称: {task.get('device_name')}")
            self.write(f"  目标状态: {'开启' if task.get('state') else '关闭'}")
        elif task_type == 'ika_start':
            self.write(f"  任务类型: 🌀 IKA 启动搅拌")
        elif task_type == 'ika_stop':
            self.write(f"  任务类型: 🌀 IKA 停止搅拌")
        elif task_type == 'ika_set_speed':
            self.write(f"  任务类型: 🌀 IKA 设置转速")
            self.write(f"  目标转速: {task.get('speed', 0)} RPM")
        elif task_type == 'ika_control':
            self.write(f"  任务类型: 🌀 IKA 设置并启动")
            self.write(f"  目标转速: {task.get('speed', 0)} RPM")
        
        self.write(f"")

    def log_transfer_success(self, index, result, transferred_vol, commands):
        """【专用】记录移液任务成功详情"""
        # 源信息
        self.write(f"  【源位置】")
        self.write(f"    名称: {result['source']}")
        self.write(f"    类型: {result['source_type']}")
        self.write(f"    泵编号: {result['source_pump']}")
        self.write(f"    端口号: {result['source_port']}")
        self.write(f"")
        
        # 目标信息
        self.write(f"  【目标位置】")
        self.write(f"    名称: {result['destination']}")
        self.write(f"    类型: {result['dest_type']}")
        self.write(f"    泵编号: {result['dest_pump']}")
        self.write(f"    端口号: {result['dest_port']}")
        self.write(f"")
        
        # 移液类型
        if result['transfer_type'] == 'same_pump':
            self.write(f"  【移液类型】同泵移液 (泵{result['pump']}内转移)")
        elif result['transfer_type'] == 'multi_hop':
            path = result.get('path', [])
            path_str = " → ".join(map(str, path))
            self.write(f"  【移液类型】多跳跨泵移液 ({path_str})")
            self.write(f"    路径: {path_str}")
        else:
            self.write(f"  【移液类型】跨泵移液 (泵{result['source_pump']} → 泵{result['dest_pump']})")
            self.write(f"    连接路径: 泵{result['source_pump']}端口{result.get('src_conn_port','?')} ↔ 泵{result['dest_pump']}端口{result.get('dst_conn_port','?')}")
        
        self.write(f"")
        self.write("-" * 70)
        self.write("【执行指令序列】")
        self.write("-" * 70)
        
        for cmd in commands:
            explanation = parse_cmd(cmd)
            self.write(f"    CMD: {cmd:<25} → {explanation}")
        
        self.write(f"")
    def log_generic_success(self, index, message):
        """【通用】简单的成功记录（适用于开关、暂停等简单任务）"""
        self.write(f"  [✓] 任务 {index} 完成: {message}")
        self.write("")
        
    def log_task_failure(self, index, error_msg):
        self.write(f"")
        self.write(f"  [✗] 任务 {index} 执行失败!")
        self.write(f"  【错误信息】 {error_msg}")
        self.write(f"")

    def log_init_commands(self, commands):
        if commands:
             self.write("-" * 70)
             self.write("【初始化指令序列】")
             self.write("-" * 70)
             for cmd in commands:
                  explanation = parse_cmd(cmd)
                  self.write(f"    CMD: {cmd:<25} → {explanation}")
             self.write("")

    def log_summary(self, total, success, failed, volume, has_error, last_error):
        self.write("=" * 70)
        self.write("【执行总结】")
        self.write("=" * 70)
        self.write(f"总任务数: {total}")
        self.write(f"成功完成: {success}")
        self.write(f"失败任务: {failed}")
        self.write(f"总移液体积: {volume:.2f} mL")
        if has_error:
            self.write(f"执行状态: ✗ 部分失败 (最后错误: {last_error})")
        else:
            self.write(f"执行状态: ✓ 全部完成")
        self.write("=" * 70)

    def log_critical_error(self, error_msg, trace_info):
        self.write(f"")
        self.write("=" * 70)
        self.write("【严重错误 - 执行中断】")
        self.write("=" * 70)
        self.write(f"错误信息: {error_msg}")
        self.write(f"")
        self.write("【错误堆栈】")
        self.write(trace_info)
        self.write("=" * 70)

    # ========== IKA 搅拌器专用日志方法 ==========
    
    def log_ika_header(self):
        """记录 IKA 控制头部信息"""
        self.write("")
        self.write("-" * 70)
        self.write("【设备】IKA 旋转搅拌控制器")
        self.write("-" * 70)
    
    def log_ika_command(self, cmd_type, speed=None, port=None):
        """记录 IKA 命令"""
        port_str = f" (串口: {port})" if port else ""
        if speed is not None:
            self.write(f"    CMD: {cmd_type:<20} 转速: {speed} RPM{port_str}")
        else:
            self.write(f"    CMD: {cmd_type:<20}{port_str}")
    
    def log_ika_commands_list(self, commands, port=None):
        """记录 IKA 命令序列"""
        self.write("-" * 70)
        self.write("【IKA 执行指令序列】")
        self.write("-" * 70)
        for cmd in commands:
            self.write(f"    CMD: {cmd}")
        self.write("")
