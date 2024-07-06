from interface import *
from mainApp import *
import sys
import os
os.environ["QT_FONT_DPI"] = "96" # Cố định vấn đề về DPI cao và tỷ lệ phóng trên 100%

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    with open("theme/styles_light.qss", 'r') as file:
        app.setStyleSheet(file.read())
    start_window = StartupApp(App)
    start_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

