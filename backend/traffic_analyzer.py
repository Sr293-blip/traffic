import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # lightweight YOLO model

VEHICLE_CLASSES = ["car", "bus", "truck", "motorcycle"]

def analyze_traffic(video_path):
    cap = cv2.VideoCapture(video_path)
    vehicle_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.4)
        for r in results:
            for box in r.boxes:
                cls = model.names[int(box.cls)]
                if cls in VEHICLE_CLASSES:
                    vehicle_count += 1

        if vehicle_count > 40:
            cap.release()
            return "HIGH"
        elif vehicle_count > 20:
            cap.release()
            return "MEDIUM"

    cap.release()
    return "LOW"