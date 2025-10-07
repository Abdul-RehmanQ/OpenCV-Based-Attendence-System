import cv2
import os
import numpy as np
import sys
import time
import insightface
import requests
import mysql.connector
from datetime import datetime
from urllib.parse import urlparse

# --- Import DB functions ---
from db import get_known_faces_from_db, list_students, add_face_to_db

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "project",
}

# --- Recognition Threshold for ArcFace (cosine similarity) ---
RECOGNITION_THRESHOLD = 0.6

# --- Maximum photos per student ---
MAX_PHOTOS_PER_STUDENT = 5

# --- Timer-based attendance settings (in seconds) ---
TIMER_DURATION = 60  # Total observation time
PRESENT_THRESHOLD = 30  # Must be visible for 30+ seconds for "present"
LATE_THRESHOLD = 15  # 15-29 seconds = "late"
# Less than 15 seconds = "absent"

# --- Load RetinaFace + ArcFace Model ---
print("Loading RetinaFace + ArcFace model...")
app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded successfully.")


# ---------------- Utility Functions ---------------- #
def cosine_similarity(a, b):
    """Compute cosine similarity between two embeddings."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def test_ip_camera_connection(url):
    """Test if IP camera URL is accessible."""
    try:
        response = requests.get(url, timeout=5, stream=True)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def choose_video_source():
    """Select laptop webcam or IP camera."""
    while True:
        print("\nChoose video source:")
        print("1. Laptop Webcam (0)")
        print("2. IP Webcam (URL)")
        print("q. Quit")
        choice = input("Enter choice: ")

        if choice.lower() == "q":
            sys.exit("Program terminated by user.")
        elif choice == "1":
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                print("✓ Laptop webcam opened successfully.")
                return cap
            else:
                print("✗ Error: Could not open laptop webcam.")
        elif choice == "2":
            url = input("Enter your IP webcam URL (or q to quit): ")
            if url.lower() == "q":
                sys.exit("Program terminated by user.")
            if test_ip_camera_connection(url):
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    print("✓ IP webcam opened successfully.")
                    return cap
            print("✗ Could not connect to IP camera.")
        else:
            print("Invalid choice, try again.")


def extract_embedding(frame):
    """Extract embedding and bounding box from frame."""
    faces = app.get(frame)
    if not faces:
        return None, None
    face = faces[0]
    return face.embedding, face.bbox


def get_photo_count(rollnumber):
    """Get the current number of photos for a student."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM student_photos WHERE rollnumber = %s", (rollnumber,)
        )
        count = cursor.fetchone()[0]
        return count
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return 0
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def mark_attendance_with_timer(
    rollnumber, name, confidence_score, duration_seen, session_id=None
):
    """
    Mark attendance based on timer duration.

    Args:
        rollnumber: Student roll number
        name: Student name
        confidence_score: ArcFace similarity score
        duration_seen: How long student was visible (seconds)
        session_id: Specific class session ID (optional)

    Returns:
        True if marked successfully, False if duplicate
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        current_date = datetime.now().date()
        current_time = datetime.now()

        # Determine status based on duration
        if duration_seen >= PRESENT_THRESHOLD:
            status = "present"
            status_msg = "PRESENT"
        elif duration_seen >= LATE_THRESHOLD:
            status = "late"
            status_msg = "LATE"
        else:
            status = "absent"
            status_msg = "ABSENT (insufficient time)"

        # Check if already marked for THIS SPECIFIC SESSION
        if session_id:
            cursor.execute(
                """
                SELECT id FROM attendance 
                WHERE rollnumber = %s AND session_id = %s
            """,
                (rollnumber, session_id),
            )

            if cursor.fetchone():
                print(f"⚠️  {name} already marked for this class session")
                return False
        else:
            # If no session_id provided, prevent duplicate within last 5 minutes
            cursor.execute(
                """
                SELECT id FROM attendance 
                WHERE rollnumber = %s 
                AND timestamp >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            """,
                (rollnumber,),
            )

            if cursor.fetchone():
                print(f"⚠️  {name} marked recently (within 5 minutes)")
                return False

        # Prepare notes with duration information
        notes = (
            f"Visible for {duration_seen:.1f} seconds out of {TIMER_DURATION}s timer"
        )

        # Insert attendance record
        cursor.execute(
            """
            INSERT INTO attendance 
            (session_id, rollnumber, student_name, confidence_score, 
             timestamp, date, status, marked_by_system, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
        """,
            (
                session_id,
                rollnumber,
                name,
                float(confidence_score),
                current_time,
                current_date,
                status,
                notes,
            ),
        )

        db_connection.commit()
        print(
            f"✓ Attendance marked: {name} - {status_msg} (seen: {duration_seen:.1f}s, confidence: {confidence_score:.3f})"
        )
        return True

    except mysql.connector.Error as err:
        print(f"✗ Error marking attendance: {err}")
        db_connection.rollback()
        return False
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


# ---------------- Enrollment Functions ---------------- #
def handle_add_new_face():
    """Guide user to add student with roll number and name."""
    rollnumber = input("Enter the student's roll number (or q to quit): ")
    if rollnumber.lower() == "q":
        return False

    name = input("Enter the student's name (or q to quit): ")
    if name.lower() == "q":
        return False

    while True:
        source_choice = input("Choose method: [1] Upload file, [2] Webcam, [q] Quit: ")
        if source_choice.lower() == "q":
            return False
        if source_choice in ("1", "2"):
            break

    # Add up to MAX_PHOTOS_PER_STUDENT photos
    photos_added = 0
    print(f"\nAdding photos for {name} (maximum {MAX_PHOTOS_PER_STUDENT} photos)")

    while photos_added < MAX_PHOTOS_PER_STUDENT:
        embedding, image_data = None, None

        if source_choice == "1":
            image_path = input(
                f"Enter image file path ({photos_added + 1}/{MAX_PHOTOS_PER_STUDENT}) or 'q' to finish: "
            )
            if image_path.lower() == "q":
                break
            if not os.path.exists(image_path):
                print("File not found.")
                continue
            frame = cv2.imread(image_path)
            with open(image_path, "rb") as f:
                image_data = f.read()
            embedding, _ = extract_embedding(frame)

        elif source_choice == "2":
            cap = choose_video_source()
            print(
                f"Press 's' to save face ({photos_added + 1}/{MAX_PHOTOS_PER_STUDENT}) or 'q' to finish."
            )
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                faces = app.get(frame)
                if faces:
                    (x1, y1, x2, y2) = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"Photo {photos_added + 1}/{MAX_PHOTOS_PER_STUDENT}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
                cv2.imshow("Capture Face", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("s") and faces:
                    embedding = faces[0].embedding
                    _, frame_enc = cv2.imencode(".jpg", frame)
                    image_data = frame_enc.tobytes()
                    break
                elif key == ord("q"):
                    cap.release()
                    cv2.destroyAllWindows()
                    if photos_added == 0:
                        print("No photos added. Student enrollment cancelled.")
                        return False
                    else:
                        cap.release()
                        cv2.destroyAllWindows()
                        print(f"Finished with {photos_added} photo(s).")
                        return True
            cap.release()
            cv2.destroyAllWindows()

        if embedding is not None:
            add_face_to_db(name, embedding, image_data, rollnumber=rollnumber)
            photos_added += 1
            print(f"✓ Added photo {photos_added}/{MAX_PHOTOS_PER_STUDENT}")
        else:
            print("No face detected in the image. Please try again.")

    if photos_added > 0:
        print(f"\n✓ Successfully enrolled {name} with {photos_added} photo(s).")
        return True
    else:
        print("No photos added. Student enrollment cancelled.")
        return False


def add_images_for_existing_student():
    """Add images for an existing student (up to maximum of 5 total)."""
    list_students()
    rollnumber = input("Enter the roll number of the student (or q to quit): ")
    if rollnumber.lower() == "q":
        return False

    # Check current photo count
    current_count = get_photo_count(rollnumber)
    if current_count >= MAX_PHOTOS_PER_STUDENT:
        print(
            f"⚠️  This student already has {current_count} photos (maximum is {MAX_PHOTOS_PER_STUDENT})."
        )
        print("Cannot add more photos.")
        return False

    remaining_slots = MAX_PHOTOS_PER_STUDENT - current_count
    print(f"\nCurrent photos: {current_count}/{MAX_PHOTOS_PER_STUDENT}")
    print(f"You can add {remaining_slots} more photo(s).")

    source_choice = input("Choose method: [1] Upload file, [2] Webcam: ")

    added = 0
    while added < remaining_slots:
        embedding, image_data = None, None

        if source_choice == "1":
            image_path = input(
                f"Enter image file path ({added + 1}/{remaining_slots}) or 'q' to quit: "
            )
            if image_path.lower() == "q":
                break
            if not os.path.exists(image_path):
                print("File not found.")
                continue
            frame = cv2.imread(image_path)
            with open(image_path, "rb") as f:
                image_data = f.read()
            embedding, _ = extract_embedding(frame)

        elif source_choice == "2":
            cap = choose_video_source()
            print(
                f"Press 's' to save face ({added + 1}/{remaining_slots}) or 'q' to cancel."
            )
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                faces = app.get(frame)
                if faces:
                    (x1, y1, x2, y2) = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        f"Photo {current_count + added + 1}/{MAX_PHOTOS_PER_STUDENT}",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
                cv2.imshow("Capture Face", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("s") and faces:
                    embedding = faces[0].embedding
                    _, frame_enc = cv2.imencode(".jpg", frame)
                    image_data = frame_enc.tobytes()
                    break
                elif key == ord("q"):
                    cap.release()
                    cv2.destroyAllWindows()
                    return added > 0
            cap.release()
            cv2.destroyAllWindows()

        if embedding is not None:
            add_face_to_db("Unknown", embedding, image_data, rollnumber=rollnumber)
            added += 1
            new_total = current_count + added
            print(
                f"✓ Added photo {added}/{remaining_slots} (Total: {new_total}/{MAX_PHOTOS_PER_STUDENT})"
            )
        else:
            print("No face detected in the image. Please try again.")

    if added > 0:
        print(
            f"\n✓ Successfully added {added} photo(s). Total photos: {current_count + added}/{MAX_PHOTOS_PER_STUDENT}"
        )
        return True
    return False


# ---------------- Main Program ---------------- #
known_names, known_face_encodings, known_rollnumbers = get_known_faces_from_db()

while True:
    print("\n--- Menu ---")
    print("1. Add a new student")
    print("2. Start face recognition (Timer-based Attendance)")
    print("3. List all students")
    print("4. Add images for existing student")
    print("q. Quit")
    choice = input("Enter your choice: ")

    if choice == "1":
        if handle_add_new_face():
            known_names, known_face_encodings, known_rollnumbers = (
                get_known_faces_from_db()
            )
    elif choice == "2":
        if not known_face_encodings:
            print("No student records found. Add at least one student first.")
        else:
            break
    elif choice == "3":
        list_students()
    elif choice == "4":
        if add_images_for_existing_student():
            known_names, known_face_encodings, known_rollnumbers = (
                get_known_faces_from_db()
            )
    elif choice.lower() == "q":
        sys.exit("Program terminated by user.")
    else:
        print("Invalid choice.")


# ---------------- Timer-Based Face Recognition Loop ---------------- #
video_capture = choose_video_source()
print("\n" + "=" * 60)
print("TIMER-BASED ATTENDANCE SYSTEM")
print("=" * 60)
print(f"⏱️  Timer Duration: {TIMER_DURATION} seconds")
print(f"✓ Present: Visible for ≥{PRESENT_THRESHOLD} seconds")
print(f"⚠️  Late: Visible for {LATE_THRESHOLD}-{PRESENT_THRESHOLD-1} seconds")
print(f"✗ Absent: Visible for <{LATE_THRESHOLD} seconds")
print("=" * 60)
print("\nPress 'q' to quit face recognition.\n")

# Track student timers
student_timers = (
    {}
)  # {rollnumber: {'start_time': time, 'total_visible': seconds, 'last_seen': time, 'marked': bool}}
already_marked = set()  # Students who have been marked (to prevent re-marking)

while True:
    ret, frame = video_capture.read()
    if not ret:
        continue

    current_time = time.time()
    faces = app.get(frame)
    detected_rollnumbers = set()

    for face in faces:
        embedding = face.embedding
        (x1, y1, x2, y2) = face.bbox.astype(int)
        name = "Unknown Student"
        rollnumber = None
        confidence = 0

        if known_face_encodings:
            sims = [cosine_similarity(embedding, enc) for enc in known_face_encodings]
            best_match_index = np.argmax(sims)
            confidence = sims[best_match_index]

            if confidence > RECOGNITION_THRESHOLD:
                name = known_names[best_match_index]
                rollnumber = known_rollnumbers[best_match_index]
                detected_rollnumbers.add(rollnumber)

                # Check if already marked in this session
                if rollnumber in already_marked:
                    detected_rollnumbers.add(rollnumber)
                    # Show marked status but don't start new timer
                    color = (0, 255, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame,
                        f"{name} ({confidence:.2f})",
                        (x1, y1 - 30),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.6,
                        (255, 255, 255),
                        2,
                    )
                    cv2.putText(
                        frame,
                        "ALREADY MARKED",
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2,
                    )
                    continue

                # Initialize timer for new student
                if rollnumber not in student_timers:
                    student_timers[rollnumber] = {
                        "start_time": current_time,
                        "total_visible": 0,
                        "last_seen": current_time,
                        "marked": False,
                        "name": name,
                        "confidence": confidence,
                    }
                    print(f"\n⏱️  Timer started for {name} (Roll: {rollnumber})")

                # Update timer
                timer_data = student_timers[rollnumber]
                elapsed_since_start = current_time - timer_data["start_time"]

                # Increment visible time (update every frame seen)
                if (
                    current_time - timer_data["last_seen"] < 2
                ):  # Within 2 seconds = continuous
                    timer_data["total_visible"] += (
                        current_time - timer_data["last_seen"]
                    )
                timer_data["last_seen"] = current_time
                timer_data["confidence"] = confidence

                # Check if timer duration completed
                if elapsed_since_start >= TIMER_DURATION and not timer_data["marked"]:
                    # Timer finished - mark attendance
                    duration_seen = timer_data["total_visible"]
                    mark_attendance_with_timer(
                        rollnumber, name, confidence, duration_seen
                    )
                    timer_data["marked"] = True
                    already_marked.add(rollnumber)

                # Visual feedback
                if timer_data["marked"]:
                    color = (0, 255, 0)  # Green for marked
                    status_text = "MARKED"
                else:
                    color = (255, 165, 0)  # Orange for in-progress
                    time_remaining = max(0, TIMER_DURATION - elapsed_since_start)
                    status_text = f"Timer: {int(time_remaining)}s | Visible: {int(timer_data['total_visible'])}s"

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Display name and confidence
                label = f"{name} ({confidence:.2f})"
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 - 30),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.6,
                    (255, 255, 255),
                    2,
                )

                # Display timer status
                cv2.putText(
                    frame,
                    status_text,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )
        else:
            # Unknown student
            color = (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                name,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_DUPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

    # Clean up students who left (not detected for 3+ seconds)
    rollnumbers_to_remove = []
    for rollnumber, timer_data in student_timers.items():
        if rollnumber not in detected_rollnumbers:
            if current_time - timer_data["last_seen"] > 3:
                if not timer_data["marked"]:
                    # Student left before timer completed - DO NOT remove from tracking
                    # Keep them in already_marked to prevent re-entry
                    elapsed = current_time - timer_data["start_time"]
                    if elapsed < TIMER_DURATION:
                        print(
                            f"⚠️  {timer_data['name']} left early (visible: {timer_data['total_visible']:.1f}s) - Will not be re-timed if returns"
                        )
                        already_marked.add(rollnumber)  # Prevent re-entry
                rollnumbers_to_remove.append(rollnumber)

    for rollnumber in rollnumbers_to_remove:
        del student_timers[rollnumber]

    cv2.imshow("Timer-Based Attendance System", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
print("\n✓ Face recognition stopped.")
