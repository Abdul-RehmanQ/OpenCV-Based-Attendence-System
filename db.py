import mysql.connector
import io
import numpy as np

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default XAMPP password is an empty string
    "database": "project",
}


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
