import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置暗色主题
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#34495e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#2c3e50"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#34495e"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ecf0f1"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#e74c3c"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#3498db"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ecf0f1"))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
