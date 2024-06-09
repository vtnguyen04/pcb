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
            "Major - Robotics and Artifficial Intelligence",
            "Project Title - PCB FAULT DETECTION",
            "Instructor - Ts. Nguyễn Văn Thái",
            "Võ Thành Nguyễn - Student ID: 22134008",
            "Phạm Văn Thịnh - Student ID: 22134014", 
            "Phạm Ngọc Phúc - Student ID: 22134010"
        ]
        self.background_images = [
            "images/robot_hand_background.png",  # Hình nền cho Major
            "images/testresult.png",  # Hình nền cho Project Title
            "images/thay.png",         # Hình nền cho Dr. Nguyễn Văn Thái
            "images/member1.png",
            "images/member2.png",
            "images/member3.png"   
        ]
        self.App = App()
        self.initUI()
        self.startScrolling()

    def initUI(self):
        self.setWindowTitle("Welcome to PCB FAULT DETECTION App")
        self.setGeometry(100, 0, 1000, 1000)
        self.setStyleSheet("background-color: #e0f7fa;")

        self.layout = QVBoxLayout()

        self.setLayout(self.layout)
            
        logos_layout = QHBoxLayout()
        school_logo_label = QLabel()
        school_logo_pixmap = QPixmap("images/logo.png")
        school_logo_label.setPixmap(school_logo_pixmap.scaled(500, 150, Qt.AspectRatioMode.KeepAspectRatio))
        department_logo_label = QLabel()
        department_logo_pixmap = QPixmap("images/khoa.png")
        department_logo_label.setPixmap(department_logo_pixmap.scaled(450, 150, Qt.AspectRatioMode.KeepAspectRatio))
        logos_layout.addWidget(school_logo_label, alignment=Qt.AlignmentFlag.AlignLeft)
        logos_layout.addWidget(department_logo_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout.addLayout(logos_layout)
        
        # Text Label
        self.text_label = QLabel("", self)
        self.text_label.setStyleSheet("color: #4D6086; font-size: 23px;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.text_label)
        
        self.background_label = QLabel(self)
        self.background_label.setScaledContents(True)
        self.background_label.setFixedSize(1000, 700)

        self.layout.addWidget(self.background_label)
	    
        
        # Start Button
        self.startButton = QPushButton("Start App", self)
        self.startButton.setStyleSheet("QPushButton { background-color: #0063B1; color: white; padding: 10px; }")
        self.startButton.clicked.connect(self.launchMainApp)
        self.layout.addWidget(self.startButton, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def startScrolling(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateText)
        self.timer.start(2000)  # Change text every 2000 ms (2 seconds)

    def updateText(self):
        if self.current_text_index < len(self.text_lines):
            self.text_label.setText(self.text_lines[self.current_text_index])
            pixmap = QPixmap(self.background_images[self.current_text_index])	
            self.background_label.setPixmap(pixmap)
            self.current_text_index += 1
        else:
            self.text_label.setText("")  # Optionally clear/reset text after the last line
            self.background_label.setPixmap(QPixmap())  # Clear the background image
            self.current_text_index = 0  # Reset index to loop the text

    def launchMainApp(self):
        self.main_app = self.App  # Assuming App is the main application class you provided
        self.main_app.show()
        self.hide()

