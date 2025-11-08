import mysql.connector
import io
import numpy as np
from datetime import datetime

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}


# ============================================
# LEGACY FUNCTIONS (Original System)
# ============================================


def get_known_faces_from_db():
    """Fetch all students and average their embeddings."""
    known_names, known_encodings, known_rollnumbers = [], [], []
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        query = """
            SELECT s.rollnumber, s.name, sp.encoding 
            FROM students s
            JOIN student_photos sp ON s.rollnumber = sp.rollnumber
            WHERE s.is_active = 1
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
            known_rollnumbers.append(rollnumber)

        print(f"Found {len(student_embeddings)} student(s) in the database.")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
    return known_names, known_encodings, known_rollnumbers


def list_students():
    """List all students with roll numbers."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute(
            """
            SELECT rollnumber, name, department, batch 
            FROM students 
            WHERE is_active = 1
            ORDER BY name
        """
        )
        results = cursor.fetchall()
        if not results:
            print("No students found in the database.")
        else:
            print("\n--- Student Records ---")
            for roll, name, dept, batch in results:
                dept_str = f" | Dept: {dept}" if dept else ""
                batch_str = f" | Batch: {batch}" if batch else ""
                print(f"Roll No: {roll} | Name: {name}{dept_str}{batch_str}")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def add_face_to_db(name, embedding, image_data, rollnumber=None):
    """Add student + embedding to DB using provided roll number and name."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        # Insert student if not exists
        cursor.execute(
            "SELECT rollnumber FROM students WHERE rollnumber = %s", (rollnumber,)
        )
        result = cursor.fetchone()
        if not result:
            cursor.execute(
                "INSERT INTO students (rollnumber, name, is_active) VALUES (%s, %s, 1)",
                (rollnumber, name),
            )

        bio_enc = io.BytesIO()
        np.save(bio_enc, embedding)
        encoding_blob = bio_enc.getvalue()

        sql = """
            INSERT INTO student_photos 
            (rollnumber, image, encoding, photo_type) 
            VALUES (%s, %s, %s, 'enrollment')
        """
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


# ============================================
# CLASS MANAGEMENT FUNCTIONS
# ============================================


def list_classes():
    """List all active classes."""
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, class_name, course_code, instructor, department, semester
            FROM classes
            WHERE is_active = 1
            ORDER BY class_name
        """
        )

        classes = cursor.fetchall()

        if not classes:
            print("No classes found in the database.")
            return []
        else:
            print("\n--- Available Classes ---")
            for cls in classes:
                print(f"ID: {cls['id']} | {cls['class_name']} ({cls['course_code']})")
                if cls["instructor"]:
                    print(f"  Instructor: {cls['instructor']}")
                if cls["department"]:
                    print(
                        f"  Department: {cls['department']} | Semester: {cls['semester']}"
                    )
            return classes

    except mysql.connector.Error as err:
        print(f"✗ Error loading classes: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def create_class(
    class_name, course_code, department, batch, semester=None, instructor=None
):
    """
    Create a new class.

    Args:
        class_name: Name of the class
        course_code: Course code (e.g., CS-301)
        department: Department name
        batch: Student batch year (e.g., 2022)
        semester: Semester (optional)
        instructor: Instructor name (optional)

    Returns:
        class_id if successful, None otherwise
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            INSERT INTO classes 
            (class_name, course_code, department, semester, instructor, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)
        """,
            (class_name, course_code, department, semester, instructor),
        )

        class_id = cursor.lastrowid
        db_connection.commit()

        print(f"\n✓ Class created successfully!")
        print(f"  Class ID: {class_id}")
        print(f"  Name: {class_name}")
        print(f"  Code: {course_code}")

        return class_id

    except mysql.connector.Error as err:
        print(f"✗ Error creating class: {err}")
        return None
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


# ============================================
# STUDENT ENROLLMENT FUNCTIONS
# ============================================


def get_eligible_students_for_class(department, batch):
    """
    Get students eligible for enrollment based on department and batch.

    Args:
        department: Department name
        batch: Student batch year

    Returns:
        List of eligible students with their details
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT 
                s.rollnumber,
                s.name,
                s.email,
                s.department,
                s.batch,
                COUNT(sp.id) as photo_count
            FROM students s
            LEFT JOIN student_photos sp ON s.rollnumber = sp.rollnumber
            WHERE s.department = %s
            AND s.batch = %s
            AND s.is_active = 1
            GROUP BY s.rollnumber, s.name, s.email, s.department, s.batch
            HAVING photo_count > 0
            ORDER BY s.name
        """,
            (department, batch),
        )

        students = cursor.fetchall()

        print(f"\n📋 Found {len(students)} eligible students")
        print(f"   Department: {department}")
        print(f"   Batch: {batch}")

        return students

    except mysql.connector.Error as err:
        print(f"✗ Error fetching eligible students: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def enroll_student_in_class(class_id, rollnumber):
    """
    Enroll a single student in a class.

    Args:
        class_id: Class ID
        rollnumber: Student roll number

    Returns:
        True if successful, False otherwise
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        # Check if already enrolled
        cursor.execute(
            """
            SELECT id FROM class_students 
            WHERE class_id = %s AND rollnumber = %s
        """,
            (class_id, rollnumber),
        )

        if cursor.fetchone():
            return False  # Already enrolled

        # Enroll student
        cursor.execute(
            """
            INSERT INTO class_students (class_id, rollnumber)
            VALUES (%s, %s)
        """,
            (class_id, rollnumber),
        )

        db_connection.commit()
        return True

    except mysql.connector.Error as err:
        print(f"✗ Error enrolling student: {err}")
        return False
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def bulk_enroll_students_in_class(class_id, rollnumbers):
    """
    Enroll multiple students in a class.

    Args:
        class_id: The class ID
        rollnumbers: List of roll numbers to enroll

    Returns:
        Number of students enrolled
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        enrolled_count = 0
        skipped_count = 0

        for rollnumber in rollnumbers:
            try:
                cursor.execute(
                    """
                    INSERT INTO class_students (class_id, rollnumber)
                    VALUES (%s, %s)
                """,
                    (class_id, rollnumber),
                )
                enrolled_count += 1
            except mysql.connector.IntegrityError:
                # Already enrolled, skip
                skipped_count += 1

        db_connection.commit()

        print(f"\n✓ Enrollment complete!")
        print(f"  Enrolled: {enrolled_count} students")
        if skipped_count > 0:
            print(f"  Skipped (already enrolled): {skipped_count}")

        return enrolled_count

    except mysql.connector.Error as err:
        print(f"✗ Error during bulk enrollment: {err}")
        db_connection.rollback()
        return 0
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def list_class_enrollments(class_id):
    """
    List all students enrolled in a specific class.

    Args:
        class_id: Class ID

    Returns:
        List of enrolled students
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        # Get class info
        cursor.execute(
            """
            SELECT class_name, course_code
            FROM classes
            WHERE id = %s
        """,
            (class_id,),
        )

        class_info = cursor.fetchone()
        if not class_info:
            print(f"✗ Class ID {class_id} not found")
            return []

        # Get enrollments
        cursor.execute(
            """
            SELECT 
                s.rollnumber,
                s.name,
                s.department,
                s.batch,
                cs.enrollment_date,
                COUNT(sp.id) as photo_count
            FROM class_students cs
            JOIN students s ON cs.rollnumber = s.rollnumber
            LEFT JOIN student_photos sp ON s.rollnumber = sp.rollnumber
            WHERE cs.class_id = %s
            GROUP BY s.rollnumber, s.name, s.department, s.batch, cs.enrollment_date
            ORDER BY s.name
        """,
            (class_id,),
        )

        enrollments = cursor.fetchall()

        print(
            f"\n--- Enrollments for {class_info['class_name']} ({class_info['course_code']}) ---"
        )

        if not enrollments:
            print("⚠️  No students enrolled yet")
        else:
            print(f"Total: {len(enrollments)} students\n")
            for idx, student in enumerate(enrollments, 1):
                print(f"{idx:2d}. {student['name']:30s} ({student['rollnumber']})")
                print(
                    f"    {student['department']}, Batch {student['batch']}, {student['photo_count']} photos"
                )

        return enrollments

    except mysql.connector.Error as err:
        print(f"✗ Error listing enrollments: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def remove_student_from_class(class_id, rollnumber):
    """
    Remove a student from a class.

    Args:
        class_id: Class ID
        rollnumber: Student roll number

    Returns:
        True if successful, False otherwise
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            DELETE FROM class_students
            WHERE class_id = %s AND rollnumber = %s
        """,
            (class_id, rollnumber),
        )

        if cursor.rowcount > 0:
            db_connection.commit()
            print(f"✓ Student {rollnumber} removed from class")
            return True
        else:
            print(f"⚠️  Student {rollnumber} not found in this class")
            return False

    except mysql.connector.Error as err:
        print(f"✗ Error removing student: {err}")
        return False
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


# ============================================
# TIMER-BASED ATTENDANCE FUNCTIONS
# ============================================


def get_class_roster(class_id):
    """
    Get all enrolled students for a class.

    Args:
        class_id: Class ID

    Returns:
        List of dicts with student info
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT s.rollnumber, s.name, s.department, s.batch
            FROM class_students cs
            JOIN students s ON cs.rollnumber = s.rollnumber
            WHERE cs.class_id = %s AND s.is_active = 1
            ORDER BY s.name
        """,
            (class_id,),
        )

        roster = cursor.fetchall()
        print(f"📋 Loaded roster: {len(roster)} students")
        return roster

    except mysql.connector.Error as err:
        print(f"✗ Error loading roster: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def create_timer_session(
    class_id,
    duration_seconds,
    late_threshold_seconds,
    min_presence_percent=0.80,
    marked_by=None,
):
    """
    Start a new timer-based attendance session.

    Args:
        class_id: Which class this session is for
        duration_seconds: Total timer duration (60 for test, 5400 for 90min class)
        late_threshold_seconds: Grace period before "late" (15 for test, 300 for 5min)
        min_presence_percent: Minimum presence required (0.80 = 80%)
        marked_by: User ID of teacher starting session

    Returns:
        session_id if successful, None otherwise
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            INSERT INTO attendance_sessions 
            (class_id, session_date, start_time, actual_start_time,
             duration_seconds, late_threshold_seconds, min_presence_percent,
             marked_by, status)
            VALUES (%s, CURDATE(), CURTIME(), NOW(), %s, %s, %s, %s, 'ongoing')
        """,
            (
                class_id,
                duration_seconds,
                late_threshold_seconds,
                min_presence_percent,
                marked_by,
            ),
        )

        session_id = cursor.lastrowid
        db_connection.commit()

        print(f"✓ Session {session_id} started")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Late threshold: {late_threshold_seconds}s")
        print(f"  Minimum presence: {min_presence_percent*100}%")

        return session_id

    except mysql.connector.Error as err:
        print(f"✗ Error creating session: {err}")
        return None
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def log_detection_event(session_id, rollnumber, detected_at_seconds, confidence_score):
    """
    Log a single face detection event during active session.
    Does NOT commit attendance yet - just logs for batch processing.

    Args:
        session_id: Active session ID
        rollnumber: Student roll number
        detected_at_seconds: Seconds elapsed since session start
        confidence_score: ArcFace similarity score
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            INSERT INTO detection_events 
            (session_id, rollnumber, detected_at_seconds, confidence_score)
            VALUES (%s, %s, %s, %s)
        """,
            (session_id, rollnumber, detected_at_seconds, confidence_score),
        )

        db_connection.commit()

    except mysql.connector.Error as err:
        print(f"✗ Error logging detection: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def log_camera_downtime(session_id, downtime_seconds):
    """
    Record camera failure time to adjust presence requirements.

    Args:
        session_id: Active session ID
        downtime_seconds: Total seconds camera was down
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            UPDATE attendance_sessions
            SET camera_downtime_seconds = camera_downtime_seconds + %s
            WHERE id = %s
        """,
            (downtime_seconds, session_id),
        )

        db_connection.commit()
        print(f"⚠️  Camera downtime logged: +{downtime_seconds}s")

    except mysql.connector.Error as err:
        print(f"✗ Error logging downtime: {err}")
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def finalize_session_attendance(session_id, user_id=None):
    """
    Process all detection events and commit final attendance records.
    Deletes detection_events after processing.

    Args:
        session_id: Session to finalize
        user_id: User finalizing the session

    Returns:
        Dict with attendance summary
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        # Call stored procedure to batch process
        cursor.callproc("sp_finalize_session_attendance", [session_id, user_id])

        # Get results
        for result in cursor.stored_results():
            summary = result.fetchone()

        db_connection.commit()

        print("\n" + "=" * 60)
        print("SESSION FINALIZED")
        print("=" * 60)
        print(f"✓ Present: {summary['total_present']}")
        print(f"⚠️  Late: {summary['total_late']}")
        print(f"✗ Absent: {summary['total_absent']}")
        print(f"⏰ Early Departure: {summary['total_early_departure']}")
        print(f"⚠️  Insufficient: {summary['total_insufficient']}")
        print(f"Total Students: {summary['total_students']}")
        print("=" * 60)

        return summary

    except mysql.connector.Error as err:
        print(f"✗ Error finalizing session: {err}")
        return None
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def get_session_info(session_id):
    """
    Get information about a specific session.

    Args:
        session_id: Session ID

    Returns:
        Dict with session info or None
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT 
                asess.id,
                asess.class_id,
                c.class_name,
                c.course_code,
                asess.duration_seconds,
                asess.late_threshold_seconds,
                asess.min_presence_percent,
                asess.actual_start_time,
                asess.actual_end_time,
                asess.status
            FROM attendance_sessions asess
            JOIN classes c ON asess.class_id = c.id
            WHERE asess.id = %s
        """,
            (session_id,),
        )

        session = cursor.fetchone()
        return session

    except mysql.connector.Error as err:
        print(f"✗ Error getting session info: {err}")
        return None
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def get_detection_count(session_id):
    """
    Get count of detection events for a session.

    Args:
        session_id: Session ID

    Returns:
        Number of detection events logged
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM detection_events 
            WHERE session_id = %s
        """,
            (session_id,),
        )

        count = cursor.fetchone()[0]
        return count

    except mysql.connector.Error as err:
        print(f"✗ Error getting detection count: {err}")
        return 0
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()


def get_detected_students(session_id):
    """
    Get list of unique students detected during a session.

    Args:
        session_id: Session ID

    Returns:
        List of roll numbers
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        cursor.execute(
            """
            SELECT DISTINCT rollnumber 
            FROM detection_events 
            WHERE session_id = %s
        """,
            (session_id,),
        )

        results = cursor.fetchall()
        return [row[0] for row in results]

    except mysql.connector.Error as err:
        print(f"✗ Error getting detected students: {err}")
        return []
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
