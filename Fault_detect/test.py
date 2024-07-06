import cv2
from cvzone.HandTrackingModule import HandDetector

# Thiết lập camera
cap = cv2.VideoCapture(0)

# Khởi tạo bộ phát hiện tay
detector = HandDetector(detectionCon=0.8, maxHands=2)

while True:
    # Đọc từ camera
    success, img = cap.read()
    if not success:
        break

    # Phát hiện tay trong hình ảnh
    hands, img = detector.findHands(img)

    # Hiển thị hình ảnh
    cv2.imshow("Image", img)

    # Thoát khi nhấn 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Giải phóng camera và đóng tất cả cửa sổ
cap.release()
cv2.destroyAllWindows()