import cv2
import threading
import time
import numpy as np
import insightface
import storage

RECOGNITION_THRESHOLD = storage.get_system_settings().get("recognition_threshold", 0.6)

def update_recognition_threshold(value):
    global RECOGNITION_THRESHOLD
    RECOGNITION_THRESHOLD = float(value)
    storage.update_system_settings({"recognition_threshold": float(value)})

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class CameraStream:
    def __init__(self, camera_id: str, source: str):
        self.camera_id = camera_id
        self.source = source
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.linked_session_id = None
        
        # We need a locking mechanism to prevent race conditions when reading the frame buffer
        self.lock = threading.Lock()
        
        # Load known faces from storage on start
        self.known_names, self.known_face_encodings, self.known_rollnumbers = storage.get_known_faces_from_db()

    def start(self, face_app):
        self.is_running = True
        # if source is an integer string, convert to int for webcam
        src = int(self.source) if str(self.source).isdigit() else self.source
        self.cap = cv2.VideoCapture(src)
        
        if not self.cap.isOpened():
            self.is_running = False
            return False

        threading.Thread(target=self._update_loop, args=(face_app,), daemon=True).start()
        return True

    def stop(self):
        self.is_running = False
        if self.cap:
            self.cap.release()

    def link_session(self, session_id: int):
        self.linked_session_id = session_id
        # Refresh face encodings in case new students were added
        self.known_names, self.known_face_encodings, self.known_rollnumbers = storage.get_known_faces_from_db()

    def _update_loop(self, face_app):
        # Local cache to prevent spamming logs
        detection_timestamps = {}
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
                
            # Run inference
            try:
                faces = face_app.get(frame)
            except Exception:
                faces = []

            current_time_s = int(time.time())

            for face in faces:
                embedding = face.embedding
                (x1, y1, x2, y2) = face.bbox.astype(int)
                
                name = "Unknown"
                rollnumber = None
                confidence = 0

                if self.known_face_encodings:
                    sims = [cosine_similarity(embedding, enc) for enc in self.known_face_encodings]
                    best_match_idx = np.argmax(sims)
                    confidence = sims[best_match_idx]

                    if confidence > RECOGNITION_THRESHOLD:
                        name = self.known_names[best_match_idx]
                        rollnumber = self.known_rollnumbers[best_match_idx]
                        color = (0, 255, 0)
                        
                        # Log attendance if a session is actively linked
                        if self.linked_session_id is not None and rollnumber:
                            last_logged = detection_timestamps.get(rollnumber, 0)
                            # Log every 2 seconds
                            if current_time_s - last_logged >= 2:
                                # Need to calculate elapsed_seconds since session started
                                session_info = storage.get_session_info(self.linked_session_id)
                                if session_info and session_info["status"] == "ongoing":
                                    from datetime import datetime
                                    try:
                                        start_dt = datetime.fromisoformat(session_info["actual_start_time"])
                                        elapsed = int((datetime.now() - start_dt).total_seconds())
                                        storage.log_detection_event(self.linked_session_id, rollnumber, elapsed, confidence)
                                        detection_timestamps[rollnumber] = current_time_s
                                    except Exception as e:
                                        print(f"Time parsing error: {e}")
                    else:
                        color = (0, 165, 255) # Low confidence
                else:
                    color = (0, 0, 255)

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{name} {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.6, color, 2)

            with self.lock:
                self.current_frame = frame

    def get_jpeg_frame(self):
        with self.lock:
            if self.current_frame is None:
                return None
            ret, buffer = cv2.imencode('.jpg', self.current_frame)
            return buffer.tobytes() if ret else None


class MultiCameraManager:
    def __init__(self):
        self.cameras = {}
        print("Loading Shared InsightFace Model for multi-cam tracking...")
        try:
            self.face_app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
            self.face_app.prepare(ctx_id=0, det_size=(320, 320))
        except Exception as e:
            print(f"Manager face model failed to load: {e}")
            self.face_app = None

    def add_camera(self, camera_id: str, source: str) -> bool:
        if camera_id in self.cameras:
            self.remove_camera(camera_id)
            
        cam = CameraStream(camera_id, source)
        if cam.start(self.face_app):
            self.cameras[camera_id] = cam
            return True
        return False

    def remove_camera(self, camera_id: str):
        if camera_id in self.cameras:
            self.cameras[camera_id].stop()
            del self.cameras[camera_id]

    def get_camera(self, camera_id: str) -> CameraStream:
        return self.cameras.get(camera_id)

    def list_cameras(self):
        return [{"id": cam.camera_id, "source": cam.source, "linked_session": cam.linked_session_id} for cam in self.cameras.values()]

# Global singleton instance
manager = MultiCameraManager()
