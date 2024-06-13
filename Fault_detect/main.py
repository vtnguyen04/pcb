from PyQt6.QtWidgets import QApplication

from interface import StartupApp
from mainApp import App
import sys

def main():
    app = QApplication(sys.argv)
    with open("styles.qss", 'r') as file:
        app.setStyleSheet(file.read())
    start_window = StartupApp(App)
    start_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

