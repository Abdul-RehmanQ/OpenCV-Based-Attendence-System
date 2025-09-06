import cv2
import face_recognition
import mysql.connector
import os
import io
import numpy as np
import sys

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}


def get_known_faces_from_db():
    known_names = []
    known_encodings = []
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        print("Connected to the database successfully.")
        cursor.execute("SELECT name, encoding FROM known_faces")
        results = cursor.fetchall()
        print(f"Found {len(results)} known faces in the database.")
        for row in results:
            name, encoding_blob = row
            encoding_array = np.load(io.BytesIO(encoding_blob))
            known_names.append(name)
            known_encodings.append(encoding_array)
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
    return known_names, known_encodings


def add_face_to_db(name, encoding, image_data):
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        bio_enc = io.BytesIO()
        np.save(bio_enc, encoding)
        encoding_blob = bio_enc.getvalue()
        sql = "INSERT INTO known_faces (name, encoding, image) VALUES (%s, %s, %s)"
        values = (name, encoding_blob, image_data)
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
    while True:
        print("\nChoose video source:")
        print("1. Laptop Webcam")
        print("2. IP Webcam (URL)")
        choice = input("Enter choice: ")
        if choice == "1":
            return cv2.VideoCapture(0)
        elif choice == "2":
            url = input("Enter your IP webcam URL: ")
            return cv2.VideoCapture(url)
        else:
            print("Invalid choice, try again.")


def handle_add_new_face():
    name = input("Enter the name of the person you want to add: ")
    while True:
        source_choice = input("Choose method: [1] Upload file, [2] Webcam: ")
        if source_choice in ("1", "2"):
            break

    face_encoding = None
    image_data = None

    if source_choice == "1":
        while True:
            image_path = input("Enter the full path to the image file: ")
            if not os.path.exists(image_path):
                print(f"File not found: {image_path}")
                continue
            with open(image_path, "rb") as f:
                image_data = f.read()
            known_image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(known_image)
            if encodings:
                face_encoding = encodings[0]
                break
            else:
                print("No face found, try another image.")

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
            face_locations = face_recognition.face_locations(frame)
            if face_locations:
                cv2.rectangle(
                    frame,
                    (face_locations[0][3], face_locations[0][0]),
                    (face_locations[0][1], face_locations[0][2]),
                    (0, 255, 0),
                    2,
                )
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
            if key == ord("s") and face_locations:
                face_encoding = face_recognition.face_encodings(frame, face_locations)[
                    0
                ]
                ret_enc, frame_enc = cv2.imencode(".jpg", frame)
                image_data = frame_enc.tobytes()
                break
            elif key == ord("q"):
                video_capture.release()
                cv2.destroyAllWindows()
                return False
        video_capture.release()
        cv2.destroyAllWindows()

    if face_encoding is not None:
        add_face_to_db(name, face_encoding, image_data)
        return True
    return False


# --- Main ---
known_names, known_face_encodings = get_known_faces_from_db()

while True:
    print("\n--- Menu ---")
    print("1. Add a new face")
    print("2. Start face recognition")
    print("q. Quit")
    choice = input("Enter your choice: ")

    if choice == "1":
        if handle_add_new_face():
            known_names, known_face_encodings = get_known_faces_from_db()
    elif choice == "2":
        if not known_face_encodings:
            print("Database is empty. Please add at least one face.")
        else:
            break
    elif choice == "q":
        sys.exit("Program terminated by user.")

# --- Face Recognition Loop ---
video_capture = choose_video_source()
if not video_capture.isOpened():
    sys.exit("Error: Could not open video source.")

process_this_frame = True
while True:
    ret, frame = video_capture.read()
    if not ret:
        break
    if process_this_frame:
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations
        )
    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4
        name = "Unknown Person"
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        if True in matches:
            first_match_index = matches.index(True)
            name = known_names[first_match_index]
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.rectangle(
            frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED
        )
        cv2.putText(
            frame,
            name,
            (left + 6, bottom - 6),
            cv2.FONT_HERSHEY_DUPLEX,
            1.0,
            (255, 255, 255),
            1,
        )
    process_this_frame = not process_this_frame
    cv2.imshow("Video", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
