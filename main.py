from PIL import Image
from pypylon import pylon



import sys
import cv2
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFrame,
                             QVBoxLayout, QHBoxLayout, QTreeWidget, QFileDialog,
                             QTreeWidgetItem, QHeaderView, QLineEdit, QMessageBox, QSplitter, QMainWindow)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QFontMetrics, QPen, QIcon
from PyQt6.QtCore import QTimer, QSize, Qt
import numpy as np

from interface import StartupApp
from mainApp import App


def init_db():
    conn = sqlite3.connect('Fault_detect.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS objects
                  (id INTEGER PRIMARY KEY, 
                  Fault TEXT, 
                  Confidence REAL,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()


def main():
    app = QApplication(sys.argv)
    with open("styles.qss", 'r') as file:
        app.setStyleSheet(file.read())
    start_window = StartupApp(App)
    start_window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

