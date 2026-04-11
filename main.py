from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import uvicorn
import cv2
import numpy as np
import base64
import os
import sys

# --- CUDA Path Setup for ONNX Runtime ---
# This ensures that ONNX Runtime can find the pip-installed cuDNN files
try:
    cudnn_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', 'cudnn', 'bin')
    cublas_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', 'cublas', 'bin')
    os.environ['PATH'] = f"{cudnn_path};{cublas_path};" + os.environ.get('PATH', '')
    if hasattr(os, 'add_dll_directory'):
        os.add_dll_directory(cudnn_path)
        os.add_dll_directory(cublas_path)
except Exception as e:
    print(f"CUDA/cuDNN Path warning: {e}")

import insightface

# Import from existing local storage
import storage
import camera_manager

# --- Models ---
class ClassCreateReq(BaseModel):
    class_name: str
    course_code: str
    department: str
    batch: str
    semester: Optional[str] = None
    instructor: Optional[str] = None

class StudentEnrollBulkReq(BaseModel):
    rollnumbers: List[str]

class SessionStartReq(BaseModel):
    class_id: int
    duration_seconds: int = 3600
    late_threshold_seconds: int = 300
    min_presence_percent: float = 0.8
    marked_by: Optional[str] = None
    camera_id: Optional[str] = None # Automatically link a camera if provided

class CameraAddReq(BaseModel):
    camera_id: str
    source: str

class CameraLinkReq(BaseModel):
    session_id: int

app = FastAPI(title="Face Recognition Attendance API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load minimal Face Analysis if needed for single image uploads in API
# Note: For multi-camera continuous, we'll build a separate manager in Part 2.
try:
    print("Loading Face Analysis Model for API Image Processing...")
    face_app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    face_app.prepare(ctx_id=0, det_size=(640, 640))
except Exception as e:
    print(f"Warning: Could not load InsightFace in API: {e}")
    face_app = None


@app.get("/")
def read_root():
    return {"status": "ok", "message": "Attendance System API Server Running"}


class SettingsReq(BaseModel):
    recognition_threshold: float

@app.get("/api/settings")
def get_settings():
    return storage.get_system_settings()

@app.post("/api/settings")
def update_settings(req: SettingsReq):
    camera_manager.update_recognition_threshold(req.recognition_threshold)
    return {"status": "success", "message": "Settings updated"}


# --- Dashboard Stats ---
@app.get("/api/stats")
def get_stats():
    data = storage._load_data()
    active_classes = len([c for c in data.get("classes", {}).values() if c.get("is_active", True)])
    active_students = len([s for s in data.get("students", {}).values() if s.get("is_active", True)])
    sessions_run = len(data.get("sessions", {}))
    return {
        "total_classes": active_classes,
        "total_students": active_students,
        "total_sessions": sessions_run,
        "system_status": "Active"
    }


# --- Students ---
@app.get("/api/students")
def get_all_students():
    data = storage._load_data()
    students = []
    for roll, details in data.get("students", {}).items():
        if details.get("is_active", True):
            # Exclude massive photo encodings from list view
            st = dict(details)
            st["photo_count"] = len(st.get("photos", []))
            st.pop("photos", None)
            students.append(st)
    return {"students": sorted(students, key=lambda x: x.get("name", "").lower())}

@app.post("/api/students")
async def register_student(
    name: str = Form(...),
    rollnumber: str = Form(...),
    department: str = Form(None),
    batch: str = Form(None),
    file: UploadFile = File(...)
):
    if not face_app:
        raise HTTPException(status_code=500, detail="Face recognition model not loaded.")
        
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image file.")
        
    faces = face_app.get(frame)
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in the image.")
        
    embedding = faces[0].embedding
    
    # Compress standard image payload to jpg
    _, frame_enc = cv2.imencode(".jpg", frame)
    image_data = frame_enc.tobytes()
    
    storage.add_face_to_db(name=name, embedding=embedding, image_data=image_data, rollnumber=rollnumber)
    
    # Update department and batch directly since add_face_to_db assumes standard fields
    data = storage._load_data()
    if department:
        data["students"][rollnumber]["department"] = department
    if batch:
        data["students"][rollnumber]["batch"] = batch
    storage._save_data(data)
    
    return {"status": "success", "message": f"Successfully registered {name} ({rollnumber})"}


# --- Classes ---
@app.get("/api/classes")
def get_all_classes():
    classes = storage.list_classes()
    return {"classes": classes}

@app.post("/api/classes")
def create_new_class(cls: ClassCreateReq):
    class_id = storage.create_class(
        class_name=cls.class_name,
        course_code=cls.course_code,
        department=cls.department,
        batch=cls.batch,
        semester=cls.semester,
        instructor=cls.instructor
    )
    return {"status": "success", "class_id": class_id}


# --- Enrollments ---
@app.get("/api/classes/{class_id}/enrollments")
def get_enrollments(class_id: int):
    enrollments = storage.list_class_enrollments(class_id)
    return {"enrollments": enrollments}

@app.post("/api/classes/{class_id}/enroll")
def enroll_students(class_id: int, req: StudentEnrollBulkReq):
    enrolled = storage.bulk_enroll_students_in_class(class_id, req.rollnumbers)
    return {"status": "success", "enrolled_count": enrolled}

@app.delete("/api/classes/{class_id}/enrollments/{rollnumber}")
def remove_enrollment(class_id: int, rollnumber: str):
    success = storage.remove_student_from_class(class_id, rollnumber)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Enrollment not found")


# --- Sessions (Timer Attendance) ---
@app.get("/api/sessions")
def get_sessions():
    data = storage._load_data()
    sessions = list(data.get("sessions", {}).values())
    return {"sessions": sessions}

@app.post("/api/sessions/start")
def start_session(req: SessionStartReq):
    session_id = storage.create_timer_session(
        class_id=req.class_id,
        duration_seconds=req.duration_seconds,
        late_threshold_seconds=req.late_threshold_seconds,
        min_presence_percent=req.min_presence_percent,
        marked_by=req.marked_by
    )
    if not session_id:
        raise HTTPException(status_code=400, detail="Failed to start session. Class may not exist.")
        
    if req.camera_id:
        cam = camera_manager.manager.get_camera(req.camera_id)
        if cam:
            cam.link_session(session_id)
            
    return {"status": "success", "session_id": session_id}

@app.post("/api/sessions/{session_id}/finalize")
def finalize_session(session_id: int):
    summary = storage.finalize_session_attendance(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found or could not be finalized")
    return {"status": "success", "summary": summary}

@app.get("/api/records")
def get_attendance_records():
    data = storage._load_data()
    records = data.get("attendance_records", [])
    return {"records": records}


# Mock Train API
@app.post("/api/model/train")
def mock_train_model():
    # ArcFace models are pre-trained. We just verify local storage integrity.
    # In a real heavy task, we'd fire a background job.
    known_names, _, _ = storage.get_known_faces_from_db()
    return {"status": "success", "message": f"Successfully re-cached {len(known_names)} known embeddings."}


# --- Multi-Camera ---
@app.get("/api/cameras")
def list_cameras():
    return {"cameras": camera_manager.manager.list_cameras()}

@app.post("/api/cameras")
def add_camera(req: CameraAddReq):
    if camera_manager.manager.add_camera(req.camera_id, req.source):
        return {"status": "success", "message": f"Camera {req.camera_id} started."}
    raise HTTPException(status_code=400, detail="Failed to open video source.")

@app.delete("/api/cameras/{camera_id}")
def remove_camera(camera_id: str):
    camera_manager.manager.remove_camera(camera_id)
    return {"status": "success"}

@app.post("/api/cameras/{camera_id}/link")
def link_camera(camera_id: str, req: CameraLinkReq):
    cam = camera_manager.manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    cam.link_session(req.session_id)
    return {"status": "success"}

def _video_stream_generator(camera_id: str):
    import time
    while True:
        cam = camera_manager.manager.get_camera(camera_id)
        if not cam or not cam.is_running:
            break
        frame = cam.get_jpeg_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.03)

@app.get("/api/video_feed/{camera_id}")
def video_feed(camera_id: str):
    cam = camera_manager.manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found or stopped.")
    return StreamingResponse(_video_stream_generator(camera_id), media_type="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
