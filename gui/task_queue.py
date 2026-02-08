"""
统一任务队列系统
支持混合执行泵任务、IKA任务等多种类型
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
import copy


class TaskType(Enum):
    """任务类型枚举"""
    PUMP_TRANSFER = "pump_transfer"    # 泵移液
    IKA_START = "ika_start"             # IKA启动
    IKA_STOP = "ika_stop"               # IKA停止
    IKA_SET_SPEED = "ika_set_speed"     # IKA设置转速
    IKA_CONTROL = "ika_control"         # IKA设置并启动
    COOLING_BATH_SET_TEMP = "cooling_bath_set_temp" # 冷却浴设置温度



@dataclass
class Task:
    """统一任务数据结构"""
    task_type: TaskType
    name: str                          # 显示名称
    params: Dict[str, Any] = field(default_factory=dict)  # 任务参数
    enabled: bool = True               # 是否启用
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_type': self.task_type.value,
            'name': self.name,
            'params': self.params,
            'enabled': self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建"""
        return cls(
            task_type=TaskType(data.get('task_type', 'pump_transfer')),
            name=data.get('name', '未命名任务'),
            params=data.get('params', {}),
            enabled=data.get('enabled', True)
        )
    
    def get_display_text(self) -> str:
        """获取显示文本"""
        if self.task_type == TaskType.PUMP_TRANSFER:
            src = self.params.get('source', '?')
            dst = self.params.get('destination', '?')
            vol = self.params.get('volume', 0)
            return f"🧪 {src} → {dst} : {vol}mL"
        elif self.task_type == TaskType.IKA_START:
            return f"🌀 启动搅拌"
        elif self.task_type == TaskType.IKA_STOP:
            return f"🌀 停止搅拌"
        elif self.task_type == TaskType.IKA_SET_SPEED:
            speed = self.params.get('speed', 0)
            return f"🌀 设置转速 {speed} RPM"
        elif self.task_type == TaskType.IKA_CONTROL:
            speed = self.params.get('speed', 0)
            return f"🌀 设置 {speed} RPM 并启动"
        elif self.task_type == TaskType.COOLING_BATH_SET_TEMP:
            temp = self.params.get('temp', 0)
            return f"❄️ 冷却浴设定 {temp} ℃"
        return f"未知任务: {self.name}"
    
    def get_icon(self) -> str:
        """获取图标"""
        if self.task_type == TaskType.PUMP_TRANSFER:
            return "🧪"
        elif self.task_type in [TaskType.IKA_START, TaskType.IKA_STOP, 
                                TaskType.IKA_SET_SPEED, TaskType.IKA_CONTROL]:
            return "🌀"
        elif self.task_type == TaskType.COOLING_BATH_SET_TEMP:
            return "❄️"
        return "❓"


class TaskQueue:
    """
    统一任务队列管理器
    支持添加、删除、移动任务
    """
    
    def __init__(self):
        self._tasks: List[Task] = []
        self._observers: List[Callable] = []  # 观察者列表，用于通知UI更新
    
    def add_observer(self, callback: Callable):
        """添加观察者，任务变化时通知"""
        self._observers.append(callback)
    
    def remove_observer(self, callback: Callable):
        """移除观察者"""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def _notify(self):
        """通知所有观察者"""
        for observer in self._observers:
            observer()
    
    # ==================== 任务操作 ====================
    
    def add_task(self, task: Task, index: int = -1) -> int:
        """
        添加任务
        
        Args:
            task: 任务对象
            index: 插入位置，-1表示添加到末尾
        
        Returns:
            插入的索引位置
        """
        if index == -1:
            self._tasks.append(task)
            index = len(self._tasks) - 1
        else:
            self._tasks.insert(index, task)
        
        self._notify()
        return index
    
    def remove_task(self, index: int) -> Optional[Task]:
        """删除指定位置的任务"""
        if 0 <= index < len(self._tasks):
            task = self._tasks.pop(index)
            self._notify()
            return task
        return None
    
    def move_task(self, from_index: int, to_index: int) -> bool:
        """移动任务位置"""
        if not (0 <= from_index < len(self._tasks)):
            return False
        
        # 调整目标位置
        if to_index < 0:
            to_index = 0
        if to_index >= len(self._tasks):
            to_index = len(self._tasks) - 1
        
        if from_index == to_index:
            return True
        
        # 移动任务
        task = self._tasks.pop(from_index)
        self._tasks.insert(to_index, task)
        self._notify()
        return True
    
    def move_up(self, index: int) -> bool:
        """将任务上移一位"""
        return self.move_task(index, index - 1)
    
    def move_down(self, index: int) -> bool:
        """将任务下移一位"""
        return self.move_task(index, index + 1)
    
    def toggle_task(self, index: int) -> bool:
        """切换任务启用/禁用状态"""
        if 0 <= index < len(self._tasks):
            self._tasks[index].enabled = not self._tasks[index].enabled
            self._notify()
            return self._tasks[index].enabled
        return False
    
    def clear(self):
        """清空所有任务"""
        self._tasks.clear()
        self._notify()
    
    # ==================== 查询方法 ====================
    
    def get_task(self, index: int) -> Optional[Task]:
        """获取指定位置的任务"""
        if 0 <= index < len(self._tasks):
            return self._tasks[index]
        return None
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务（副本）"""
        return copy.deepcopy(self._tasks)
    
    def get_enabled_tasks(self) -> List[Task]:
        """获取所有启用的任务"""
        return [copy.deepcopy(t) for t in self._tasks if t.enabled]
    
    def get_task_count(self) -> int:
        """获取任务总数"""
        return len(self._tasks)
    
    def get_enabled_count(self) -> int:
        """获取启用的任务数"""
        return sum(1 for t in self._tasks if t.enabled)
    
    # ==================== 快捷添加方法 ====================
    
    def add_pump_transfer(self, source: str, destination: str, volume: float, 
                         index: int = -1) -> int:
        """添加泵移液任务"""
        task = Task(
            task_type=TaskType.PUMP_TRANSFER,
            name=f"{source}→{destination}",
            params={
                'source': source,
                'destination': destination,
                'volume': volume
            }
        )
        return self.add_task(task, index)
    
    def add_ika_start(self, index: int = -1) -> int:
        """添加IKA启动任务"""
        task = Task(
            task_type=TaskType.IKA_START,
            name="启动搅拌",
            params={}
        )
        return self.add_task(task, index)
    
    def add_ika_stop(self, index: int = -1) -> int:
        """添加IKA停止任务"""
        task = Task(
            task_type=TaskType.IKA_STOP,
            name="停止搅拌",
            params={}
        )
        return self.add_task(task, index)
    
    def add_ika_set_speed(self, speed: int, index: int = -1) -> int:
        """添加IKA设置转速任务"""
        task = Task(
            task_type=TaskType.IKA_SET_SPEED,
            name=f"设置转速 {speed}",
            params={'speed': speed}
        )
        return self.add_task(task, index)
    
    def add_ika_control(self, speed: int, index: int = -1) -> int:
        """添加IKA设置并启动任务"""
        task = Task(
            task_type=TaskType.IKA_CONTROL,
            name=f"设置 {speed} 并启动",
            params={'speed': speed}
        )
        return self.add_task(task, index)

    def add_cooling_bath_set_temp(self, temp: float, index: int = -1) -> int:
        """添加冷却浴设置温度任务"""
        task = Task(
            task_type=TaskType.COOLING_BATH_SET_TEMP,
            name=f"冷却浴设温 {temp}℃",
            params={'temp': temp}
        )
        return self.add_task(task, index)
    
    # ==================== 序列化 ====================
    
    def to_list(self) -> List[Dict[str, Any]]:
        """转换为列表（用于保存）"""
        return [t.to_dict() for t in self._tasks]
    
    def from_list(self, data: List[Dict[str, Any]]):
        """从列表加载"""
        self._tasks = [Task.from_dict(d) for d in data]
        self._notify()
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_list(), f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str):
        """从文件加载"""
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_list(data)


# 全局任务队列实例
task_queue = TaskQueue()
