# OpenCV-Based Attendance System

A real-time facial recognition attendance system built with Python, OpenCV, InsightFace (RetinaFace + ArcFace), and MySQL. The system detects and recognizes student faces via webcam or IP camera, logs timed attendance sessions, and manages class enrollments through a terminal-based interface.

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
- SQL schema included for direct database setup

---

## Technologies Used

| Component | Library / Tool |
|---|---|
| Face Detection | InsightFace (RetinaFace) |
| Face Recognition | InsightFace (ArcFace – `buffalo_l`) |
| Video Capture | OpenCV (`opencv-python`) |
| Inference Runtime | ONNX Runtime |
| Database | MySQL (`mysql-connector-python`) |
| Numerical Computing | NumPy |
| HTTP / IP Camera | Requests |
| Web Interface (optional) | Flask |
| Image Processing | Pillow |

---

## Project Structure

```
OpenCV-Based-Attendence-System/
├── main.py                  # Entry point – CLI menu, enrollment, attendance session logic
├── db.py                    # All database operations (students, classes, sessions, attendance)
├── recognition.py           # Standalone recognition script (webcam)
├── new_model.py             # Model experimentation / alternative recognition pipeline
├── wireless_cam.py          # IP/wireless camera stream handler
├── wireless_recognition.py  # Recognition via wireless camera feed
├── project.sql              # MySQL schema – tables for students, classes, sessions, attendance
├── my_face.jpg              # Sample enrollment image
├── requirements.txt         # Python dependency list
└── .gitignore
```

---

## Installation and Setup

### Prerequisites

- Python 3.9 or 3.10 (recommended; InsightFace and ONNX Runtime have version constraints)
- MySQL Server running locally
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

### 4. Set Up the Database

1. Start your MySQL server.
2. Create the database and import the schema:

```bash
mysql -u root -p -e "CREATE DATABASE project;"
mysql -u root -p project < project.sql
```

3. Verify the `DB_CONFIG` block in `main.py` matches your MySQL credentials:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",       # Set your MySQL root password here
    "database": "project",
}
```

### 5. Download InsightFace Model

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

Run `wireless_cam.py` or `wireless_recognition.py` for dedicated IP camera sessions, or select the IP camera option within `main.py` and provide the stream URL (e.g., `http://192.168.1.x:8080/video`).

---

## Running Without a Database (Database-Free Mode)

The default system requires MySQL. To run the system without a database, replace all `db.py` calls with in-memory data structures and CSV-based persistence. The following describes the required modifications and assumptions.

### Assumptions

- Student identity data (name, roll number, face embeddings) is stored in a local JSON or CSV file.
- Attendance records are written to a CSV file per session.
- Class and enrollment management is handled via in-memory dictionaries, optionally persisted to JSON files.
- No multi-user or concurrent session support.

### Required Modifications

**1. Replace `db.py` imports in `main.py`**

Remove the import block:

```python
from db import (
    get_known_faces_from_db,
    list_students,
    add_face_to_db,
    ...
)
```

Replace with a local `storage.py` module that implements the same function signatures using file I/O.

**2. Implement `storage.py` (minimal interface)**

```python
import json
import csv
import numpy as np
from datetime import datetime

STUDENTS_FILE = "students.json"
ATTENDANCE_FILE = "attendance.csv"

def load_students():
    try:
        with open(STUDENTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_students(students):
    with open(STUDENTS_FILE, "w") as f:
        json.dump(students, f)

def get_known_faces_from_db():
    students = load_students()
    names, embeddings, rollnumbers = [], [], []
    for s in students:
        for emb in s["embeddings"]:
            names.append(s["name"])
            rollnumbers.append(s["rollnumber"])
            embeddings.append(np.array(emb))
    return names, embeddings, rollnumbers

def add_face_to_db(name, embedding, image_data=None, rollnumber=None):
    students = load_students()
    for s in students:
        if s["rollnumber"] == rollnumber:
            s["embeddings"].append(embedding.tolist())
            save_students(students)
            return
    students.append({
        "name": name,
        "rollnumber": rollnumber,
        "embeddings": [embedding.tolist()]
    })
    save_students(students)

def list_students():
    for s in load_students():
        print(f"{s['rollnumber']} - {s['name']} ({len(s['embeddings'])} photos)")

def log_attendance_to_csv(session_id, rollnumber, name, status, timestamp):
    with open(ATTENDANCE_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([session_id, rollnumber, name, status, timestamp])
```

**3. Replace session and detection logging**

- Replace `create_timer_session`, `log_detection_event`, and `finalize_session_attendance` with in-memory dictionaries that accumulate detection timestamps during the session loop.
- At session end, iterate over the detection log, apply the presence threshold, and write results to `attendance.csv`.

**Example finalization logic (no DB):**

```python
def finalize_no_db(detection_log, roster, session_start, duration, late_threshold):
    results = []
    for rollnumber, detections in detection_log.items():
        name = detections["name"]
        first_seen = detections["first_seen_at"]
        total_detections = detections["count"]
        presence_ratio = total_detections / duration

        if presence_ratio >= 0.80:
            status = "Late" if first_seen > late_threshold else "Present"
        else:
            status = "Absent"

        results.append((rollnumber, name, status))
        log_attendance_to_csv(
            session_id="local_session",
            rollnumber=rollnumber,
            name=name,
            status=status,
            timestamp=datetime.now().isoformat()
        )

    # Mark remaining roster students as Absent
    detected_rolls = {r[0] for r in results}
    for student in roster:
        if student["rollnumber"] not in detected_rolls:
            log_attendance_to_csv("local_session", student["rollnumber"], student["name"], "Absent", datetime.now().isoformat())
```

**4. Remove MySQL-specific imports**

Remove any `import mysql.connector` and `DB_CONFIG` references from `main.py` and all supporting files. The system will operate entirely from local JSON and CSV files.

### Output

Attendance records are written to `attendance.csv` in the working directory:

```
session_id,rollnumber,name,status,timestamp
local_session,2022-CS-001,Ali Hassan,Present,2025-09-01T09:05:32
local_session,2022-CS-002,Sara Khan,Late,2025-09-01T09:07:10
local_session,2022-CS-003,Usman Tariq,Absent,2025-09-01T09:00:00
```

---

## Notes

- The recognition threshold is set to `0.6` cosine similarity. Lower this value to increase strictness; raise it to be more permissive.
- A maximum of 5 photos per student is enforced. More photos improve recognition accuracy under varied lighting and angles.
- The `buffalo_l` InsightFace model runs on CPU by default (`CPUExecutionProvider`). GPU acceleration requires CUDA and the appropriate ONNX Runtime GPU package.
- The `project.sql` file contains the complete schema; inspect it before importing to verify table names match `db.py` queries.

---

## License

This project does not currently specify a license. All rights reserved by the author unless otherwise stated.
