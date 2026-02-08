"""
IKA 搅拌控制界面 - 简洁版
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSpinBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

# 导入 IKA 搅拌控制模块
# 真实模式
# from core.hardware.ikaset import StirController
# 虚拟调试模式
from core.hardware.ikaset_test import StirController

# 导入统一任务队列
from gui.task_queue import task_queue


class IKAEditorWidget(QWidget):
    """IKA 搅拌控制编辑器 - 简洁版"""
    
    task_added = pyqtSignal()  # 任务添加信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stir_controller = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === 顶部：标题和串口选择 ===
        header_layout = QHBoxLayout()
        
        title = QLabel("🌀 IKA 搅拌控制")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 串口选择
        header_layout.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItems(["COM10", "COM11", "COM12", "COM13", "COM14", "COM15"])
        self.port_combo.setCurrentText("COM10")
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
        
        quick_layout.addWidget(QLabel("转速:"))
        self.quick_speed_spin = QSpinBox()
        self.quick_speed_spin.setRange(0, 1500)
        self.quick_speed_spin.setValue(500)
        self.quick_speed_spin.setSuffix(" RPM")
        quick_layout.addWidget(self.quick_speed_spin)
        
        self.btn_quick_start = QPushButton("▶️ 启动")
        self.btn_quick_start.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_quick_start.clicked.connect(self._on_quick_start)
        quick_layout.addWidget(self.btn_quick_start)
        
        self.btn_quick_stop = QPushButton("⏹️ 停止")
        self.btn_quick_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_quick_stop.clicked.connect(self._on_quick_stop)
        quick_layout.addWidget(self.btn_quick_stop)
        
        self.btn_quick_control = QPushButton("🔧 设置并启动")
        self.btn_quick_control.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        self.btn_quick_control.clicked.connect(self._on_quick_control)
        quick_layout.addWidget(self.btn_quick_control)
        
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
        queue_layout = QVBoxLayout(queue_group)
        
        # 转速设置
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("转速:"))
        self.queue_speed_spin = QSpinBox()
        self.queue_speed_spin.setRange(0, 1500)
        self.queue_speed_spin.setValue(500)
        self.queue_speed_spin.setSuffix(" RPM")
        speed_layout.addWidget(self.queue_speed_spin)
        speed_layout.addStretch()
        queue_layout.addLayout(speed_layout)
        
        # 添加按钮行
        btn_layout = QHBoxLayout()
        
        self.btn_add_start = QPushButton("➕ 添加启动任务")
        self.btn_add_start.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_add_start.clicked.connect(self._on_add_start)
        btn_layout.addWidget(self.btn_add_start)
        
        self.btn_add_stop = QPushButton("➕ 添加停止任务")
        self.btn_add_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_add_stop.clicked.connect(self._on_add_stop)
        btn_layout.addWidget(self.btn_add_stop)
        
        self.btn_add_set_speed = QPushButton("➕ 添加设置转速")
        self.btn_add_set_speed.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d68910; }
        """)
        self.btn_add_set_speed.clicked.connect(self._on_add_set_speed)
        btn_layout.addWidget(self.btn_add_set_speed)
        
        self.btn_add_control = QPushButton("➕ 添加设置并启动")
        self.btn_add_control.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        self.btn_add_control.clicked.connect(self._on_add_control)
        btn_layout.addWidget(self.btn_add_control)
        
        btn_layout.addStretch()
        queue_layout.addLayout(btn_layout)
        
        hint = QLabel("💡 这些任务将被添加到统一队列，与泵任务按顺序混合执行\n"
                    "在「系统配置」标签页可查看端口使用矩阵")
        hint.setStyleSheet("color: #7f8c8d;")
        queue_layout.addWidget(hint)
        
        layout.addWidget(queue_group)
        
        # 添加弹簧
        layout.addStretch()
    
    def get_port(self) -> str:
        """获取当前选择的串口"""
        return self.port_combo.currentText()
    
    # ===== 快速控制（立即执行） =====
    
    def _on_quick_start(self):
        """快速启动搅拌"""
        port = self.get_port()
        try:
            if self._stir_controller is None:
                self._stir_controller = StirController(port=port)
            if self._stir_controller.start():
                QMessageBox.information(self, "成功", "已启动搅拌马达")
            else:
                QMessageBox.warning(self, "失败", "启动搅拌失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")
    
    def _on_quick_stop(self):
        """快速停止搅拌"""
        port = self.get_port()
        try:
            if self._stir_controller is None:
                self._stir_controller = StirController(port=port)
            if self._stir_controller.stop():
                QMessageBox.information(self, "成功", "已停止搅拌马达")
            else:
                QMessageBox.warning(self, "失败", "停止搅拌失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")
    
    def _on_quick_control(self):
        """快速设置并启动"""
        speed = self.quick_speed_spin.value()
        port = self.get_port()
        try:
            if self._stir_controller is None:
                self._stir_controller = StirController(port=port)
            if self._stir_controller.control(speed):
                QMessageBox.information(self, "成功", f"已设置转速 {speed} RPM 并启动搅拌")
            else:
                QMessageBox.warning(self, "失败", "设置并启动失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")
    
    # ===== 添加到队列 =====
    
    def _on_add_start(self):
        """添加启动任务到队列"""
        task_queue.add_ika_start()
        QMessageBox.information(self, "成功", "已添加 IKA 启动任务到队列")
        self.task_added.emit()
    
    def _on_add_stop(self):
        """添加停止任务到队列"""
        task_queue.add_ika_stop()
        QMessageBox.information(self, "成功", "已添加 IKA 停止任务到队列")
        self.task_added.emit()
    
    def _on_add_set_speed(self):
        """添加设置转速任务到队列"""
        speed = self.queue_speed_spin.value()
        task_queue.add_ika_set_speed(speed)
        QMessageBox.information(self, "成功", f"已添加 IKA 设置转速 {speed} RPM 到队列")
        self.task_added.emit()
    
    def _on_add_control(self):
        """添加设置并启动任务到队列"""
        speed = self.queue_speed_spin.value()
        task_queue.add_ika_control(speed)
        QMessageBox.information(self, "成功", f"已添加 IKA 设置 {speed} RPM 并启动到队列")
        self.task_added.emit()
