import cv2
import os
import numpy as np
import sys
import time
import insightface
import requests
import mysql.connector
from urllib.parse import urlparse

# --- Import DB functions ---
from db import (
    get_known_faces_from_db,
    list_students,
    add_face_to_db,
    mark_attendance_automatic,
)

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
    print("2. Start face recognition")
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


# ---------------- Face Recognition Loop ---------------- #
video_capture = choose_video_source()
print("\nPress 'q' to quit face recognition.")

# Track recently marked students to prevent spam
recently_marked = {}  # {rollnumber: timestamp}
COOLDOWN_SECONDS = 30  # Don't mark same student twice within 30 seconds

while True:
    ret, frame = video_capture.read()
    if not ret:
        continue
    faces = app.get(frame)
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

                # Check cooldown period before marking attendance
                current_time = time.time()
                if (
                    rollnumber not in recently_marked
                    or current_time - recently_marked[rollnumber] > COOLDOWN_SECONDS
                ):

                    # Mark attendance automatically
                    if mark_attendance_automatic(rollnumber, name, confidence):
                        recently_marked[rollnumber] = current_time

        # Visual feedback
        color = (0, 255, 0) if name != "Unknown Student" else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"{name} ({confidence:.2f})"
        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        # Show if recently marked (visual confirmation)
        if rollnumber in recently_marked:
            time_since_marked = int(current_time - recently_marked[rollnumber])
            if time_since_marked < 5:  # Show "MARKED" for 5 seconds
                cv2.putText(
                    frame,
                    "MARKED",
                    (x1, y2 + 25),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

    cv2.imshow("Video", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
