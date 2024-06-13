import cv2
import sqlite3
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QFrame,
                             QVBoxLayout, QHBoxLayout, QTreeWidget, QFileDialog,
                             QTreeWidgetItem, QHeaderView, QLineEdit, QMessageBox, QSplitter, QMainWindow, QMenu, QMenuBar, QStatusBar)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon, QImage, QAction
from PyQt6.QtCore import QTimer, QSize, Qt
from PIL import Image
#from pypylon import pylon
 
model = 'best.onnx'
filename_classes = 'detection_classes.txt'

net = cv2.dnn.readNet(model)
net.setPreferableBackend(0)
net.setPreferableTarget(0)
outNames = net.getUnconnectedOutLayersNames()

mean = [0, 0, 0]

# Hàm khởi tạo cơ sở dữ liệu
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

class WatermarkLabel(QLabel):
    def __init__(self, parent=None):
        super(WatermarkLabel, self).__init__(parent)
        self.camera_off = True
        self.setFixedSize(600, 500)  

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


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PCB Fault Detection App')
        self.left, self.top, self.width, self.height = 50, 50, 1600, 1000
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.camera_on = False
        self.cap = None
        self.is_running = False
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self.capture_image)
        self.load = False
        self.is_image_loaded = False
        self.classes = None
        if filename_classes:
            with open(filename_classes, 'rt') as f:
                self.classes = f.read().rstrip('\n').split('\n')

        self.mywidth, self.myheight = 640, 640
        self.scale = 0.00392
        self.load_image = False
        
        self.initUI()
        
    def initUI(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.menuBar = self.menuBar()
        fileMenu = self.menuBar.addMenu('File')
        editMenu = self.menuBar.addMenu('Edit')
        viewMenu = self.menuBar.addMenu('View')
        helpMenu = self.menuBar.addMenu('Help')

        exitAction = QAction(QIcon('icons/exit.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)
        
        helpAction = QAction('User Guide', self)
        helpAction.triggered.connect(self.show_help)
        helpMenu.addAction(helpAction)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.video_label = WatermarkLabel()
        self.video_label.setStyleSheet("border: 2px solid #7160F2;")
        self.video_label2 = QLabel(self)
        self.video_label2.setStyleSheet("border: 2px solid #7160F2;")
        self.video_label2.setFixedSize(600, 500)  

        self.data_tree = QTreeWidget(self)
        self.data_tree.setColumnCount(4)
        self.data_tree.setHeaderLabels(['ID', 'Fault', 'Confidence', 'Times'])
        self.data_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.capture_button = self.create_button('Capture', 'icons/capture.png', self.capture_and_save)
        self.load_button = self.create_button('Load Data', 'icons/load.png', self.load_data)
        self.stop_button = self.create_button('Stop \nApplication', 'icons/stop.png', self.stop_application)
        self.start_capture_button = self.create_button('Start Timed \nCapture', 'icons/start.png', self.start_timed_capture)
        self.stop_capture_button = self.create_button('Stop \nCapture', 'icons/stop2.png', self.stop_timed_capture)
        self.camera_button = self.create_button('Camera on', 'icons/camera.png', self.toggle_camera)
        self.reset_button = self.create_button('Reset \nDatabase', 'icons/reset.png', self.reset_database)

        self.delay_input = QLineEdit(self)
        self.delay_input.setPlaceholderText("Set delay in seconds")
        self.delay_input.setFixedSize(150, 30)

        self.confThreshold_input = QLineEdit(self)
        self.confThreshold_input.setPlaceholderText("Set confThreshold")
        self.confThreshold_input.setFixedSize(150, 30)

        self.nmsThreshold_input = QLineEdit(self)
        self.nmsThreshold_input.setPlaceholderText("Set nmsThreshold")
        self.nmsThreshold_input.setFixedSize(150, 30)

        button_layout1 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout1, [
            self.camera_button, self.capture_button, self.load_button, 
            self.reset_button, self.stop_button
        ])

        button_layout2 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout2, [
            self.confThreshold_input, self.nmsThreshold_input, self.delay_input, self.start_capture_button, 
            self.stop_capture_button
        ])

        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout1)
        main_layout.addLayout(button_layout2)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.create_left_panel())
        splitter.addWidget(self.create_right_panel())

        splitter.setSizes([250, 900])
        main_layout.addWidget(splitter)

        self.main_widget.setLayout(main_layout)

    def create_button(self, text, icon, handler):
        size = (124, 52)
        button = QPushButton(text)
        button.setIcon(QIcon(icon))
        button.setIconSize(QSize(32, 32))
        button.setFixedSize(*size)
        button.clicked.connect(handler)
        return button
    
    def add_widgets_to_layout(self, layout, widgets):
        for widget in widgets:
            layout.addWidget(widget)

    def create_left_panel(self):
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
        return left_frame

    def create_right_panel(self):
        splitter = QSplitter(Qt.Orientation.Vertical)

        video_splitter = QSplitter(Qt.Orientation.Horizontal)
        video_layout = QHBoxLayout()
        video_layout.addWidget(self.video_label)
        video_widget = QWidget()
        video_widget.setLayout(video_layout)
        video_splitter.addWidget(video_widget)

        video_layout = QHBoxLayout()
        video_layout.addWidget(self.video_label2)
        video_widget = QWidget()
        video_widget.setLayout(video_layout)
        video_splitter.addWidget(video_widget)
        splitter.addWidget(video_splitter)

        down_splitter = QSplitter(Qt.Orientation.Horizontal)
        data_layout = QHBoxLayout()
        data_layout.addWidget(self.data_tree)
        data_widget = QWidget()
        data_widget.setLayout(data_layout)
        down_splitter.addWidget(data_widget)

        log_layout = QHBoxLayout()
        self.log_tree = QTreeWidget()
        self.log_tree.setHeaderLabel("Log Messages")
        log_layout.addWidget(self.log_tree)
        log_widget = QWidget()
        log_widget.setLayout(log_layout)
        down_splitter.addWidget(log_widget)

        splitter.addWidget(down_splitter)
        
        return splitter
    
    def populate_device_tree(self):
        root = QTreeWidgetItem(self.device_tree, ["Devices"])
        QTreeWidgetItem(root, ["Basler camera"])

    def populate_category_tree(self):
        root = QTreeWidgetItem(self.category_tree, ["Category"])
        QTreeWidgetItem(root, ["break Fault"])
        QTreeWidgetItem(root, ["over-etching Fault"])
    
    def show_help(self):
        help_text = (
            "User Guide for PCB Fault Detection App\n"
            "\n"
            "* Buttons:\n"
            "- Capture: Capture an image from the camera.\n"
            "- Load Data: Load fault data from the database.\n"
            "- Stop Application: Stop the application.\n"
            "- Start Timed Capture: Start capturing images at the set time interval.\n"
            "- Stop Capture: Stop timed image capturing.\n"
            "- Camera on: Turn the camera on or off.\n"
            "- Reset Database: Reset the database, deleting all saved entries.\n"
            "\n"
            "*Input Fields:\n"
            "- Set delay in seconds: Set the image capture interval (in seconds).\n"
            "- Set confThreshold: Set the confidence threshold for fault detection.\n"
            "- Set nmsThreshold: Set the Non-Maximum Suppression threshold.\n"
            "\n"
            "*Other Components:\n"
            "- Devices: Display available devices.\n"
            "- Category: Display types of detectable faults.\n"
            "- Log Messages: Display application log messages.\n"
            "- Video Feed: Display video from the camera.\n"
            "- Detection Data: Display fault detection data.\n"
        )
        QMessageBox.information(self, "User Guide", help_text, QMessageBox.StandardButton.Ok)

    
    def identify_fault(self, frame, outs,
                       background_label_id=-1, 
                       postprocessing='yolov8', confThreshold=0.5, nmsThreshold=0.4):
        
        

        frameHeight, frameWidth = frame.shape[:2]
        fault_detect = []

        def drawPred(classId, conf, left, top, right, bottom):
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0))
            label = f'{conf:.2f}'
            if self.classes:
                fault_detect.append((self.classes[classId], label))
                label = f'{self.classes[classId]}: {label}'
                

            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            top = max(top, labelSize[1])
            cv2.rectangle(frame, (left, top - labelSize[1]), (left + labelSize[0], top + baseLine), (255, 255, 255), cv2.FILLED)
            cv2.putText(frame, label, (left, top), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))
            self.log_message(f"fault detect -> {label}")

        layerNames = net.getLayerNames()
        lastLayerId = net.getLayerId(layerNames[-1])
        lastLayer = net.getLayer(lastLayerId)

        classIds, confidences, boxes = [], [], []

        scale_w, scale_h = 1, 1
        if postprocessing == 'yolov8':
            scale_w, scale_h = frameWidth / self.mywidth, frameHeight / self.myheight

        for out in outs:
            if postprocessing == 'yolov8':
                out = out[0].transpose(1, 0)

            for detection in out:
                scores = detection[4:]
                if background_label_id >= 0:
                    scores = np.delete(scores, background_label_id)

                classId = np.argmax(scores)
                confidence = scores[classId]
                
                if confidence > confThreshold:
                    center_x = int(detection[0] * scale_w)
                    center_y = int(detection[1] * scale_h)
                    width = int(detection[2] * scale_w)
                    height = int(detection[3] * scale_h)
                    left = int(center_x - width / 2)
                    top = int(center_y - height / 2)
                    classIds.append(classId)
                    confidences.append(float(confidence))
                    boxes.append([left, top, width, height])

        if len(outNames) > 1 or (lastLayer.type == 'Region' or postprocessing == 'yolov8') and 0 != cv2.dnn.DNN_BACKEND_OPENCV:
            indices = []
            classIds = np.array(classIds)
            boxes = np.array(boxes)
            confidences = np.array(confidences)
            unique_classes = set(classIds)
            for cl in unique_classes:
                class_indices = np.where(classIds == cl)[0]
                conf = confidences[class_indices]
                box  = boxes[class_indices].tolist()
                nms_indices = cv2.dnn.NMSBoxes(box, conf, confThreshold, nmsThreshold)
                indices.extend(class_indices[nms_indices])
        else:
            indices = np.arange(0, len(classIds))
        for i in indices:
            left, top, width, height = boxes[i]
            drawPred(classIds[i], confidences[i], left, top, left + width, top + height)

        return fault_detect
    
    def log_message(self, message):
        QTreeWidgetItem(self.log_tree, [message])              

    def add_to_tree_widget(self, ID, Fault, Confidence, timestamp):
        item = QTreeWidgetItem([ID, Fault, Confidence, timestamp])
        self.data_tree.addTopLevelItem(item)

    def toggle_camera(self):
        
        if self.camera_on:
            self.cap.Close()
            self.timer.stop()
            self.camera_on = False
            self.camera_button.setText('Camera on')
            self.video_label.clear() 
         
        else:
            self.cap = self.connect_camera_by_ip()
            self.timer.start(30)
            self.camera_on = True
            self.camera_button.setText('Camera off')
            
            
    def connect_camera_by_ip(self):
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if len(devices) == 0:
            print("Không tìm thấy camera nào.")
            sys.exit(-1)

        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        camera.Open()
        return camera

    def update_frame(self):
        camera = self.cap 
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
        
        if camera.IsGrabbing():
            grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grabResult.GrabSucceeded():
                image = converter.Convert(grabResult)
                image = image.GetArray()
                height, width, channel = image.shape
                step = channel * width
                qImg = QImage(image.data, width, height, step, QImage.Format.Format_RGB888)

                pixmap = QPixmap.fromImage(qImg)

                scaled_pixmap = pixmap.scaled(self.video_label.size(), 
                                            Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                self.video_label.setPixmap(scaled_pixmap)
            grabResult.Release()

        camera.StopGrabbing()
        
   
    def capture_and_save(self):
        if self.camera_on:
            
            camera = self.cap 
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            frame = None
            if camera.IsGrabbing():
                grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grabResult.GrabSucceeded():
                    frame = converter.Convert(grabResult)
                    frame = frame.GetArray()                    
                grabResult.Release()
            camera.StopGrabbing()
            if frame is not None:
                frameHeight = frame.shape[0]
                frameWidth = frame.shape[1]

                inpWidth = self.mywidth if self.mywidth else frameWidth
                inpHeight = self.myheight if self.myheight else frameHeight
                blob = cv2.dnn.blobFromImage(frame, scalefactor = self.scale, size=(inpWidth, inpHeight), mean=mean, swapRB=True, crop=False)

                net.setInput(blob)
                if net.getLayer(0).outputNameToIndex('im_info') != -1:  # Faster-RCNN or R-FCN
                    frame = cv2.resize(frame, (inpWidth, inpHeight))
                    net.setInput(np.array([[inpHeight, inpWidth, 1.6]], dtype=np.float32), 'im_info')
                
                outs = net.forward(outNames)
                confThreshold = self.confThreshold_input.text()
                try:
                    confThreshold = float(confThreshold)
                except ValueError:
                    return []

                nmsThreshold = self.nmsThreshold_input.text()
                try:
                    nmsThreshold = float(nmsThreshold)
                except ValueError:
                    return []
                fault_detect = self.identify_fault(frame, outs, confThreshold  = confThreshold, nmsThreshold = nmsThreshold)

                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                conn = sqlite3.connect('Fault_detect.db')
                cursor = conn.cursor()
                for obj in fault_detect:
                    cursor.execute("INSERT INTO objects (Fault, Confidence, timestamp) VALUES (?, ?, ?)", (obj[0], obj[1], timestamp))
                    last_id = cursor.lastrowid
                    self.add_to_tree_widget(str(last_id), obj[0], obj[1], timestamp)
                conn.commit()
                conn.close()
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                cv2.imwrite("anh2.png", image_rgb)
                h, w, ch = image_rgb.shape
                bytes_per_line = ch * w

                convert_to_Qt_format = QImage(image_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(convert_to_Qt_format)

                scaled_pixmap = pixmap.scaled(self.video_label.size(), 
                                            Qt.AspectRatioMode.KeepAspectRatio, 
                                            Qt.TransformationMode.SmoothTransformation)
                self.video_label2.setPixmap(scaled_pixmap)
        
        else:
            QMessageBox.warning(self, "Warning", "Camera is not on.")

    def load_data(self):
        if self.load == False:
            self.load_button.setText('off data')
            conn = sqlite3.connect('Fault_detect.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM objects")
            rows = cursor.fetchall()
            
            conn.close()

            self.data_tree.clear()
            for row in rows:
                QTreeWidgetItem(self.data_tree, [str(row[0]), row[1], str(row[2]), row[3]])
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
            conn = sqlite3.connect('Fault_detect.db')
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS objects")
            conn.commit()
            conn.close()
            init_db()
            QMessageBox.information(self, "Success", "Database reset successfully.")
            self.data_tree.clear()
