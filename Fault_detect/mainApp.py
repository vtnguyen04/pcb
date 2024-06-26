# khai báo thư viện xử lí ảnh 
import cv2
# khai báo thư viện để kết nối và quản lí database
import sqlite3
# thư viện đọc thời gian hiện tại trực tiếp
from datetime import datetime

# Pyqt6 là thư viện để viết app 
# PyQt6 là thư viện code app trên python với nhiều tính năng hay ho và giao diện đẹp
from PyQt6.QtWidgets import * # import toàn bộ tool của thư viện
from PyQt6.QtGui import *
from PyQt6.QtCore import *

# import vào thư viện để xử lí ảnh phát hiện lỗi tự viết
from Identify_fault import Fault_detect
# thư viện kết nối với camera 
#from pypylon import pylon

# Hàm khởi tạo cơ sở dữ liệu
def init_db():
    # nếu mà database chưa có thì mình sẽ khởi tạo database có tên là Fault_detect
    conn = sqlite3.connect('Fault_detect.db')
    cursor = conn.cursor()
    # thêm vào các thông tin dữ liệu cần được lưu
    cursor.execute('''CREATE TABLE IF NOT EXISTS objects
                  (id INTEGER PRIMARY KEY, 
                  Fault TEXT, 
                  Confidence REAL,
                  timestamp TEXT)''')
    # luư khở tạo và đóng
    conn.commit()
    conn.close()

# gọi hàm khởi tạo database
init_db()

# vẽ watermark lên màn hình chính
class WatermarkLabel(QLabel):
    def __init__(self, parent=None):
        super(WatermarkLabel, self).__init__(parent)

        # biến quản lí xem là cam đã bật hay chưa
        self.camera_off = True
        # set kích thước mặc định của khung hiển thị là 600x500
        self.setFixedSize(600, 500)  

    def paintEvent(self, event):
        super(WatermarkLabel, self).paintEvent(event)
        if self.camera_off:

            # khởi tạo painter để vẽ watermark lên khung hình hiển thị
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # set màu sắc, font chữ, kích thước của chữ hiển thị
            painter.setPen(QColor(255, 255, 255, 128))  
            font = QFont('Roboto', 24, QFont.Weight.Bold)
            painter.setFont(font)

            # khơi tạo hình chữ nhật
            rect = self.rect()
            painter.translate(rect.width() / 2, rect.height() / 2) # dịch chuyển đến giữa màn hình
            painter.rotate(-45)  # quay 45 độ

            # tiến hành vẽ lên khung
            painter.drawText(
                # tính toán vị trí để vẽ
                int(-rect.width() / 2), 
                int(-rect.height() / 4),  
                int(rect.width()), 
                int(rect.height() / 2), 
                Qt.AlignmentFlag.AlignCenter, # vẽ vào trung tâm
                # chũ cần vẽ lên khung
                "BACKER"
            )
            # dừng vẽ
            painter.end()
    # hàm quản lí trạng thái của cam, nếu mà cam tắt thì mới vẽ watermark
    def set_camera_status(self, status):
        self.camera_off = status
        self.update()  

class App(QMainWindow):

    # hàm khởi tạo các giá trị mặc định ban đầu 
    def __init__(self):
        super().__init__()
        # đặt tên cho app
        self.setWindowTitle('PCB Fault Detection App')
        # set vị trí mở app
        self.left, self.top, self.width, self.height = 0, 0, 1920, 1080 
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        # khởi tạo timer để quán lí hiển thị
        self.timer = QTimer(self)
        # hàm self.update_frame sẽ quản lí timer
        self.timer.timeout.connect(self.update_frame)
        self.camera_on = False
        self.cap = None
        self.is_running = False
        self.capture_timer = QTimer(self)
        # timer quản lí thời gian chụp
        self.capture_timer.timeout.connect(self.capture_image)
        self.load = False
        self.is_image_loaded = False
        # trạng thái ảnh có đang được load hay k
        self.load_image = False
        # kích thước hình ảnh
        self.mywidth, self.myheight = 640, 640
        self.initUI()
    ### kết thúc ###

    ### hàm chính thiết kế giao diện UI ###
    def initUI(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # tạo thanh menu
        self.menuBar = self.menuBar()
        fileMenu = self.menuBar.addMenu('File')
        editMenu = self.menuBar.addMenu('Edit')
        viewMenu = self.menuBar.addMenu('View')
        helpMenu = self.menuBar.addMenu('Help')

        # tạo chức năng cho fileMenu
        exitAction = QAction(QIcon('icons/stop.png'), 'Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        fileMenu.addAction(exitAction)
        
        # tạo chức năng cho help
        helpAction = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion), 
                             'User Guide', self)
        # kết nối chức năng của nút help này dến hàm show_help
        helpAction.triggered.connect(self.show_help)
        helpMenu.addAction(helpAction)


        # khởi tạo layout chính và cho nằm giữa khung
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # khởi tạo màn hình 1 
        self.video_label = WatermarkLabel()
        # gán cho viền ngoài màu tím
        self.video_label.setStyleSheet("border: 2px solid #7155F2;")
        # khởi tạo màn hình 2
        self.video_label2 = QLabel(self)
        # gán cho viền ngoài màu tím
        self.video_label2.setStyleSheet("border: 2px solid #7155F2;")
        self.video_label2.setFixedSize(600, 500)  

        # khởi tạo bảng hiển thị thông tin từ database
        self.data_tree = QTreeWidget(self)
        # bảng có 4 cột
        self.data_tree.setColumnCount(4)
        # gán tên cho từng cột
        self.data_tree.setHeaderLabels(['ID', 'Fault', 'Confidence', 'Times'])
        # stretch bảng cho chia đều
        self.data_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # khởi tạo nút bấm và taọ chức năng cho từng nút bấm cụ thê
        # khởi tạo nút cho hàng trên
        self.capture_button = self.create_button('Capture', 'icons/capture.png', self.capture_image)
        self.load_button = self.create_button('Load\nData', 'SP_BrowserReload', self.load_data)
        self.stop_button = self.create_button('Exit', 'SP_TabCloseButton', self.stop_application)
        self.camera_button = self.create_button('Turn on\ncamera', 'icons/camera.png', self.toggle_camera)
        self.reset_button = self.create_button('Reset\nData', 'SP_DialogDiscardButton', self.reset_database)
        self.load_image_button = self.create_button('Load\nImage', 'SP_DirLinkIcon', self.load_Image)

        # khởi tạo nút cho hàng dưới
        self.btn_add = self.create_button('Find\nFault', 'SP_FileDialogInfoView', self.search_by_error)
        self.btn_search = self.create_button('Search\nby Date', 'SP_FileDialogListView', self.search_fault)
        self.btn_delete = self.create_button('Delete\nby Date', 'SP_TrashIcon', self.delete_fault)
        self.start_capture_button = self.create_button('Start\nCapture', 'SP_MediaPlay', self.start_timed_capture)
        self.stop_capture_button = self.create_button('Stop\nCapture', 'SP_MediaStop', self.stop_timed_capture)

        # kết nối input với các nút bấm
        self.confThreshold_input = QSpinBox()
        # khởi tạo nơi để lấy giá trị confidence score với giá trị trong khoảng [1, 10], tiền tố là $0 và bước nhảy là 1
        self.fixed1 = self.create_fixed_widget(165, 55, "Confidence score:", self.confThreshold_input,
                                        fixed_size=(60, 40), setMinimum=1, setMaximum=10, setPrefix="$0.", setSingleStep=1)
        # khởi tạo nơi để lấy giá trị delay với giá trị trong khoảng [0, 100], hậu tố là s và bước nhảy là 3
        self.delay_input = QSpinBox()
        self.fixed2 = self.create_fixed_widget(165, 65, "Set delay:", self.delay_input,
                                        fixed_size=(60, 40), setMinimum=0, setMaximum=100, setSuffix="s", setSingleStep=3)

        # khởi tạo nơi để lấy giá trị lỗi 
        self.error_info_input = QComboBox()
        self.fixed3 = self.create_fixed_widget(165, 60, "Set Fault:", self.error_info_input,
                                        fixed_size=(100, 40), add_items=['Break', 'Over-etching', 'Under-etching'])

        self.timestamp_input = QDateEdit(calendarPopup=True)
        self.fixed4 = self.create_fixed_widget(165, 60, "Set date:", self.timestamp_input,
                                        fixed_size=(100, 40), setDate=QDate.currentDate())

        # kết hợp nút Find_fault với input của nó fixed3 (Set Fault)
        findFault = QWidget()        
        findFault.setFixedSize(300, 75)
        Flayout = QHBoxLayout(findFault)
        Flayout.addWidget(self.fixed3)
        Flayout.addWidget(self.btn_add)
        
        # kết hợp nút search_by_date với input của nó là (Set date), fixed4
        setDate = QWidget()        
        setDate.setFixedSize(400, 75)
        Slayout = QHBoxLayout(setDate)
        Slayout.addWidget(self.fixed4)
        Slayout.addWidget(self.btn_search)
        Slayout.addWidget(self.btn_delete)

        # kết hợp nút start_capture_button và start_capture_button với input của nó là setdelay, fixed2
        loop = QWidget()        
        loop.setFixedSize(400, 80)
        Llayout = QHBoxLayout(loop)
        Llayout.addWidget(self.fixed2)
        Llayout.addWidget(self.start_capture_button)
        Llayout.addWidget(self.stop_capture_button)

        # khởi tạo layout1 và thêm các nút bấm vào layout
        button_layout1 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout1, [
            self.camera_button, self.capture_button, self.load_image_button, 
            self.load_button, self.reset_button, self.stop_button
        ])

        
        # khởi tạo layout2 và thêm các nút bấm vào layout
        button_layout2 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout2, [
            self.fixed1 , findFault, setDate, loop
        ])

        # thêm vào từng layout bên trái và bên phải tương ứng
        # lưu ý là trong 2 layout này vẫn còn nhiều layout con nên sẽ viết hàm để tạo riêng cho dễ hình dung
        layout3 = QSplitter(Qt.Orientation.Horizontal)
        self.add_widgets_to_layout(layout3, [
            self.create_left_panel(), self.create_right_panel()
        ])
        # phân chia diện tích của splitter
        layout3.setSizes([200, 900])

        # thêm 3 layout thành phần vào layout chính
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout1)
        main_layout.addLayout(button_layout2)
        main_layout.addWidget(layout3)
        # hiển thị layout chính
        self.main_widget.setLayout(main_layout)
    ### kết thúc ###

    ### hàm khởi tạo các nút bấm ###
    # hàm tạo các nút bấm đơn lẻ
    def create_button(self, text, ic, handler):
        # khởi tạo kích thước của nút bấm
        size = (90, 55)
        # khởi tạo nút bấm và tên nút bấm
        button = QPushButton(text)

        # Kiểm tra nếu thuộc tính tồn tại trong QStyle.StandardPixmap
        if hasattr(QStyle.StandardPixmap, ic):
            # lấy icon của app
            pixmapi = getattr(QStyle.StandardPixmap, ic)
            icon = self.style().standardIcon(pixmapi)
        else:
            # tool lấy icon của mình
            icon = QIcon(ic)
            button.setIconSize(QSize(17, 17))
        # gán icon cho nút
        button.setIcon(icon)
        # gán kích thước cho nút
        button.setFixedSize(*size)
        button.clicked.connect(handler)
        return button
    #hàm tạo các nút bấm và input có liên kết với nhau
    def create_fixed_widget(self, width, height, label_text, control, 
                            fixed_size=None, add_items=None, **kwargs):
    # Tạo widget chứa và thiết lập kích thước cố định
        fixed_widget = QWidget()
        fixed_widget.setFixedSize(width, height)
        
        # Tạo layout và thêm vào widget
        layout = QHBoxLayout(fixed_widget)
        
        # Tạo và cấu hình nhãn
        label = QLabel(label_text)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        # Xử lý các phương thức đặc biệt
        if fixed_size:
            control.setFixedSize(*fixed_size)
        if add_items:
            control.addItems(add_items)
        
        # Cấu hình các thuộc tính khác
        for key, value in kwargs.items():
            getattr(control, key)(value) if callable(getattr(control, key, None)) else setattr(control, key, value)
        
        # Thêm control vào layout
        layout.addWidget(control)
        
        return fixed_widget
    ### kết thúc ###


    ### hàm thêm các layout vào giao diện ###
    def add_widgets_to_layout(self, layout, widgets):
        for widget in widgets:
            layout.addWidget(widget)
    ### kết thúc ###


    ### các hàm hiển thị thông tin lên giao diện ###
    # hàm hiển thị log của appp
    def log_message(self, message):
        new_item = QTreeWidgetItem(self.log_tree, [message])   
        self.log_tree.scrollToItem(new_item)   
    # hàm hiển thị thông tin từ database
    def add_to_tree_widget(self, ID, Fault, Confidence, timestamp):
        item = QTreeWidgetItem([ID, Fault, Confidence, timestamp])
        self.data_tree.addTopLevelItem(item)
        self.data_tree.scrollToItem(item) 
    ### kết thúc ###


    ### hàm tạo các panel ###
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

        ### hàm thêm tính năng vào left_panel ###
    # wiget trên
    def populate_device_tree(self):
        root = QTreeWidgetItem(self.device_tree, ["Devices"])
        QTreeWidgetItem(root, ["Basler camera"])
    # wiget dưới
    def populate_category_tree(self):
        root = QTreeWidgetItem(self.category_tree, ["Category"])
        QTreeWidgetItem(root, ["break Fault"])
        QTreeWidgetItem(root, ["over-etching Fault"])
    ### kết thúc ###
    def create_right_panel(self):

        def show_first_screen():
        # Show only the first screen
            self.video_splitter.setSizes([200, 0])
        
        def show_second_screen():
            # Show only the second screen
            self.video_splitter.setSizes([0, 200])

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.video_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Initial sizes for the video splitter
        self.video_splitter.setSizes([200, 200])
        
        # Create layouts for the video labels
        video_layout1 = QHBoxLayout()
        video_layout1.addWidget(self.video_label)
        video_widget1 = QWidget()
        video_widget1.setLayout(video_layout1)
        
        video_layout2 = QHBoxLayout()
        video_layout2.addWidget(self.video_label2)
        video_widget2 = QWidget()
        video_widget2.setLayout(video_layout2)

        # Add widgets to the horizontal splitter
        self.video_splitter.addWidget(video_widget1)
        self.video_splitter.addWidget(video_widget2)
        
        # Create buttons to switch views
        self.button_show_first = QPushButton("Show First\n Screen")
        self.button_show_first.setFixedSize(115, 60)
        self.button_show_second = QPushButton("Show Second\nScreen")
        self.button_show_second.setFixedSize(115, 60)
        
        # Connect buttons to the switch functions
        self.button_show_first.clicked.connect(show_first_screen)
        self.button_show_second.clicked.connect(show_second_screen)
        
        # Create layout for the buttons
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.button_show_first)
        button_layout.addWidget(self.button_show_second)

        set_widget = QWidget()        
        # Create layout and add widgets
        main_layout = QHBoxLayout(set_widget)
        main_layout.addWidget(self.video_splitter)
        main_layout.addLayout(button_layout)
        splitter.addWidget(set_widget)

        down_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Data layout
        data_layout = QHBoxLayout()
        data_layout.addWidget(self.data_tree)
        data_widget = QWidget()
        data_widget.setLayout(data_layout)
        down_splitter.addWidget(data_widget)

        # Log layout
        self.log_tree = QTreeWidget()
        self.log_tree.setHeaderLabel("Log Messages")
        log_layout = QHBoxLayout()
        log_layout.addWidget(self.log_tree)
        log_widget = QWidget()
        log_widget.setLayout(log_layout)
        down_splitter.addWidget(log_widget)

        # Set initial sizes for the down splitter
        down_splitter.setSizes([175, 200])

        splitter.addWidget(down_splitter)
    
        return splitter
    ### kết thúc ###


    #### Từ đây trở đi là các hàm tính năng cụ thể của các nút bấm #####


    ### các hàm kết nối với các nút bấm để sử lí từng tính năng truy vấn với dữ liệu ###
    # hàm kết nối vói nút search by fault
    def search_fault(self):
        date = self.timestamp_input.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        # Chỉ lấy phần ngày của timestamp để so sánh
        cursor.execute('SELECT * FROM objects WHERE strftime("%Y-%m-%d", timestamp) = ?', (date,))

        rows = cursor.fetchall()
        if len(rows):
            conn.close()
            self.log_message(f"Detected Faults in {date}".upper())
            for row in rows:
                self.log_message(f" Id : {str(row[0])}  -  Fault : {str(row[1])}  -  Confidence : {row[2]}")
        else :
            self.log_message(f"Has not found any data")
    # hàm kết nối vói nút delete by fault
    def delete_fault(self):
        date = self.timestamp_input.date().toString("yyyy-MM-dd")
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        # Chỉ lấy phần ngày của timestamp để so sánh
        cursor.execute('DELETE FROM objects WHERE strftime("%Y-%m-%d", timestamp) = ?', (date,))
        deleted_count = cursor.rowcount 
        conn.commit()
        conn.close()
        self.log_message(f"Deleted {deleted_count} logs from {date}")
    # hàm kết nối với nút Find_fault
    def search_by_error(self):
        error_info = self.error_info_input.currentText()
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM objects WHERE Fault LIKE ?", ('%'+error_info+'%'+'%',))
        rows = cursor.fetchall()
        conn.close()
        if len(rows):
            self.log_message(f"{error_info} Faults was detected".upper())
            for row in rows:
                self.log_message(f" Id : {str(row[0])}  -  Confidence : {str(row[2])}  -  Date : {row[3]}")
        else :
            self.log_message(f"There are no Faults was detected".upper())
    ### kết thúc ###


    ### hàm hiển thị hướng dẫn sử dụng app 
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
    ### kết thúc ###


    ### các hàm kết nối với cam và hiển thị lên video_layout chính ###
    #hàm đóng tắt camera
    def toggle_camera(self):
        
        if self.camera_on:
            self.cap.Close()
            self.timer.stop()
            self.camera_on = False
            self.camera_button.setText('Turn on\ncamera')
            self.log_message(f"Camera is on now")
            self.video_label.clear() 
         
        else:
            self.cap = self.connect_camera_by_ip()
            self.timer.start(30)
            self.camera_on = True
            self.camera_button.setText('Turn off\ncamera')
            self.log_message(f"Camera is off now")
    #hàm thực hiện kết nối camera         
    def connect_camera_by_ip(self):
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if len(devices) == 0:
            self.log_message(f"Can not find any camera")
            sys.exit(-1)

        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        camera.Open()
        return camera
    #hàm hiển thị khung hình lên giao diện
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
                self.show_image(image, self.video_label)
            grabResult.Release()

        camera.StopGrabbing()
    ###


    ### hàm tải toàn bộ dữ liệu từ database lên giao diện app ###
    def load_data(self):
        if self.load == False:
            
            conn = sqlite3.connect('Fault_detect.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM objects")
            rows = cursor.fetchall()

            if len(rows) > 0:
                self.load_button.setText('off data')
                self.data_tree.clear()
                for row in rows:
                    self.add_to_tree_widget(str(row[0]), row[1], str(row[2]), row[3])
                conn.commit()
                conn.close()
                self.load = True
                self.log_message(f"Data loading...")
            else :
                self.log_message(f"There is no data in the database....")
        else: 
            self.load_button.setText('load data')
            self.data_tree.clear()
            self.load = False
            self.log_message(f"Show off Data")
    ### kết thúc ###


    ### các hàm xử lí ảnh ###
    # hàm bắt đầu thực hiện chụp liên tục sau t giây
    def start_timed_capture(self):
        delay = self.delay_input.value()
        delay = int(delay) * 1000
        self.capture_timer.start(delay)
        self.is_running = True
        QMessageBox.information(self, "Success", "Timed capture started.")
        self.log_message(f"Timed capture started")
    # hàm dừng chụp
    def stop_timed_capture(self):
        if self.is_running:
            self.capture_timer.stop()
            self.is_running = False
            QMessageBox.information(self, "Success", "Timed capture stopped.")
            self.log_message(f"Success, Timed capture stopped.")
        else:
            QMessageBox.warning(self, "Warning", "Timed capture is not running.")
            self.log_message(f"Warning, Timed capture is not running.")
    # hàm chụp đơn lẻ và lấy ảnh từ camera sau đó đưa qua hàm execute_detectFault để thực thi phát hiện lỗi
    def capture_image(self):
        # kiểm tra xem cam có đang được bật hay không
        if self.camera_on:
            # nếu đang bật thì lấy khung hình hiện tại 
            camera = self.cap 
            # bắt đầu chụp lấy ảnh từng màn hình
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            # khởi tạo ảnh đã được chụp ban đầu là 
            frame = None
            if camera.IsGrabbing():
                grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grabResult.GrabSucceeded():
                    frame = converter.Convert(grabResult)
                    # chuyển khung hình này qua kiểu 
                    frame = frame.GetArray()                    
                grabResult.Release()
            camera.StopGrabbing()

            # nếu là có ảnh thì sẽ bắt đầu thực thi phát hiện lỗi
            if frame is not None:
                self.execute_detectFault(frame) 
                # hiển thị lên thanh log quá trình chụp thành công
                self.log_message(f"Image has Captured")
        else:
            QMessageBox.warning(self, "Warning", "Camera is not on.")
    # hàm tải ảnh trực tiếp từ thư mục
    def load_Image(self):
        if self.load_image == False:
            self.fileName, _ = QFileDialog.getOpenFileName(
                self, 
                "Select an image", 
                "pcb/", 
                "Image Files (*.png *.jpg *.jpeg *.bmp)"
            )
            if self.fileName:
                self.load_image = True
                self.load_image_button.setText('Show off\nImage')
                self.log_message(f"Loading image...".upper())
                self.is_image_loaded = True
                frame = cv2.imread(self.fileName)
                if frame is None:
                    QMessageBox.warning(self, "Image Load Error", "The image file could not be loaded.")
                    self.log_message(f"Image Load Error, The image file could not be loaded.".upper())
                    return
                self.log_message(f"Image file is loading...".upper())
                self.execute_detectFault(frame)
            else:
                self.log_message(f"No Image is Loading.".upper())
        else: 
            self.load_image_button.setText('Load\nImage')
            self.log_message(f"Image is showing off.".upper())
            self.load_image = False
            self.video_label2.clear() 
            self.video_label2.setFixedSize(600, 500)         
    # hàm thực thi quá trình phát hiện lỗi
    def execute_detectFault(self, frame):
        frameHeight = frame.shape[0]
        frameWidth = frame.shape[1]

        inpWidth = self.mywidth if self.mywidth else frameWidth
        inpHeight = self.myheight if self.myheight else frameHeight

        confThreshold = self.confThreshold_input.value() / 10

        # lấy thông tin đã được detect và ảnh đã được vẽ qua module phát hiện lỗi đã code trước đó
        fault_detect, frame = Fault_detect(inpWidth, inpHeight, confThreshold, frame).call()

        # sau khi đã lấy thông tin thì thêm vào database
        self.add_to_database(fault_detect)

        # chuyển hình ảnh từ BGR sang RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # hiển thị hình ảnh lên màn hình 2
        self.show_image(frame, self.video_label2)
    ### kết thúc ###


    ### hiển thị hình ảnh từ cam lên giao diện
    def show_image(self, image, video_label):
        # lấy kích thước của hình ảnh
        height, width, channel = image.shape
        step = channel * width
        # sài tool của PyQt6 để vẽ lên màn hình
        qImg = QImage(image.data, width, height, step, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(qImg)

        # scale lại hình ảnh cho khớp với màn hình
        scaled_pixmap = pixmap.scaled(self.video_label.size(), 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
        # hiển thị ảnh lên màn hình
        video_label.setPixmap(scaled_pixmap)
    ### kết thúc ###

    ### thêm dữ liệu vào database ###
    def add_to_database(self, fault_detect):
        
        # lấy thông tin thời gian thực hiện tại
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        # kết nối với database
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        # thêm các thông tin đã lấy được vào database
        # duyệt qua tất các các lỗi đã đuọc detect và thêm lần lượt vào database
        for obj in fault_detect:
            cursor.execute("INSERT INTO objects (Fault, Confidence, timestamp) VALUES (?, ?, ?)", (obj[0], obj[1], timestamp))
            last_id = cursor.lastrowid
            self.add_to_tree_widget(str(last_id), obj[0], obj[1], timestamp)
        conn.commit()
        conn.close()
    ### kết thúc ###


    ### hàm dừng ứng dụng ###
    def stop_application(self):
        if self.camera_on:
            self.timer.stop()
            if self.cap:
                self.cap.release()
        self.capture_timer.stop()
        self.close()
    ### kết thúc ###


    ### hàm reset toàn bộ dữ liệu đã lưu ###
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
            self.log_message(f"Success, Database reset successfully.")
            self.data_tree.clear()
    ### kết thúc ###
