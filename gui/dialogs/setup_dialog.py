from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
    QPushButton, QDialogButtonBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

class SetupDialog(QDialog):
    def __init__(self, parent=None, current_pumps=4, current_ports=8):
        super().__init__(parent)
        self.setWindowTitle("系统设置 (System Setup)")
        self.resize(350, 200)
        
        self.result_pumps = current_pumps
        self.result_ports = current_ports
        
        layout = QVBoxLayout(self)
        
        # 分组框
        group = QGroupBox("硬件规格 (Hardware Specs)")
        form_layout = QFormLayout()
        
        self.spin_pumps = QSpinBox()
        self.spin_pumps.setRange(1, 100)
        self.spin_pumps.setValue(current_pumps)
        self.spin_pumps.setSuffix(" 个")
        
        self.spin_ports = QSpinBox()
        self.spin_ports.setRange(1, 100)
        self.spin_ports.setValue(current_ports)
        self.spin_ports.setSuffix(" 个")
        
        form_layout.addRow("泵数量 (Pump Count):", self.spin_pumps)
        form_layout.addRow("单泵端口数 (Ports/Pump):", self.spin_ports)
        
        group.setLayout(form_layout)
        layout.addWidget(group)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        self.result_pumps = self.spin_pumps.value()
        self.result_ports = self.spin_ports.value()
        super().accept()
        
    def get_values(self):
        return self.result_pumps, self.result_ports
