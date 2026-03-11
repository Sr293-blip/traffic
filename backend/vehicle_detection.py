from ultralytics import YOLO
import cv2

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Traffic thresholds (adjust for Madurai roads)
LOW = 10
MEDIUM = 25

def detect_congestion(video_path):
    cap = cv2.VideoCapture(video_path)
    vehicle_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, stream=True)

        count = 0
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                # COCO vehicle classes
                if cls in [2, 3, 5, 7]:  # car, bike, bus, truck
                    count += 1

        vehicle_count = count
        cv2.putText(frame, f"Vehicles: {count}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Traffic Feed", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

    if vehicle_count < LOW:
        return "LOW"
    elif vehicle_count < MEDIUM:
        return "MEDIUM"
    else:
        return "HIGH"