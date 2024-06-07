import sys
import cv2
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFrame,
                             QVBoxLayout, QHBoxLayout, QTreeWidget, QFileDialog,
                             QTreeWidgetItem, QHeaderView, QLineEdit, QMessageBox, QSplitter)
from PyQt6.QtGui import QImage, QPixmap, QIcon, QPainter, QColor, QFont
from PyQt6.QtCore import QTimer, QSize, Qt


class StartupApp(QWidget):
    def __init__(self, App):
        super().__init__()
        self.current_text_index = 0
        self.text_lines = [
            "Department: Faculty of Mechanical Engineering.",
            "Major: ROBOTICS AND ARTIFICIAL INTELLIGENCE",
            "Project Title: PCB FAULT DETECTION",
            "Instructor: Dr. Nguyễn Văn Thái",
            "Students: \nVõ Thành Nguyên, Student ID: 22134008\nPhạm Văn Thịnh, Student ID: 22134002\nPhạm Ngọc Phúc, Student ID: 22134004"
        ]
        self.App = App()
        self.initUI()
        self.startScrolling()

    def initUI(self):
        self.setWindowTitle("Welcome to PCB FAULT DETECTION App")
        self.setGeometry(100, 100, 700, 700)
        self.setStyleSheet("background-color: #34495E;")

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Background Image
        self.background_label = QLabel(self)
        pixmap_background = QPixmap("icons/robot_hand_background.png")
        self.background_label.setPixmap(pixmap_background)
        self.background_label.setScaledContents(True)
        self.background_label.resize(700, 700)
        self.layout.addWidget(self.background_label)
        
        self.logo_label = QLabel(self)
        pixmap_logo = QPixmap("icons/images.png")
        self.logo_label.setPixmap(pixmap_logo)
        self.logo_label.setScaledContents(True)
        self.logo_label.resize(200, 200)  # Adjust size as needed
        self.logo_label.move(30, 30)
	
	
        # Text Label
        self.text_label = QLabel("", self)
        self.text_label.setStyleSheet("color: white; font-size: 16px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.text_label)

        # Start Button
        self.startButton = QPushButton("Start App", self)
        self.startButton.setStyleSheet("QPushButton { background-color: #0063B1; color: white; padding: 10px; }")
        self.startButton.clicked.connect(self.launchMainApp)
        self.layout.addWidget(self.startButton, alignment=Qt.AlignmentFlag.AlignCenter)

    def launchMainApp(self):
        self.main_app = self.App  # Assuming App is the main application class you provided
        self.main_app.show()
        self.hide()
    def startScrolling(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateText)
        self.timer.start(2000)  # Change text every 2000 ms (2 seconds)

    def updateText(self):
        if self.current_text_index < len(self.text_lines):
            self.text_label.setText(self.text_lines[self.current_text_index])
            self.current_text_index += 1
        else:
            self.text_label.setText("")  # Optionally clear/reset text after the last line
            self.current_text_index = 0  # Reset index to loop the text

