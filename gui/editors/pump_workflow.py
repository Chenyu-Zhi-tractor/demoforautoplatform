"""
泵工作流界面 - 配置编辑 → 移液执行
"""
import json
import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QFileDialog, QGroupBox, QTableView,
    QHeaderView, QAbstractItemView, QMessageBox, QStackedWidget,
    QSpinBox, QDoubleSpinBox, QFormLayout, QScrollArea, QFrame,
    QListWidget, QListWidgetItem, QMenu
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt, pyqtSignal

from .json_editor import UsageMatrixModel, WrappingItemDelegate

# 导入泵控制器
from core.hardware.serial_driver import PumpController as RealPumpController
from core.hardware.serial_driver_test import PumpController as MockPumpController
from core.hardware.parse_cmd import parse_cmd
from core.pump_logger import PumpLogger

class TaskItemWidget(QWidget):
    """单个移液任务项"""
    def __init__(self, parent=None, liquids=None, containers=None, task_type="移液"):
        super().__init__(parent)
        self.liquids = liquids or []
        self.containers = containers or []
        self.task_type = task_type
        self._selected = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)
        
        # 任务类型标签
        self.type_label = QLabel(f"[{self.task_type}]")
        self.type_label.setStyleSheet("color: #3498db; font-weight: bold;")
        self.main_layout.addWidget(self.type_label)
        
        # 源选择
        self.source_combo = QComboBox()
        self.source_combo.setPlaceholderText("选择源...")
        self.source_combo.setMinimumWidth(150)
        self._populate_sources()
        self.main_layout.addWidget(QLabel("从:"))
        self.main_layout.addWidget(self.source_combo)
        
        # 目标选择
        self.dest_combo = QComboBox()
        self.dest_combo.setPlaceholderText("选择目标...")
        self.dest_combo.setMinimumWidth(150)
        self._populate_dests()
        self.main_layout.addWidget(QLabel("到:"))
        self.main_layout.addWidget(self.dest_combo)
        
        # 体积输入
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.1, 1000)
        self.volume_spin.setValue(10.0)
        self.volume_spin.setSuffix(" mL")
        self.volume_spin.setDecimals(1)
        self.volume_spin.setMinimumWidth(100)
        self.main_layout.addWidget(QLabel("体积:"))
        self.main_layout.addWidget(self.volume_spin)
        
        self.main_layout.addStretch()
        
        # 设置默认样式
        self._update_style()
        
        # 启用鼠标跟踪
        self.setMouseTracking(True)
    
    def _update_style(self):
        """更新选中状态样式"""
        if self._selected:
            self.setStyleSheet("""
                TaskItemWidget {
                    background-color: #2980b9;
                    border: 2px solid #3498db;
                    border-radius: 4px;
                }
                QLabel { color: white; background: transparent; }
            """)
        else:
            self.setStyleSheet("""
                TaskItemWidget {
                    background-color: #34495e;
                    border: 1px solid #2c3e50;
                    border-radius: 4px;
                }
                QLabel { color: #ecf0f1; background: transparent; }
            """)
    
    def set_selected(self, selected):
        """设置选中状态"""
        self._selected = selected
        self._update_style()
    
    def is_selected(self):
        """获取选中状态"""
        return self._selected
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        # 通知父组件选中自己
        parent = self.parent()
        if parent:
            # 找到 PumpWorkflowWidget 并调用其方法
            widget = self
            while widget and not isinstance(widget, PumpWorkflowWidget):
                widget = widget.parent()
            if widget and isinstance(widget, PumpWorkflowWidget):
                widget._select_task_widget(self)
        super().mousePressEvent(event)
    
    def _populate_sources(self):
        """填充源选项（液体+容器）"""
        self.source_combo.clear()
        self.source_combo.addItem("-- 液体 --")
        self.source_combo.model().item(0).setEnabled(False)
        for idx, name in enumerate(self.liquids):
            self.source_combo.addItem(f"{idx}: {name}")
        
        if self.containers:
            self.source_combo.addItem("-- 容器 --")
            self.source_combo.model().item(self.source_combo.count()-1).setEnabled(False)
            for idx, name in enumerate(self.containers):
                self.source_combo.addItem(f"{idx}: {name}")
    
    def _populate_dests(self):
        """填充目标选项（仅容器）"""
        self.dest_combo.clear()
        self.dest_combo.addItem("-- 选择目标容器 --")
        self.dest_combo.model().item(0).setEnabled(False)
        for idx, name in enumerate(self.containers):
            self.dest_combo.addItem(f"container{idx}: {name}")
    
    def get_task(self):
        """获取任务数据"""
        # 从格式 "0: DCM" 中提取名称
        source_text = self.source_combo.currentText()
        source = source_text.split(": ", 1)[1] if ": " in source_text else source_text
        # 从格式 "0: Flask" 中提取名称
        dest_text = self.dest_combo.currentText()
        dest = dest_text.split(": ", 1)[1] if ": " in dest_text else dest_text
        volume = self.volume_spin.value()
        
        if not source or source.startswith("--"):
            return None
        if not dest or dest.startswith("--"):
            return None
        
        return {
            'type': 'transfer',  # 【新增】明确任务类型
            'source': source,
            'destination': dest,
            'volume': volume
        }
    
class PumpWorkflowWidget(QWidget):
    """泵工作流主界面"""
    
    log_saved = pyqtSignal(str)  # 日志保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_data = None
        self.liquids = []
        self.containers = []
        self.gases = []
        self._pump_controller = None  # 泵控制器实例（延迟初始化）
        self._virtual_mode = True  # 默认为虚拟调试模式
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === 顶部标题和模式切换 ===
        header_layout = QHBoxLayout()
        
        self.lbl_title = QLabel("🔧 配置编辑模式")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(self.lbl_title)
        
        header_layout.addStretch()
        
        # 下一步/返回按钮
        self.btn_next = QPushButton("下一步 ➡️")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_next.clicked.connect(self._on_next_clicked)
        header_layout.addWidget(self.btn_next)
        
        layout.addLayout(header_layout)
        
        # === 堆叠窗口：配置编辑 / 移液执行 ===
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, stretch=1)
        
        # --- 页面1: 配置编辑 ---
        self.page_config = QWidget()
        self._setup_config_page()
        self.stack.addWidget(self.page_config)
        
        # --- 页面2: 移液执行 ---
        self.page_execute = QWidget()
        self._setup_execute_page()
        self.stack.addWidget(self.page_execute)
    
    def _toggle_virtual_mode(self):
        """切换虚拟/真实模式"""
        self._virtual_mode = self.chk_virtual_mode.isChecked()
        if self._virtual_mode:
            self.chk_virtual_mode.setText("🐛 虚拟模式")
            self.chk_virtual_mode.setStyleSheet("""
                QPushButton {
                    background-color: #f39c12;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background-color: #27ae60;
                }
                QPushButton:hover { background-color: #d68910; }
            """)
        else:
            self.chk_virtual_mode.setText("⚙️ 真实模式")
            self.chk_virtual_mode.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background-color: #27ae60;
                }
                QPushButton:hover { background-color: #c0392b; }
            """)
    
    def _setup_config_page(self):
        """设置配置编辑页面"""
        layout = QVBoxLayout(self.page_config)
        layout.setContentsMargins(0, 0, 0, 0)
        
        hint = QLabel("💡 请先完成配置编辑，然后点击右上角的'下一步'")
        hint.setStyleSheet("color: #bdc3c7; padding: 10px;")
        layout.addWidget(hint)
    
    def _setup_execute_page(self):
        """设置移液执行页面"""
        layout = QHBoxLayout(self.page_execute)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # --- 左侧：Matrix 显示 ---
        left_panel = QVBoxLayout()
        
        matrix_group = QGroupBox("端口使用矩阵")
        matrix_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #34495e; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        matrix_layout = QVBoxLayout(matrix_group)
        
        self.matrix_view = QTableView()
        self.matrix_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # 水平列宽填满左边栏（Stretch），行高自适应文本内容
        self.matrix_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.matrix_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        # 使用支持文本换行的委托
        wrapping_delegate = WrappingItemDelegate(self.matrix_view)
        self.matrix_view.setItemDelegate(wrapping_delegate)
        matrix_layout.addWidget(self.matrix_view)
        
        left_panel.addWidget(matrix_group)
        
        # 添加左侧到主布局
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        layout.addWidget(left_widget, stretch=2)
        
        # --- 右侧：任务面板 ---
        right_panel = QVBoxLayout()
        
        # 任务列表组
        task_group = QGroupBox("任务列表")
        task_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #34495e; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        task_layout = QVBoxLayout(task_group)
        
        # 任务列表区域（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #2c3e50; border: none;")
        
        self.task_container = QWidget()
        self.task_list_layout = QVBoxLayout(self.task_container)
        self.task_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_list_layout.setSpacing(5)
        self.task_widgets = []
        self._selected_task_widget = None
        
        scroll.setWidget(self.task_container)
        task_layout.addWidget(scroll)
        
        right_panel.addWidget(task_group)
        
        # 安装事件过滤器以捕获鼠标点击
        self.task_container.installEventFilter(self)
        
        # 日志设置组
        log_group = QGroupBox("日志设置")
        log_group.setStyleSheet("""
            QGroupBox { 
                color: #ecf0f1; 
                font-weight: bold; 
                border: 1px solid #34495e; 
                margin-top: 10px; 
            } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; }
        """)
        log_layout = QFormLayout(log_group)
        
        # 日志路径
        path_layout = QHBoxLayout()
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("选择日志保存位置...")
        self.log_path_edit.setReadOnly(True)
        path_layout.addWidget(self.log_path_edit)
        
        self.btn_browse = QPushButton("浏览...")
        self.btn_browse.clicked.connect(self._browse_log_path)
        path_layout.addWidget(self.btn_browse)
        log_layout.addRow("保存位置:", path_layout)
        
        # 日志文件名
        self.log_name_edit = QLineEdit()
        self.log_name_edit.setPlaceholderText("pump_log_20240206.txt")
        self.log_name_edit.setText(f"pump_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        log_layout.addRow("文件名:", self.log_name_edit)
        
        right_panel.addWidget(log_group)
        
        # 虚拟模式开关
        self.chk_virtual_mode = QPushButton("🐛 虚拟模式")
        self.chk_virtual_mode.setCheckable(True)
        self.chk_virtual_mode.setChecked(True)
        self.chk_virtual_mode.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                padding: 10px;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #27ae60;
            }
            QPushButton:hover { background-color: #d68910; }
        """)
        self.chk_virtual_mode.clicked.connect(self._toggle_virtual_mode)
        right_panel.addWidget(self.chk_virtual_mode)
        
        # 执行按钮
        self.btn_execute = QPushButton("▶️ 开始执行")
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #7f8c8d; }
        """)
        self.btn_execute.clicked.connect(self._execute_tasks)
        right_panel.addWidget(self.btn_execute)
        
        # 添加右侧到主布局
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        layout.addWidget(right_widget, stretch=1)
    
    def set_editor_widget(self, editor_widget):
        """设置配置编辑器（从外部传入）"""
        self.editor_widget = editor_widget
        # 将编辑器插入到配置页面
        self.page_config.layout().addWidget(editor_widget)
    
    def load_config(self, config_data):
        """加载配置数据"""
        self.config_data = config_data
        
        # 提取液体、容器、气体列表
        self.liquids = [item['name'] for item in config_data.get('liquids', [])]
        self.containers = [item['name'] for item in config_data.get('containers', [])]
        self.gases = [item['name'] for item in config_data.get('gases', [])]
        
        # 更新 matrix 模型
        settings = config_data.get('settings', {'pump_count': 4, 'port_count': 8})
        connections = config_data.get('connections', [])
        liquids = config_data.get('liquids', [])
        gases = config_data.get('gases', [])
        containers = config_data.get('containers', [])
        
        self.matrix_model = UsageMatrixModel(settings, connections, liquids, gases, containers)
        self.matrix_view.setModel(self.matrix_model)
        
        # 更新现有任务的选择列表
        for task_widget in self.task_widgets:
            task_widget.liquids = self.liquids
            task_widget.containers = self.containers
            task_widget._populate_sources()
            task_widget._populate_dests()
    
    def _on_next_clicked(self):
        """下一步/返回按钮点击"""
        if self.stack.currentIndex() == 0:
            # 当前是配置页面，切换到执行页面
            self._switch_to_execute()
        else:
            # 当前是执行页面，返回配置页面
            self._switch_to_config()
    
    def _switch_to_execute(self):
        """切换到执行页面"""
        # 获取当前配置数据
        if hasattr(self, 'editor_widget'):
            self.config_data = self.editor_widget.to_json()
            self.load_config(self.config_data)
        
        self.stack.setCurrentIndex(1)
        self.lbl_title.setText("▶️ 移液执行模式")
        self.btn_next.setText("⬅️ 返回编辑")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
    
    def _switch_to_config(self):
        """返回配置页面"""
        self.stack.setCurrentIndex(0)
        self.lbl_title.setText("🔧 配置编辑模式")
        self.btn_next.setText("下一步 ➡️")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理任务容器的鼠标点击"""
        if obj == self.task_container and event.type() == event.Type.MouseButtonPress:
            # 左键点击：选中任务项
            if event.button() == Qt.MouseButton.LeftButton:
                clicked_widget = self.task_container.childAt(event.pos())
                if clicked_widget and clicked_widget != self.task_container:
                    # 找到对应的 TaskItemWidget 并选中
                    widget = clicked_widget
                    while widget and not isinstance(widget, TaskItemWidget):
                        widget = widget.parent()
                    if widget:
                        self._select_task_widget(widget)
                        return True
                else:
                    # 点击空白区域，取消选中
                    self._select_task_widget(None)
                    return True
            
            # 右键点击：弹出菜单
            elif event.button() == Qt.MouseButton.RightButton:
                # 检查是否点击在空白区域（没有点击到具体任务项）
                clicked_widget = self.task_container.childAt(event.pos())
                if clicked_widget is None or clicked_widget == self.task_container:
                    # 显示添加任务菜单
                    self._show_add_task_menu(event.globalPosition().toPoint())
                    return True
                else:
                    # 找到对应的 TaskItemWidget
                    widget = clicked_widget
                    while widget and not isinstance(widget, TaskItemWidget):
                        widget = widget.parent()
                    if widget:
                        self._select_task_widget(widget)
                        # 显示上下文菜单（在行之上/之下添加）
                        self._show_task_context_menu(widget, event.globalPosition().toPoint())
                        return True
        return super().eventFilter(obj, event)
    
    def _select_task_widget(self, task_widget):
        """选中指定的任务项"""
        # 取消之前的选中
        if self._selected_task_widget and self._selected_task_widget != task_widget:
            self._selected_task_widget.set_selected(False)
        
        self._selected_task_widget = task_widget
        if task_widget:
            task_widget.set_selected(True)
    
    def _show_add_task_menu(self, pos):
        """显示添加任务菜单（空白区域点击）"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """)
        
        add_pipette = menu.addAction("🧪 添加移液任务")
        action = menu.exec(pos)
        
        if action == add_pipette:
            self._add_task_at_index(len(self.task_widgets))
    
    def _show_task_context_menu(self, task_widget, pos):
        """显示任务项的上下文菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """)
        
        # 获取当前任务项的索引
        index = self.task_widgets.index(task_widget) if task_widget in self.task_widgets else -1
        
        add_above = menu.addAction("⬆️ 在上方添加任务")
        add_below = menu.addAction("⬇️ 在下方添加任务")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ 删除此任务")
        menu.addSeparator()
        cancel_action = menu.addAction("取消")
        
        action = menu.exec(pos)
        
        if action == add_above:
            self._add_task_at_index(index)
        elif action == add_below:
            self._add_task_at_index(index + 1)
        elif action == delete_action:
            self._remove_task(task_widget)
    
    def _add_task_at_index(self, index, task_type="移液"):
        """在指定索引位置添加新任务"""
        task_widget = TaskItemWidget(
            liquids=self.liquids, 
            containers=self.containers,
            task_type=task_type
        )
        
        # 插入到指定位置
        self.task_widgets.insert(index, task_widget)
        self.task_list_layout.insertWidget(index, task_widget)
        
        # 选中新添加的任务
        self._select_task_widget(task_widget)
    
    def _remove_task(self, task_widget):
        """移除任务"""
        if task_widget in self.task_widgets:
            self.task_widgets.remove(task_widget)
            if self._selected_task_widget == task_widget:
                self._selected_task_widget = None
            task_widget.deleteLater()
    
    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Delete:
            # 删除选中的任务
            if self._selected_task_widget:
                self._remove_task(self._selected_task_widget)
        else:
            super().keyPressEvent(event)
    
    def _browse_log_path(self):
        """浏览日志保存位置"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "选择日志保存位置", 
            self.log_name_edit.text(),
            "文本文件 (*.txt);;所有文件 (*)"
        )
        if filename:
            self.log_path_edit.setText(os.path.dirname(filename))
            self.log_name_edit.setText(os.path.basename(filename))
    
    def _execute_tasks(self):
        """执行所有任务"""
        # 收集所有任务
        tasks = []
        for task_widget in self.task_widgets:
            task = task_widget.get_task()
            if task:
                tasks.append(task)
        
        if not tasks:
            QMessageBox.warning(self, "警告", "请先添加至少一个任务！\n在任务列表区域左键点击添加任务。")
            return
        
        # 检查日志路径
        log_path = self.log_path_edit.text()
        log_name = self.log_name_edit.text()
        
        if not log_path:
            # 使用默认路径
            log_path = os.path.join(os.path.dirname(__file__), '..\..', 'logs')
            os.makedirs(log_path, exist_ok=True)
        
        if not log_name:
            log_name = f"pump_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        full_path = os.path.join(log_path, log_name)
        
        # 确认执行
        task_summary = "\n".join([f"  {i+1}. {t['source']} → {t['destination']} : {t['volume']}mL" 
                                  for i, t in enumerate(tasks)])
        
        reply = QMessageBox.question(
            self, "确认执行",
            f"即将执行以下 {len(tasks)} 个移液任务:\n{task_summary}\n\n"
            f"日志将保存到: {full_path}\n\n确认开始执行吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 根据当前模式选择控制器类
            self._pump_controller_class = MockPumpController if self._virtual_mode else RealPumpController
            self._run_pump_tasks(tasks, full_path)
    
    def _run_pump_tasks(self, tasks, log_path):
        """
        实际执行泵任务
        使用 serial_driver 中的 PumpController
        只在第一次执行任务时初始化泵
        实时写入日志，即使出错也能保存已执行的内容
        使用 PumpLogger 处理日志记录
        """
        has_error = False
        error_msg = ""
        completed_tasks = 0
        
        # 使用上下文管理器自动处理文件打开/关闭和异常记录
        with PumpLogger(log_path) as logger:
            try:
                # 只在第一次执行时创建和初始化泵控制器
                if self._pump_controller is None:
                    logger.log_system_action("创建泵控制器")
                    self._pump_controller = self._pump_controller_class(
                        port='COM11', 
                        config_dict=self.config_data  # 传入当前界面的配置数据
                    )
                    logger.log_system_action("初始化所有泵")
                    
                    # 1. 静默底层驱动的输出（防止它往日志或控制台打印"Step 1"等调试信息）
                    self._pump_controller.set_logger(lambda x: None)
                    
                    self._pump_controller.init_all_pumps()

                    # 记录初始化指令
                    init_cmds = self._pump_controller.get_commands_log()
                    logger.log_init_commands(init_cmds)
                
                controller = self._pump_controller
                
                # 确保驱动保持静默
                controller.set_logger(lambda x: None)

                # 日志头部和配置
                logger.log_header(len(tasks))
                logger.log_config_summary(self.config_data)
                
                # 记录当前命令日志长度
                cmd_start_index = len(controller.get_commands_log())
                
                for i, task in enumerate(tasks, 1):
                    # 更新当前命令起始位置
                    cmd_start_index = len(controller.get_commands_log())

                    logger.log_task_start(i, len(tasks), task)
                    
                    try:
                        # 执行移液
                        result = controller.transfer(task['source'], task['destination'], task['volume'])
                        
                        # 获取该任务执行的所有命令（只取新增部分）
                        all_cmds = controller.get_commands_log()
                        new_cmds = all_cmds[cmd_start_index:]
                        
                        # 记录成功结果
                        if task.get('type') == 'transfer':
                            logger.log_transfer_success(i, result, result['transferred'], new_cmds)
                        else:
                            # 简单的通用记录
                            logger.log_generic_success(i, "操作执行成功")
                        
                        completed_tasks += 1
                        
                    except Exception as task_error:
                        # 单个任务出错，记录错误但继续执行后续任务
                        has_error = True
                        error_msg = str(task_error)
                        logger.log_task_failure(i, error_msg)
                        # 继续执行下一个任务
                        continue
                
                # 执行总结
                total_vol = sum(t['volume'] for t in tasks[:completed_tasks])
                logger.log_summary(len(tasks), completed_tasks, len(tasks) - completed_tasks, 
                                 total_vol, has_error, error_msg)
                
                self.log_saved.emit(log_path)
                
                if has_error:
                    QMessageBox.warning(self, "部分完成", 
                        f"任务执行完成，但有 {len(tasks) - completed_tasks} 个任务失败。\n"
                        f"最后错误: {error_msg}\n\n"
                        f"日志已保存到:\n{log_path}")
                else:
                    QMessageBox.information(self, "完成", f"所有任务执行完成！\n日志已保存到:\n{log_path}")
            
            except Exception as e:
                # 顶层错误处理由 PumpLogger.__exit__ 记录日志
                error_msg = str(e)
                # 只需要弹出提示框
                QMessageBox.critical(self, "执行错误", 
                    f"执行过程中出现错误:\n{error_msg}\n\n"
                    f"日志已保存到:\n{log_path}")
