"""
泵任务编辑器 - 简洁版，只显示任务配置
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QMessageBox
)
from PyQt6.QtCore import pyqtSignal

# 导入统一任务队列
from gui.task_queue import task_queue


class PumpEditorWidget(QWidget):
    """泵任务编辑器 - 简洁版"""
    
    task_added = pyqtSignal()  # 任务添加信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_data = None
        self.liquids = []
        self.containers = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === 顶部：标题和串口选择 ===
        header_layout = QHBoxLayout()
        
        title = QLabel("🧪 泵移液任务配置")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # 串口选择
        header_layout.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5", 
                                   "COM6", "COM7", "COM8", "COM9", "COM10",
                                   "COM11", "COM12", "COM13", "COM14", "COM15"])
        self.port_combo.setCurrentText("COM11")
        self.port_combo.setMinimumWidth(100)
        header_layout.addWidget(self.port_combo)
        
        layout.addLayout(header_layout)
        
        # === 任务配置区 ===
        config_group = QGroupBox("任务参数")
        config_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #34495e; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        form_layout = QFormLayout(config_group)
        
        # 源选择
        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("选择源...")
        self.source_combo.setMinimumWidth(250)
        form_layout.addRow("从 (Source):", self.source_combo)
        
        # 目标选择
        self.dest_combo = QComboBox()
        self.dest_combo.setPlaceholderText("选择目标...")
        self.dest_combo.setMinimumWidth(250)
        form_layout.addRow("到 (Destination):", self.dest_combo)
        
        # 体积输入
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.1, 1000)
        self.volume_spin.setValue(10.0)
        self.volume_spin.setSuffix(" mL")
        self.volume_spin.setDecimals(1)
        form_layout.addRow("体积 (Volume):", self.volume_spin)
        
        layout.addWidget(config_group)
        
        # === 添加到队列按钮 ===
        self.btn_add = QPushButton("➕ 添加到任务队列")
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 12px 24px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_add.clicked.connect(self._on_add_to_queue)
        layout.addWidget(self.btn_add)
        
        # === 提示信息 ===
        hint = QLabel("💡 提示：\n"
                     "1. 在「系统配置」标签页查看端口使用矩阵\n"
                     "2. 配置好参数后点击上方按钮添加到队列\n"
                     "3. 在右侧任务队列查看和管理所有任务")
        hint.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(hint)
        
        # 添加弹簧
        layout.addStretch()
    
    def get_port(self) -> str:
        """获取当前选择的串口"""
        return self.port_combo.currentText()
    
    def load_config(self, config_data):
        """加载配置数据"""
        self.config_data = config_data
        
        # 提取列表
        self.liquids = [item['name'] for item in config_data.get('liquids', [])]
        self.containers = [item['name'] for item in config_data.get('containers', [])]
        
        # 更新下拉框
        self._update_combos()
    
    def _update_combos(self):
        """更新源和目标下拉框"""
        current_source = self.source_combo.currentText()
        current_dest = self.dest_combo.currentText()
        
        # 更新源选择（液体+容器）
        self.source_combo.clear()
        self.source_combo.addItem("-- 请选择 --")
        self.source_combo.model().item(0).setEnabled(False)
        
        if self.liquids:
            self.source_combo.addItem("-- 液体 --")
            offset = self.source_combo.count() - 1
            self.source_combo.model().item(offset).setEnabled(False)
            for idx, name in enumerate(self.liquids):
                self.source_combo.addItem(f"{idx}: {name}")
        
        if self.containers:
            self.source_combo.addItem("-- 容器 --")
            offset = self.source_combo.count() - 1
            self.source_combo.model().item(offset).setEnabled(False)
            for idx, name in enumerate(self.containers):
                self.source_combo.addItem(f"{idx}: {name}")
        
        # 更新目标选择（仅容器）
        self.dest_combo.clear()
        self.dest_combo.addItem("-- 请选择 --")
        self.dest_combo.model().item(0).setEnabled(False)
        
        if self.containers:
            self.dest_combo.addItem("-- 容器 --")
            offset = self.dest_combo.count() - 1
            self.dest_combo.model().item(offset).setEnabled(False)
            for idx, name in enumerate(self.containers):
                self.dest_combo.addItem(f"{idx}: {name}")
        
        # 恢复选择
        if current_source:
            index = self.source_combo.findText(current_source)
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
        
        if current_dest:
            index = self.dest_combo.findText(current_dest)
            if index >= 0:
                self.dest_combo.setCurrentIndex(index)
    
    def _get_selected_source(self) -> str:
        """获取选中的源名称"""
        text = self.source_combo.currentText()
        if ": " in text:
            return text.split(": ", 1)[1]
        return text
    
    def _get_selected_dest(self) -> str:
        """获取选中的目标名称"""
        text = self.dest_combo.currentText()
        if ": " in text:
            return text.split(": ", 1)[1]
        return text
    
    def _on_add_to_queue(self):
        """添加到任务队列"""
        source = self._get_selected_source()
        dest = self._get_selected_dest()
        volume = self.volume_spin.value()
        
        # 验证
        if not source or source.startswith("--") or source == "请选择":
            QMessageBox.warning(self, "警告", "请选择源位置！")
            return
        
        if not dest or dest.startswith("--") or dest == "请选择":
            QMessageBox.warning(self, "警告", "请选择目标位置！")
            return
        
        if source == dest:
            QMessageBox.warning(self, "警告", "源和目标不能相同！")
            return
        
        # 添加到统一队列
        task_queue.add_pump_transfer(source, dest, volume)
        
        QMessageBox.information(
            self, "成功", 
            f"已添加移液任务:\n{source} → {dest} : {volume}mL\n\n"
            f"请查看右侧任务队列。"
        )
        
        self.task_added.emit()
