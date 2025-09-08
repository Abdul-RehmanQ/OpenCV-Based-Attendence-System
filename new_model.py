import cv2
import mysql.connector
import os
import io
import numpy as np
import sys
import time
import insightface
import requests
from urllib.parse import urlparse

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}

# --- Recognition Threshold for ArcFace (cosine similarity) ---
RECOGNITION_THRESHOLD = 0.5

# --- Load RetinaFace + ArcFace Model ---
print("Loading RetinaFace + ArcFace model...")
app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded successfully.")


def cosine_similarity(a, b):
    """Compute cosine similarity between two embeddings."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_known_faces_from_db():
    """Fetch all students and average their embeddings."""
    known_names, known_encodings = [], []
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        query = """
            SELECT s.rollnumber, s.name, sp.encoding 
            FROM students s
            JOIN student_photos sp ON s.rollnumber = sp.rollnumber
        """
        cursor.execute(query)
        results = cursor.fetchall()

        student_embeddings, student_names = {}, {}
        for rollnumber, name, encoding_blob in results:
            encoding_array = np.load(io.BytesIO(encoding_blob))
            student_embeddings.setdefault(rollnumber, []).append(encoding_array)
            student_names[rollnumber] = name

        for rollnumber, embeddings in student_embeddings.items():
            avg_embedding = np.mean(embeddings, axis=0)
            known_encodings.append(avg_embedding)
            known_names.append(student_names[rollnumber])

        print(f"Found {len(student_embeddings)} student(s) in the database.")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
    return known_names, known_encodings


def list_students():
    """List all students with roll numbers."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute("SELECT rollnumber, name FROM students")
        results = cursor.fetchall()
        if not results:
            print("No students found in the database.")
        else:
            print("\n--- Student Records ---")
            for roll, name in results:
                print(f"Roll No: {roll} | Name: {name}")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def add_face_to_db(name, embedding, image_data, rollnumber=None):
    """Add student + embedding to DB (create new if not exists)."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        if not rollnumber:
            cursor.execute("SELECT rollnumber FROM students WHERE name = %s", (name,))
            result = cursor.fetchone()
            if result:
                rollnumber = result[0]
            else:
                rollnumber = str(int(time.time()))
                cursor.execute(
                    "INSERT INTO students (rollnumber, name) VALUES (%s, %s)",
                    (rollnumber, name),
                )

        bio_enc = io.BytesIO()
        np.save(bio_enc, embedding)
        encoding_blob = bio_enc.getvalue()

        sql = "INSERT INTO student_photos (rollnumber, image, encoding) VALUES (%s, %s, %s)"
        cursor.execute(sql, (rollnumber, image_data, encoding_blob))

        db_connection.commit()
        print(f"Successfully added face for '{name}' (Roll No: {rollnumber}).")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        db_connection.rollback()
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


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
    faces = app.get(frame)
    if not faces:
        return None, None
    face = faces[0]
    return face.embedding, face.bbox


def handle_add_new_face():
    """Guide user to add student with images."""
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
            add_face_to_db(name, embedding, image_data)
    return True


def add_images_for_existing_student():
    """Add up to 5 images for an existing student."""
    list_students()
    rollnumber = input("Enter the roll number of the student (or q to quit): ")
    if rollnumber.lower() == "q":
        return False

    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM students WHERE rollnumber = %s", (rollnumber,))
        result = cursor.fetchone()
        if not result:
            print("No student found with that roll number.")
            return False
        name = result[0]
        print(f"Adding images for {name} (Roll No: {rollnumber})")

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
                add_face_to_db(name, embedding, image_data, rollnumber=rollnumber)
                added += 1
                print(f"✓ Added {added}/5 images for {name}")
        return True
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return False


# --- Main Program Execution ---
known_names, known_face_encodings = get_known_faces_from_db()

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
            known_names, known_face_encodings = get_known_faces_from_db()
    elif choice == "2":
        if not known_face_encodings:
            print("No student records found. Add at least one student first.")
        else:
            break
    elif choice == "3":
        list_students()
    elif choice == "4":
        if add_images_for_existing_student():
            known_names, known_face_encodings = get_known_faces_from_db()
    elif choice.lower() == "q":
        sys.exit("Program terminated by user.")
    else:
        print("Invalid choice.")


# --- Face Recognition Loop ---
video_capture = choose_video_source()
print("\nPress 'q' to quit face recognition.")

while True:
    ret, frame = video_capture.read()
    if not ret:
        continue
    faces = app.get(frame)
    for face in faces:
        embedding = face.embedding
        (x1, y1, x2, y2) = face.bbox.astype(int)
        name = "Unknown Student"
        confidence = 0
        if known_face_encodings:
            sims = [cosine_similarity(embedding, enc) for enc in known_face_encodings]
            best_match_index = np.argmax(sims)
            confidence = sims[best_match_index]
            if confidence > RECOGNITION_THRESHOLD:
                name = known_names[best_match_index]
        color = (0, 255, 0) if name != "Unknown Student" else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{name} ({confidence:.2f})" if name != "Unknown Student" else name
        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_DUPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    cv2.imshow("Video", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
