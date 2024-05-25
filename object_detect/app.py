import sys
import cv2
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFrame,
                             QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QLineEdit, QMessageBox, QSplitter)
                             

from PyQt6.QtGui import QImage, QPixmap, QIcon, QPainter, QColor, QFont
from PyQt6.QtCore import QTimer, QSize, Qt
from ultralytics import YOLO

# Hàm khởi tạo cơ sở dữ liệu
def init_db():
    conn = sqlite3.connect('object_recognition.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS objects
                      (id INTEGER PRIMARY KEY, Fault TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()


class WatermarkLabel(QLabel):
    def __init__(self, parent=None):
        super(WatermarkLabel, self).__init__(parent)
        self.camera_off = True
        self.setFixedSize(640, 400)  

    def paintEvent(self, event):
        super(WatermarkLabel, self).paintEvent(event)
        if self.camera_off:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(QColor(255, 255, 255, 128))  
            font = QFont('Roboto', 24, QFont.Weight.Bold)
            painter.setFont(font)

            rect = self.rect()
            painter.translate(rect.width() / 2, rect.height() / 2)
            painter.rotate(-45)  

            painter.drawText(
                int(-rect.width() / 2), 
                int(-rect.height() / 4),  
                int(rect.width()), 
                int(rect.height() / 2), 
                Qt.AlignmentFlag.AlignCenter, 
                "BACKER"
            )
            painter.end()
    def set_camera_status(self, status):
        self.camera_off = status
        self.update()  


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'PCB FAULT DETECTION App'
        self.left = 100
        self.top = 100
        self.width = 1280
        self.height = 720
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.camera_on = False
        self.cap = None
        self.is_running = False
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_image)
        self.load = False
        self.initUI()

    def identify_object(self, image):
        model = YOLO('yolov8l.pt')
        img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        app_instance.log_message("Image preprocessed.")

        results = model(img)
        app_instance.log_message("Model inference done.")

        detected_objects = set()
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls)
                detected_objects.add(model.names[class_id])

        app_instance.log_message(f"Detected objects: {detected_objects}")
        return list(detected_objects)

    def log_message(self, message):
        # Add a new item to the log tree widget
        QTreeWidgetItem(self.log_tree, [message])


    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        #set video         
        self.video_label = WatermarkLabel()
        self.video_label.setStyleSheet("border: 2px solid #7160F2;")

        self.data_tree = QTreeWidget(self)
        self.data_tree.setColumnCount(3)
        self.data_tree.setHeaderLabels(['ID', 'Fault', 'Times'])
        self.data_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        button_size = (124, 52)

        self.capture_button = QPushButton('Capture', self)
        self.capture_button.setIcon(QIcon('icons/capture.png'))
        self.capture_button.setIconSize(QSize(32, 32))
        self.capture_button.setFixedSize(*button_size)
        self.capture_button.clicked.connect(self.capture_and_save)

        self.load_button = QPushButton('Load Data', self)
        self.load_button.setIcon(QIcon('icons/load.png'))
        self.load_button.setIconSize(QSize(32, 32))
        self.load_button.setFixedSize(*button_size)
        self.load_button.clicked.connect(self.load_data)

        self.stop_button = QPushButton('Stop \nApplication', self)
        self.stop_button.setIcon(QIcon('icons/stop.png'))
        self.stop_button.setIconSize(QSize(32, 32))
        self.stop_button.setFixedSize(*button_size)
        self.stop_button.clicked.connect(self.stop_application)

        self.delay_input = QLineEdit(self)
        self.delay_input.setPlaceholderText("Set delay in seconds")
        self.delay_input.setFixedSize(200, 30)

        self.start_capture_button = QPushButton('Start Timed \nCapture', self)
        self.start_capture_button.setIcon(QIcon('icons/start.png'))
        self.start_capture_button.setIconSize(QSize(32, 32))
        self.start_capture_button.setFixedSize(*button_size)
        self.start_capture_button.clicked.connect(self.start_timed_capture)

        self.stop_capture_button = QPushButton('Stop \nCapture', self)
        self.stop_capture_button.setIcon(QIcon('icons/stop2.png'))
        self.stop_capture_button.setIconSize(QSize(32, 32))
        self.stop_capture_button.setFixedSize(*button_size)
        self.stop_capture_button.clicked.connect(self.stop_timed_capture)

        self.camera_button = QPushButton('Camera on', self)
        self.camera_button.setIcon(QIcon('icons/camera.png'))
        self.camera_button.setIconSize(QSize(32, 32))
        self.camera_button.setFixedSize(*button_size)
        self.camera_button.clicked.connect(self.toggle_camera)

        self.reset_button = QPushButton('Reset \nDatabase', self)
        self.reset_button.setIcon(QIcon('icons/reset.png'))
        self.reset_button.setIconSize(QSize(32, 32))
        self.reset_button.setFixedSize(*button_size)
        self.reset_button.clicked.connect(self.reset_database)

        button_layout1 = QHBoxLayout()
        button_layout1.addWidget(self.camera_button)
        button_layout1.addWidget(self.capture_button)
        button_layout1.addWidget(self.load_button)
        button_layout1.addWidget(self.reset_button)
        button_layout1.addWidget(self.stop_button)

        button_layout2 = QHBoxLayout()
        button_layout2.addWidget(self.delay_input)
        button_layout2.addWidget(self.start_capture_button)
        button_layout2.addWidget(self.stop_capture_button)

        
        main_layout = QVBoxLayout()
        
        main_layout.addLayout(button_layout1)
        main_layout.addLayout(button_layout2)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Devices and User Define panel
        left_frame = QFrame()
        left_layout = QVBoxLayout()

        self.device_tree = QTreeWidget()
        self.device_tree.setHeaderLabel("Devices")
        self.populate_device_tree()
        left_layout.addWidget(self.device_tree)

        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabel("Category")
        self.populate_category_tree()
        left_layout.addWidget(self.category_tree)

        left_frame.setLayout(left_layout)
        splitter.addWidget(left_frame)

        splitter2 = QSplitter(Qt.Orientation.Vertical)

        splitter3 = QSplitter(Qt.Orientation.Horizontal)

        up_layout = QHBoxLayout()
        up_layout.addWidget(self.video_label)
        up_w = QWidget()
        up_w.setLayout(up_layout)
        splitter3.addWidget(up_w)
        log_layout = QHBoxLayout()
        self.log_tree = QTreeWidget()
        self.log_tree.setHeaderLabel("Log Messages")
        log_layout.addWidget(self.log_tree)
        log_widget = QWidget()
        log_widget.setLayout(log_layout)
        splitter3.addWidget(log_widget)
        splitter2.addWidget(splitter3)
        down_layout = QHBoxLayout()
        down_layout.addWidget(self.data_tree)
        
        down_widget = QWidget()

        down_widget.setLayout(down_layout)
        splitter2.addWidget(down_widget)

        splitter.addWidget(splitter2)

        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter)

        
        self.setLayout(main_layout)
    
    def populate_device_tree(self):
        root = QTreeWidgetItem(self.device_tree, ["Integrated Camera"])
        usb = QTreeWidgetItem(self.device_tree, ["USB"])
        QTreeWidgetItem(root, [""])
        QTreeWidgetItem(usb, ["Basler Camera"])

    def populate_category_tree(self):
        Size_constraint = QTreeWidgetItem(self.category_tree, ["Size constraint"])
        Ignored_error = QTreeWidgetItem(self.category_tree, ["Ignored error"])

    def add_to_tree_widget(self, ID, Fault, timestamp):
        item = QTreeWidgetItem([ID, Fault, timestamp])
        self.data_tree.addTopLevelItem(item)

    def toggle_camera(self):
        if self.camera_on:
            self.cap.release()
            self.timer.stop()
            self.camera_on = False
            self.camera_button.setText('Camera on')
            self.video_label.clear() 
            self.video_label.set_camera_status(True)
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.critical(self, "Camera Error", "Could not open camera.")
            self.timer.start(30)
            self.camera_on = True
            self.camera_button.setText('Camera off')
            self.video_label.set_camera_status(False)
            


    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = image.shape
            step = channel * width
            qImg = QImage(image.data, width, height, step, QImage.Format.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qImg))
        else:
            print("Failed to capture image")

    def capture_and_save(self):
        if self.camera_on:
            ret, frame = self.cap.read()
            if ret:
                detected_objects = self.identify_object(frame)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                conn = sqlite3.connect('object_recognition.db')
                cursor = conn.cursor()
                for obj in detected_objects:
                    cursor.execute("INSERT INTO objects (Fault, timestamp) VALUES (?, ?)", (obj, timestamp))
                    last_id = cursor.lastrowid
                    self.add_to_tree_widget(str(last_id), obj, timestamp)
                conn.commit()
                conn.close()
            else:
                QMessageBox.warning(self, "Warning", "Failed to capture image.")
        else:
            QMessageBox.warning(self, "Warning", "Camera is not on.")

    def load_data(self):
        if self.load == False:
            self.load_button.setText('off data')
            conn = sqlite3.connect('object_recognition.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM objects")
            rows = cursor.fetchall()
            conn.close()

            self.data_tree.clear()
            for row in rows:
                QTreeWidgetItem(self.data_tree, [str(row[0]), row[1], row[2]])
            self.load = True
        else: 
            self.load_button.setText('load data')
            self.data_tree.clear()
            self.load = False


    def start_timed_capture(self):
        delay = self.delay_input.text()
        if delay.isdigit():
            delay = int(delay) * 1000
            self.capture_timer.start(delay)
            self.is_running = True
            QMessageBox.information(self, "Success", "Timed capture started.")
        else:
            QMessageBox.warning(self, "Warning", "Invalid delay input.")

    def stop_timed_capture(self):
        if self.is_running:
            self.capture_timer.stop()
            self.is_running = False
            QMessageBox.information(self, "Success", "Timed capture stopped.")
        else:
            QMessageBox.warning(self, "Warning", "Timed capture is not running.")

    def capture_image(self):
        self.capture_and_save()

    def stop_application(self):
        if self.camera_on:
            self.timer.stop()
            if self.cap:
                self.cap.release()
        self.capture_timer.stop()
        self.close()

    def reset_database(self):
        reply = QMessageBox.question(self, 'Reset Database',
                                     "Are you sure you want to reset the database?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect('object_recognition.db')
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS objects")
            conn.commit()
            conn.close()
            init_db()
            QMessageBox.information(self, "Success", "Database reset successfully.")
            self.data_tree.clear()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    with open('styles.qss', 'r') as file:
        app.setStyleSheet(file.read())
    app_instance = App()	
    app_instance.show()
    sys.exit(app.exec())


# %%
