import base64
import json
import os
from datetime import datetime

import numpy as np


DATA_DIR = os.path.join(os.path.dirname(__file__), "local_data")
DATA_FILE = os.path.join(DATA_DIR, "attendance_data.json")


def _default_data():
    return {
        "meta": {
            "next_class_id": 1,
            "next_session_id": 1,
        },
        "students": {},
        "classes": {},
        "class_students": [],
        "sessions": {},
        "detection_events": [],
        "attendance_records": [],
    }


def _ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_default_data(), f, indent=2)


def _load_data():
    _ensure_storage()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_data(data):
    _ensure_storage()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _photo_count(student):
    return len(student.get("photos", []))


def _get_class_from_data(data, class_id):
    return data["classes"].get(str(class_id))


def _get_class_roster_from_data(data, class_id):
    roster = []
    for enrollment in data.get("class_students", []):
        if int(enrollment.get("class_id")) != int(class_id):
            continue

        rollnumber = enrollment.get("rollnumber")
        student = data["students"].get(rollnumber)
        if not student or not student.get("is_active", True):
            continue

        roster.append(
            {
                "rollnumber": rollnumber,
                "name": student.get("name", "Unknown"),
                "department": student.get("department"),
                "batch": student.get("batch"),
            }
        )

    roster.sort(key=lambda item: item["name"].lower())
    return roster


# ============================================
# STUDENT MANAGEMENT FUNCTIONS
# ============================================


def get_known_faces_from_db():
    """Fetch all active students and average their embeddings."""
    data = _load_data()
    known_names, known_encodings, known_rollnumbers = [], [], []

    for rollnumber, student in data["students"].items():
        if not student.get("is_active", True):
            continue

        embeddings = [
            np.array(photo["encoding"], dtype=np.float32)
            for photo in student.get("photos", [])
            if photo.get("encoding")
        ]

        if not embeddings:
            continue

        avg_embedding = np.mean(embeddings, axis=0)
        known_encodings.append(avg_embedding)
        known_names.append(student.get("name", "Unknown"))
        known_rollnumbers.append(rollnumber)

    print(f"Found {len(known_rollnumbers)} student(s) in local storage.")
    return known_names, known_encodings, known_rollnumbers


def list_students():
    """List all active students with roll numbers."""
    data = _load_data()
    students = [
        (roll, details)
        for roll, details in data["students"].items()
        if details.get("is_active", True)
    ]

    students.sort(key=lambda item: item[1].get("name", "").lower())

    if not students:
        print("No students found in local storage.")
        return

    print("\n--- Student Records ---")
    for roll, student in students:
        dept = student.get("department")
        batch = student.get("batch")
        dept_str = f" | Dept: {dept}" if dept else ""
        batch_str = f" | Batch: {batch}" if batch else ""
        print(f"Roll No: {roll} | Name: {student.get('name', 'Unknown')}{dept_str}{batch_str}")


def add_face_to_db(name, embedding, image_data, rollnumber=None):
    """Add/update student and save a new face embedding."""
    if not rollnumber:
        rollnumber = f"AUTO-{int(datetime.now().timestamp())}"

    data = _load_data()
    students = data["students"]

    if rollnumber not in students:
        students[rollnumber] = {
            "rollnumber": rollnumber,
            "name": name or "Unknown",
            "email": None,
            "department": None,
            "batch": None,
            "is_active": True,
            "photos": [],
            "created_at": _now_iso(),
        }
    else:
        # Do not replace a known name with placeholder input.
        if name and name.lower() != "unknown":
            students[rollnumber]["name"] = name

    photo = {
        "photo_type": "enrollment",
        "encoding": np.asarray(embedding, dtype=np.float32).tolist(),
        "image_b64": (
            base64.b64encode(image_data).decode("ascii") if image_data else None
        ),
        "created_at": _now_iso(),
    }

    students[rollnumber].setdefault("photos", []).append(photo)
    _save_data(data)
    print(
        f"Successfully added face for '{students[rollnumber]['name']}' (Roll No: {rollnumber})."
    )


def get_photo_count(rollnumber):
    """Get the current number of photos for a student."""
    data = _load_data()
    student = data["students"].get(rollnumber)
    if not student:
        return 0
    return _photo_count(student)


# ============================================
# CLASS MANAGEMENT FUNCTIONS
# ============================================


def list_classes():
    """List all active classes."""
    data = _load_data()
    classes = [
        class_data
        for class_data in data["classes"].values()
        if class_data.get("is_active", True)
    ]

    classes.sort(key=lambda item: item.get("class_name", "").lower())

    if not classes:
        print("No classes found in local storage.")
        return []

    print("\n--- Available Classes ---")
    for cls in classes:
        print(f"ID: {cls['id']} | {cls['class_name']} ({cls['course_code']})")
        if cls.get("instructor"):
            print(f"  Instructor: {cls['instructor']}")
        if cls.get("department"):
            print(f"  Department: {cls['department']} | Semester: {cls.get('semester')}")
        if cls.get("batch"):
            print(f"  Batch: {cls['batch']}")

    return classes


def create_class(
    class_name, course_code, department, batch, semester=None, instructor=None
):
    """Create a new class in local storage."""
    data = _load_data()
    class_id = int(data["meta"]["next_class_id"])
    data["meta"]["next_class_id"] = class_id + 1

    class_data = {
        "id": class_id,
        "class_name": class_name,
        "course_code": course_code,
        "department": department,
        "batch": batch,
        "semester": semester,
        "instructor": instructor,
        "is_active": True,
        "created_at": _now_iso(),
    }

    data["classes"][str(class_id)] = class_data
    _save_data(data)

    print("\nClass created successfully!")
    print(f"  Class ID: {class_id}")
    print(f"  Name: {class_name}")
    print(f"  Code: {course_code}")

    return class_id


def get_class_by_id(class_id):
    """Get class details by ID."""
    data = _load_data()
    class_info = _get_class_from_data(data, class_id)
    if not class_info or not class_info.get("is_active", True):
        return None
    return class_info


# ============================================
# STUDENT ENROLLMENT FUNCTIONS
# ============================================


def get_eligible_students_for_class(department, batch):
    """Get students eligible for enrollment based on department and batch."""
    data = _load_data()
    students = []

    for rollnumber, student in data["students"].items():
        if not student.get("is_active", True):
            continue

        photo_count = _photo_count(student)
        if photo_count <= 0:
            continue

        student_department = student.get("department")
        student_batch = student.get("batch")

        # If department/batch are missing on a student, keep them eligible.
        dept_matches = (
            not student_department
            or str(student_department).strip().lower() == str(department).strip().lower()
        )
        batch_matches = (
            not student_batch
            or str(student_batch).strip().lower() == str(batch).strip().lower()
        )

        if not (dept_matches and batch_matches):
            continue

        students.append(
            {
                "rollnumber": rollnumber,
                "name": student.get("name", "Unknown"),
                "email": student.get("email"),
                "department": student_department or "N/A",
                "batch": student_batch or "N/A",
                "photo_count": photo_count,
            }
        )

    students.sort(key=lambda item: item["name"].lower())

    print(f"\nFound {len(students)} eligible students")
    print(f"   Department filter: {department}")
    print(f"   Batch filter: {batch}")
    return students


def enroll_student_in_class(class_id, rollnumber):
    """Enroll a single student in a class."""
    data = _load_data()

    if not _get_class_from_data(data, class_id):
        return False

    if rollnumber not in data["students"]:
        return False

    for enrollment in data["class_students"]:
        if (
            int(enrollment.get("class_id")) == int(class_id)
            and enrollment.get("rollnumber") == rollnumber
        ):
            return False

    data["class_students"].append(
        {
            "class_id": int(class_id),
            "rollnumber": rollnumber,
            "enrollment_date": _now_iso(),
        }
    )
    _save_data(data)
    return True


def bulk_enroll_students_in_class(class_id, rollnumbers):
    """Enroll multiple students in a class."""
    enrolled_count = 0
    skipped_count = 0

    for rollnumber in rollnumbers:
        if enroll_student_in_class(class_id, rollnumber):
            enrolled_count += 1
        else:
            skipped_count += 1

    print("\nEnrollment complete!")
    print(f"  Enrolled: {enrolled_count} students")
    if skipped_count > 0:
        print(f"  Skipped (already enrolled/not found): {skipped_count}")

    return enrolled_count


def list_class_enrollments(class_id):
    """List all students enrolled in a specific class."""
    data = _load_data()
    class_info = _get_class_from_data(data, class_id)

    if not class_info:
        print(f"Class ID {class_id} not found")
        return []

    enrollments = []
    for enrollment in data["class_students"]:
        if int(enrollment.get("class_id")) != int(class_id):
            continue

        rollnumber = enrollment.get("rollnumber")
        student = data["students"].get(rollnumber)
        if not student:
            continue

        enrollments.append(
            {
                "rollnumber": rollnumber,
                "name": student.get("name", "Unknown"),
                "department": student.get("department") or "N/A",
                "batch": student.get("batch") or "N/A",
                "enrollment_date": enrollment.get("enrollment_date"),
                "photo_count": _photo_count(student),
            }
        )

    enrollments.sort(key=lambda item: item["name"].lower())

    print(
        f"\n--- Enrollments for {class_info['class_name']} ({class_info['course_code']}) ---"
    )
    if not enrollments:
        print("No students enrolled yet")
    else:
        print(f"Total: {len(enrollments)} students\n")
        for idx, student in enumerate(enrollments, 1):
            print(f"{idx:2d}. {student['name']:30s} ({student['rollnumber']})")
            print(
                f"    {student['department']}, Batch {student['batch']}, {student['photo_count']} photos"
            )

    return enrollments


def remove_student_from_class(class_id, rollnumber):
    """Remove a student from a class."""
    data = _load_data()
    before = len(data["class_students"])

    data["class_students"] = [
        enrollment
        for enrollment in data["class_students"]
        if not (
            int(enrollment.get("class_id")) == int(class_id)
            and enrollment.get("rollnumber") == rollnumber
        )
    ]

    if len(data["class_students"]) == before:
        print(f"Student {rollnumber} not found in this class")
        return False

    _save_data(data)
    print(f"Student {rollnumber} removed from class")
    return True


# ============================================
# TIMER-BASED ATTENDANCE FUNCTIONS
# ============================================


def get_class_roster(class_id):
    """Get all enrolled students for a class."""
    data = _load_data()
    roster = _get_class_roster_from_data(data, class_id)
    print(f"Loaded roster: {len(roster)} students")
    return roster


def create_timer_session(
    class_id,
    duration_seconds,
    late_threshold_seconds,
    min_presence_percent=0.80,
    marked_by=None,
):
    """Start a new timer-based attendance session."""
    data = _load_data()

    if not _get_class_from_data(data, class_id):
        print(f"Class ID {class_id} not found")
        return None

    session_id = int(data["meta"]["next_session_id"])
    data["meta"]["next_session_id"] = session_id + 1

    now = datetime.now()
    data["sessions"][str(session_id)] = {
        "id": session_id,
        "class_id": int(class_id),
        "session_date": now.strftime("%Y-%m-%d"),
        "start_time": now.strftime("%H:%M:%S"),
        "actual_start_time": now.isoformat(timespec="seconds"),
        "actual_end_time": None,
        "duration_seconds": int(duration_seconds),
        "late_threshold_seconds": int(late_threshold_seconds),
        "min_presence_percent": float(min_presence_percent),
        "marked_by": marked_by,
        "camera_downtime_seconds": 0,
        "status": "ongoing",
    }

    _save_data(data)

    print(f"Session {session_id} started")
    print(f"  Duration: {duration_seconds}s")
    print(f"  Late threshold: {late_threshold_seconds}s")
    print(f"  Minimum presence: {min_presence_percent * 100}%")

    return session_id


def log_detection_event(session_id, rollnumber, detected_at_seconds, confidence_score):
    """Log a single face detection event during active session."""
    data = _load_data()

    if str(session_id) not in data["sessions"]:
        return

    data["detection_events"].append(
        {
            "session_id": int(session_id),
            "rollnumber": rollnumber,
            "detected_at_seconds": int(detected_at_seconds),
            "confidence_score": float(confidence_score),
            "logged_at": _now_iso(),
        }
    )
    _save_data(data)


def log_camera_downtime(session_id, downtime_seconds):
    """Record camera failure time to adjust presence requirements."""
    data = _load_data()
    session = data["sessions"].get(str(session_id))
    if not session:
        return

    session["camera_downtime_seconds"] = int(session.get("camera_downtime_seconds", 0)) + int(
        downtime_seconds
    )
    _save_data(data)
    print(f"Camera downtime logged: +{downtime_seconds}s")


def finalize_session_attendance(session_id, user_id=None):
    """Process all detection events and commit final attendance records."""
    data = _load_data()
    session = data["sessions"].get(str(session_id))

    if not session:
        print(f"Session {session_id} not found")
        return None

    class_id = int(session["class_id"])
    roster = _get_class_roster_from_data(data, class_id)
    events = [
        event
        for event in data["detection_events"]
        if int(event.get("session_id")) == int(session_id)
    ]

    by_student = {}
    for event in events:
        rollnumber = event.get("rollnumber")
        detected_second = int(event.get("detected_at_seconds", 0))
        by_student.setdefault(rollnumber, set()).add(detected_second)

    duration_seconds = max(1, int(session.get("duration_seconds", 1)))
    downtime_seconds = int(session.get("camera_downtime_seconds", 0))
    effective_duration = max(1, duration_seconds - downtime_seconds)
    min_presence_percent = float(session.get("min_presence_percent", 0.80))
    min_required_seconds = max(1, int(round(effective_duration * min_presence_percent)))
    late_threshold_seconds = int(session.get("late_threshold_seconds", 0))

    summary = {
        "total_present": 0,
        "total_late": 0,
        "total_absent": 0,
        "total_early_departure": 0,
        "total_insufficient": 0,
        "total_students": len(roster),
    }

    # Replace any existing attendance records for this session.
    data["attendance_records"] = [
        record
        for record in data["attendance_records"]
        if int(record.get("session_id")) != int(session_id)
    ]

    for student in roster:
        rollnumber = student["rollnumber"]
        name = student["name"]
        seen_seconds = sorted(by_student.get(rollnumber, set()))
        present_seconds = len(seen_seconds)
        arrival_seconds = seen_seconds[0] if seen_seconds else None
        is_late = bool(
            arrival_seconds is not None and arrival_seconds > late_threshold_seconds
        )

        if present_seconds == 0:
            status = "absent"
            summary["total_absent"] += 1
        elif present_seconds < min_required_seconds:
            status = "insufficient"
            summary["total_insufficient"] += 1
        elif is_late:
            status = "late"
            summary["total_late"] += 1
        else:
            status = "present"
            summary["total_present"] += 1

        data["attendance_records"].append(
            {
                "session_id": int(session_id),
                "class_id": class_id,
                "rollnumber": rollnumber,
                "name": name,
                "status": status,
                "present_seconds": present_seconds,
                "required_seconds": min_required_seconds,
                "arrival_seconds": arrival_seconds,
                "finalized_by": user_id,
                "finalized_at": _now_iso(),
            }
        )

    session["status"] = "completed"
    session["actual_end_time"] = _now_iso()

    # Match DB behavior by clearing raw events after finalization.
    data["detection_events"] = [
        event
        for event in data["detection_events"]
        if int(event.get("session_id")) != int(session_id)
    ]

    _save_data(data)

    print("\n" + "=" * 60)
    print("SESSION FINALIZED")
    print("=" * 60)
    print(f"Present: {summary['total_present']}")
    print(f"Late: {summary['total_late']}")
    print(f"Absent: {summary['total_absent']}")
    print(f"Early Departure: {summary['total_early_departure']}")
    print(f"Insufficient: {summary['total_insufficient']}")
    print(f"Total Students: {summary['total_students']}")
    print("=" * 60)

    return summary


def get_detected_students(session_id):
    """Get list of unique students detected during a session."""
    data = _load_data()
    detected_rollnumbers = {
        event.get("rollnumber")
        for event in data["detection_events"]
        if int(event.get("session_id")) == int(session_id)
    }
    return sorted([roll for roll in detected_rollnumbers if roll])


def get_session_info(session_id):
    """Get information about a specific session."""
    data = _load_data()
    session = data["sessions"].get(str(session_id))
    if not session:
        return None

    class_info = _get_class_from_data(data, session.get("class_id")) or {}
    merged = dict(session)
    merged["class_name"] = class_info.get("class_name")
    merged["course_code"] = class_info.get("course_code")
    return merged


def get_detection_count(session_id):
    """Get count of detection events for a session."""
    data = _load_data()
    return sum(
        1
        for event in data["detection_events"]
        if int(event.get("session_id")) == int(session_id)
    )