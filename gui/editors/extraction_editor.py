"""
Extraction task editor (A: stir, B: piston)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QDoubleSpinBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal

from core.hardware.driver_manager import DriverManager
from gui.task_queue import task_queue


class ExtractionEditorWidget(QWidget):
    """Extraction control editor."""

    task_added = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title = QLabel("🧪 萃取任务")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        header_layout.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.addItems(["COM1", "COM2", "COM3", "COM4", "COM5",
                                  "COM6", "COM7", "COM8", "COM9", "COM10",
                                  "COM11", "COM12", "COM13", "COM14", "COM15"])
        self.port_combo.setCurrentText("COM9")
        self.port_combo.setMinimumWidth(100)
        header_layout.addWidget(self.port_combo)

        layout.addLayout(header_layout)

        # === A 电机：搅拌（定时） ===
        stir_group = QGroupBox("搅拌")
        stir_group.setStyleSheet("""
            QGroupBox {
                color: #ecf0f1;
                font-weight: bold;
                border: 1px solid #34495e;
                margin-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        stir_layout = QHBoxLayout(stir_group)

        stir_layout.addWidget(QLabel("速度:"))
        self.stir_speed_spin = QDoubleSpinBox()
        self.stir_speed_spin.setRange(0.1, 20.0)
        self.stir_speed_spin.setValue(1.0)
        self.stir_speed_spin.setSuffix(" rps")
        self.stir_speed_spin.setDecimals(2)
        stir_layout.addWidget(self.stir_speed_spin)

        stir_layout.addWidget(QLabel("时间:"))
        self.stir_time_spin = QDoubleSpinBox()
        self.stir_time_spin.setRange(0.1, 600.0)
        self.stir_time_spin.setValue(5.0)
        self.stir_time_spin.setSuffix(" s")
        self.stir_time_spin.setDecimals(1)
        stir_layout.addWidget(self.stir_time_spin)

        self.btn_stir_run = QPushButton("▶️ 立即搅拌")
        self.btn_stir_run.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_stir_run.clicked.connect(self._on_stir_run)
        stir_layout.addWidget(self.btn_stir_run)

        layout.addWidget(stir_group)

        # === B 电机：活塞（固定 90 度） ===
        piston_group = QGroupBox("活塞")
        piston_group.setStyleSheet("""
            QGroupBox {
                color: #ecf0f1;
                font-weight: bold;
                border: 1px solid #34495e;
                margin-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        piston_layout = QHBoxLayout(piston_group)

        piston_layout.addWidget(QLabel("速度: 2 rps"))
        piston_layout.addWidget(QLabel("圈数: 0.25"))

        self.btn_piston_run = QPushButton("▶️ 旋转活塞")
        self.btn_piston_run.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_piston_run.clicked.connect(self._on_piston_run)
        piston_layout.addWidget(self.btn_piston_run)
        piston_layout.addStretch()

        layout.addWidget(piston_group)

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

        add_row = QHBoxLayout()
        self.btn_add_stir = QPushButton("➕ 添加萃取装置搅拌任务")
        self.btn_add_stir.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d68910; }
        """)
        self.btn_add_stir.clicked.connect(self._on_add_stir)
        add_row.addWidget(self.btn_add_stir)

        self.btn_add_piston = QPushButton("➕ 添加萃取装置旋转活塞任务")
        self.btn_add_piston.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        self.btn_add_piston.clicked.connect(self._on_add_piston)
        add_row.addWidget(self.btn_add_piston)

        add_row.addStretch()
        queue_layout.addLayout(add_row)

        hint = QLabel("💡 A 电机按设定速度/时间搅拌，B 电机固定 90° 动作")
        hint.setStyleSheet("color: #7f8c8d;")
        queue_layout.addWidget(hint)

        layout.addWidget(queue_group)
        layout.addStretch()

    def get_port(self) -> str:
        return self.port_combo.currentText()

    def _get_controller(self):
        if self._controller is None:
            ControllerClass = DriverManager.instance().get_extraction_stepper_controller_class()
            self._controller = ControllerClass(port=self.get_port())
        return self._controller

    def _on_stir_run(self):
        speed = self.stir_speed_spin.value()
        seconds = self.stir_time_spin.value()
        revs = speed * seconds

        try:
            controller = self._get_controller()
            if controller.set_speed_rps("A", speed) is None:
                pass
            controller.rotate_revolutions("A", revs)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")

    def _on_piston_run(self):
        try:
            controller = self._get_controller()
            if controller.set_speed_rps("B", 2) is None:
                pass
            controller.rotate_revolutions("B", 0.25)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行出错:\n{str(e)}")

    def _on_add_stir(self):
        speed = self.stir_speed_spin.value()
        seconds = self.stir_time_spin.value()
        task_queue.add_extraction_stir(speed, seconds)
        QMessageBox.information(self, "成功", f"已添加萃取装置搅拌任务: {speed} rps, {seconds} s")
        self.task_added.emit()

    def _on_add_piston(self):
        task_queue.add_extraction_piston()
        QMessageBox.information(self, "成功", "已添加萃取装置旋转活塞任务")
        self.task_added.emit()
