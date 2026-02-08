import sys
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QMessageBox, QTabWidget,
    QLineEdit, QSplitter
)
from PyQt6.QtCore import Qt

# 引入编辑器
from gui.editors.json_editor import JsonEditorWidget
from gui.dialogs.setup_dialog import SetupDialog
from gui.editors.pump_editor import PumpEditorWidget
from gui.editors.ika_editor import IKAEditorWidget
from gui.task_queue_widget import TaskQueueWidget
from gui.task_queue import task_queue, TaskType

# 导入日志器
from core.pump_logger import PumpLogger

# 导入硬件驱动
# 虚拟调试模式
from core.hardware.serial_driver_test import PumpController
from core.hardware.ikaset_test import StirController
# 真实模式请使用：
# from core.hardware.serial_driver import PumpController
# from core.hardware.ikaset import StirController


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("实验控制系统 (Pump & IKA Control)")
        self.setGeometry(100, 100, 1600, 1000)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # === 顶部工具栏 ===
        toolbar = QHBoxLayout()
        
        self.btn_new = QPushButton("📄 新建配置")
        self.btn_new.clicked.connect(self.new_file)
        self.btn_new.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_new)

        self.btn_open = QPushButton("📂 打开配置")
        self.btn_open.clicked.connect(self.open_file)
        self.btn_open.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_open)
        
        self.btn_save = QPushButton("💾 保存")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_save)
        
        self.btn_save_as = QPushButton("💾 另存为")
        self.btn_save_as.clicked.connect(self.save_as_file)
        self.btn_save_as.setEnabled(False)
        self.btn_save_as.setStyleSheet("padding: 5px 15px; font-weight: bold;")
        toolbar.addWidget(self.btn_save_as)
        
        toolbar.addStretch()
        
        self.lbl_file = QLabel("未打开文件")
        self.lbl_file.setStyleSheet("color: #ecf0f1; font-weight: bold;")
        toolbar.addWidget(self.lbl_file)
        
        layout.addLayout(toolbar)
        
        # === 全局设置区域 ===
        settings_group = QWidget()
        settings_layout = QHBoxLayout(settings_group)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        
        settings_layout.addWidget(QLabel("日志路径:"))
        self.log_path_edit = QLineEdit()
        self.log_path_edit.setPlaceholderText("选择日志保存位置...")
        self.log_path_edit.setReadOnly(True)
        settings_layout.addWidget(self.log_path_edit, stretch=2)
        
        self.btn_browse_log = QPushButton("浏览...")
        self.btn_browse_log.clicked.connect(self._browse_log_path)
        settings_layout.addWidget(self.btn_browse_log)
        
        settings_layout.addWidget(QLabel("文件名:"))
        self.log_name_edit = QLineEdit()
        self.log_name_edit.setPlaceholderText("log_20240206.txt")
        self.log_name_edit.setText(f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        settings_layout.addWidget(self.log_name_edit, stretch=1)
        
        layout.addWidget(settings_group)
        
        # === 主分割器：左侧配置区 | 右侧任务队列 ===
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- 左侧：上下分割（上方系统配置，下方任务配置） ---
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上方：系统配置（包含Matrix）
        self.editor = JsonEditorWidget()
        left_splitter.addWidget(self.editor)
        
        # 下方：任务配置标签页
        self.task_tabs = QTabWidget()
        self.task_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #34495e; }
            QTabBar::tab {
                background-color: #34495e;
                color: #ecf0f1;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
            }
        """)
        
        # 泵任务配置
        self.pump_editor = PumpEditorWidget()
        self.pump_editor.task_added.connect(self._on_task_added)
        self.task_tabs.addTab(self.pump_editor, "🧪 泵任务")
        
        # IKA任务配置
        self.ika_editor = IKAEditorWidget()
        self.ika_editor.task_added.connect(self._on_task_added)
        self.task_tabs.addTab(self.ika_editor, "🌀 IKA任务")
        
        left_splitter.addWidget(self.task_tabs)
        left_splitter.setSizes([600, 300])  # 上方占2/3，下方占1/3
        
        # --- 右侧：任务队列 ---
        self.task_queue_widget = TaskQueueWidget()
        self.task_queue_widget.queue_changed.connect(self._on_queue_changed)
        
        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(self.task_queue_widget)
        main_splitter.setSizes([1000, 600])
        
        layout.addWidget(main_splitter, stretch=1)
        
        # === 底部执行栏 ===
        execute_layout = QHBoxLayout()
        
        self.lbl_task_stats = QLabel("队列: 0 个任务")
        self.lbl_task_stats.setStyleSheet("color: #bdc3c7;")
        execute_layout.addWidget(self.lbl_task_stats)
        
        execute_layout.addStretch()
        
        self.btn_execute = QPushButton("▶️ 执行任务队列")
        self.btn_execute.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 12px 30px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:disabled { background-color: #7f8c8d; }
        """)
        self.btn_execute.clicked.connect(self._execute_tasks)
        execute_layout.addWidget(self.btn_execute)
        
        layout.addLayout(execute_layout)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        self.current_file = None
        self.config_data = None
        self._pump_controller = None
        self._stir_controller = None
        
        # 自动检查文件
        self._check_init_file()
        
        # 设置默认日志路径
        self._set_default_log_path()
    
    def _set_default_log_path(self):
        """设置默认日志路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        log_dir = os.path.join(project_root, "logs")
        self.log_path_edit.setText(log_dir)
    
    def _browse_log_path(self):
        """浏览日志保存位置"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "选择日志保存位置", 
            self.log_name_edit.text(),
            "文本文件 (*.txt);;所有文件 (* *)"
        )
        if filename:
            self.log_path_edit.setText(os.path.dirname(filename))
            self.log_name_edit.setText(os.path.basename(filename))
    
    def _get_full_log_path(self):
        """获取完整日志路径"""
        log_path = self.log_path_edit.text()
        log_name = self.log_name_edit.text()
        
        if not log_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            log_path = os.path.join(project_root, "logs")
        
        if not log_name:
            log_name = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        return os.path.join(log_path, log_name)
    
    def _on_task_added(self):
        """任务添加后的回调"""
        self._update_task_stats()
        self.statusBar().showMessage("任务已添加到队列")
    
    def _on_queue_changed(self):
        """队列变化时的回调"""
        self._update_task_stats()
    
    def _update_task_stats(self):
        """更新任务统计"""
        total = task_queue.get_task_count()
        enabled = task_queue.get_enabled_count()
        self.lbl_task_stats.setText(f"队列: {total} 个任务 ({enabled} 个启用)")
        self.btn_execute.setEnabled(enabled > 0)
    
    def _execute_tasks(self):
        """执行任务队列"""
        tasks = task_queue.get_enabled_tasks()
        if not tasks:
            QMessageBox.warning(self, "警告", "没有启用的任务！")
            return
        
        log_path = self._get_full_log_path()
        
        # 确认执行
        task_summary = []
        for i, task in enumerate(tasks[:10], 1):
            task_summary.append(f"  {i}. {task.get_display_text()}")
        if len(tasks) > 10:
            task_summary.append(f"  ... 还有 {len(tasks) - 10} 个任务")
        
        reply = QMessageBox.question(
            self, "确认执行",
            f"即将按顺序执行 {len(tasks)} 个任务:\n" + "\n".join(task_summary) + 
            f"\n\n日志将保存到: {log_path}\n\n确认开始执行吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._run_tasks(tasks, log_path)
    
    def _run_tasks(self, tasks, log_path):
        """按顺序执行任务队列"""
        import time
        
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        has_error = False
        error_msg = ""
        completed = 0
        failed = 0
        
        with PumpLogger(log_path) as logger:
            try:
                # 日志头部
                logger.write("=" * 70)
                logger.write(" " * 20 + "实验执行日志")
                logger.write("=" * 70)
                logger.write(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.write(f"总任务数: {len(tasks)}")
                logger.write("")
                
                # 记录配置
                if self.config_data:
                    logger.log_config_summary(self.config_data)
                    logger.write("")
                
                # 按顺序执行任务
                for i, task in enumerate(tasks, 1):
                    logger.write("=" * 70)
                    logger.write(f"【任务 {i}/{len(tasks)}】{task.get_display_text()}")
                    logger.write("=" * 70)
                    logger.write("")
                    
                    try:
                        if task.task_type == TaskType.PUMP_TRANSFER:
                            self._execute_pump_task(task, logger, i, len(tasks))
                        elif task.task_type == TaskType.IKA_START:
                            self._execute_ika_start(task, logger, i)
                        elif task.task_type == TaskType.IKA_STOP:
                            self._execute_ika_stop(task, logger, i)
                        elif task.task_type == TaskType.IKA_SET_SPEED:
                            self._execute_ika_set_speed(task, logger, i)
                        elif task.task_type == TaskType.IKA_CONTROL:
                            self._execute_ika_control(task, logger, i)
                        
                        completed += 1
                        
                    except Exception as e:
                        has_error = True
                        error_msg = str(e)
                        logger.log_task_failure(i, error_msg)
                        failed += 1
                        continue
                    
                    if i < len(tasks):
                        time.sleep(0.3)
                
                # 执行总结
                logger.write("")
                logger.write("=" * 70)
                logger.write("【执行总结】")
                logger.write("=" * 70)
                logger.write(f"总任务数: {len(tasks)}")
                logger.write(f"成功完成: {completed}")
                logger.write(f"失败任务: {failed}")
                if has_error:
                    logger.write(f"执行状态: ✗ 部分失败 (最后错误: {error_msg})")
                else:
                    logger.write(f"执行状态: ✓ 全部完成")
                logger.write("=" * 70)
                
                self.statusBar().showMessage(f"执行完成！日志: {log_path}")
                
                if has_error:
                    QMessageBox.warning(self, "部分完成", 
                        f"任务执行完成，但有 {failed} 个任务失败。\n\n"
                        f"日志已保存到:\n{log_path}")
                else:
                    QMessageBox.information(self, "完成", 
                        f"所有 {completed} 个任务执行完成！\n\n"
                        f"日志已保存到:\n{log_path}")
                
            except Exception as e:
                import traceback
                logger.log_critical_error(str(e), traceback.format_exc())
                QMessageBox.critical(self, "执行错误", 
                    f"执行过程中出现严重错误:\n{str(e)}\n\n"
                    f"日志已保存到:\n{log_path}")
    
    def _execute_pump_task(self, task, logger, index, total):
        """执行单个泵任务"""
        source = task.params.get('source')
        dest = task.params.get('destination')
        volume = task.params.get('volume', 0)
        
        task_dict = {
            'type': 'transfer',
            'source': source,
            'destination': dest,
            'volume': volume
        }
        
        logger.log_task_start(index, total, task_dict)
        
        if self._pump_controller is None:
            logger.log_system_action("创建泵控制器")
            self._pump_controller = PumpController(
                port=self.pump_editor.get_port(),
                config_dict=self.config_data
            )
            self._pump_controller.set_logger(lambda x: None)
            logger.log_system_action("初始化所有泵")
            self._pump_controller.init_all_pumps()
            init_cmds = self._pump_controller.get_commands_log()
            logger.log_init_commands(init_cmds)
        
        controller = self._pump_controller
        controller.set_logger(lambda x: None)
        
        cmd_start = len(controller.get_commands_log())
        result = controller.transfer(source, dest, volume)
        all_cmds = controller.get_commands_log()
        new_cmds = all_cmds[cmd_start:]
        
        logger.log_transfer_success(index, result, result['transferred'], new_cmds)
    
    def _execute_ika_start(self, task, logger, index):
        """执行IKA启动"""
        port = self.ika_editor.get_port()
        logger.log_ika_header()
        logger.log_ika_command("START_4", port=port)
        
        if self._stir_controller is None:
            self._stir_controller = StirController(port=port)
        self._stir_controller.set_logger(lambda x: None)
        
        if self._stir_controller.start():
            logger.log_generic_success(index, "IKA 搅拌马达已启动")
        else:
            raise Exception("启动失败")
    
    def _execute_ika_stop(self, task, logger, index):
        """执行IKA停止"""
        port = self.ika_editor.get_port()
        logger.log_ika_header()
        logger.log_ika_command("STOP_4", port=port)
        
        if self._stir_controller is None:
            self._stir_controller = StirController(port=port)
        self._stir_controller.set_logger(lambda x: None)
        
        if self._stir_controller.stop():
            logger.log_generic_success(index, "IKA 搅拌马达已停止")
        else:
            raise Exception("停止失败")
    
    def _execute_ika_set_speed(self, task, logger, index):
        """执行IKA设置转速"""
        port = self.ika_editor.get_port()
        speed = task.params.get('speed', 0)
        
        logger.log_ika_header()
        logger.log_ika_command(f"OUT_SP_4 {speed}", speed=speed, port=port)
        
        if self._stir_controller is None:
            self._stir_controller = StirController(port=port)
        self._stir_controller.set_logger(lambda x: None)
        
        if self._stir_controller.set_speed(speed):
            logger.log_generic_success(index, f"转速已设置为 {speed} RPM")
        else:
            raise Exception("设置转速失败,转速必须在 0-1500 RPM 范围内")
    
    def _execute_ika_control(self, task, logger, index):
        """执行IKA设置并启动"""
        port = self.ika_editor.get_port()
        speed = task.params.get('speed', 0)
        
        logger.log_ika_header()
        logger.log_ika_command(f"OUT_SP_4 {speed}", speed=speed, port=port)
        logger.log_ika_command("START_4", port=port)
        
        if self._stir_controller is None:
            self._stir_controller = StirController(port=port)
        self._stir_controller.set_logger(lambda x: None)
        
        if self._stir_controller.control(speed):
            logger.log_generic_success(index, f"转速设置为 {speed} RPM 并启动")
        else:
            raise Exception("设置并启动失败")
    
    # ==================== 文件操作 ====================
    
    def new_file(self):
        """创建新配置"""
        dialog = SetupDialog(self)
        if dialog.exec():
            pump_count = dialog.spin_pumps.value()
            port_count = dialog.spin_ports.value()
            
            self.config_data = {
                "settings": {"pump_count": pump_count, "port_count": port_count},
                "connections": [],
                "liquids": [],
                "gases": [],
                "containers": []
            }
            self._load_config_to_editors(self.config_data)
            
            self.current_file = None
            self.lbl_file.setText("未保存的新配置")
            self.btn_save.setEnabled(True)
            self.btn_save_as.setEnabled(True)
            self.statusBar().showMessage(f"已新建配置: {pump_count} 泵, {port_count} 端口")
    
    def load_from_path(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.config_data = data
            self._load_config_to_editors(data)
            
            self.current_file = filename
            self.lbl_file.setText(f"当前配置: {os.path.basename(filename)}")
            self.btn_save.setEnabled(True)
            self.btn_save_as.setEnabled(True)
            self.statusBar().showMessage(f"已加载: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载文件:\n{str(e)}")
    
    def _load_config_to_editors(self, config_data):
        """加载配置到各个编辑器"""
        # 加载到JSON编辑器（包含Matrix）
        self.editor.load_json(config_data)
        # 加载到泵编辑器（下拉框选项）
        self.pump_editor.load_config(config_data)
    
    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择 JSON 文件", "", "JSON 文件 (*.json);;所有文件 (* *)"
        )
        if filename:
            self.load_from_path(filename)
    
    def _check_init_file(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_dir = os.path.join(project_root, "config")
        target_path = os.path.join(config_dir, "pump_config.json")
        
        if os.path.exists(target_path):
            self.load_from_path(target_path)
        else:
            try:
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                    
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
            except Exception as e:
                self.statusBar().showMessage(f"自动创建失败: {str(e)}")
    
    def _generate_default_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_dir = os.path.join(project_root, "config")
        
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        base_name = "pump_config"
        full_path = os.path.join(config_dir, f"{base_name}.json")
        if not os.path.exists(full_path):
            return full_path
            
        counter = 1
        while True:
            full_path = os.path.join(config_dir, f"{base_name}_{counter}.json")
            if not os.path.exists(full_path):
                return full_path
            counter += 1
    
    def save_file(self):
        if self.current_file:
            self._do_save(self.current_file)
        else:
            new_path = self._generate_default_path()
            if self._do_save(new_path, silent=True):
                self.current_file = new_path
                self.lbl_file.setText(f"当前配置: {os.path.basename(new_path)}")
                QMessageBox.information(self, "已保存", f"配置已保存为:\n{new_path}")
    
    def save_as_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "另存为", "", "JSON 文件 (*.json)"
        )
        if filename:
            if not filename.endswith('.json'):
                filename += '.json'
            
            if self._do_save(filename, silent=True):
                self.current_file = filename
                self.lbl_file.setText(f"当前配置: {os.path.basename(filename)}")
                QMessageBox.information(self, "另存为成功", f"配置已保存到:\n{filename}")
    
    def _do_save(self, filename, silent=False):
        try:
            data = self.editor.to_json()
            self.config_data = data
            # 更新泵编辑器的配置
            self.pump_editor.load_config(data)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.statusBar().showMessage(f"已保存: {filename}")
            
            if not silent:
                QMessageBox.information(self, "成功", f"配置已保存!\n{filename}")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存失败:\n{str(e)}")
            return False
    
    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        if self._pump_controller:
            try:
                self._pump_controller.close()
            except:
                pass
        if self._stir_controller:
            try:
                self._stir_controller.close()
            except:
                pass
        event.accept()
