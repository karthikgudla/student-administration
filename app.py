from flask import Flask, render_template, request, redirect, flash,session,url_for
from pymongo import MongoClient
from flask import send_from_directory, abort
from werkzeug.utils import safe_join
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret'

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client["student_portal"]
students_collection = db["students"]
faculty_collection = db["faculty"]
marks_collection = db['marks']
attendance_collection = db['attendance']
notifications_collection = db['notifications']
study_material_collection = db['study_material']





@app.route('/')
def home():
    return render_template('home.html')  # This is your landing page



ADMIN_EMAIL = 'adminv@gmail.com'
ADMIN_PASSWORD = 'var123'

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('admin_login'))

    return render_template('admin-login.html')







@app.route('/add-student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        name = request.form.get('name')

        if roll_no and name:
            # Check if roll number already exists
            existing_student = students_collection.find_one({"roll_no": roll_no})
            
            if existing_student:
                flash("⚠️ Roll No already exists. Please use a unique Roll No.", "danger")
            else:
                students_collection.insert_one({
                    "roll_no": roll_no,
                    "name": name
                })
                flash("✅ Student added successfully!", "success")
        else:
            flash("⚠️ Please fill in all fields.", "danger")

        return redirect('/add-student')

    return render_template('add-student.html')






@app.route('/add-faculty', methods=['GET', 'POST'])
def add_faculty():
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        name = request.form.get('name')
        department = request.form.get('department')

        # Extract timetable data from form inputs
        timetable = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        hours = range(1, 7)

        for day in days:
            timetable[day] = {}
            for hour in hours:
                key = f'timetable-{day}-{hour}'
                subject = request.form.get(key, '').strip()
                timetable[day][f'Hour {hour}'] = subject

        if faculty_id and name and department:
            existing_faculty = faculty_collection.find_one({"faculty_id": faculty_id})
            if existing_faculty:
                flash("⚠️ Faculty ID already exists. Please use a new Faculty ID.", "warning")
            else:
                faculty_collection.insert_one({
                    "faculty_id": faculty_id,
                    "name": name,
                    "department": department,
                    "timetable": timetable
                })
                flash("✅ Faculty added successfully!", "success")
        else:
            flash("⚠️ Please fill in all fields.", "danger")

        return redirect('/add-faculty')

    return render_template('add-faculty.html')




@app.route('/add-marks', methods=['GET', 'POST'])
def add_marks():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        year = request.form.get('year')
        semester = request.form.get('semester')
        subject_marks = {}

        # Only process keys that start with "subject_"
        for key in request.form:
            if key.startswith('subject_'):
                try:
                    subject_marks[key[len('subject_'):]] = int(request.form.get(key))
                except ValueError:
                    flash(f"⚠️ Invalid mark for {key[len('subject_'):]}: please enter a number.", "danger")
                    return redirect('/add-marks')

        # Check if student exists
        student_exists = students_collection.find_one({'roll_no': roll_no})

        if not student_exists:
            flash("⚠️ Student with this Roll No does not exist. Please add student first.", "danger")
            return redirect('/add-marks')

        # Update or insert marks document
        existing_doc = marks_collection.find_one({'roll_no': roll_no})

        if existing_doc:
            marks_collection.update_one(
                {'roll_no': roll_no},
                {'$set': {f'marks.{year}-{semester}': subject_marks}}
            )
        else:
            marks_collection.insert_one({
                'roll_no': roll_no,
                'marks': {
                    f'{year}-{semester}': subject_marks
                }
            })

        flash("✅ Marks added successfully!", "success")
        return redirect('/add-marks')

    return render_template('add-marks.html')



@app.route('/add-attendance', methods=['GET', 'POST'])
def add_attendance():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        year = request.form.get('year')
        semester = request.form.get('semester')

        # Check if student exists
        student_exists = students_collection.find_one({'roll_no': roll_no})
        if not student_exists:
            flash("⚠️ Student with this Roll No does not exist. Please add student first.", "danger")
            return redirect('/add-attendance')

        # Collect attendance from form
        attendance_data = {}
        for key in request.form:
            if key not in ['roll_no', 'year', 'semester']:
                try:
                    val = int(request.form.get(key))
                    if val < 0 or val > 90:
                        raise ValueError("Attendance must be between 0 and 90")
                    attendance_data[key] = val
                except ValueError:
                    flash(f"Invalid attendance for {key}. Must be a number between 0 and 90.", "danger")
                    return redirect('/add-attendance')

        # Check if attendance doc exists
        existing_doc = attendance_collection.find_one({'roll_no': roll_no})

        if existing_doc:
            # Update attendance for this semester
            attendance_collection.update_one(
                {'roll_no': roll_no},
                {'$set': {f'attendance.{year}-{semester}': attendance_data}}
            )
        else:
            # Insert new attendance document
            attendance_collection.insert_one({
                'roll_no': roll_no,
                'attendance': {
                    f'{year}-{semester}': attendance_data
                }
            })

        flash("✅ Attendance added successfully!", "success")
        return redirect('/add-attendance')

    return render_template('add-attendance.html')







UPLOAD_FOLDER = 'static/uploads/notifications'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/post-notification', methods=['GET', 'POST'])
def post_notification():
    if request.method == 'POST':
        message = request.form.get('message').strip()
        file = request.files.get('attachment')

        if not message:
            flash("⚠️ Message cannot be empty.", "danger")
            return redirect('/post-notification')

        attachment_url = None
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                # Make sure upload folder exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                attachment_url = filepath  # Save relative path or URL for frontend
            else:
                flash("⚠️ File type not allowed. Allowed types: pdf, doc, docx, png, jpg, jpeg", "danger")
                return redirect('/post-notification')

        # Insert notification to DB
        notifications_collection.insert_one({
            "message": message,
            "attachment_url": attachment_url,
            "posted_at": datetime.utcnow()
        })

        flash("✅ Notification posted successfully!", "success")
        return redirect('/post-notification')

    return render_template('post-notification.html')


@app.route('/notifications')
def show_notifications():
    notifications = list(notifications_collection.find().sort("posted_at", -1))
    return render_template('notifications.html', notifications=notifications)








@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/faculty')
def faculty():
    return render_template('faculty.html')


@app.route('/faculty-login', methods=['GET', 'POST'])
def faculty_login():
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        password = request.form.get('password')

        faculty = faculty_collection.find_one({"faculty_id": faculty_id})

        # Check if faculty exists and password is exactly "var123"
        if faculty and password == "var123":
            session['faculty_id'] = faculty_id
            flash("Login successful.", "success")
            return redirect(url_for('faculty_dashboard'))
        else:
            flash("Invalid Faculty ID or password.", "danger")
    return render_template('faculty.html')

# -----------------
# Faculty Logout
# -----------------
@app.route('/faculty-logout')
def faculty_logout():
    session.pop('faculty_id', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('faculty_login'))

# -----------------
# Faculty Dashboard
# -----------------
@app.route('/faculty-dashboard')
def faculty_dashboard():
    if 'faculty_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('faculty_login'))

    faculty_id = session['faculty_id']
    faculty = faculty_collection.find_one({"faculty_id": faculty_id})

    if not faculty:
        flash("Faculty not found.", "danger")
        return redirect(url_for('faculty_login'))

    # Fetch last 10 notifications, newest first
    notifications_cursor = notifications_collection.find().sort("timestamp", -1).limit(10)
    notifications = list(notifications_cursor)

    return render_template(
        'faculty-dashboard.html',
        faculty_id=faculty['faculty_id'],
        faculty_name=faculty.get('name', ''),
        notifications=notifications
    )

# -----------------
# Post Notification (Faculty)
# -----------------
@app.route('/post-notification-faculty', methods=['POST'])
def post_notification_faculty():
    if 'faculty_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('faculty_login'))

    message = request.form.get('message', '').strip()
    if not message:
        flash("Notification message cannot be empty.", "danger")
        return redirect(url_for('faculty_dashboard'))

    notification = {
        "message": message,
        "posted_by": session['faculty_id'],
        "timestamp": datetime.utcnow()
    }

    notifications_collection.insert_one(notification)
    flash("Notification posted successfully.", "success")
    return redirect(url_for('faculty_dashboard'))

# -----------------
# View Timetable
# -----------------
@app.route('/view-timetable')
def view_timetable():
    if 'faculty_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('faculty_login'))

    faculty = faculty_collection.find_one({'faculty_id': session['faculty_id']})
    timetable = faculty.get('timetable', {}) if faculty else {}

    return render_template('view-timetable.html', timetable=timetable)


# -----------------
# Upload Study Material (GET and POST)
# -----------------
@app.route('/upload-study-material', methods=['GET', 'POST'])
def upload_study_material():
    if 'faculty_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('faculty_login'))

    if request.method == 'POST':
        title = request.form.get('title')
        file = request.files.get('file')

        if not title or not file:
            flash("Both title and file are required.", "danger")
            return redirect(url_for('upload_study_material'))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        study_material_collection.insert_one({
            "faculty_id": session['faculty_id'],
            "title": title,
            "filename": filename,
            "upload_time": datetime.utcnow()
        })

        flash("Study material uploaded successfully.", "success")
        return redirect(url_for('faculty_dashboard'))

    return render_template('upload-study-material.html')

# -----------------
# View Student Marks
# -----------------
@app.route('/view-student-marks', methods=['GET', 'POST'])
def view_student_marks():
    if 'faculty_id' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('faculty_login'))

    roll_numbers = marks_collection.distinct('roll_no')
    selected_roll = None
    marks_by_sem = {}

    if request.method == 'POST':
        selected_roll = request.form.get('roll_no')
        if selected_roll:
            student_doc = marks_collection.find_one({'roll_no': selected_roll})
            if student_doc and 'marks' in student_doc:
                marks_by_sem = student_doc['marks']  # e.g., {'1-1': {...}, '1-2': {...}}

    return render_template('view-student-marks.html',
                           roll_numbers=roll_numbers,
                           selected_roll=selected_roll,
                           marks_by_sem=marks_by_sem)







@app.route('/student')  # Renders login form
def student():
    return render_template('student.html')


@app.route('/student-login', methods=['GET', 'POST'])  # Processes login form
def student_login():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        password = request.form.get('password')

        student = students_collection.find_one({'roll_no': roll_no})
        if student and password == "var321":  # Hardcoded password
            session['student_roll_no'] = roll_no
            flash('Login successful.', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid roll number or password.', 'danger')

    return render_template('student.html')


@app.route('/student-dashboard')  # Dashboard after login
def student_dashboard():
    if 'student_roll_no' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('student_login'))

    student = students_collection.find_one({'roll_no': session['student_roll_no']})
    notifications = list(notifications_collection.find().sort('date', -1))  # Optional sort

    return render_template('student-dashboard.html', student=student, notifications=notifications)





@app.route('/student-logout')
def student_logout():
    session.pop('student_roll_no', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('student_login'))




# View Student Marks
@app.route('/student-view-marks')
def student_view_marks():
    if 'student_roll_no' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('student_login'))

    roll_no = session['student_roll_no']
    student = students_collection.find_one({'roll_no': roll_no})
    marks_data = marks_collection.find_one({'roll_no': roll_no})

    return render_template('student-marks.html', student=student, marks_data=marks_data)



@app.route('/student-marks-insights')
def student_marks_insights():
    roll_no = request.args.get('roll_no')

    if not roll_no:
        if 'student_roll_no' in session:
            roll_no = session['student_roll_no']
        else:
            flash("Please login first or provide a roll number.", "warning")
            return redirect(url_for('student_login'))

    student_marks_doc = db.marks.find_one({'roll_no': roll_no})
    student_info = db.students.find_one({'roll_no': roll_no})

    if not student_marks_doc or 'marks' not in student_marks_doc:
        return render_template('student-marks-insights.html', student=None, marks=None)

    student = {
        'name': student_info['name'] if student_info else 'Unknown',
        'roll_no': roll_no
    }
    marks = student_marks_doc['marks']

    return render_template('student-marks-insights.html', student=student, marks=marks)













# View Student Attendance
@app.route('/student-view-attendance')
def student_view_attendance():
    if 'student_roll_no' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('student_login'))

    roll_no = session['student_roll_no']
    attendance_doc = attendance_collection.find_one({'roll_no': roll_no})  # Your attendance collection
    student = students_collection.find_one({'roll_no': roll_no})

    return render_template('student-attendance.html', student=student, attendance=attendance_doc)




@app.route('/student-attendance-insights')
def student_attendance_insights():
    if 'student_roll_no' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('student_login'))

    roll_no = session['student_roll_no']

    # Fetch attendance document by roll_no
    student_attendance_doc = db.attendance.find_one({'roll_no': roll_no})
    student_info = db.students.find_one({'roll_no': roll_no})  # Assuming student info is in a separate collection

    if not student_attendance_doc or 'attendance' not in student_attendance_doc:
        return render_template('student-attendance-insights.html', student=None, attendance_data=None, sem=None)

    # For demo: Let's pick the first semester available in attendance dict
    attendance = student_attendance_doc['attendance']
    if not attendance:
        return render_template('student-attendance-insights.html', student=None, attendance_data=None, sem=None)

    sem = list(attendance.keys())[0]  # e.g., '1-1'
    attendance_data = attendance[sem]  # dict of subjects and attendance %

    student = {
        'name': student_info['name'] if student_info else 'Unknown',
        'roll_no': roll_no
    }

    return render_template('student-attendance-insights.html',
                           student=student,
                           attendance_data=attendance_data,
                           sem=sem)







# View Study Materials
@app.route('/student-view-materials')
def student_view_materials():
    if 'student_roll_no' not in session:
        flash("Please login first.", "warning")
        return redirect(url_for('student_login'))

    # Fetch all study materials (you may filter by faculty or other criteria)
    materials = list(study_material_collection.find().sort('upload_time', -1))
    return render_template('student-materials.html', materials=materials)

@app.route('/download-material/<filename>')
def download_material(filename):
    try:
        return send_from_directory(
            os.path.join('static', 'uploads', 'notifications'),
            filename,
            as_attachment=True
        )
    except FileNotFoundError:
        abort(404)




if __name__ == '__main__':
    app.run(debug=True)
