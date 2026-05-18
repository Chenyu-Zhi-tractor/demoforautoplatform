import serial
import time
import json
from pathlib import Path

# 常量定义
COUNTS_PER_ML = 240
MAX_COUNTS = 6000  # 25mL
DEFAULT_SPEED = 600


class PumpController:
    """基于配置文件的注射泵控制器"""
    
    def __init__(self, port=None, baudrate=9600, config_path=None, config_dict=None):
        """
        初始化泵控制器
        
        参数:
            port: 串口号（必填）
            baudrate: 波特率，默认9600
            config_path: 配置文件路径，默认使用 demo/config/pump_config.json
            config_dict: 配置字典(优先于文件路径)
        """
        if port is None:
            raise ValueError("必须指定串口号 port")
        
        # 初始化命令日志
        self.commands_log = []
        
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )
        
        # 加载配置文件
        if config_dict is not None:
            self.config = config_dict
        else:
            if config_path is None:
                # 默认配置文件路径
                base_dir = Path(__file__).parent.parent.parent
                config_path = base_dir / "config" / "pump_config.json"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        
        # 日志输出函数，默认使用 print
        self._logger = print

        self._build_lookup_table()
        self._build_connection_graph()
    
    def set_logger(self, logger_func):
        """设置日志输出函数"""
        self._logger = logger_func

    def _log(self, msg):
        """统一日志输出"""
        if self._logger:
            self._logger(msg)

    def _build_connection_graph(self):
        """构建泵连接图"""
        self.graph = {}
        for conn in self.config.get('connections', []):
            pa = int(conn.get('pump_a'))
            pb = int(conn.get('pump_b'))
            port_a = int(conn.get('port_a'))
            port_b = int(conn.get('port_b'))
            
            if pa not in self.graph: self.graph[pa] = {}
            if pb not in self.graph: self.graph[pb] = {}
            
            self.graph[pa][pb] = {'my_port': port_a, 'neighbor_port': port_b}
            self.graph[pb][pa] = {'my_port': port_b, 'neighbor_port': port_a}

    def _find_path(self, start, end):
        """BFS寻找最短路径"""
        if start == end: return [start]
        queue = [[start]]
        visited = {start}
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node == end:
                return path
            
            if node in self.graph:
                for neighbor in self.graph[node]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_path = list(path)
                        new_path.append(neighbor)
                        queue.append(new_path)
        return None
    
    def _sync_push_pull(self, src_pump, dst_pump, src_conn_port, dst_conn_port, volume, speed=600):
        """同步推拉操作：src推 -> dst吸"""
        counts = int(volume * COUNTS_PER_ML)
        # 根据体积计算等待时间
        transfer_wait_time = max(5, int(volume * 0.6))

        self._log(f"  [同步] 切换阀门: 泵{src_pump}->{src_conn_port}(Out), 泵{dst_pump}->{dst_conn_port}(In)")
        self.set_valve(src_pump, src_conn_port, direction='O')
        self.set_valve(dst_pump, dst_conn_port, direction='I')
        
        self._log(f"  [同步] 动作: 泵{dst_pump}吸, 0.1s后 泵{src_pump}推")
        dst_cmd = f'/{dst_pump}V{speed}A{counts}R\r\n'.encode()
        src_cmd = f'/{src_pump}V{speed}A0R\r\n'.encode()
        
        # 目标泵吸液 (不等待)
        self._send_command(dst_cmd, wait_time=0)
        
        # 严格延时 0.1s
        time.sleep(0.1)
        
        # 源泵推液 (等待运动完成)
        self._send_command(src_cmd, wait_time=transfer_wait_time)
        self._log(f"  -> 同步传输完成")

    def _build_lookup_table(self):
        """构建快速查找表：name -> list of {pump, port, type}"""
        self.lookup = {}
        
        def _add_entry(item, item_type):
            name = item.get('name')
            if not name: return
            try:
                entry = {
                    'pump': int(item['pump']),
                    'port': int(item['port']),
                    'type': item_type
                }
                if name not in self.lookup:
                    self.lookup[name] = []
                self.lookup[name].append(entry)
            except:
                pass
        
        # 液体
        for item in self.config.get('liquids', []):
            _add_entry(item, 'liquid')
        
        # 气体
        for item in self.config.get('gases', []):
            _add_entry(item, 'gas')
        
        # 容器
        for item in self.config.get('containers', []):
            _add_entry(item, 'container')

    def get_location(self, name, reference_pump=None, type_priority=None):
        """
        获取名称对应的泵和端口位置
        
        参数:
            name: 液体名称或容器名称
            reference_pump: (可选) 参考泵编号，如果有多个同名位置，选择离参考泵最近的
            type_priority: (可选) 类型优先级列表，例如 ['liquid', 'container']。如果指定，将优先匹配列表前部的类型。
        
        返回:
            dict: {'pump': int, 'port': int, 'type': str} 或 None
        """
        entries = self.lookup.get(name)
        if not entries:
            return None
            
        # 根据类型优先级过滤
        valid_entries = entries
        if type_priority and len(entries) > 1:
            # 查找列表中存在的最高优先级的类型
            best_type = None
            for p_type in type_priority:
                if any(e['type'] == p_type for e in entries):
                    best_type = p_type
                    break
            
            # 如果找到了优先类型，只保留该类型的条目
            if best_type:
                valid_entries = [e for e in entries if e['type'] == best_type]

        # 只有一个位置，直接返回
        if len(valid_entries) == 1:
            return valid_entries[0]
            
        # 如果没有参考泵，返回默认(最后一个)
        if reference_pump is None:
            return valid_entries[-1]
            
        # 寻找最近的位置
        best_entry = valid_entries[-1]
        min_hops = float('inf')
        
        for entry in valid_entries:
            target_pump = entry['pump']
            if target_pump == reference_pump:
                return entry # 同泵，距离为0，最优
            
            path = self._find_path(reference_pump, target_pump)
            if path:
                hops = len(path) - 1
                # 如果距离更短，或者距离相等
                # (这里使用 <= 是为了在距离相等时保留列表后面的也就是pump4，符合用户描述的3->4偏好)
                if hops <= min_hops:
                    min_hops = hops
                    best_entry = entry
                    
        return best_entry
    
    def _send_command(self, cmd_bytes, wait_time=0.5):
        """发送命令并等待"""
        try:
            # Ensure clear state
            self.ser.reset_output_buffer()
            self.ser.reset_input_buffer()
            
            self.ser.write(cmd_bytes)
            self.ser.flush()  # Ensure data is sent
            
            # Log the command
            try:
                cmd_str = cmd_bytes.decode('utf-8').strip()
                self.commands_log.append(cmd_str)
            except:
                pass
            
            time.sleep(wait_time)
            
        except Exception as e:
            error_msg = f"ERROR: 发送命令失败: {e}"
            self._log(error_msg)
            self.commands_log.append(error_msg)
            raise # Re-raise to stop execution logic if hardware fails

    def init_all_pumps(self):
        """初始化所有泵（归零）"""
        pump_count = self.config.get('settings', {}).get('pump_count', 4)
        
        for pump_num in range(1, pump_count + 1):
            cmd = f'/{pump_num}ZR\r\n'.encode()
            # Initialization can take significantly longer than 2 seconds (full stroke)
            # Increasing wait time to ensure pump is ready before next command
            self._send_command(cmd, wait_time=10) 
            self._log(f"泵 {pump_num} 初始化完成")
    
    def init_pump(self, pump_num):
        """初始化单个泵"""
        cmd = f'/{pump_num}ZR\r\n'.encode()
        self._send_command(cmd, wait_time=10)
        self._log(f"泵 {pump_num} 初始化完成")
    
    def set_valve(self, pump_num, port, direction='I', wait_time=4):
        """
        设置阀门位置
        
        参数:
            pump_num: 泵编号
            port: 端口号
            direction: 'I'=Input(吸液), 'O'=Output(排液)
            wait_time: 等待时间(秒)
        """
        cmd = f'/{pump_num}{direction}{port}R\r\n'.encode()
        self._send_command(cmd, wait_time=wait_time)
        self._log(f"泵{pump_num}阀门切换至端口{port} (方向: {direction})")
    
    def aspirate(self, pump_num, volume_ml, speed=None):
        """
        吸取液体
        
        参数:
            pump_num: 泵编号
            volume_ml: 体积(mL)
            speed: 速度，默认600
        
        返回:
            实际吸取的体积(mL)
        """
        if speed is None:
            speed = DEFAULT_SPEED
        
        counts = int(volume_ml * COUNTS_PER_ML)
        counts = min(counts, MAX_COUNTS)  # 不超过最大计数
        
        cmd = f'/{pump_num}V{speed}A{counts}R\r\n'.encode()
        
        # 根据体积计算等待时间
        wait_time = max(5, int(volume_ml * 0.6))  # 粗略估计
        
        self._send_command(cmd, wait_time=wait_time)
        
        actual_volume = counts / COUNTS_PER_ML
        self._log(f"泵{pump_num} 吸取 {actual_volume}mL")
        return actual_volume
    
    def dispense(self, pump_num, volume_ml=None, speed=None):
        """
        排出液体
        
        参数:
            pump_num: 泵编号
            volume_ml: 体积(mL)，None表示全部排出(归零)
            speed: 速度，默认600
        """
        if speed is None:
            speed = DEFAULT_SPEED
        
        if volume_ml is None:
            # 全部排出（归零）
            cmd = f'/{pump_num}V{speed}A0R\r\n'.encode()
            wait_time = 15
            self._send_command(cmd, wait_time=wait_time)
            self._log(f"泵{pump_num} 全部排出")
        else:
            counts = int(volume_ml * COUNTS_PER_ML)
            cmd = f'/{pump_num}V{speed}D{counts}R\r\n'.encode()
            wait_time = max(5, int(volume_ml * 0.6))
            self._send_command(cmd, wait_time=wait_time)
            self._log(f"泵{pump_num} 排出 {volume_ml}mL")

    def _find_pump_connection(self, pump_a, pump_b):
        """
        查找两个泵之间的连接端口
        
        返回:
            dict: {'pump_a_port': int, 'pump_b_port': int} 或 None
        """
        for conn in self.config.get('connections', []):
            pa, pb = conn.get('pump_a'), conn.get('pump_b')
            if (pa == pump_a and pb == pump_b):
                return {'pump_a_port': conn.get('port_a'), 'pump_b_port': conn.get('port_b')}
            if (pa == pump_b and pb == pump_a):
                return {'pump_a_port': conn.get('port_b'), 'pump_b_port': conn.get('port_a')}
        return None

    def _get_candidates(self, name, type_priority=None):
        """获取所有候选位置"""
        entries = self.lookup.get(name)
        if not entries:
            return []
            
        if type_priority and len(entries) > 1:
            for p_type in type_priority:
                # 检查是否有该类型的条目
                if any(e['type'] == p_type for e in entries):
                    # 只返回该类型的条目
                    return [e for e in entries if e['type'] == p_type]
        
        return entries

    def _resolve_locations(self, src_candidates, dst_candidates):
        """解析最佳源和目标位置对（最短路径优先）"""
        if not src_candidates or not dst_candidates:
            return None, None
            
        best_pair = (None, None)
        min_hops = float('inf')
        
        # 遍历所有组合寻找最短路径
        # 在距离相等时，保留列表后部的条目(模拟旧默认行为或用户偏好)
        for s in src_candidates:
            for d in dst_candidates:
                s_pump = s['pump']
                d_pump = d['pump']
                
                hops = 0
                if s_pump != d_pump:
                    path = self._find_path(s_pump, d_pump)
                    if path:
                        hops = len(path) - 1
                    else:
                        hops = float('inf') # 不连通
                
                # 更新最优解
                if hops <= min_hops:
                    min_hops = hops
                    best_pair = (s, d)
                    
        return best_pair

    def transfer(self, source, destination, volume):
        """
        移液函数 - 从源位置移动液体到目标位置
        """
        try:
            self._log(f"\n=== 开始移液: {volume}mL 从 [{source}] 到 [{destination}] ===")
            
            # 获取所有候选位置
            # 源: 优先液体; 目标: 优先容器
            src_candidates = self._get_candidates(source, type_priority=['liquid', 'container'])
            dst_candidates = self._get_candidates(destination, type_priority=['container', 'liquid'])
            
            if not src_candidates:
                raise ValueError(f"未找到源位置: {source}")
            if not dst_candidates:
                raise ValueError(f"未找到目标位置: {destination}")
                
            # 解析最佳位置对
            src_loc, dst_loc = self._resolve_locations(src_candidates, dst_candidates)
            
            if not src_loc or not dst_loc:
                 raise ValueError(f"无法在 {source} 和 {destination} 之间建立连接")

            src_pump, src_port = src_loc['pump'], src_loc['port']
            dst_pump, dst_port = dst_loc['pump'], dst_loc['port']
            
            self._log(f"源位置: 泵{src_pump} 端口{src_port} ({src_loc['type']})")
            self._log(f"目标位置: 泵{dst_pump} 端口{dst_port} ({dst_loc['type']})")

            # 收集执行信息
            execution_info = {
                'source': source,
                'destination': destination,
                'volume': volume,
                'source_pump': src_pump,
                'source_port': src_port,
                'source_type': src_loc['type'],
                'dest_pump': dst_pump,
                'dest_port': dst_port,
                'dest_type': dst_loc['type'],
                'commands': []
            }
            
            # 判断是否为跨泵移液
            if src_pump == dst_pump:
                # 同泵移液
                result = self._same_pump_transfer(src_pump, src_port, dst_port, volume)
                execution_info['transfer_type'] = 'same_pump'
                execution_info['pump'] = src_pump
            else:
                # 跨泵多跳移液
                path = self._find_path(src_pump, dst_pump)
                if path:
                    result = self._multi_hop_transfer(path, src_port, dst_port, volume)
                    execution_info['transfer_type'] = 'multi_hop'
                    execution_info['path'] = path
                else:
                    raise ValueError(f"泵{src_pump}和泵{dst_pump}之间没有连接路径")
            
            execution_info['transferred'] = result
            return execution_info
            
        except Exception as e:
            msg = f"ERROR: 移液过程出错: {e}"
            self._log(msg)
            self.commands_log.append(msg)
            raise e
    
    def _same_pump_transfer(self, pump_num, src_port, dst_port, volume):
        """同泵移液"""
        self._log(f"\n--- 同泵移液: 泵{pump_num} 端口{src_port} -> 端口{dst_port} ---")
        
        total_transferred = 0
        vol_remaining = float(volume)
        
        while vol_remaining > 0:
            # 计算本次吸取体积
            aspirate_vol = min(vol_remaining, 25)  # 最大25mL
            
            # 1. 切换阀门到源端口(吸液方向)
            self.set_valve(pump_num, src_port, direction='I')
            
            # 2. 吸取
            self.aspirate(pump_num, aspirate_vol)
            
            # 3. 切换阀门到目标端口(排液方向)
            self.set_valve(pump_num, dst_port, direction='O')
            
            # 4. 排液
            self.dispense(pump_num, volume_ml=None)  # 全部排出
            
            total_transferred += aspirate_vol
            vol_remaining -= aspirate_vol
            
            self._log(f"进度: 已转移 {total_transferred}mL, 剩余 {vol_remaining}mL")
        
        self._log(f">>> 同泵移液完成: 共转移 {total_transferred}mL\n")
        return total_transferred
    
    def _multi_hop_transfer(self, path, src_port, dst_port, volume):
        """
        多跳移液逻辑
        
        path: 泵的路径列表 [start_pump, next_pump, ..., end_pump]
        """
        start_pump = path[0]
        end_pump = path[-1]
        
        self._log(f"\n--- 多跳移液: {' -> '.join(map(str, path))} (总{volume}mL) ---")
        
        total_transferred = 0
        vol_remaining = float(volume)
        speed = 600
        
        while vol_remaining > 0:
            current_vol = min(vol_remaining, 25)
            # counts = int(current_vol * COUNTS_PER_ML)
            
            self._log(f"\n=== [Cycle] 处理分块: {current_vol}mL ===")
            
            # 1. 初始泵吸液
            self._log(f"[Step 1] 源泵{start_pump} 从端口{src_port} 吸液")
            self.set_valve(start_pump, src_port, direction='I')
            self.aspirate(start_pump, current_vol, speed=speed)
            
            # 2. 沿路径传递
            for i in range(len(path) - 1):
                u = path[i]
                v = path[i+1]
                
                # 获取连接端口
                conn = self.graph[u][v]
                u_conn_port = conn['my_port']
                v_conn_port = conn['neighbor_port']
                
                self._log(f"[Step 2-{i+1}] 转移: 泵{u} -> 泵{v}")
                self._sync_push_pull(u, v, u_conn_port, v_conn_port, current_vol, speed)
            
            # 3. 目标泵排出
            self._log(f"[Step 3] 目标泵{end_pump} 排出到端口{dst_port}")
            self.set_valve(end_pump, dst_port, direction='O')
            self.dispense(end_pump, volume_ml=None, speed=speed)
            
            total_transferred += current_vol
            vol_remaining -= current_vol
            
            self._log(f"进度: 已转移 {total_transferred}mL, 剩余 {vol_remaining}mL")
            
        self._log(f">>> 多跳移液完成: 共转移 {total_transferred}mL\n")
        return total_transferred

    def close(self):
        """关闭串口连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log("串口已关闭")

    def get_commands_log(self):
        """获取命令日志"""
        return list(self.commands_log)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()




