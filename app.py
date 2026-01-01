import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()  # load .env if present

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev_secret_key")

# DB config from environment variables with defaults
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS"),
    "database": os.getenv("DB_NAME", "CollegeDB"),
    "raise_on_warnings": True,
    "autocommit": True,
}

# Use a connection pool
pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **DB_CONFIG)

def get_conn():
    return pool.get_connection()

# ---------- Routes ----------
@app.route("/")
def index():
    # simple dashboard counts
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Student")
    students = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Course")
    courses = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Enrollment")
    enrollments = cur.fetchone()[0]
    cur.close(); conn.close()
    return render_template("index.html", students=students, courses=courses, enrollments=enrollments)

# ---------------- Students ----------------
@app.route("/students")
def students():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Student ORDER BY student_id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("students.html", students=rows)

@app.route("/students/add", methods=["POST"])
def add_student():
    first = request.form.get("first_name")
    last = request.form.get("last_name")
    email = request.form.get("email")
    city = request.form.get("city")
    roll = request.form.get("roll_number")
    birth = request.form.get("birth_date") or None
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO Student (roll_number, first_name, last_name, birth_date, city, email) VALUES (%s,%s,%s,%s,%s,%s)",
            (roll, first, last, birth, city, email)
        )
        flash("Student added successfully.", "success")
    except mysql.connector.Error as e:
        flash(f"Error adding student: {e.msg}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("students"))

# ---------------- Courses ----------------
@app.route("/courses")
def courses():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Course ORDER BY course_id")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return render_template("courses.html", courses=rows)

@app.route("/courses/add", methods=["POST"])
def add_course():
    code = request.form.get("course_code")
    name = request.form.get("name")
    duration = request.form.get("duration_months") or 0
    fees = request.form.get("fees") or 0
    desc = request.form.get("description")
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO Course (course_code, name, duration_months, fees, description) VALUES (%s,%s,%s,%s,%s)",
            (code, name, duration, fees, desc)
        )
        flash("Course added.", "success")
    except mysql.connector.Error as e:
        flash(f"Error: {e.msg}", "danger")
    finally:
        cur.close(); conn.close()
    return redirect(url_for("courses"))

# ---------------- Enrollments ----------------
@app.route("/enroll", methods=["GET", "POST"])
def enroll():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        student_id = request.form.get("student_id")
        course_id = request.form.get("course_id")
        teacher_id = request.form.get("teacher_id") or None
        enroll_date = request.form.get("enroll_date") or None
        try:
            cur.execute(
                "INSERT INTO Enrollment (student_id, course_id, teacher_id, enroll_date, status, fee_paid) VALUES (%s,%s,%s,%s,'active',0)",
                (student_id, course_id, teacher_id, enroll_date)
            )
            flash("Enrollment added.", "success")
        except mysql.connector.Error as e:
            flash(f"Error: {e.msg}", "danger")
        cur.close(); conn.close()
        return redirect(url_for("enroll"))
    # GET: show students, courses, teachers
    cur.execute("SELECT student_id, CONCAT(first_name,' ',last_name) AS name FROM Student")
    students = cur.fetchall()
    cur.execute("SELECT course_id, name FROM Course")
    courses = cur.fetchall()
    cur.execute("SELECT teacher_id, name FROM Teacher")
    teachers = cur.fetchall()
    cur.close(); conn.close()
    return render_template("enroll.html", students=students, courses=courses, teachers=teachers)

# ---------------- Payments ----------------
@app.route("/payments", methods=["GET", "POST"])
def payments():
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        enroll_id = request.form.get("enroll_id")
        amount = request.form.get("amount")
        method = request.form.get("method")
        reference = request.form.get("reference")
        paid_on = request.form.get("paid_on") or None
        try:
            cur.execute("INSERT INTO Payment (enroll_id, amount, paid_on, method, reference) VALUES (%s,%s,%s,%s,%s)",
                        (enroll_id, amount, paid_on, method, reference))
            flash("Payment recorded.", "success")
        except mysql.connector.Error as e:
            flash(f"Error: {e.msg}", "danger")
        cur.close(); conn.close()
        return redirect(url_for("payments"))
    # GET: list enrollments and payments
    cur.execute("""SELECT p.payment_id, p.amount, p.paid_on, p.method, p.reference,
                   e.enroll_id, s.first_name, s.last_name, c.name AS course
                   FROM Payment p
                   JOIN Enrollment e ON p.enroll_id = e.enroll_id
                   JOIN Student s ON e.student_id = s.student_id
                   JOIN Course c ON e.course_id = c.course_id
                   ORDER BY p.paid_on DESC""")
    payments = cur.fetchall()
    cur.close(); conn.close()
    return render_template("payments.html", payments=payments)

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

