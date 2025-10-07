import cv2
import os
import numpy as np
import sys
import time
import insightface
import requests
from urllib.parse import urlparse

# --- Import DB functions ---
from db import get_known_faces_from_db, list_students, add_face_to_db, mark_attendance_automatic

# --- Recognition Threshold for ArcFace (cosine similarity) ---
RECOGNITION_THRESHOLD = 0.6

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

    for _ in range(3):  # default 3 pics for new student
        embedding, image_data = None, None
        if source_choice == "1":
            image_path = input("Enter image file path: ")
            if not os.path.exists(image_path):
                print("File not found.")
                continue
            frame = cv2.imread(image_path)
            with open(image_path, "rb") as f:
                image_data = f.read()
            embedding, _ = extract_embedding(frame)
        elif source_choice == "2":
            cap = choose_video_source()
            print("Press 's' to save face or 'q' to cancel.")
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                faces = app.get(frame)
                if faces:
                    (x1, y1, x2, y2) = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
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
                    return False
            cap.release()
            cv2.destroyAllWindows()

        if embedding is not None:
            add_face_to_db(name, embedding, image_data, rollnumber=rollnumber)
    return True


def add_images_for_existing_student():
    """Add up to 5 images for an existing student."""
    list_students()
    rollnumber = input("Enter the roll number of the student (or q to quit): ")
    if rollnumber.lower() == "q":
        return False

    print(f"Adding images for Roll No: {rollnumber}")
    source_choice = input("Choose method: [1] Upload file, [2] Webcam: ")

    added = 0
    while added < 5:
        embedding, image_data = None, None
        if source_choice == "1":
            image_path = input("Enter image file path (or q to quit): ")
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
            print("Press 's' to save face or 'q' to cancel.")
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                faces = app.get(frame)
                if faces:
                    (x1, y1, x2, y2) = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
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
                    return False
            cap.release()
            cv2.destroyAllWindows()
        if embedding is not None:
            add_face_to_db("Unknown", embedding, image_data, rollnumber=rollnumber)
            added += 1
            print(f"✓ Added {added}/5 images for Roll No: {rollnumber}")
    return True


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
            known_names, known_face_encodings, known_rollnumbers = get_known_faces_from_db()
    elif choice == "2":
        if not known_face_encodings:
            print("No student records found. Add at least one student first.")
        else:
            break
    elif choice == "3":
        list_students()
    elif choice == "4":
        if add_images_for_existing_student():
            known_names, known_face_encodings, known_rollnumbers = get_known_faces_from_db()
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
                if rollnumber not in recently_marked or \
                   current_time - recently_marked[rollnumber] > COOLDOWN_SECONDS:
                    
                    # Mark attendance automatically
                    if mark_attendance_automatic(rollnumber, name, confidence):
                        recently_marked[rollnumber] = current_time
        
        # Visual feedback
        color = (0, 255, 0) if name != "Unknown Student" else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        label = f"{name} ({confidence:.2f})"
        cv2.putText(frame, label, (x1, y1 - 10),
                   cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
        
        # Show if recently marked (visual confirmation)
        if rollnumber in recently_marked:
            time_since_marked = int(current_time - recently_marked[rollnumber])
            if time_since_marked < 5:  # Show "MARKED" for 5 seconds
                cv2.putText(frame, "MARKED", (x1, y2 + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Video", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()