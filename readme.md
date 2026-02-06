serial_driver.py是阻塞的，禁止在 GUI 线程直接调用！！！！
demo主体分为
0.入口文件 (main.py):
位于项目根目录，负责启动应用程序、设置 Qt 样式和主题，并显示主窗口
1.config
文件夹包含了仪器的硬件配置和其他配置文件
2.gui
负责图形化交互界面和实验设计，包括
(1)主界面编辑系统 (gui/main_window.py)
包含了 MainWindow 类。
这里负责 UI 的搭建（工具栏、表格视图）、用户交互（打开/保存按钮）、布局管理和主题设置。
它从 json_editor.py 导入模型来驱动界面。
(2)模块导出 (gui/__init__.py)
(3)编辑器组
(a)json_editor.py:
包含了 PumpTableModel（数据模型）和 TypeDelegate（下拉框代理）。
这里负责数据的逻辑、读写处理、以及与 PUMP_COUNT 和 type_map 相关的底层逻辑。
(b)pump_editor.py
包含了
(4)对话框
(a)set_dialogs.py
设置泵数和泵控制数，默认为4泵，8通
3.core
负责硬件控制核心



关于泵的逻辑：
对于命名相同的同一类,假如有多个端口，将自动寻找多个端口
跨泵移液已修复