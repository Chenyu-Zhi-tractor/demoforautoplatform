import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox, QHeaderView,
    QAbstractItemView, QGroupBox
)
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

# 引入我们的编辑器 Widget
from gui.editors.json_editor import JsonEditorWidget
# 引入设置对话框
from gui.dialogs.setup_dialog import SetupDialog
# 引入工作流界面
from gui.editors.pump_workflow import PumpWorkflowWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("泵配置与执行系统 (Pump Config & Control)")
        self.setGeometry(100, 100, 1200, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # === 工具栏 ===
        toolbar = QHBoxLayout()
        
        self.btn_new = QPushButton("📄 新建 (New)")
        self.btn_new.clicked.connect(self.new_file)
        self.btn_new.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_new)

        self.btn_open = QPushButton("📂 打开 (Open)")
        self.btn_open.clicked.connect(self.open_file)
        self.btn_open.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_open)
        
        self.btn_save = QPushButton("💾 保存 (Save)")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_save)
        
        self.btn_save_as = QPushButton("💾 另存为 (Save As)")
        self.btn_save_as.clicked.connect(self.save_as_file)
        self.btn_save_as.setEnabled(False)
        self.btn_save_as.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_save_as)
        
        toolbar.addStretch()
        
        self.lbl_file = QLabel("未打开文件")
        self.lbl_file.setStyleSheet("color: #ecf0f1; font-weight: bold;")
        toolbar.addWidget(self.lbl_file)
        
        layout.addLayout(toolbar)
        
        # === 主工作流界面 ===
        self.workflow = PumpWorkflowWidget()
        self.workflow.log_saved.connect(self.on_log_saved)
        layout.addWidget(self.workflow, stretch=1)
        
        # 创建编辑器并设置到工作流
        self.editor = JsonEditorWidget()
        self.workflow.set_editor_widget(self.editor)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        self.current_file = None
        
        # 自动检查文件
        self._check_init_file()

    def new_file(self):
        """创建新文件，询问配置"""
        dialog = SetupDialog(self)
        if dialog.exec():
            # 获取用户输入
            pump_count = dialog.spin_pumps.value()
            port_count = dialog.spin_ports.value()
            
            # 使用包含 settings 的字典更新编辑器
            new_data = {
                "settings": {"pump_count": pump_count, "port_count": port_count},
                "connections": [],
                "liquids": [],
                "gases": [],
                "containers": []
            }
            self.editor.load_json(new_data)
            self.workflow.load_config(new_data)
            
            # 重置文件状态
            self.current_file = None
            self.lbl_file.setText("未保存的新文件")
            self.btn_save.setEnabled(True)
            self.btn_save_as.setEnabled(True)
            self.statusBar().showMessage(f"已新建配置: {pump_count} 泵, {port_count} 端口")

    def load_from_path(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 读取配置
            p_count = 4 
            port_count = 8
            if "settings" in data:
                p_count = int(data["settings"].get("pump_count", 4))
                port_count = int(data["settings"].get("port_count", 8))
            
            self.editor.load_json(data)
            self.workflow.load_config(data)
            
            self.current_file = filename
            
            self.lbl_file.setText(f"当前文件: {os.path.basename(filename)}")
            self.btn_save.setEnabled(True)
            self.btn_save_as.setEnabled(True)
            
            self.statusBar().showMessage(f"已加载: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件:\n{str(e)}")

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择 JSON 文件", "", "JSON 文件 (*.json);;所有文件 (*)"
        )
        if filename:
            self.load_from_path(filename)

    def _check_init_file(self):
        # 寻找上级 config 文件夹里的 pump_config.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # gui 的上一级，即 demo 目录
        config_dir = os.path.join(project_root, "config")
        target_path = os.path.join(config_dir, "pump_config.json")
        
        if os.path.exists(target_path):
            self.load_from_path(target_path)
        else:
            try:
                # 确保 config 文件夹存在
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                    
                # 不存在则创建默认文件
                data = {
                    "settings": {"pump_count": 4, "port_count": 8},
                    "connections": [],
                    "liquids": [],
                    "gases": [],
                    "containers": []
                }
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.load_from_path(target_path)
                self.statusBar().showMessage(f"默认文件不存在，已自动创建: {target_path}")
            except Exception as e:
                self.statusBar().showMessage(f"自动创建失败: {str(e)}")

    def _generate_default_path(self):
        """生成默认文件名，如果有冲突则自动递增"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_dir = os.path.join(project_root, "config")
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        base_name = "pump_config"
        
        # 1. 尝试 pump_config.json
        full_path = os.path.join(config_dir, f"{base_name}.json")
        if not os.path.exists(full_path):
            return full_path
            
        # 2. 尝试 pump_config_1.json, _2.json ...
        counter = 1
        while True:
            full_path = os.path.join(config_dir, f"{base_name}_{counter}.json")
            if not os.path.exists(full_path):
                return full_path
            counter += 1

    def save_file(self):
        if self.current_file:
            # 原地保存
            self._do_save(self.current_file)
        else:
            # 如果是新文件，自动生成不冲突的文件名
            new_path = self._generate_default_path()
            if self._do_save(new_path, silent=True):
                self.current_file = new_path
                self.lbl_file.setText(f"当前文件: {os.path.basename(new_path)}")
                QMessageBox.information(self, "已自动保存", f"新文件已保存为:\n{new_path}")

    def save_as_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "JSON 文件 (*.json)"
        )
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            if self._do_save(filename, silent=True):
                self.current_file = filename
                self.lbl_file.setText(f"当前文件: {os.path.basename(filename)}")
                QMessageBox.information(self, "另存为成功", f"文件已保存到:\n{filename}")
            
    def _do_save(self, filename, silent=False):
        """执行保存操作"""
        try:
            data = self.editor.to_json()
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.statusBar().showMessage(f"已保存: {filename}")
            
            if not silent:
                QMessageBox.information(self, "成功", f"文件已保存!\n{filename}")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存失败:\n{str(e)}")
            return False
    
    def on_log_saved(self, log_path):
        """日志保存后的回调"""
        self.statusBar().showMessage(f"执行日志已保存: {log_path}")
