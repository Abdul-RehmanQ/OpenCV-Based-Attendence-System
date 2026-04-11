# Distributed Multi-Camera Facial Recognition & Real-Time Attendance Tracking System

A real-time attendance platform with a **FastAPI backend** and **React dashboard** for managing students, classes, camera feeds, and timer-based attendance sessions using facial recognition (InsightFace RetinaFace + ArcFace).

---

## What's New (Latest Updates)

- Migrated from CLI-based app to a unified **FastAPI API server** (`main.py`)
- Added **React admin dashboard** (`frontend/`) replacing the terminal interface
- Added dedicated **Classes management page**
- Added **dynamic recognition threshold slider** in Settings
- Introduced **multi-camera manager** with stream/session linking and live MJPEG feed endpoint
- Removed legacy standalone scripts (`api.py`, `recognition.py`, `wireless_recognition.py`, `wireless_cam.py`, `new_model.py`, `db.py`, `project.sql`)

---

## Core Features

- Student registration with face embedding extraction (up to 5 photos per student; more photos improve accuracy across varied lighting and angles)
- Class creation and student enrollment workflows with department/batch filtering
- Timer-based attendance sessions with on-time / late classification
- 80% minimum presence threshold for marking a student present
- Multi-camera feed registration and per-session camera linking
- Live MJPEG video feed endpoint for active cameras
- Configurable recognition threshold at runtime (default: `0.6` cosine similarity — lower to increase strictness, raise to increase permissiveness)
- Local JSON persistence — no database server required

---

## Tech Stack

| Component | Library / Tool |
|---|---|
| Face Detection | InsightFace (RetinaFace) |
| Face Recognition | InsightFace (ArcFace – `buffalo_l`) |
| Video Capture | OpenCV (`opencv-python`) |
| Inference Runtime | ONNX Runtime (CPU by default; GPU requires CUDA + ONNX Runtime GPU package) |
| Backend | FastAPI, Uvicorn |
| Frontend | React (Vite), React Router, Tailwind CSS, Lucide Icons |
| Storage | Local JSON file (`local_data/attendance_data.json`) |
| Numerical Computing | NumPy |

---

## Project Structure

```text
Distributed-Multi-Camera-Facial-Recognition-and-Real-Time-Attendance-Tracking-System/
├── main.py                   # FastAPI app — all API routes and recognition session logic
├── camera_manager.py         # Multi-camera stream and session linking
├── storage.py                # Local JSON storage backend
├── requirements.txt
├── README.md
└── frontend/
    ├── package.json
    └── src/
        ├── App.jsx
        ├── layouts/
        └── pages/
```

---

## Installation and Setup

### Prerequisites

- Python 3.9 or 3.10 (InsightFace and ONNX Runtime have version constraints)
- Node.js (for the React frontend)
- A working webcam or IP camera

### 1. Clone

```bash
git clone https://github.com/Abdul-RehmanQ/Distributed-Multi-Camera-Facial-Recognition-and-Real-Time-Attendance-Tracking-System.git
cd Distributed-Multi-Camera-Facial-Recognition-and-Real-Time-Attendance-Tracking-System
```

### 2. Backend Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

> **Windows note:** `dlib-bin` and `cmake` may require Visual Studio Build Tools. Install from [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before running `pip install`.

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. InsightFace Model

The `buffalo_l` model downloads automatically on first backend startup via InsightFace's model zoo. Internet access is required for the initial download. The model is cached locally after that.

---

## Running the App

### Start Backend (port 8000)

```bash
# from repo root
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend (Vite dev server)

```bash
cd frontend
npm run dev
```

Open the URL shown by Vite (typically `http://localhost:5173`). The frontend targets the backend at `http://localhost:8000`.

---

## Key API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/stats` | Dashboard summary stats |
| GET / POST | `/api/settings` | Read / update system settings (including recognition threshold) |
| GET / POST | `/api/students` | List students / register new student |
| GET / POST | `/api/classes` | List classes / create class |
| GET | `/api/classes/{class_id}/enrollments` | List enrolled students |
| POST | `/api/classes/{class_id}/enroll` | Enroll a student |
| DELETE | `/api/classes/{class_id}/enrollments/{rollnumber}` | Remove enrollment |
| POST | `/api/sessions/start` | Start an attendance session |
| POST | `/api/sessions/{session_id}/finalize` | Finalize and compute attendance |
| GET | `/api/records` | Retrieve attendance records |
| GET / POST / DELETE | `/api/cameras...` | Camera registration and management |
| GET | `/api/video_feed/{camera_id}` | Live MJPEG stream for a camera |

---

## Attendance Session Behavior

- Sessions are timer-based with a configurable duration and late-arrival threshold (both in seconds).
- Face recognition runs in real time; detections are logged per second with confidence scores.
- Students detected for ≥80% of the session duration are marked **present**.
- Students first detected after the late threshold are marked **late**.
- Sessions finalize automatically at timer expiry or via the `/finalize` endpoint.

---

## Data Storage

All data is persisted locally in `local_data/attendance_data.json` (created automatically on first run). This includes students, classes, enrollments, sessions, detection events, attendance records, and system settings.

No MySQL setup or database credentials are required. The legacy `db.py` and `project.sql` files have been removed.

---

## Notes

- InsightFace model initialization runs on backend startup; first startup takes longer due to model loading.
- `requirements.txt` may include some legacy dependencies from earlier versions of the project.
- GPU acceleration requires CUDA and the `onnxruntime-gpu` package in place of `onnxruntime`.

---

## License

No license is currently specified. All rights reserved by the author unless otherwise stated.
