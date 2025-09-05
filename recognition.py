import cv2
import face_recognition
import os

# Create a path to the directory containing your script and image
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to your known face image
known_image_path = os.path.join(script_dir, "my_face.jpg")

# Load the known face image and get its face encoding
print("Loading known face image...")
try:
    known_image = face_recognition.load_image_file(known_image_path)
    known_face_encoding = face_recognition.face_encodings(known_image)[0]
    known_face_encodings = [known_face_encoding]
    print("Known face encoding created.")
except IndexError:
    print(
        f"Error: No face found in {known_image_path}. Please ensure a clear face is visible."
    )
    exit()
except FileNotFoundError:
    print(
        f"Error: The file '{known_image_path}' was not found. Please ensure it's in the same directory as the script."
    )
    exit()

# Open webcam
video_capture = cv2.VideoCapture(0)

print("Press 'q' to quit.")

while True:
    # Grab a single frame of video
    ret, frame = video_capture.read()

    # Check if the frame was captured successfully
    if not ret:
        print("Error: Could not read frame from webcam.")
        break

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    # Loop through each face found in the frame
    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):

        # Compare the current face encoding with the known face encoding
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

        name = "Unknown Person"

        # If a match is found, use the known person's name
        if True in matches:
            name = "FA22-BCS-093"  # You can replace this with your name

        # Draw a box around the face
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

        # Draw a label with a name below the face
        cv2.rectangle(
            frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED
        )
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

    # Display the resulting image
    cv2.imshow("Video", frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Release handle to the webcam
video_capture.release()
cv2.destroyAllWindows()
