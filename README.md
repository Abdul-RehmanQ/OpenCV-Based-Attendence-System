# OpenCV-Based Attendance System

A real-time facial recognition attendance system built with Python, OpenCV, and InsightFace (RetinaFace + ArcFace). The system detects and recognizes student faces via webcam or IP camera, logs timed attendance sessions, and manages class enrollments through a terminal-based interface, with local JSON storage (no MySQL server required).

---

## Features

- Face enrollment from image files or live webcam capture (up to 5 photos per student)
- High-accuracy face detection and recognition using RetinaFace + ArcFace (InsightFace `buffalo_l` model)
- Cosine similarity-based identity matching with configurable threshold
- Timer-based attendance sessions with on-time / late classification
- 80% minimum presence threshold for marking attendance
- Class creation and student enrollment management
- Support for laptop webcam and IP/wireless cameras
- Real-time bounding box overlay with recognition confidence scores
- Local file-based persistence via `storage.py` (`local_data/attendance_data.json`)

---

## Technologies Used

| Component | Library / Tool |
|---|---|
| Face Detection | InsightFace (RetinaFace) |
| Face Recognition | InsightFace (ArcFace – `buffalo_l`) |
| Video Capture | OpenCV (`opencv-python`) |
| Inference Runtime | ONNX Runtime |
| Storage | Local JSON file (`local_data/attendance_data.json`) |
| Numerical Computing | NumPy |
| HTTP / IP Camera | Requests |
| Web Interface (optional) | Flask |
| Image Processing | Pillow |

---

## Project Structure

```
OpenCV-Based-Attendence-System/
├── main.py                  # Entry point – CLI menu, enrollment, attendance session logic
├── storage.py               # Local JSON storage backend used by main.py
├── db.py                    # Legacy MySQL backend (optional/legacy)
├── recognition.py           # Standalone recognition script (webcam)
├── new_model.py             # Model experimentation / alternative recognition pipeline
├── wireless_cam.py          # IP/wireless camera stream handler
├── wireless_recognition.py  # Recognition via wireless camera feed
├── project.sql              # MySQL schema – tables for students, classes, sessions, attendance
├── local_data/              # Auto-created local storage directory
├── my_face.jpg              # Sample enrollment image
├── requirements.txt         # Python dependency list
└── .gitignore
```

---

## Installation and Setup

### Prerequisites

- Python 3.9 or 3.10 (recommended; InsightFace and ONNX Runtime have version constraints)
- A working webcam or IP camera

### 1. Clone the Repository

```bash
git clone https://github.com/Abdul-RehmanQ/OpenCV-Based-Attendence-System.git
cd OpenCV-Based-Attendence-System
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `dlib-bin` and `cmake` may require Visual Studio Build Tools on Windows. Install them from [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before running pip install.

### 4. Download InsightFace Model

The `buffalo_l` model is downloaded automatically on first run via InsightFace's model zoo. Ensure internet access is available during the first launch. The model is cached locally after the initial download.

---

## Usage

### Run the Application

```bash
python main.py
```

The system loads the face recognition model and presents a terminal menu:

```
======================================================================
FACE RECOGNITION ATTENDANCE SYSTEM
======================================================================
1. Add a new student
2. Add images for existing student
3. List all students
4. Create a new class
5. Enroll students in a class
6. View class enrollments
7. Start Timer-Based Attendance
q. Quit
======================================================================
```

### Enrollment Workflow

1. Select **Option 1** to register a new student (requires roll number, name, and up to 5 face photos).
2. Photos can be provided as image file paths or captured live via webcam.
3. Select **Option 4** to create a class (name, course code, department, batch, semester, instructor).
4. Select **Option 5** to enroll students in a class. Eligible students must have face photos and match the target department and batch.

### Running an Attendance Session

1. Select **Option 7**.
2. Choose a class from the listed classes.
3. Set session duration (seconds) and the late-arrival threshold (seconds).
4. Select a video source (webcam index `0` or IP camera URL).
5. The system runs face recognition in real time, logs detections every second, and displays a countdown timer with per-frame confidence scores.
6. Press `q` to end the session early or wait for the timer to expire.
7. Attendance is finalized automatically: students detected for ≥80% of session duration are marked present; those arriving after the late threshold are marked late.

### Wireless / IP Camera

Use `wireless_cam.py` for camera-only stream testing, or select the IP camera option within `main.py` and provide the stream URL (e.g., `http://192.168.1.x:8080/video`).

---

## Data Storage

This workspace is already configured for database-free mode in `main.py`.

- Student, class, session, and attendance data are stored in `local_data/attendance_data.json`.
- The file and folder are created automatically on first run.
- No MySQL setup and no localhost DB credentials are required.

If you still want MySQL mode later, `db.py`, `project.sql`, and legacy scripts (`recognition.py`, `wireless_recognition.py`, `new_model.py`) are kept as references.

---

## Notes

- The recognition threshold is set to `0.6` cosine similarity. Lower this value to increase strictness; raise it to be more permissive.
- A maximum of 5 photos per student is enforced. More photos improve recognition accuracy under varied lighting and angles.
- The `buffalo_l` InsightFace model runs on CPU by default (`CPUExecutionProvider`). GPU acceleration requires CUDA and the appropriate ONNX Runtime GPU package.
- The `project.sql` file and `db.py` are legacy MySQL artifacts and are not required for `main.py` in this setup.

---

## License

This project does not currently specify a license. All rights reserved by the author unless otherwise stated.
