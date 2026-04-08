import cv2
import os
import numpy as np
import sys
import time
import insightface
import requests
from datetime import datetime

# --- Import local storage functions ---
from storage import (
    # Student management
    get_known_faces_from_db,
    list_students,
    add_face_to_db,
    get_photo_count,
    # Class management
    list_classes,
    create_class,
    # Enrollment management
    get_eligible_students_for_class,
    enroll_student_in_class,
    bulk_enroll_students_in_class,
    list_class_enrollments,
    remove_student_from_class,
    # Timer-based attendance
    create_timer_session,
    log_detection_event,
    finalize_session_attendance,
    get_class_roster,
    get_detected_students,
    get_class_by_id,
)

# --- Recognition Threshold for ArcFace (cosine similarity) ---
RECOGNITION_THRESHOLD = 0.6

# --- Maximum photos per student ---
MAX_PHOTOS_PER_STUDENT = 5

# --- Load RetinaFace + ArcFace Model ---
print("Loading RetinaFace + ArcFace model...")
app = insightface.app.FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("Model loaded successfully.")


# ============================================
# UTILITY FUNCTIONS
# ============================================


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


def parse_selection(selection_str):
    """
    Parse selection like "1,3,5-10,15" into list of indices.
    Returns: [1, 3, 5, 6, 7, 8, 9, 10, 15]
    """
    indices = set()
    parts = selection_str.replace(" ", "").split(",")

    for part in parts:
        if "-" in part:
            try:
                start, end = part.split("-")
                indices.update(range(int(start), int(end) + 1))
            except ValueError:
                continue
        else:
            try:
                indices.add(int(part))
            except ValueError:
                continue

    return sorted(indices)


# ============================================
# ENROLLMENT FUNCTIONS
# ============================================


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


# ============================================
# CLASS MANAGEMENT FUNCTIONS
# ============================================


def handle_create_class():
    """Interactive class creation."""
    print("\n--- Create New Class ---")

    class_name = input("Class name (e.g., Database Systems): ").strip()
    if not class_name:
        print("Class name cannot be empty.")
        return False

    course_code = input("Course code (e.g., CS-301): ").strip()
    if not course_code:
        print("Course code cannot be empty.")
        return False

    department = input("Department (e.g., Computer Science): ").strip()
    if not department:
        print("Department cannot be empty.")
        return False

    batch = input("Target batch/year (e.g., 2022): ").strip()
    if not batch:
        print("Batch cannot be empty.")
        return False

    semester = input("Semester (optional, e.g., Fall 2025): ").strip()
    instructor = input("Instructor name (optional): ").strip()

    # Create class
    class_id = create_class(
        class_name=class_name,
        course_code=course_code,
        department=department,
        batch=batch,
        semester=semester if semester else None,
        instructor=instructor if instructor else None,
    )

    if class_id:
        # Ask if teacher wants to enroll students now
        enroll_now = input("\nEnroll students now? (y/n): ").strip().lower()
        if enroll_now == "y":
            handle_enroll_students_in_class(class_id, department, batch)
        return True

    return False


def handle_enroll_students_in_class(class_id=None, department=None, batch=None):
    """Interactive student enrollment for a class."""

    # If class_id not provided, ask user to select
    if class_id is None:
        classes = list_classes()
        if not classes:
            print("\n✗ No classes found. Create a class first.")
            return False

        class_id = input("\nEnter class ID to enroll students: ").strip()
        if not class_id.isdigit():
            print("Invalid class ID.")
            return False
        class_id = int(class_id)

    # Get class info if department/batch not provided
    if department is None or batch is None:
        class_info = get_class_by_id(class_id)
        if not class_info:
            print(f"✗ Class ID {class_id} not found")
            return False

        print(
            f"\n--- Enrolling Students in {class_info['class_name']} ({class_info['course_code']}) ---"
        )

        if department is None:
            department = class_info.get("department")

        if batch is None:
            batch = class_info.get("batch")
            if not batch:
                batch = input("Enter target batch (e.g., 2022): ").strip()

        if not department:
            department = input("Enter target department: ").strip()

    # Get eligible students
    eligible = get_eligible_students_for_class(department, batch)

    if not eligible:
        print("\n✗ No eligible students found.")
        print("   Students must:")
        print("   1. Be in the specified department and batch")
        print("   2. Have face photos enrolled")
        print("   3. Be active")
        return False

    # Display list
    print("\n" + "=" * 70)
    print("ELIGIBLE STUDENTS")
    print("=" * 70)

    for idx, student in enumerate(eligible, 1):
        print(f"{idx:2d}. {student['name']:30s} ({student['rollnumber']})")
        print(
            f"    {student['department']}, Batch {student['batch']}, {student['photo_count']} photos"
        )

    print("=" * 70)

    # Get teacher's selection
    print("\nEnrollment Options:")
    print("1. Enroll all students")
    print("2. Select specific students (e.g., 1,3,5-10,15)")
    print("3. Cancel")

    choice = input("\nEnter choice: ").strip()

    if choice == "1":
        # Enroll all
        rollnumbers = [s["rollnumber"] for s in eligible]
        bulk_enroll_students_in_class(class_id, rollnumbers)
        return True

    elif choice == "2":
        # Select specific
        selection = input("Enter student numbers (e.g., 1,3,5-10,15): ").strip()

        # Parse selection
        selected_indices = parse_selection(selection)
        rollnumbers = [
            eligible[i - 1]["rollnumber"]
            for i in selected_indices
            if 0 < i <= len(eligible)
        ]

        if rollnumbers:
            bulk_enroll_students_in_class(class_id, rollnumbers)
            return True
        else:
            print("✗ No valid students selected.")
            return False

    else:
        print("Enrollment cancelled.")
        return False


def handle_view_class_enrollments():
    """View students enrolled in a class."""
    classes = list_classes()
    if not classes:
        print("\n✗ No classes found.")
        return

    class_id = input("\nEnter class ID to view enrollments: ").strip()
    if not class_id.isdigit():
        print("Invalid class ID.")
        return

    enrollments = list_class_enrollments(int(class_id))

    if enrollments:
        # Ask if teacher wants to remove any student
        remove = input("\nRemove a student? (y/n): ").strip().lower()
        if remove == "y":
            rollnumber = input("Enter roll number to remove: ").strip()
            remove_student_from_class(int(class_id), rollnumber)


# ============================================
# TIMER-BASED ATTENDANCE SYSTEM
# ============================================


def start_timer_based_attendance():
    """
    Timer-based attendance system.
    Teacher starts session, system logs detections, finalizes at end.
    """
    # Step 1: Show available classes
    classes = list_classes()
    if not classes:
        print("\n✗ No classes found. Please create a class first.")
        return

    # Step 2: Get class selection
    print("\n")
    class_id = input("Enter class ID: ").strip()
    if not class_id.isdigit():
        print("Invalid class ID.")
        return
    class_id = int(class_id)

    # Step 3: Get timer settings
    print("\n--- Timer Settings ---")
    print("Recommended for testing: 60 seconds duration, 15 seconds late threshold")
    print("Recommended for real class: 5400 seconds (90 min), 300 seconds (5 min)")

    duration_input = input("\nEnter timer duration in seconds (default 60): ").strip()
    duration_seconds = int(duration_input) if duration_input else 60

    late_threshold_input = input(
        "Enter late threshold in seconds (default 15): "
    ).strip()
    late_threshold = int(late_threshold_input) if late_threshold_input else 15

    # Step 4: Load roster
    print("\n🔄 Loading class roster...")
    roster = get_class_roster(class_id)
    if not roster:
        print("\n✗ No students enrolled in this class!")
        print("   Go to menu option 5 to enroll students first.")
        return

    print(f"\n✓ Loaded {len(roster)} students:")
    for student in roster:
        print(f"  - {student['name']} ({student['rollnumber']})")

    # Step 5: Load known faces
    print("\n🔄 Loading face recognition data...")
    known_names, known_face_encodings, known_rollnumbers = get_known_faces_from_db()
    if not known_face_encodings:
        print("✗ No student face data found. Enroll students first.")
        return

    # Step 6: Create session
    print("\n🔄 Creating attendance session...")
    session_id = create_timer_session(
        class_id=class_id,
        duration_seconds=duration_seconds,
        late_threshold_seconds=late_threshold,
        min_presence_percent=0.80,  # 80% rule
        marked_by=None,  # TODO: Add user_id when implementing login
    )

    if not session_id:
        print("✗ Failed to create session!")
        return

    # Step 7: Start video capture
    video_capture = choose_video_source()

    # Step 8: Display session info
    print("\n" + "=" * 70)
    print("TIMER-BASED ATTENDANCE SESSION STARTED")
    print("=" * 70)
    print(f"📋 Class ID: {class_id}")
    print(f"🆔 Session ID: {session_id}")
    print(f"⏱️  Duration: {duration_seconds}s ({duration_seconds/60:.1f} minutes)")
    print(f"✓ On-time window: 0-{late_threshold}s")
    print(f"⚠️  Late if arrives after: {late_threshold}s")
    print(f"📊 Minimum presence required: 80% ({int(duration_seconds*0.8)}s)")
    print(f"👥 Expected students: {len(roster)}")
    print("=" * 70)
    print("\n⌨️  Press 'q' to stop early and finalize attendance")
    print("⌨️  Press 'd' to see detection stats\n")

    # Step 9: Run detection loop
    session_start_time = time.time()
    detection_log = {}  # Track who we've seen {rollnumber: last_logged_time}
    frame_count = 0

    try:
        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("⚠️  Failed to read frame from camera")
                time.sleep(0.1)
                continue

            current_time = time.time()
            elapsed_seconds = int(current_time - session_start_time)
            frame_count += 1

            # Check if timer expired
            if elapsed_seconds >= duration_seconds:
                print(f"\n⏰ Timer completed ({duration_seconds}s)")
                break

            # Detect faces (process every frame for smooth display)
            faces = app.get(frame)

            for face in faces:
                embedding = face.embedding
                (x1, y1, x2, y2) = face.bbox.astype(int)

                name = "Unknown"
                rollnumber = None
                confidence = 0

                if known_face_encodings:
                    # Find best match
                    sims = [
                        cosine_similarity(embedding, enc)
                        for enc in known_face_encodings
                    ]
                    best_match_index = np.argmax(sims)
                    confidence = sims[best_match_index]

                    if confidence > RECOGNITION_THRESHOLD:
                        name = known_names[best_match_index]
                        rollnumber = known_rollnumbers[best_match_index]

                        # Log detection every second (avoid spam)
                        last_log = detection_log.get(rollnumber, 0)
                        if current_time - last_log >= 1.0:
                            log_detection_event(
                                session_id=session_id,
                                rollnumber=rollnumber,
                                detected_at_seconds=elapsed_seconds,
                                confidence_score=confidence,
                            )
                            detection_log[rollnumber] = current_time
                            print(
                                f"✓ Logged: {name} at {elapsed_seconds}s (confidence: {confidence:.3f})"
                            )

                        # Visual feedback - green for recognized
                        color = (0, 255, 0)
                        status = f"DETECTED ({confidence:.2f})"
                    else:
                        # Low confidence - yellow
                        color = (0, 165, 255)
                        status = f"Low Conf ({confidence:.2f})"
                else:
                    # Unknown - red
                    color = (0, 0, 255)
                    status = "UNKNOWN"

                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Draw name/status
                cv2.putText(
                    frame,
                    f"{name}",
                    (x1, y1 - 30),
                    cv2.FONT_HERSHEY_DUPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                cv2.putText(
                    frame,
                    status,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

            # Display timer info on frame
            remaining = duration_seconds - elapsed_seconds
            minutes_remaining = remaining // 60
            seconds_remaining = remaining % 60

            # Timer display
            timer_text = f"Time: {minutes_remaining:02d}:{seconds_remaining:02d}"
            cv2.putText(
                frame,
                timer_text,
                (10, 40),
                cv2.FONT_HERSHEY_DUPLEX,
                1.2,
                (0, 255, 255),
                2,
            )

            # Detected count
            unique_detected = len(detection_log)
            detected_text = f"Detected: {unique_detected}/{len(roster)}"
            cv2.putText(
                frame,
                detected_text,
                (10, 80),
                cv2.FONT_HERSHEY_DUPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

            # Show frame
            cv2.imshow("Timer-Based Attendance System", frame)

            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print(f"\n⚠️  Timer stopped early at {elapsed_seconds}s")
                break
            elif key == ord("d"):
                # Show detection stats
                detected_students = get_detected_students(session_id)
                print(f"\n📊 Detection Stats:")
                print(f"   Unique students detected: {len(detected_students)}")
                print(f"   Expected students: {len(roster)}")
                if len(roster) > 0:
                    print(
                        f"   Detection rate: {len(detected_students)/len(roster)*100:.1f}%"
                    )

    except KeyboardInterrupt:
        print(f"\n⚠️  Session interrupted by user")

    finally:
        # Step 10: Cleanup
        video_capture.release()
        cv2.destroyAllWindows()

        # Step 11: Finalize attendance
        print("\n" + "=" * 70)
        print("🔄 FINALIZING ATTENDANCE...")
        print("=" * 70)
        print("Processing detection events and calculating attendance status...")

        summary = finalize_session_attendance(session_id, user_id=None)

        if summary:
            print("\n✅ Attendance session completed successfully!")
            print("\nAttendance records were saved to local storage.")
        else:
            print("\n✗ Error finalizing attendance. Check local storage data.")


# ============================================
# MAIN PROGRAM
# ============================================

# Load known faces on startup
known_names, known_face_encodings, known_rollnumbers = get_known_faces_from_db()

while True:
    print("\n" + "=" * 70)
    print("FACE RECOGNITION ATTENDANCE SYSTEM")
    print("=" * 70)
    print("1. Add a new student")
    print("2. Add images for existing student")
    print("3. List all students")
    print("4. Create a new class")
    print("5. Enroll students in a class")
    print("6. View class enrollments")
    print("7. Start Timer-Based Attendance")
    print("q. Quit")
    print("=" * 70)

    choice = input("Enter your choice: ").strip()

    if choice == "1":
        if handle_add_new_face():
            # Reload faces after adding new student
            known_names, known_face_encodings, known_rollnumbers = (
                get_known_faces_from_db()
            )

    elif choice == "2":
        if add_images_for_existing_student():
            # Reload faces after adding images
            known_names, known_face_encodings, known_rollnumbers = (
                get_known_faces_from_db()
            )

    elif choice == "3":
        list_students()

    elif choice == "4":
        if handle_create_class():
            # Reload data if needed
            known_names, known_face_encodings, known_rollnumbers = (
                get_known_faces_from_db()
            )

    elif choice == "5":
        handle_enroll_students_in_class()

    elif choice == "6":
        handle_view_class_enrollments()

    elif choice == "7":
        start_timer_based_attendance()

    elif choice.lower() == "q":
        print("\n👋 Thank you for using the attendance system!")
        sys.exit(0)

    else:
        print("\n❌ Invalid choice. Please try again.")
