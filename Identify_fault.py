# import thư viện xử lí ảnh 
import cv2
# import vào thư viện xử lí số 
import numpy as np
# file lưu tên các classes cần detect
filename_classes = 'detection_classes.txt'
# tên model để xử lí 
model = 'best.onnx'
# giá trị mean scales
mean = [0, 0, 0]
   
# khái báo tên đối tượng (1 đối tượng sẽ có nhiều phương thức)
class Fault_detect:
    # hàm khai báo các thông tin của đối tượng
    def __init__(self, inpWidth, inpHeight, confThreshold, frame) :
        
        self.scale = 0.00392
        # khai báo thông tin cụ thể của đối tượng cần được lưu
        self.confThreshold = confThreshold
        self.frame = frame
        self.mywidth, self.myheight = 640, 640 # kích thuớc đầu vào của mạng yolov8

        # lưu lại các label (classes) vào đối tượng
        # self.classes = ['break', 'over-etching']
        self.classes = None
        if filename_classes:
            with open(filename_classes, 'rt') as f:
                self.classes = f.read().rstrip('\n').split('\n')
        
        # gọi lại module xử lí mạng sâu của cv2
        self.net = cv2.dnn.readNet(model)

        # tiền xử lí để cv2 có thể đọc được 
        self.net.setPreferableBackend(0)
        self.net.setPreferableTarget(0)
        self.outNames = self.net.getUnconnectedOutLayersNames()
        blob = cv2.dnn.blobFromImage(self.frame, scalefactor = self.scale, size=(inpWidth, inpHeight)
                                     , mean=mean, swapRB=True, crop=False)
        # set đầu vào cho model
        self.net.setInput(blob)
        if self.net.getLayer(0).outputNameToIndex('im_info') != -1:  
            self.frame = cv2.resize(self.frame, (inpWidth, inpHeight))
            self.net.setInput(np.array([[inpHeight, inpWidth, 1.6]], dtype=np.float32), 'im_info')
    
    # hàm thực hiện phát hiện lỗi trả về thông tin lỗi và ảnh sau khi đã xủ lí
    def identify_fault(self, outs, confThreshold):
        """
            self.frame: Khung hình đầu vào.
            outs: Đầu ra từ mô hình.
            background_label_id: ID của lớp nền (nếu có).
            postprocessing: Phương pháp hậu xử lý (ở đây là 'yolov8').
            confThreshold: Ngưỡng xác suất để chấp nhận một phát hiện.
            nmsThreshold: Ngưỡng Non-Maximum Suppression (NMS) để loại bỏ các hộp bao không cần thiết.
        """
        nmsThreshold = 0.5 # ngưỡng xóa boudingbox
        background_label_id = -1
        # Lấy chiều cao và chiều rộng của khung hình.
        frameHeight, frameWidth = self.frame.shape[:2]
        postprocessing='yolov8'
        # list để lưu lại các lỗi phát hiện được trên ảnh ban đầu rỗng
        fault_detect = []

        # hàm vẽ bounding-box lên những vị trí có lỗi được phát hiện
        def drawPred(classId, conf, left, top, right, bottom):
            # Vẽ một hình chữ nhật xung quanh đối tượng được phát hiện với màu xanh lá cây.
            cv2.rectangle(self.frame, (left, top), (right, bottom), (0, 255, 0))
            # Tạo nhãn cho đối tượng dựa trên độ tin cậy (confidence).
            label = f'{conf:.2f}'
            # model trả ra giá trị 0, 1 nên cần phải chuyển qua class cụ thể
            # Kiểm tra xem danh sách lớp có tồn tại hay không.
            if self.classes:
                # Thêm đối tượng phát hiện vào danh sách fault_detect.
                fault_detect.append((self.classes[classId], label))
                # Thêm tên lớp vào nhãn.
                label = f'{self.classes[classId]}: {label}'
            # lấy kích thước của nhãn để vẽ.
            labelSize, baseLine = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            # Điều chỉnh vị trí của nhãn để không bị tràn ra ngoài khung hình.
            top = max(top, labelSize[1])
            # Vẽ một hình chữ nhật màu trắng làm nền cho nhãn.
            cv2.rectangle(self.frame, (left, top - labelSize[1]), (left + labelSize[0], top + baseLine), (255, 255, 255), cv2.FILLED)
            # Vẽ nhãn lên khung hình.
            cv2.putText(self.frame, label, (left, top), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0))

        # lấy layer cuối cùng để detect
        layerNames = self.net.getLayerNames()
        lastLayerId = self.net.getLayerId(layerNames[-1])
        lastLayer = self.net.getLayer(lastLayerId)

        classIds, confidences, boxes = [], [], [] # Khởi tạo danh sách cho các ID lớp, độ tin cậy và hộp chứa.

        # scale lại giá trị của ảnh
        scale_w, scale_h = 1, 1
        if postprocessing == 'yolov8': #Tính tỷ lệ nếu sử dụng phương pháp hậu xử lý 'yolov8'.
            scale_w, scale_h = frameWidth / self.mywidth, frameHeight / self.myheight

        # duyệt qua tất cả cacs lỗi phát hiện được trên 1 ảnh
        # thực hiện lưu thông tin của từng lỗi để sau đó sử 
        # dụng thông tin này vẽ lên ảnh hoặc lưu về database
        for out in outs:
            if postprocessing == 'yolov8':
                out = out[0].transpose(1, 0)

            # [x, y, w, h, conf, [xác suất của từng classé]]
            for detection in out:
                # xác suất của từng class
                scores = detection[4:]
                if background_label_id >= 0:
                    scores = np.delete(scores, background_label_id)

                classId = np.argmax(scores)
                confidence = scores[classId]
                
                # lấy vị trị của lỗi 
                # kiểm tra xem những nào có confidence lớn hơn ngưỡng cho trước thì mới lấy
                if confidence > confThreshold:
                    """ 
                    center_x, center_y: Tọa độ trung tâm của hộp chứa, tính theo tỷ lệ của chiều rộng và chiều cao khung hình.
                    width, height: Chiều rộng và chiều cao của hộp chứa, tính theo tỷ lệ.
                    left, top: Tọa độ góc trên bên trái của hộp chứa.
                    classIds.append(classId): Thêm ID lớp vào danh sách classIds.
                    confidences.append(float(confidence)): Thêm độ tin cậy vào danh sách confidences.
                    boxes.append([left, top, width, height]): Thêm hộp chứa vào danh sách boxes.
                    """
                    center_x = int(detection[0] * scale_w) 
                    center_y = int(detection[1] * scale_h) 
                    width = int(detection[2] * scale_w) 
                    height = int(detection[3] * scale_h)
                    left = int(center_x - width / 2)
                    top = int(center_y - height / 2)
                    classIds.append(classId)
                    confidences.append(float(confidence))
                    boxes.append([left, top, width, height])
        
        """
        if len(outNames) > 1 or (lastLayer.type == 'Region' or postprocessing == 'yolov8') and 0 != cv2.dnn.DNN_BACKEND_OPENCV: 
        indices = []: Khởi tạo danh sách indices.
        classIds = np.array(classIds): Chuyển classIds thành mảng NumPy.
        boxes = np.array(boxes): Chuyển boxes thành mảng NumPy.
        confidences = np.array(confidences): Chuyển confidences thành mảng NumPy.
        unique_classes = set(classIds): Lấy tập hợp các lớp duy nhất.
        for cl in unique_classes: Lặp qua từng lớp duy nhất:
            class_indices = np.where(classIds == cl)[0]: Lấy các chỉ số của các đối tượng thuộc lớp hiện tại.
            conf = confidences[class_indices]: Lấy độ tin cậy của các đối tượng thuộc lớp hiện tại.
            box = boxes[class_indices].tolist(): Lấy hộp chứa của các đối tượng thuộc lớp hiện tại.
            nms_indices = cv2.dnn.NMSBoxes(box, conf, confThreshold, nmsThreshold): Áp dụng NMS để loại bỏ các hộp chứa không cần thiết.
            indices.extend(class_indices[nms_indices]): Thêm các chỉ số sau NMS vào indices.
        else: indices = np.arange(0, len(classIds)): Nếu không cần NMS, lấy tất cả các chỉ số.
        for i in indices: Lặp qua các chỉ số để vẽ hộp chứa và nhãn cho các đối tượng:
            left, top, width, height = boxes[i]: Lấy tọa độ và kích thước của hộp chứa.
            drawPred(classIds[i], confidences[i], left, top, left + width, top + height): Vẽ hộp chứa và nhãn lên khung hình.
        """
        # lọc thông tin và cho ra kết quả cuối cùng
        # nếu có object [[x, y, w, h, class, confidenc], [], [], [], []]
        if len(self.outNames) > 1 or (lastLayer.type == 'Region' or postprocessing == 'yolov8') and 0 != cv2.dnn.DNN_BACKEND_OPENCV:
            # lưu lại toàn bộ thông tin đã được lọc
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
        cv2.imwrite('anh2.jpg', self.frame)
        return fault_detect, self.frame    
    
    def call(self):
        outs = self.net.forward(self.outNames)
        return self.identify_fault(outs, self.confThreshold)
        # kết quả là thông tin lỗi, và ảnh đã được vẽ
        