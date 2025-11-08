import cv2
import face_recognition
import mysql.connector
import os
import io
import numpy as np
import sys
import time

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}

# --- Recognition Threshold ---
# Lower values mean a stricter match is required.
# Adjust this value to improve accuracy. A good starting range is 0.4 to 0.6.
RECOGNITION_THRESHOLD = 0.6


def get_known_faces_from_db():
    """
    Fetches all students and their face encodings from the database.
    Groups multiple encodings under the same student.
    """
    known_names = []
    known_encodings = []
    unique_students = set()
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

        for row in results:
            rollnumber, name, encoding_blob = row
            encoding_array = np.load(io.BytesIO(encoding_blob))
            known_encodings.append(encoding_array)
            known_names.append(name)
            unique_students.add(rollnumber)

        print(f"Found records of {len(unique_students)} student(s) in the database.")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()

    return known_names, known_encodings


def add_face_to_db(name, encoding, image_data):
    """
    Adds a new student (if not exists), face encoding, and image to the database.
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

        # Convert encoding to blob
        bio_enc = io.BytesIO()
        np.save(bio_enc, encoding)
        encoding_blob = bio_enc.getvalue()

        # Save photo + encoding
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


def list_students():
    """
    Fetches and displays all students with rollnumbers.
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute("SELECT rollnumber, name FROM students")
        students = cursor.fetchall()
        if not students:
            print("No students found in the database.")
            return []
        print("\n--- Student Records ---")
        for roll, name in students:
            print(f"Roll No: {roll} | Name: {name}")
        return students
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def add_images_for_existing_student(rollnumber):
    """
    Adds new images/encodings for an existing student.
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM students WHERE rollnumber = %s", (rollnumber,))
        student = cursor.fetchone()
        if not student:
            print("No student found with that rollnumber.")
            return False
        name = student[0]

        print(f"Adding new images for {name} (Roll No: {rollnumber})")

        while True:
            source_choice = input(
                "Choose method: [1] Upload file, [2] Webcam, [q] Quit: "
            )
            if source_choice == "q":
                break

            face_encoding = None
            image_data = None

            if source_choice == "1":
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
                else:
                    print("No face found, try another image.")
                    continue

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
                        face_encoding = face_recognition.face_encodings(
                            frame, face_locations
                        )[0]
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
                bio_enc = io.BytesIO()
                np.save(bio_enc, face_encoding)
                encoding_blob = bio_enc.getvalue()
                sql = "INSERT INTO student_photos (rollnumber, image, encoding) VALUES (%s, %s, %s)"
                cursor.execute(sql, (rollnumber, image_data, encoding_blob))
                db_connection.commit()
                print(f"New image added for {name} (Roll No: {rollnumber})")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
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


def handle_add_new_face():
    """
    Guides the user through adding a new face to the database.
    """
    name = input("Enter the name of the student you want to add: ")
    while True:
        source_choice = input("Choose method: [1] Upload file, [2] Webcam: ")
        if source_choice in ("1", "2"):
            break

    face_encoding = None
    image_data = None

    adding_more_faces = True
    while adding_more_faces:
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
                    face_encoding = face_recognition.face_encodings(
                        frame, face_locations
                    )[0]
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
    print("3. Add images for an existing student")
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
    elif choice == "3":
        students = list_students()
        if students:
            roll = input("Enter the rollnumber of the student: ")
            add_images_for_existing_student(roll)
            known_names, known_face_encodings = get_known_faces_from_db()
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

    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        name = "Unknown Student"

        face_distances = face_recognition.face_distance(
            known_face_encodings, face_encoding
        )
        best_match_index = np.argmin(face_distances)

        if face_distances[best_match_index] < RECOGNITION_THRESHOLD:
            name = known_names[best_match_index]
            color = (0, 255, 0)
        else:
            color = (0, 0, 255)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
        cv2.putText(
            frame,
            name,
            (left + 6, bottom - 6),
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
