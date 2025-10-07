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


def mark_attendance_automatic(rollnumber, name, confidence_score, session_id=None):
    """
    Automatically mark attendance via face recognition.
    Called by main.py recognition loop.

    Args:
        rollnumber: Student roll number
        name: Student name
        confidence_score: ArcFace similarity score
        session_id: Specific class session ID (optional)

    Returns:
        True if marked successfully, False if duplicate
    """
    try:
        db_connection = mysql.connector.connect(**DB_CONFIG)
        cursor = db_connection.cursor()

        current_date = datetime.now().date()
        current_time = datetime.now()

        # Check if already marked for THIS SPECIFIC SESSION
        # This allows multiple classes per day!
        if session_id:
            cursor.execute(
                """
                SELECT id FROM attendance 
                WHERE rollnumber = %s AND session_id = %s
            """,
                (rollnumber, session_id),
            )

            if cursor.fetchone():
                print(f"⚠️  {name} already marked for this class session")
                return False
        else:
            # If no session_id provided, prevent duplicate within last 5 minutes
            # (In case you're running without sessions)
            cursor.execute(
                """
                SELECT id FROM attendance 
                WHERE rollnumber = %s 
                AND timestamp >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            """,
                (rollnumber,),
            )

            if cursor.fetchone():
                print(f"⚠️  {name} marked recently (within 5 minutes)")
                return False

        # Insert attendance record
        cursor.execute(
            """
            INSERT INTO attendance 
            (session_id, rollnumber, student_name, confidence_score, 
             timestamp, date, status, marked_by_system)
            VALUES (%s, %s, %s, %s, %s, %s, 'present', 1)
        """,
            (
                session_id,
                rollnumber,
                name,
                float(confidence_score),
                current_time,
                current_date,
            ),
        )

        db_connection.commit()
        print(f"✓ Attendance marked for {name} (confidence: {confidence_score:.3f})")
        return True

    except mysql.connector.Error as err:
        print(f"❌ Error marking attendance: {err}")
        db_connection.rollback()
        return False
    finally:
        if "db_connection" in locals() and db_connection.is_connected():
            cursor.close()
            db_connection.close()
