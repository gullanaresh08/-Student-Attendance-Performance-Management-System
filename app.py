"""
app.py
Student Attendance & Performance Management System Using Python
Main Flask application: routes for auth, student management, attendance,
marks, performance analysis, dashboard, and reports.
"""

import csv
import io
import os
from datetime import date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, Response
)
from werkzeug.security import check_password_hash

import database

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-before-deployment"  # CHANGE before real deployment

BASE_DIR = os.path.dirname(__file__)
SAMPLE_CSV = os.path.join(BASE_DIR, "data", "sample_student_dataset.csv")

# Thresholds used for the early-warning system
ATTENDANCE_THRESHOLD = 75.0   # % below this is flagged
MARKS_THRESHOLD = 40.0        # average below this is flagged


# ---------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = database.get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------
# Shared analytics helpers
# ---------------------------------------------------------------------
def compute_attendance_percentage(conn, student_id):
    row = conn.execute(
        """SELECT
             SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
             COUNT(*) as total
           FROM attendance WHERE student_id = ?""",
        (student_id,),
    ).fetchone()
    if not row or not row["total"]:
        return 0.0
    return round((row["present_count"] / row["total"]) * 100, 2)


def compute_average_marks(conn, student_id):
    row = conn.execute(
        "SELECT AVG(marks) as avg_marks FROM marks WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    return round(row["avg_marks"], 2) if row and row["avg_marks"] is not None else 0.0


def build_performance_rows(conn):
    """One row per student: attendance %, average marks, and status."""
    students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    rows = []
    for s in students:
        att = compute_attendance_percentage(conn, s["id"])
        avg = compute_average_marks(conn, s["id"])
        at_risk = att < ATTENDANCE_THRESHOLD or avg < MARKS_THRESHOLD
        rows.append({
            "id": s["id"],
            "name": s["name"],
            "roll_no": s["roll_no"],
            "student_class": s["student_class"],
            "attendance": att,
            "average_marks": avg,
            "status": "At Risk" if at_risk else "Good Standing",
        })
    return rows


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------
@app.route("/")
@login_required
def dashboard():
    conn = database.get_connection()
    rows = build_performance_rows(conn)

    total_students = len(rows)
    overall_attendance = round(
        sum(r["attendance"] for r in rows) / total_students, 2
    ) if total_students else 0.0
    overall_avg_marks = round(
        sum(r["average_marks"] for r in rows) / total_students, 2
    ) if total_students else 0.0
    at_risk_count = sum(1 for r in rows if r["status"] == "At Risk")

    # Subject-wise average, for the chart
    subject_rows = conn.execute(
        "SELECT subject, AVG(marks) as avg_marks FROM marks GROUP BY subject"
    ).fetchall()
    subjects = [r["subject"] for r in subject_rows]
    subject_averages = [round(r["avg_marks"], 2) for r in subject_rows]

    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        overall_attendance=overall_attendance,
        overall_avg_marks=overall_avg_marks,
        at_risk_count=at_risk_count,
        subjects=subjects,
        subject_averages=subject_averages,
    )


# ---------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------
@app.route("/students")
@login_required
def students():
    query = request.args.get("q", "").strip()
    conn = database.get_connection()
    if query:
        like = f"%{query}%"
        rows = conn.execute(
            """SELECT * FROM students
               WHERE name LIKE ? OR roll_no LIKE ? OR student_class LIKE ?
               ORDER BY name""",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    conn.close()
    return render_template("students.html", students=rows, query=query)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        student_class = request.form.get("student_class", "").strip()
        contact = request.form.get("contact", "").strip()

        if not name or not roll_no:
            flash("Name and Roll No. are required.", "error")
            return render_template("student_form.html", student=None)

        conn = database.get_connection()
        try:
            conn.execute(
                "INSERT INTO students (name, roll_no, student_class, contact) "
                "VALUES (?, ?, ?, ?)",
                (name, roll_no, student_class, contact),
            )
            conn.commit()
            flash("Student added successfully.", "success")
            return redirect(url_for("students"))
        except Exception:
            flash("A student with that Roll No. already exists.", "error")
        finally:
            conn.close()

    return render_template("student_form.html", student=None)


@app.route("/students/edit/<int:student_id>", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    conn = database.get_connection()
    student = conn.execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        flash("Student not found.", "error")
        return redirect(url_for("students"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll_no = request.form.get("roll_no", "").strip()
        student_class = request.form.get("student_class", "").strip()
        contact = request.form.get("contact", "").strip()

        try:
            conn.execute(
                """UPDATE students SET name = ?, roll_no = ?, student_class = ?, contact = ?
                   WHERE id = ?""",
                (name, roll_no, student_class, contact, student_id),
            )
            conn.commit()
            flash("Student updated successfully.", "success")
            return redirect(url_for("students"))
        except Exception:
            flash("Update failed — Roll No. may already be in use.", "error")
        finally:
            conn.close()
        return render_template("student_form.html", student=student)

    conn.close()
    return render_template("student_form.html", student=student)


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    conn = database.get_connection()
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))


# ---------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    conn = database.get_connection()
    all_students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()

    if request.method == "POST":
        att_date = request.form.get("date") or str(date.today())
        subject = request.form.get("subject", "").strip()

        if not subject:
            flash("Subject is required.", "error")
        else:
            saved = 0
            for s in all_students:
                status = request.form.get(f"status_{s['id']}")
                if status in ("Present", "Absent"):
                    conn.execute(
                        """INSERT INTO attendance (student_id, date, subject, status)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(student_id, date, subject)
                           DO UPDATE SET status = excluded.status""",
                        (s["id"], att_date, subject, status),
                    )
                    saved += 1
            conn.commit()
            flash(f"Attendance saved for {saved} student(s).", "success")

    # Show current attendance % alongside the form
    rows = []
    for s in all_students:
        rows.append({
            "id": s["id"],
            "name": s["name"],
            "roll_no": s["roll_no"],
            "attendance": compute_attendance_percentage(conn, s["id"]),
        })
    conn.close()

    return render_template(
        "attendance.html", students=rows, today=str(date.today())
    )


# ---------------------------------------------------------------------
# Marks
# ---------------------------------------------------------------------
@app.route("/marks", methods=["GET", "POST"])
@login_required
def marks():
    conn = database.get_connection()
    all_students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        subject = request.form.get("subject", "").strip()
        marks_value = request.form.get("marks", "").strip()

        if not (student_id and subject and marks_value):
            flash("Student, subject, and marks are all required.", "error")
        else:
            try:
                marks_value = float(marks_value)
                conn.execute(
                    """INSERT INTO marks (student_id, subject, marks)
                       VALUES (?, ?, ?)
                       ON CONFLICT(student_id, subject)
                       DO UPDATE SET marks = excluded.marks""",
                    (student_id, subject, marks_value),
                )
                conn.commit()
                flash("Marks saved.", "success")
            except ValueError:
                flash("Marks must be a number.", "error")

    # Marks table grouped by student
    student_marks = []
    for s in all_students:
        subject_rows = conn.execute(
            "SELECT subject, marks FROM marks WHERE student_id = ?", (s["id"],)
        ).fetchall()
        student_marks.append({
            "id": s["id"],
            "name": s["name"],
            "roll_no": s["roll_no"],
            "subjects": subject_rows,
            "average": compute_average_marks(conn, s["id"]),
        })
    conn.close()

    return render_template("marks.html", students=all_students, student_marks=student_marks)


# ---------------------------------------------------------------------
# Performance analysis / early warning
# ---------------------------------------------------------------------
@app.route("/performance")
@login_required
def performance():
    conn = database.get_connection()
    rows = build_performance_rows(conn)
    conn.close()
    at_risk = [r for r in rows if r["status"] == "At Risk"]
    return render_template(
        "performance.html",
        rows=rows,
        at_risk=at_risk,
        attendance_threshold=ATTENDANCE_THRESHOLD,
        marks_threshold=MARKS_THRESHOLD,
    )


# ---------------------------------------------------------------------
# Reports / CSV export
# ---------------------------------------------------------------------
@app.route("/reports")
@login_required
def reports():
    conn = database.get_connection()
    rows = build_performance_rows(conn)
    conn.close()
    return render_template("reports.html", rows=rows)


@app.route("/reports/export")
@login_required
def export_csv():
    conn = database.get_connection()
    rows = build_performance_rows(conn)
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Roll No", "Class", "Attendance %", "Average Marks", "Status"])
    for r in rows:
        writer.writerow([
            r["name"], r["roll_no"], r["student_class"],
            r["attendance"], r["average_marks"], r["status"],
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=performance_report.csv"},
    )


# ---------------------------------------------------------------------
if __name__ == "__main__":
    database.init_db()
    database.seed_sample_data(SAMPLE_CSV)
    app.run(debug=True)
