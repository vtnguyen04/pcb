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

import numpy as np
# import vào thư viện để xử lí ảnh phát hiện lỗi tự viết
from Identify_fault import Fault_detect
# thư viện kết nối với camera 
#from pypylon import pylon

# Hàm khởi tạo cơ sở dữ liệu

def init_db():
    conn = sqlite3.connect('Fault_detect.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS images
                        (id INTEGER PRIMARY KEY, 
                        timestamp TEXT,
                        image BLOB,
                        faults_table TEXT)''')
    conn.commit()
    conn.close()

# gọi hàm khởi tạo database
init_db()

class WatermarkLabel(QLabel):
    def __init__(self, parent=None):
        super(WatermarkLabel, self).__init__(parent)

        # biến quản lí xem là cam đã bật hay chưa
        self.camera_off = True
        # set kích thước mặc định của khung hiển thị là 600x500
        self.setFixedSize(650, 600)  

    def paintEvent(self, event):
        super(WatermarkLabel, self).paintEvent(event)
        if self.camera_off:

            # khởi tạo painter để vẽ watermark lên khung hình hiển thị
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # set màu sắc, font chữ, kích thước của chữ hiển thị
            painter.setPen(QColor(10, 10, 10, 128))  
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

class ImageViewer(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.pixmap_item = QGraphicsPixmapItem()
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)  # Smooth scaling
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)  # Enable drag mode
        self.state = 1
    
    def setImage(self, image):
        self.scene.addItem(self.pixmap_item)
        pixmap = QPixmap.fromImage(image)
        self.pixmap_item.setPixmap(pixmap)
        self.setSceneRect(0, 0, pixmap.width(), pixmap.height())  # Set the scene size to match the image

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
    def clear_image(self):
        self.scene.removeItem(self.pixmap_item)

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

    
    def set_bluegradient(self):
        with open(f"theme/styles_blue.qss", "r") as file:
            self.setStyleSheet(file.read())
    def set_light_theme(self):
        with open("theme/styles_light.qss", "r") as file:
            self.setStyleSheet(file.read())
    def set_dark_theme(self):
        with open("theme/styles_dark.qss", "r") as file:
            self.setStyleSheet(file.read())
    def set_green_theme(self):
        with open("theme/styles_green.qss", "r") as file:
            self.setStyleSheet(file.read())
    def set_purple_theme(self):
        with open("theme/styles_purple.qss", "r") as file:
            self.setStyleSheet(file.read())
    def set_pink_theme(self):
        with open("theme/styles_pink.qss", "r") as file:
            self.setStyleSheet(file.read())

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

        theme_menu = self.menuBar.addMenu('Theme')

        # Tạo hành động cho theme sáng
        light_action = QAction('Light Theme', self)
        light_action.triggered.connect(self.set_light_theme)
        theme_menu.addAction(light_action)

        # Tạo hành động cho theme tối
        dark_action = QAction('Dark Theme', self)
        dark_action.triggered.connect(self.set_dark_theme)
        theme_menu.addAction(dark_action)

        blue_gradient = QAction('Blue Theme', self)
        blue_gradient.triggered.connect(self.set_bluegradient)
        theme_menu.addAction(blue_gradient)

        green_action = QAction('Green Theme', self)
        green_action.triggered.connect(self.set_green_theme)
        theme_menu.addAction(green_action)

        purple_action = QAction('purple Theme', self)
        purple_action.triggered.connect(self.set_purple_theme)
        theme_menu.addAction(purple_action)

        pink_action = QAction('pink Theme', self)
        pink_action.triggered.connect(self.set_pink_theme)
        theme_menu.addAction(pink_action)
        # Thiết lập layout chính
        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)
        self.setCentralWidget(container)

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
        self.video_label2 = ImageViewer()
        # gán cho viền ngoài màu tím
        self.video_label2.setStyleSheet("border: 2px solid #7155F2;")
        self.video_label2.setFixedSize(650, 600)  


        # khởi tạo phần hiển thị database
        self.stacked_widget = QStackedWidget()
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.add_to_tree_widget)
        # khởi tạo bảng hiển thị thông tin từ database
        self.data_tree = QTreeWidget(self)
        # bảng có 4 cột
        self.data_tree.setColumnCount(4)
        # gán tên cho từng cột
        self.data_tree.setHeaderLabels(['ID', 'Fault', 'Confidence', 'Coordinate'])
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
        self.return_button = self.create_button('Return', 'SP_ArrowBack', self.reset_ui)
        # khởi tạo nút cho hàng dưới
        self.btn_add = self.create_button('Find\nFault', 'SP_FileDialogInfoView', self.search_by_error)
        self.btn_search = self.create_button('Search\nby Date', 'SP_FileDialogListView', self.search_fault)
        self.btn_delete = self.create_button('Delete\nby Date', 'SP_TrashIcon', self.delete_fault)
        self.Stcapture_button = self.create_button('Start\nCapture', 'SP_MediaPlay', self.toggle_capture)
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
        findFault.setFixedSize(270, 75)
        Flayout = QHBoxLayout(findFault)
        Flayout.addWidget(self.fixed3)
        Flayout.addWidget(self.btn_add)
        
        # kết hợp nút search_by_date với input của nó là (Set date), fixed4
        setDate = QWidget()        
        setDate.setFixedSize(370, 75)
        Slayout = QHBoxLayout(setDate)
        Slayout.addWidget(self.fixed4)
        Slayout.addWidget(self.btn_search)
        Slayout.addWidget(self.btn_delete)

        # kết hợp nút start_capture_button và start_capture_button với input của nó là setdelay, fixed2
        loop = QWidget()        
        loop.setFixedSize(270, 80)
        Llayout = QHBoxLayout(loop)
        Llayout.addWidget(self.fixed2)
        Llayout.addWidget(self.Stcapture_button)
        #Llayout.addWidget(self.stop_capture_button)

        # khởi tạo layout1 và thêm các nút bấm vào layout
        button_layout1 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout1, [
            self.camera_button, self.capture_button, self.load_image_button, 
            self.load_button, self.reset_button, self.return_button, self.stop_button
        ])
        
        # khởi tạo layout2 và thêm các nút bấm vào layout
        button_layout2 = QHBoxLayout()
        self.add_widgets_to_layout(button_layout2, [
            self.fixed1, loop, findFault, setDate
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
        self.data_tree.addTopLevelItem(new_item)
        self.log_tree.scrollToItem(new_item, QAbstractItemView.ScrollHint.PositionAtTop)
        new_item.setSelected(True)
        # Đảm bảo mục mới được đánh dấu (highlight)
        self.log_tree.setCurrentItem(new_item)
    # hàm hiển thị thông tin từ database
    def add_to_tree_widget(self, item):

        self.data_tree.clear()
        image_id, timestamp = item.text().split(' - ')
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        cursor.execute("SELECT image, faults_table FROM images WHERE id = ?", (image_id,))
        image_data, faults_table_name = cursor.fetchone()

        # Hiển thị hình ảnh
        image_array = np.frombuffer(image_data, dtype = np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        height, width, channel = image.shape
        step = channel * width
        qImg = QImage(image.data, width, height, step, QImage.Format.Format_RGB888)
        self.video_label2.setImage(qImg)
        cursor.execute(f"SELECT Fault, Confidence, Coordinate FROM {faults_table_name}")
        rows = cursor.fetchall()
        
        numBreak = 0
        for i, row in enumerate(rows):
            fault_item = QTreeWidgetItem([str(i), row[0], str(row[1]), str(row[2])])
            self.data_tree.addTopLevelItem(fault_item)
            if row[0] == 'break':
                numBreak += 1
        
        total_item = QTreeWidgetItem(["Total:", f"break: {numBreak}" , f"over-et: {len(rows) - numBreak}"])
        self.data_tree.addTopLevelItem(total_item)
        self.data_tree.scrollToItem(total_item, QAbstractItemView.ScrollHint.PositionAtTop)
        total_item.setSelected(True)
        self.data_tree.setCurrentItem(total_item)
        conn.close()

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
        
        self.show_screen = QComboBox()
        self.show_screen.fixed_size=(50, 40)
        self.show_screen.addItems(['1', '2', '3'])
        
        def show_screen():
        # Show only the first screen
            tx = int(self.show_screen.currentIndex())
            idx = [[200, 0], [0, 200], [200, 200]]
            self.video_splitter.setSizes(idx[tx - 1])


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
        self.button_show = QPushButton("Show\nScreen")
        self.button_show.setFixedSize(100, 60)
        
        # Connect buttons to the switch functions
        self.button_show.clicked.connect(show_screen)
        #self.button_show_second.clicked.connect(show_second_screen
        screen = QWidget()        
        screen.setFixedSize(115, 150)
        layout = QVBoxLayout(screen)
        layout.addWidget(self.button_show)
        layout.addWidget(self.show_screen)

        set_widget = QWidget()        
        # Create layout and add widgets
        main_layout = QHBoxLayout(set_widget)
        main_layout.addWidget(self.video_splitter)
        main_layout.addWidget(screen)
        splitter.addWidget(set_widget)

        down_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Data layout
        nlayout = QVBoxLayout()
        label = QLabel("DATABASE INFO")
        # Tạo QListWidget
        # Thêm QLabel và QListWidget vào layout
        self.container_widget = QWidget()
        nlayout = QVBoxLayout()
        nlayout.addWidget(label)
        nlayout.addWidget(self.image_list)
        self.container_widget.setLayout(nlayout)

        self.stacked_widget.addWidget(self.container_widget)
        self.stacked_widget.addWidget(self.data_tree)
        self.container_widget.keyPressEvent = self.switch_to_data_tree
        self.data_tree.keyPressEvent = self.switch_to_image_list
        down_splitter.addWidget(self.stacked_widget)

        # Log layout
        self.log_tree = QTreeWidget()
        self.log_tree.setHeaderLabel("Log Messages")
        log_layout = QHBoxLayout()
        log_layout.addWidget(self.log_tree)
        log_widget = QWidget()
        log_widget.setLayout(log_layout)
        down_splitter.addWidget(log_widget)

        # Set initial sizes for the down splitter
        down_splitter.setSizes([173, 200])

        splitter.addWidget(down_splitter)
        return splitter
    ### kết thúc ###

    def switch_to_data_tree(self, event):
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.stacked_widget.setCurrentWidget(self.data_tree)

    def switch_to_image_list(self, event):
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.stacked_widget.setCurrentWidget(self.container_widget)
    #### Từ đây trở đi là các hàm tính năng cụ thể của các nút bấm #####


    ### các hàm kết nối với các nút bấm để sử lí từng tính năng truy vấn với dữ liệu ###
    # hàm kết nối vói nút search by fault
    def search_fault(self):
        # Get the selected date from the input widget
        date = self.timestamp_input.date().toString("yyyy-MM-dd")
        self.log_message(f"Search date: {date}")

        # Connect to the SQLite database
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()

        # Query to fetch images based on the date
        cursor.execute('''SELECT id, timestamp, faults_table 
                          FROM images 
                          WHERE strftime('%Y-%m-%d', substr(timestamp, 7, 4) || '-' || substr(timestamp, 4, 2) || '-' || substr(timestamp, 1, 2)) = ?''', (date,))
        
        # Fetch all matching rows
        rows = cursor.fetchall()
        self.log_message(f"Number of rows fetched: {len(rows)}")

        # Inform the user about the data loading status
        QMessageBox.information(self, "Success", f"Loading data for {date}")

        # Check if any rows were returned
        if rows:
            self.log_message(f"DETECTED FAULTS ON {date}")

            # Iterate over the fetched rows
            for row in rows:
                image_id = row[0]
                faults_table_name = row[2]

                self.log_message(f"Checking faults for image ID: {image_id}, Faults Table: {faults_table_name}")

                # Query to count faults for break and over-etching in the current image
                cursor.execute(f'''SELECT Fault, COUNT(*) 
                                   FROM {faults_table_name} 
                                   WHERE Fault IN ('break', 'over-etching')
                                   GROUP BY Fault''')
                faults = cursor.fetchall()

                total_breaks = 0
                total_over_etchings = 0

                # Aggregate the counts
                for fault in faults:
                    if fault[0] == 'break':
                        total_breaks += fault[1]
                    elif fault[0] == 'over-etching':
                        total_over_etchings += fault[1]

                # Log the total counts for the current image
                self.log_message(f"Image ID: {image_id} - Total breaks: {total_breaks} - Total over-etchings: {total_over_etchings}")
        else:
            self.log_message(f"No data found for {date}")
    # hàm kết nối vói nút delete by fault
    def delete_fault(self):
        date = self.timestamp_input.date().toString("yyyy-MM-dd")
        self.log_message(f"Selected date for deletion: {date}")
        # Connect to the SQLite database
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        # Delete records from the objects table where the date matches
        cursor.execute('''DELETE FROM images 
                          WHERE strftime('%Y-%m-%d', substr(timestamp, 7, 4) 
                                                     || '-' || 
                                                     substr(timestamp, 4, 2) 
                                                     || '-' || 
                                                     substr(timestamp, 1, 2)) = ?''', (date,))
        
        # Get the count of deleted rows
        deleted_count = cursor.rowcount
        # Commit the transaction
        conn.commit()
        # Log and inform the user about the deletion
        self.log_message(f"Deleted {deleted_count} images from {date}")
        QMessageBox.information(self, "Success", f"Deleted {deleted_count} images from {date}")

    # hàm kết nối với nút Find_fault
    def search_by_error(self):
        error_info = self.error_info_input.currentText()
        # Connect to the SQLite database
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()

        # Query to fetch all images
        cursor.execute("SELECT id, timestamp, faults_table FROM images")
        image_rows = cursor.fetchall()

        # Initialize a dictionary to collect fault counts
        fault_counts = {}

        # Iterate over each image entry
        for image_row in image_rows:
            image_id = image_row[0]
            faults_table_name = image_row[2]

            # Query to count faults from the corresponding faults table that match the error_info
            cursor.execute(f'''SELECT COUNT(*) 
                            FROM {faults_table_name} 
                            WHERE Fault LIKE ?''', ('%' + error_info + '%',))
            count = cursor.fetchone()[0]

            if count > 0:
                fault_counts[image_id] = count

        conn.close()

        # Check if any faults were found
        if fault_counts:
            self.log_message(f"{error_info} Faults were detected".upper())
            for image_id, count in fault_counts.items():
                self.log_message(f"Id: {image_id} - Total Faults: {count}")
        else:
            self.log_message("There are no Faults detected".upper())
    ### kết thúc ###


    ### hàm hiển thị hướng dẫn sử dụng app 
    def show_help(self):
        help_text = (
            "User Guide for PCB Fault Detection App\n"
            "\n"
            """ 1. Turn Camera On/Off:
            - Click the **Turn on camera** button to turn on the camera.
            - Click the **Turn on camera** button again to turn off the camera."""
            "\n"
            """ 2. Capture Image:
            - Click the **Capture** button to capture an image from the camera."""
            "\n"
            """ 3. Load Image:
            - Click the **Load Image** button to load an image from your computer into the application."""
            "\n"
            """ 4. Manage Data:
            - Click the **Load Data** button to load data from the database.
            - Click the **Reset Data** button to reset the database.
            - Click the **Exit** button to exit the application."""
            "\n"
            """ 5. Find and Delete Faults:
            - Use **Set Fault** to select the fault type (Break, Over-etching, Under-etching).
            - Click the **Find Fault** button to detect faults based on the selected fault type.
            - Use **Set date** to select a date.
            - Click the **Search by Date** button to search for faults by date.
            - Click the **Delete by Date** button to delete faults by date."""
            "\n"
            """ 6. Start and Stop Automatic Capture:
            - Use **Set delay** to set the delay time (in seconds).
            - Click the **Start Capture** button to start automatic image capture.
            - Click the **Stop Capture** button to stop automatic image capture."""
            "\n"
            """ 7. Set Confidence Threshold:
            - Use **Confidence score** to set the confidence threshold (1-10)."""
            "\n"
            """ 8. Change Theme:
            - Select **Theme** from the menu to change the application theme (Light Theme, Dark Theme, Blue Gradient Theme, Green Theme, Custom Theme, Custom2 Theme)."""
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
                self.show_screen(image)
            grabResult.Release()

        camera.StopGrabbing()
    ###


    ### hàm tải toàn bộ dữ liệu từ database lên giao diện app ###
    def load_data(self):
        if self.load == False:
            conn = sqlite3.connect('Fault_detect.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp FROM images")
            rows = cursor.fetchall()
            if len(rows) > 0:
                self.load_button.setText('off\ndata')
                self.image_list.clear()
                for row in rows:
                    self.image_list.addItem(f"{row[0]} - {row[1]}")
                conn.commit()
                conn.close()
                self.load = True
                self.log_message(f"Loading data....")
                QMessageBox.information(self, "Success", "The data is being loaded.")
                self.log_message(f"Stop loading")
            else :
                self.log_message(f"There is no data in the database....")
        else: 
            self.load_button.setText('load\ndata')
            self.data_tree.clear()
            self.image_list.clear()
            self.load = False
            self.log_message(f"Show off Data")
            self.video_label2.clear_image()
    ### kết thúc ###


    ### các hàm xử lí ảnh ###
    # hàm bắt đầu thực hiện chụp liên tục sau t giây
    # hàm thay đổi trạng thái
    def toggle_capture(self):
        if self.is_running:
            self.stop_timed_capture()
        else:
            self.start_timed_capture()
    # hàm bắt đầu chụp
    def start_timed_capture(self):
        pixmapi = QStyle.StandardPixmap.SP_MediaStop
        icon = self.style().standardIcon(pixmapi)
        if self.camera_on:
            # lấy icon của app
            self.Stcapture_button.setText("Stop\nCapture")
            self.Stcapture_button.setIcon(icon)
            delay = self.delay_input.value()
            delay = int(delay) * 1000
            self.capture_timer.start(delay)
            self.is_running = True
            QMessageBox.information(self, "Success", "Timed capture started.")
            self.log_message(f"Timed capture started")
        else:
            self.log_message(f"Camera is not on.")
            QMessageBox.warning(self, "Warning", "Camera is not on.")
    # hàm dừng chụp if self.camera_on
    def stop_timed_capture(self):
        pixmapi = QStyle.StandardPixmap.SP_MediaPlay
        icon = self.style().standardIcon(pixmapi)
        if self.is_running:
            self.Stcapture_button.setText("Start\nCapture")
            self.Stcapture_button.setIcon(icon)
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
                self.log_message(f"Loading Image file...".upper())
                QMessageBox.information(self, "Sucess", "The image is being loaded")
                self.execute_detectFault(frame)
            else:
                self.log_message(f"No Image is Loading.".upper())
        else: 
            self.load_image_button.setText('Load\nImage')
            self.log_message(f"Showing off Image.".upper())
            QMessageBox.information(self, "Sucess", "The image is being showed off")
            self.load_image = False
            self.video_label2.clear_image()
    # hàm thực thi quá trình phát hiện lỗi
    def execute_detectFault(self, frame):
        frameHeight = frame.shape[0]
        frameWidth = frame.shape[1]

        inpWidth = self.mywidth if self.mywidth else frameWidth
        inpHeight = self.myheight if self.myheight else frameHeight

        confThreshold = self.confThreshold_input.value() / 10

        # lấy thông tin đã được detect và ảnh đã được vẽ qua module phát hiện lỗi đã code trước đó
        fault_detect, frame, nBreak, nOv = Fault_detect(inpWidth, inpHeight, confThreshold, frame).call()

        # sau khi đã lấy thông tin thì thêm vào database
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.add_to_database(fault_detect, frame)
        self.log_message(f"The image contains a total {nBreak} BREAK errors and {nOv} OVER-ETCHING errors.")
        # chuyển hình ảnh từ BGR sang RGB
        
        # hiển thị hình ảnh lên màn hình 2
        height, width, channel = frame.shape
        step = channel * width
        qImg = QImage(frame.data, width, height, step, QImage.Format.Format_RGB888)
        self.video_label2.setImage(qImg)
    ### kết thúc ###

    ### hiển thị hình ảnh từ cam lên giao diện
    def show_screen(self, image):
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
    
        self.video_label.setPixmap(qImg)
    ### kết thúc ###
 
    ### thêm dữ liệu vào database ###
    def add_to_database(self, fault_detect, image):
        
        # lấy thông tin thời gian thực hiện tại
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        # kết nối với database

        _, buffer = cv2.imencode('.png', image)
        image_blob = buffer.tobytes()

        # Thêm dữ liệu vào cơ sở dữ liệu
        conn = sqlite3.connect('Fault_detect.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO images (timestamp, image, faults_table) 
                            VALUES (?, ?, ?)''', 
                        (timestamp, image_blob, ''))
        image_id = cursor.lastrowid
        faults_table_name = f'faults_{image_id}'
        cursor.execute('''UPDATE images 
                            SET faults_table = ? 
                            WHERE id = ?''', 
                        (faults_table_name, image_id))
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS {faults_table_name}
                            (id INTEGER PRIMARY KEY, 
                            Fault TEXT, 
                            Confidence REAL,
                            Coordinate TEXT)''')
        conn.commit()


        for fault in fault_detect:
            cursor.execute(f"""INSERT INTO {faults_table_name} 
                           (Fault, Confidence, Coordinate) VALUES (?, ?, ?)""", 
                            (fault[0], fault[1], fault[2]))
            #self.add_to_tree_widget(str(last_id), obj[0], obj[1], str(NFault), timestamp)
        conn.commit()

        self.image_list.clear()
        self.data_tree.clear()
        cursor.execute("SELECT id, timestamp FROM images")
        rows = cursor.fetchall()
        for row in rows:
            self.image_list.addItem(f"{row[0]} - {row[1]}")
        conn.close()
        # conn = sqlite3.connect('Fault_detect.db')
        # cursor = conn.cursor()
        # thêm các thông tin đã lấy được vào database
        # duyệt qua tất các các lỗi đã đuọc detect và thêm lần lượt vào database
        # for obj in fault_detect:
        #     cursor.execute("INSERT INTO objects (Fault, Confidence, NFault, timestamp) VALUES (?, ?, ?, ?)", (obj[0], obj[1], int(NFault), timestamp))
        #     last_id = cursor.lastrowid
        #     self.add_to_tree_widget(str(last_id), obj[0], obj[1], str(NFault), timestamp)
        # conn.commit()
        # conn.close()
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


    def reset_ui(self):
    # Dừng các timer nếu đang chạy
        self.timer.stop()
        self.capture_timer.stop()
        
        # Tắt camera nếu đang bật
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            self.camera_on = False
            self.video_label.set_camera_status(True)
        
        # Xóa các hình ảnh hiển thị
        self.video_label.clear()
        self.video_label2.clear_image()
        
        # Đặt lại các giá trị mặc định cho các input
        self.confThreshold_input.setValue(1)
        self.delay_input.setValue(0)
        self.error_info_input.setCurrentIndex(0)
        self.timestamp_input.setDate(QDate.currentDate())
        
        # Xóa danh sách và bảng dữ liệu
        self.image_list.clear()
        self.data_tree.clear()
        
        # Đặt trạng thái các nút về mặc định
        self.camera_button.setText('Turn on\ncamera')
        self.camera_button.setIcon(QIcon('icons/camera.png'))
        self.load = False
        self.is_image_loaded = False
        self.load_image = False
        self.log_tree.clear()
        # Thiết lập lại theme về mặc định (tùy chọn)
        # self.set_light_theme()
        
        # Cập nhật status bar
        self.statusBar.showMessage('UI has been reset to default state.', 5000)


    ### hàm reset toàn bộ dữ liệu đã lưu ###
    def reset_database(self):
        reply = QMessageBox.question(self, 'Confirm Reset', 'Are you sure you want to reset the database? This action cannot be undone.', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = sqlite3.connect('Fault_detect.db')
            cursor = conn.cursor()
            cursor.execute("SELECT faults_table FROM images")
            fault_tables = cursor.fetchall()

            for table in fault_tables:
                table_name = table[0]
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            cursor.execute("DROP TABLE IF EXISTS images")
            conn.commit()
            conn.close()
            init_db()
            self.image_list.clear()
            self.data_tree.clear()
            self.video_label2.clear_image()
            QMessageBox.information(self, "Reset", "Database has been reset successfully.")
    ### kết thúc ###



# def delete_image_and_faults(image_id):
#     # Kết nối tới cơ sở dữ liệu
#     conn = sqlite3.connect('Fault_detect.db')
#     cursor = conn.cursor()

#     # Lấy tên bảng lỗi liên quan đến ảnh
#     cursor.execute("SELECT faults_table FROM images WHERE id = ?", (image_id,))
#     result = cursor.fetchone()

#     if result:
#         faults_table_name = result[0]

#         # Xóa bảng lỗi liên quan
#         cursor.execute(f"DROP TABLE IF EXISTS {faults_table_name}")

#         # Xóa ảnh từ bảng images
#         cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))

#         # Xác nhận thay đổi
#         conn.commit()
#         print(f"Đã xóa ảnh và các lỗi liên quan cho ID: {image_id}")
#     else:
#         print(f"Không tìm thấy ảnh với ID: {image_id}")

#     # Đóng kết nối tới cơ sở dữ liệu
#     conn.close()

# # Ví dụ sử dụng hàm xóa
# image_id = int(input("Nhập ID của ảnh cần xóa: "))
# delete_image_and_faults(image_id)
