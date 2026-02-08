demo主体分为
0.入口文件 (main.py):
位于项目根目录，负责启动应用程序、设置 Qt 样式和主题，并显示主窗口
1.config
文件夹包含了仪器的硬件配置文件
2.gui
负责图形化交互界面和实验设计，包括
(1)主界面系统
包含了 MainWindow 类。
这里负责 UI 的搭建（工具栏、表格视图）、用户交互（打开/保存按钮）、布局管理和主题设置。
(1.5)任务排序系统
提交任务的排序模块，包含task_queue以及task_queque_widget
(2)模块导出 (gui/__init__.py)
(3)编辑器组
(a)json_editor.py:
负责编辑配置文件
(b)pump_editor.py和pump_workflow.py
包含了控制泵移液的功能
(c)ika-editor.py
包含了下发ika搅拌的功能
(4)对话框
(a)set_dialogs.py
设置泵数和泵控制数，默认为4泵，8通
3.core
负责硬件控制核心
(1)hardware内包含：
硬件的接口、虚拟接口
(a)
(b)
(c)
以及虚拟/真实接口切换组件
(2)
4.logs

关于泵的逻辑：
对于命名相同的同一类,假如有多个端口，将自动寻找多个端口
跨泵移液已修复

当你需要添加新硬件（例如：Heater）并支持虚拟/真实切换时，请遵循以下步骤：
1.编写驱动：
编写真实驱动 core/hardware/heater.py。
编写模拟驱动 core/hardware/heater_test.py
2.注册到管理器：
在 driver_manager.py 中添加方法
def get_heater_controller_class(self):
    if self.use_virtual:
        from core.hardware.heater_test import HeaterController
        return HeaterController
    else:
        from core.hardware.heater import HeaterController
        return HeaterController
3.前端调用：
在前端代码中不要直接 import 驱动，而是这样写：
from core.hardware.driver_manager import DriverManager
HeaterClass = DriverManager.instance().get_heater_controller_class()
self.heater = HeaterClass(port="COMx")
self.heater.set_temperature(100)r