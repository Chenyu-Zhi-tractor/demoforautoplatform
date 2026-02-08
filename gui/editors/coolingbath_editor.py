"""
低温恒温冷却浴控制界面 (Cooling Bath Editor)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

# 导入硬件驱动管理器
from core.hardware.driver_manager import DriverManager

# 导入统一任务队列
from gui.task_queue import task_queue 

class CoolingBathEditorWidget(QWidget):
    """低温恒温冷却浴控制编辑器"""
    
    task_added = pyqtSignal()  # 任务添加信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === 顶部：标题和串口选择 ===
        header_layout = QHBoxLayout()
        
        title = QLabel("❄️ 低温冷却浴控制")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 串口选择
        header_layout.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        # 默认 COM9，也可加上其他常见端口
        self.port_combo.addItems(["COM9", "COM10", "COM11", "COM12"])
        self.port_combo.setCurrentText("COM9")
        self.port_combo.setMinimumWidth(100)
        header_layout.addWidget(self.port_combo)
        
        layout.addLayout(header_layout)
        
        # === 快速控制区（立即执行） ===
        quick_group = QGroupBox("快速控制（立即执行）")
        quick_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #34495e; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        quick_layout = QHBoxLayout(quick_group)
        
        quick_layout.addWidget(QLabel("设定温度:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(-100.0, 100.0)  # 根据设备实际能力调整
        self.temp_spin.setValue(-20.0)
        self.temp_spin.setSuffix(" ℃")
        self.temp_spin.setDecimals(1)
        quick_layout.addWidget(self.temp_spin)
        
        self.btn_set_temp = QPushButton("设定温度")
        self.btn_set_temp.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_set_temp.clicked.connect(self._on_set_temp)
        quick_layout.addWidget(self.btn_set_temp)
        
        quick_layout.addStretch()
        layout.addWidget(quick_group)
        
        # === 添加到队列区 ===
        queue_group = QGroupBox("添加到任务队列")
        queue_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #e67e22; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        queue_layout = QHBoxLayout(queue_group)
        
        queue_layout.addWidget(QLabel("设定温度:"))
        self.queue_temp_spin = QDoubleSpinBox()
        self.queue_temp_spin.setRange(-100.0, 100.0)
        self.queue_temp_spin.setValue(-20.0)
        self.queue_temp_spin.setSuffix(" ℃")
        self.queue_temp_spin.setDecimals(1)
        queue_layout.addWidget(self.queue_temp_spin)
        
        self.btn_add_task = QPushButton("➕ 添加到队列")
        self.btn_add_task.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d68910; }
        """)
        self.btn_add_task.clicked.connect(self._on_add_task)
        queue_layout.addWidget(self.btn_add_task)
        
        queue_layout.addStretch()
        layout.addWidget(queue_group)
        
        # 底部弹簧
        layout.addStretch()
        
    def get_port(self) -> str:
        """获取当前选择的串口"""
        return self.port_combo.currentText()
        
    def _on_set_temp(self):
        """设定温度的回调"""
        temp = self.temp_spin.value()
        port = self.get_port()
        
        try:
            # 始终获取最新的类（可能刚刚切换了虚拟/真实模式）
            ControllerClass = DriverManager.instance().get_cooling_bath_controller_class()
            
            # 使用临时控制器进行单次操作
            # 如果需要保持连接，可以像 StirController 那样缓存 self._controller
            # 这里为了简单起见，每次创建新实例（反正 init 只是存端口）
            controller = ControllerClass(port=port)
            
            if controller.set_temperature(temp):
                QMessageBox.information(self, "成功", f"温度已设定为 {temp} ℃")
            else:
                QMessageBox.warning(self, "失败", "设定温度失败，请检查连接或参数")
            
            controller.close()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")

    def _on_add_task(self):
        """添加到队列的回调"""
        temp = self.queue_temp_spin.value()
        task_queue.add_cooling_bath_set_temp(temp)
        QMessageBox.information(self, "成功", f"已添加任务: 冷却浴设温 {temp} ℃")
        self.task_added.emit()

