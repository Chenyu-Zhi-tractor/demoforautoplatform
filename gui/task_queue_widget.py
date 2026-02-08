"""
任务队列显示和控制界面
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QGroupBox,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from .task_queue import task_queue, TaskType, Task


class TaskQueueWidget(QWidget):
    """任务队列显示和控制界面"""
    
    # 信号
    task_selected = pyqtSignal(int)  # 选中任务索引
    queue_changed = pyqtSignal()     # 队列发生变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_index = -1
        self._setup_ui()
        
        # 注册为任务队列的观察者
        task_queue.add_observer(self._on_queue_changed)
        self._refresh_list()
    
    def __del__(self):
        # 清理观察者
        try:
            task_queue.remove_observer(self._on_queue_changed)
        except:
            pass
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === 标题栏 ===
        header_layout = QHBoxLayout()
        
        title = QLabel("📋 任务队列")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ecf0f1;")
        header_layout.addWidget(title)
        
        self.lbl_count = QLabel("(0 个任务)")
        self.lbl_count.setStyleSheet("color: #bdc3c7;")
        header_layout.addWidget(self.lbl_count)
        
        header_layout.addStretch()
        
        # 清空按钮
        self.btn_clear = QPushButton("🗑️ 清空")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 5px 10px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_clear.clicked.connect(self._on_clear)
        header_layout.addWidget(self.btn_clear)
        
        layout.addLayout(header_layout)
        
        # === 任务列表 ===
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                background-color: #2c3e50;
                border: 1px solid #34495e;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #34495e;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:disabled {
                color: #7f8c8d;
            }
        """)
        self.task_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.task_list.itemClicked.connect(self._on_item_clicked)
        self.task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.task_list)
        
        # === 操作按钮栏 ===
        btn_layout = QHBoxLayout()
        
        self.btn_move_up = QPushButton("⬆️ 上移")
        self.btn_move_up.setStyleSheet("padding: 8px;")
        self.btn_move_up.clicked.connect(self._on_move_up)
        self.btn_move_up.setEnabled(False)
        btn_layout.addWidget(self.btn_move_up)
        
        self.btn_move_down = QPushButton("⬇️ 下移")
        self.btn_move_down.setStyleSheet("padding: 8px;")
        self.btn_move_down.clicked.connect(self._on_move_down)
        self.btn_move_down.setEnabled(False)
        btn_layout.addWidget(self.btn_move_down)
        
        btn_layout.addStretch()
        
        self.btn_toggle = QPushButton("✓ 启用/禁用")
        self.btn_toggle.setStyleSheet("padding: 8px;")
        self.btn_toggle.clicked.connect(self._on_toggle)
        self.btn_toggle.setEnabled(False)
        btn_layout.addWidget(self.btn_toggle)
        
        self.btn_delete = QPushButton("🗑️ 删除")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.setEnabled(False)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addLayout(btn_layout)
        
        # === 提示信息 ===
        hint = QLabel("💡 提示：右键点击任务可进行更多操作\n"
                     "从其他标签页添加的任务会显示在这里，按顺序执行")
        hint.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(hint)
    
    def _refresh_list(self):
        """刷新任务列表显示"""
        self.task_list.clear()
        
        tasks = task_queue.get_all_tasks()
        self.lbl_count.setText(f"({len(tasks)} 个任务, {task_queue.get_enabled_count()} 个启用)")
        
        for i, task in enumerate(tasks):
            item = QListWidgetItem()
            
            # 设置显示文本
            display_text = f"{i+1}. {task.get_display_text()}"
            if not task.enabled:
                display_text += " [已禁用]"
                item.setForeground(QColor("#7f8c8d"))
            
            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, i)  # 存储索引
            
            self.task_list.addItem(item)
        
        # 恢复选中状态
        if self._selected_index >= 0 and self._selected_index < len(tasks):
            self.task_list.setCurrentRow(self._selected_index)
        
        self._update_button_state()
        self.queue_changed.emit()
    
    def _on_queue_changed(self):
        """队列发生变化时的回调"""
        self._refresh_list()
    
    def _update_button_state(self):
        """更新按钮状态"""
        has_selection = self._selected_index >= 0
        task_count = task_queue.get_task_count()
        
        self.btn_move_up.setEnabled(has_selection and self._selected_index > 0)
        self.btn_move_down.setEnabled(has_selection and self._selected_index < task_count - 1)
        self.btn_toggle.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_clear.setEnabled(task_count > 0)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """列表项点击事件"""
        self._selected_index = item.data(Qt.ItemDataRole.UserRole)
        self._update_button_state()
        self.task_selected.emit(self._selected_index)
    
    def _on_context_menu(self, position):
        """右键菜单"""
        item = self.task_list.itemAt(position)
        if item is None:
            return
        
        index = item.data(Qt.ItemDataRole.UserRole)
        task = task_queue.get_task(index)
        if task is None:
            return
        
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
        
        # 添加操作
        move_up_action = menu.addAction("⬆️ 上移")
        move_down_action = menu.addAction("⬇️ 下移")
        menu.addSeparator()
        
        toggle_text = "✓ 禁用" if task.enabled else "✓ 启用"
        toggle_action = menu.addAction(toggle_text)
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ 删除")
        
        # 禁用不可用的操作
        move_up_action.setEnabled(index > 0)
        move_down_action.setEnabled(index < task_queue.get_task_count() - 1)
        
        # 执行菜单
        action = menu.exec(self.task_list.mapToGlobal(position))
        
        if action == move_up_action:
            task_queue.move_up(index)
            self._selected_index = index - 1
        elif action == move_down_action:
            task_queue.move_down(index)
            self._selected_index = index + 1
        elif action == toggle_action:
            task_queue.toggle_task(index)
        elif action == delete_action:
            task_queue.remove_task(index)
            self._selected_index = -1
    
    def _on_move_up(self):
        """上移按钮"""
        if self._selected_index > 0:
            task_queue.move_up(self._selected_index)
            self._selected_index -= 1
    
    def _on_move_down(self):
        """下移按钮"""
        if self._selected_index < task_queue.get_task_count() - 1:
            task_queue.move_down(self._selected_index)
            self._selected_index += 1
    
    def _on_toggle(self):
        """切换启用/禁用"""
        if self._selected_index >= 0:
            task_queue.toggle_task(self._selected_index)
    
    def _on_delete(self):
        """删除按钮"""
        if self._selected_index >= 0:
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除选中的任务吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                task_queue.remove_task(self._selected_index)
                self._selected_index = -1
    
    def _on_clear(self):
        """清空按钮"""
        if task_queue.get_task_count() == 0:
            return
        
        reply = QMessageBox.question(
            self, "确认清空",
            f"确定要清空所有 {task_queue.get_task_count()} 个任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            task_queue.clear()
            self._selected_index = -1
    
    def get_selected_index(self) -> int:
        """获取当前选中的索引"""
        return self._selected_index
    
    def select_index(self, index: int):
        """选中指定索引"""
        if 0 <= index < self.task_list.count():
            self._selected_index = index
            self.task_list.setCurrentRow(index)
            self._update_button_state()
