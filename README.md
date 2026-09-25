# Student Attendance & Performance Management System Using Python

A web-based system built with **Python (Flask)** and **SQLite** for digitizing
student academic management: student records, attendance tracking, marks
entry, performance analysis, an early-warning system for at-risk students,
a dashboard, and CSV reporting.

## Features

- 🔐 Login system (session-based)
- 👩‍🎓 Student management — Add / Edit / Delete / Search
- 🗓️ Attendance management with automatic attendance percentage
- 📝 Marks management with automatic average calculation
- 📊 Performance analysis (attendance % + average marks per student)
- ⚠️ Early-warning system for at-risk students (low attendance or low marks)
- 📈 Dashboard with subject-wise performance chart
- 📄 Reports page with CSV export
- 🧪 Small sample dataset included to get started immediately

## Tech Stack

- **Backend:** Python, Flask
- **Database:** SQLite
- **Frontend:** Jinja2 templates, plain CSS, Chart.js (via CDN) for the dashboard chart
- **Auth:** Werkzeug password hashing + Flask sessions

## Project Structure

```
Student-Attendance-Performance-Management-System/
├── app.py
├── database.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   └── sample_student_dataset.csv
├── database/            # SQLite file is created here at runtime (ignored by git)
├── reports/             # optional local export destination
├── static/
│   └── css/
│       └── style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── students.html
    ├── student_form.html
    ├── attendance.html
    ├── marks.html
    ├── performance.html
    └── reports.html
```

## Setup & Run

1. **Check Python is installed**
   ```bash
   python --version
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python app.py
   ```
   Then open **http://127.0.0.1:5000** in your browser.

5. **Login (demo credentials)**
   - Username: `admin`
   - Password: `admin123`

   > ⚠️ These are demo credentials for local development only. Change the
   > password and the Flask `secret_key` in `app.py` before any real
   > deployment.

On first run, `app.py` automatically creates the SQLite database
(`database/app.db`) and loads the small sample dataset from
`data/sample_student_dataset.csv` if the students table is empty.

## How the System Works

```
Student Management
        │
   ┌────┴────┐
   ▼         ▼
Attendance  Marks
   │         │
   ▼         ▼
Attendance % Average Marks
   └────┬────┘
        ▼
 Performance Analysis
        │
        ▼
   Early Warning
        │
        ▼
     Dashboard
        │
        ▼
      Reports
```

- **Early-warning thresholds** (in `app.py`): attendance below 75% OR
  average marks below 40 flags a student as "At Risk". These are easy to
  adjust at the top of `app.py`.

## Dataset

This repo ships with a small demonstration dataset
(`data/sample_student_dataset.csv`) so the app works out of the box.

For an actual submission, consider documenting a real public dataset, for
example the **UCI Student Performance Dataset** (649 instances, includes
grades and absences, CC BY 4.0 licensed) — see the UCI Machine Learning
Repository. You can adapt its fields to this system's `students`, `marks`,
and `attendance` tables, or use it as a reference for realistic values.

## Demo Walkthrough (for showing the project to a trainer/reviewer)

1. **Login** → reach the Dashboard
2. **Student Management** → Add Student → Student List → Edit → Search
3. **Attendance** → pick date, subject, mark Present/Absent → Save →
   see updated attendance %
4. **Marks** → enter marks per subject per student → see average
5. **Performance** → view attendance %, average marks, and status per student
6. **Early Warning** → view the list of at-risk students
7. **Dashboard** → total students, overall attendance, average marks,
   at-risk count, subject-wise chart
8. **Reports** → view the report table and export it as CSV

## Notes

- The database uses `UNIQUE(student_id, date, subject)` for attendance and
  `UNIQUE(student_id, subject)` for marks, so re-saving the same
  date/subject or subject updates the existing record instead of
  duplicating it.
- Deleting a student cascades to their attendance and marks records.
- Before submitting or deploying this project for real use: change the
  demo password, change `app.secret_key` in `app.py`, and consider moving
  secrets to environment variables.
