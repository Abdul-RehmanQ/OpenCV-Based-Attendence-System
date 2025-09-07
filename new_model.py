import cv2
import mysql.connector
import os
import io
import numpy as np
import sys
import time
import insightface

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}

# --- Recognition Threshold for ArcFace (cosine similarity) ---
# ArcFace embeddings are L2-normalized, so cosine similarity ~1.0 means same person.
RECOGNITION_THRESHOLD = 0.35

# --- Load RetinaFace + ArcFace Model ---
print("Loading RetinaFace + ArcFace model...")
app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded successfully.")


def cosine_similarity(a, b):
    """Compute cosine similarity between two embeddings."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_known_faces_from_db():
    """
    Fetches all students and their averaged face embeddings from the database.
    Groups multiple embeddings per student into one.
    """
    known_names = []
    known_encodings = []
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        print("Connected to the database successfully.")

        query = """
            SELECT s.rollnumber, s.name, sp.encoding 
            FROM students s
            JOIN student_photos sp ON s.rollnumber = sp.rollnumber
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Group embeddings by student rollnumber
        student_embeddings = {}
        student_names = {}

        for rollnumber, name, encoding_blob in results:
            encoding_array = np.load(io.BytesIO(encoding_blob))
            if rollnumber not in student_embeddings:
                student_embeddings[rollnumber] = []
            student_embeddings[rollnumber].append(encoding_array)
            student_names[rollnumber] = name

        # Average embeddings per student
        for rollnumber, embeddings in student_embeddings.items():
            avg_embedding = np.mean(embeddings, axis=0)
            known_encodings.append(avg_embedding)
            known_names.append(student_names[rollnumber])

        print(f"Found records of {len(student_embeddings)} student(s) in the database.")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()

    return known_names, known_encodings


def add_face_to_db(name, embedding, image_data):
    """
    Adds a new student (if not exists), face embedding, and image to the database.
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        # Check if student already exists
        cursor.execute("SELECT rollnumber FROM students WHERE name = %s", (name,))
        result = cursor.fetchone()
        if result:
            rollnumber = result[0]
        else:
            rollnumber = str(int(time.time()))  # unique ID using timestamp
            cursor.execute(
                "INSERT INTO students (rollnumber, name) VALUES (%s, %s)",
                (rollnumber, name),
            )

        # Convert embedding to blob
        bio_enc = io.BytesIO()
        np.save(bio_enc, embedding)
        encoding_blob = bio_enc.getvalue()

        # Save photo + embedding
        sql = "INSERT INTO student_photos (rollnumber, image, encoding) VALUES (%s, %s, %s)"
        values = (rollnumber, image_data, encoding_blob)
        cursor.execute(sql, values)

        db_connection.commit()
        print(f"Successfully added '{name}' to the database.")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        db_connection.rollback()
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def choose_video_source():
    """
    Allows the user to select between a laptop webcam and an IP webcam.
    """
    while True:
        print("\nChoose video source:")
        print("1. Laptop Webcam (0)")
        print("2. IP Webcam (URL)")
        choice = input("Enter choice: ")
        if choice == "1":
            return cv2.VideoCapture(0)
        elif choice == "2":
            url = input("Enter your IP webcam URL: ")
            return cv2.VideoCapture(url)
        else:
            print("Invalid choice, try again.")


def extract_embedding(frame):
    """
    Detects face in the frame and returns embedding + aligned bbox.
    """
    faces = app.get(frame)
    if not faces:
        return None, None
    face = faces[0]  # take first detected face
    embedding = face.embedding
    return embedding, face.bbox


def handle_add_new_face():
    """
    Guides the user through adding a new student.
    """
    name = input("Enter the name of the student you want to add: ")
    while True:
        source_choice = input("Choose method: [1] Upload file, [2] Webcam: ")
        if source_choice in ("1", "2"):
            break

    adding_more_faces = True
    while adding_more_faces:
        embedding = None
        image_data = None

        if source_choice == "1":
            image_path = input("Enter the full path to the image file: ")
            if not os.path.exists(image_path):
                print(f"File not found: {image_path}")
                return False
            frame = cv2.imread(image_path)
            with open(image_path, "rb") as f:
                image_data = f.read()
            embedding, _ = extract_embedding(frame)
            if embedding is None:
                print("No face detected in the image.")
                return False

        elif source_choice == "2":
            video_capture = choose_video_source()
            if not video_capture.isOpened():
                print("Error: Could not open video source.")
                return False
            print("Press 's' to save face or 'q' to cancel.")
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    break
                faces = app.get(frame)
                if faces:
                    (x1, y1, x2, y2) = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        "Face Detected",
                        (50, 50),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0, 255, 0),
                        2,
                    )
                else:
                    cv2.putText(
                        frame,
                        "No Face Detected",
                        (50, 50),
                        cv2.FONT_HERSHEY_DUPLEX,
                        1,
                        (0, 0, 255),
                        2,
                    )
                cv2.imshow("Capture Face", frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("s") and faces:
                    embedding = faces[0].embedding
                    ret_enc, frame_enc = cv2.imencode(".jpg", frame)
                    image_data = frame_enc.tobytes()
                    break
                elif key == ord("q"):
                    video_capture.release()
                    cv2.destroyAllWindows()
                    return False
            video_capture.release()
            cv2.destroyAllWindows()

        if embedding is not None:
            add_face_to_db(name, embedding, image_data)

        choice = input(f"Would you like to add another picture for '{name}'? (y/n): ")
        if choice.lower() != "y":
            adding_more_faces = False

    return True


# --- Main Program Execution ---
known_names, known_face_encodings = get_known_faces_from_db()

while True:
    print("\n--- Menu ---")
    print("1. Add a new student")
    print("2. Start face recognition")
    print("q. Quit")
    choice = input("Enter your choice: ")

    if choice == "1":
        if handle_add_new_face():
            known_names, known_face_encodings = get_known_faces_from_db()
    elif choice == "2":
        if not known_face_encodings:
            print("No student records found. Please add at least one student.")
        else:
            break
    elif choice == "q":
        sys.exit("Program terminated by user.")
    else:
        print("Invalid choice, please try again.")


# --- Face Recognition Loop ---
video_capture = choose_video_source()
if not video_capture.isOpened():
    sys.exit("Error: Could not open video source.")

print("\nPress 'q' to quit face recognition.")
while True:
    ret, frame = video_capture.read()
    if not ret:
        print("Error: Could not read frame from video source.")
        break

    faces = app.get(frame)
    for face in faces:
        embedding = face.embedding
        (x1, y1, x2, y2) = face.bbox.astype(int)

        name = "Unknown Student"
        if known_face_encodings:
            sims = [cosine_similarity(embedding, enc) for enc in known_face_encodings]
            best_match_index = np.argmax(sims)
            if sims[best_match_index] > RECOGNITION_THRESHOLD:
                name = known_names[best_match_index]

        # Draw bounding box + name
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.rectangle(frame, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
        cv2.putText(
            frame,
            name,
            (x1 + 6, y2 - 6),
            cv2.FONT_HERSHEY_DUPLEX,
            1.0,
            (255, 255, 255),
            1,
        )

    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
