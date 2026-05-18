from typing import Type, Optional, Any

class DriverManager:
    """
    硬件驱动管理器 (单例模式)
    统一管理虚拟/真实硬件模式切换，以及驱动类的获取。
    """
    _instance = None
    
    def __init__(self):
        # 默认为虚拟模式
        self.use_virtual = True
    
    @classmethod
    def instance(cls) -> 'DriverManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def set_virtual_mode(self, enabled: bool):
        """设置是否使用虚拟模式"""
        self.use_virtual = enabled
        print(f"[DriverManager] Mode switched to: {'Virtual' if enabled else 'Real'}")
        
    def is_virtual_mode(self) -> bool:
        return self.use_virtual

    # === 泵控制器 (Pump) ===
    
    def get_pump_controller_class(self) -> Type:
        """获取当前模式下的泵控制器类"""
        if self.use_virtual:
            from .virtual_mode.serial_driver_test import PumpController
            return PumpController
        else:
            try:
                from .real_mode.serial_driver import PumpController
                return PumpController
            except ImportError:
                print("Warning: Real Pump driver not found, falling back to test driver.")
                from .virtual_mode.serial_driver_test import PumpController
                return PumpController

    # === IKA 搅拌器 (Stir) ===
    
    def get_stir_controller_class(self) -> Type:
        """获取当前模式下的搅拌控制器类"""
        if self.use_virtual:
            from .virtual_mode.ikaset_test import StirController
            return StirController
        else:
            try:
                from .real_mode.ikaset import StirController
                return StirController
            except ImportError:
                print("Warning: Real IKA driver not found, falling back to test driver.")
                from .virtual_mode.ikaset_test import StirController
                return StirController

    # === 冷却浴 (Cooling Bath) ===
    
    def get_cooling_bath_controller_class(self) -> Type:
        """获取当前模式下的冷却浴控制器类"""
        if self.use_virtual:
            from .virtual_mode.coolingbath_test import CoolingBathController
            return CoolingBathController
        else:
            try:
                from .real_mode.coolingbath import CoolingBathController
                return CoolingBathController
            except ImportError:
                print("Warning: Real CoolingBath driver not found, falling back to test driver.")
                from .virtual_mode.coolingbath_test import CoolingBathController
                return CoolingBathController

    # === Arduino 步进电机 (Stepper) ===

    def get_stepper_controller_class(self) -> Type:
        """获取当前模式下的步进电机控制器类"""
        if self.use_virtual:
            from .virtual_mode.stepper_test import StepperController
            return StepperController
        else:
            try:
                from .real_mode.stepper import StepperController
                return StepperController
            except ImportError:
                print("Warning: Real Stepper driver not found, falling back to test driver.")
                from .virtual_mode.stepper_test import StepperController
                return StepperController

    # === Extraction Stepper (Dual) ===

    def get_extraction_stepper_controller_class(self) -> Type:
        """获取当前模式下的双步进电机控制器类（单板单口）"""
        if self.use_virtual:
            from .virtual_mode.extraction_steepper import ExtractionStepperController
            return ExtractionStepperController
        else:
            try:
                from .real_mode.extraction_steepper import ExtractionStepperController
                return ExtractionStepperController
            except ImportError:
                print("Warning: Real Extraction Stepper driver not found, falling back to test driver.")
                from .virtual_mode.extraction_steepper import ExtractionStepperController
                return ExtractionStepperController

    # === 未来可在此处扩展其他硬件 ===
    # def get_heater_controller_class(self): ...
