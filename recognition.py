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
    """
    Fetches all names and face encodings from the database.
    Returns a tuple of two lists: known_names and known_encodings.
    """
    known_names = []
    known_encodings = []

    try:
        # Connect to the database
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        print("Connected to the database successfully.")

        # Execute the query to get names and encodings
        cursor.execute("SELECT name, encoding FROM known_faces")

        # Fetch all results
        results = cursor.fetchall()
        print(f"Found {len(results)} known faces in the database.")

        # Process the results
        for row in results:
            name, encoding_blob = row
            # Convert the BLOB (bytes) back to a numpy array
            encoding_array = np.load(io.BytesIO(encoding_blob))
            known_names.append(name)
            known_encodings.append(encoding_array)

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        # Close the connection
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()

    return known_names, known_encodings


def add_face_to_db(name, encoding, image_data):
    """
    Adds a new name, face encoding, and image to the database.
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        # Convert the numpy array encoding to bytes for storage
        bio_enc = io.BytesIO()
        np.save(bio_enc, encoding)
        encoding_blob = bio_enc.getvalue()

        # The image_data is already in bytes
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


def handle_add_new_face():
    """
    Handles the user interaction for adding a new face,
    including capturing from a webcam or uploading a file.
    """
    # Get user input for new face
    name = input("Enter the name of the person you want to add: ")

    # Get user choice for image source
    while True:
        source_choice = input(
            "Choose a method to get the image: [1] Upload from file, [2] Take a picture now: "
        )
        if source_choice in ("1", "2"):
            break
        else:
            print("Invalid choice. Please enter '1' or '2'.")

    face_encoding = None
    image_data = None

    if source_choice == "1":
        while True:
            image_path = input("Enter the full path to the image file: ")
            if not os.path.exists(image_path):
                print(
                    f"Error: The file '{image_path}' was not found. Please try again."
                )
                continue
            try:
                print("Loading image...")
                # Read the image as binary data
                with open(image_path, "rb") as f:
                    image_data = f.read()

                known_image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(known_image)
                if not encodings:
                    print(
                        "Error: No face found in the image. Please try another image."
                    )
                else:
                    face_encoding = encodings[0]
                    break
            except Exception as e:
                print(f"An error occurred: {e}")

    elif source_choice == "2":
        print(
            "\nOpening webcam. Please look at the camera and press 's' to capture your face."
        )
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            print("Error: Could not open webcam.")
            return False

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Error: Could not read frame from webcam.")
                break

            # Find faces in the current frame
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
                    (face_locations[0][3], face_locations[0][0] - 10),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.5,
                    (0, 255, 0),
                    1,
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
            if key == ord("s"):
                if face_locations:
                    print("Capturing face...")
                    face_encoding = face_recognition.face_encodings(
                        frame, face_locations
                    )[0]
                    # Convert the frame to a binary format (JPEG) for storage
                    ret_enc, frame_enc = cv2.imencode(".jpg", frame)
                    image_data = frame_enc.tobytes()
                    video_capture.release()
                    cv2.destroyAllWindows()
                    break
                else:
                    print("No face detected. Please try again.")
            elif key == ord("q"):
                print("Capture cancelled.")
                video_capture.release()
                cv2.destroyAllWindows()
                return False

    if face_encoding is not None:
        add_face_to_db(name, face_encoding, image_data)
        return True
    return False


# --- Main Program Logic ---
known_names, known_face_encodings = get_known_faces_from_db()

# Main menu loop
while True:
    print("\n--- Menu ---")
    print("1. Add a new face")
    print("2. Start face recognition")
    print("q. Quit")

    choice = input("Enter your choice: ")

    if choice == "1":
        if handle_add_new_face():
            # Reload faces from the database to include the new one
            known_names, known_face_encodings = get_known_faces_from_db()
    elif choice == "2":
        if not known_face_encodings:
            print(
                "Database is empty. Please add at least one face before starting recognition."
            )
        else:
            break  # Break out of the menu loop to start the recognition loop
    elif choice == "q":
        sys.exit("Program terminated by user.")
    else:
        print("Invalid choice. Please try again.")

# --- Face Recognition Loop ---
print("\nStarting face recognition. Press 'q' to quit.")
video_capture = cv2.VideoCapture(0)

if not video_capture.isOpened():
    sys.exit("Error: Could not open webcam.")

# Initialize variables for performance optimization
process_this_frame = True

while True:
    ret, frame = video_capture.read()
    if not ret:
        print("Error: Could not read frame from webcam.")
        break

    # Resize frame for faster face recognition processing
    if process_this_frame:
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations
        )

    # Display the results
    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):
        # Scale back up face locations since the frame we detected in was scaled
        top *= 4
        right *= 4
        bottom *= 4
        left *= 4

        name = "Unknown Person"
        # Compare current face with known faces
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

        # Find the best match
        if True in matches:
            first_match_index = matches.index(True)
            name = known_names[first_match_index]

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
        cv2.rectangle(
            frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED
        )
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Toggle the frame processing flag
    process_this_frame = not process_this_frame

    # Display the resulting image
    cv2.imshow("Video", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
