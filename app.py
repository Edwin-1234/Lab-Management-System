from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session ,flash
import mysql.connector

app = Flask(__name__)
# ***IMPORTANT: CHANGE THIS TO A STRONG, UNIQUE KEY IN PRODUCTION***
# You can generate a good key with: import os; os.urandom(24).hex()
app.secret_key = 'your_super_secret_key_here_a_much_longer_and_random_string'

# --- Database Configuration ---
# Replace with your MySQL database credentials
DB_CONFIG = {
    'host': 'localhost',  # Or your database host (e.g., '127.0.0.1' or a remote IP)
    'user': 'root', # Your MySQL username
    'password': 'password', # Your MySQL password
    'database': 'LAB_MANAGEMENT' # The name of your database
}

# Function to get a database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

@app.route('/')
def index():
    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login authentication based on first character of the user ID (S or L)."""
    conn = None
    cursor = None
    try:
        user_id_from_form = request.form['email'].strip()
        password = request.form['password']

        if not user_id_from_form or not password:
            return redirect(url_for('index', error='Please enter both ID and password.'))

        # Determine user type from first character
        first_char = user_id_from_form[0].upper()
        if first_char == 'S':
            table = 'STUDENT'
            id_col = 'SID'
            redirect_route = 'dashboard'
            user_type = 'student'
        elif first_char == 'L':
            table = 'LABSTAFF'
            id_col = 'ID'
            redirect_route = 'staff_dashboard'
            user_type = 'staff'
        else:
            return redirect(url_for('index', error='Invalid user ID prefix. Must start with S or L.'))

        # Connect to database
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('index', error='Database connection error. Please try again later.'))
        cursor = conn.cursor(buffered=True)

        # Prepare and execute query
        query = f"SELECT {id_col}, Password FROM {table} WHERE {id_col} = %s AND Password = %s"
        cursor.execute(query, (user_id_from_form, password))
        result = cursor.fetchone()

        if result:
            session['logged_in'] = True
            session['user_id'] = user_id_from_form
            session['user_type'] = user_type
            return redirect(url_for(redirect_route))
        else:
            return redirect(url_for('index', error='Invalid ID or Password.'))

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        return redirect(url_for('index', error='Internal database error. Please try again.'))

    except KeyError as e:
        print(f"Missing form input: {e}")
        return redirect(url_for('index', error='Missing form data.'))

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles student registration."""
    conn = None
    cursor = None
    try:
        if request.method == 'POST':
            sid = request.form['sid']
            roll_no = int(request.form['roll_no'])
            name = request.form['name']
            semester = int(request.form['semester'])
            department = request.form['department']
            dob = request.form['dob']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if not (1 <= roll_no <= 200):
                return "Roll number must be between 001 and 200!", 400

            if not (1 <= semester <= 8):
                return "Semester must be between 1 and 8!", 400

            dob_date = datetime.strptime(dob, '%Y-%m-%d')
            age = (datetime.now() - dob_date).days // 365
            if age < 17:
                return "You must be at least 17 years old!", 400

            if password != confirm_password:
                return "Passwords do not match!", 400

            conn = get_db_connection()
            if conn is None:
                return "Database connection error.", 500
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO STUDENT (SID, RollNo, Name, Semester, Department, DOB, Password) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                           (sid, roll_no, name, semester, department, dob, password))
            conn.commit()
            return redirect(url_for('index')) # Redirect to the main login page after signup
        
        return render_template('signup.html')
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/dashboard')
def dashboard():
    """Renders the student dashboard if authenticated as a student."""
    if 'logged_in' not in session or session.get('user_type') != 'student':
        return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
    conn = None
    cursor = None
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('index', error='Database connection error.'))
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (user_id,))
        student = cursor.fetchone()
        
        return render_template('dashboard.html', student=student)
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()



@app.route('/personal_details')
def personal_details():
    """Renders a page with current student's personal details."""
    if 'logged_in' not in session or session.get('user_type') != 'student':
        return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
    conn = None
    cursor = None
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('student_dashboard'))
        
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (user_id,))
        student = cursor.fetchone()
        
        if student:
            # Format the date before passing to template
            formatted_dob = student[5].strftime('%d-%m-%Y')
            
            # Prepare the student data dictionary
            student_data = {
                'SID': student[0],
                'RollNo': student[1],
                'Name': student[2],
                'Semester': student[3],
                'Department': student[4],
                'DOB': formatted_dob,
            }
            
            # Render the template with student data
            return render_template('personal_details.html', student=student_data)
        else:
            flash('Student not found.', 'error')
            return redirect(url_for('student_dashboard'))
            
    except mysql.connector.Error as err:
        flash(f"Database Error: {err}", 'error')
        return redirect(url_for('student_dashboard'))
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", 'error')
        return redirect(url_for('student_dashboard'))
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()




# @app.route('/personal_details')
# def personal_details():
#     """Fetches and returns current student's personal details as JSON."""
#     if 'logged_in' not in session or session.get('user_type') != 'student':
#         return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return jsonify({'error': 'Database connection error.'}), 500
#         cursor = conn.cursor(buffered=True)
#         cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (user_id,))
#         student = cursor.fetchone()
        
#         if student:
#             formatted_dob = student[5].strftime('%d-%m-%Y')
#             return jsonify({
#                 'SID': student[0],
#                 'RollNo': student[1],
#                 'Name': student[2],
#                 'Semester': student[3],
#                 'Department': student[4],
#                 'DOB': formatted_dob,
#             })
#         else:
#             return jsonify({'error': 'Student not found.'}), 404
#     except mysql.connector.Error as err:
#         return jsonify({'error': f"Database Error: {err}"}), 500
#     except Exception as e:
#         return jsonify({'error': f"An unexpected error occurred: {e}"}), 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()




@app.route('/course_details')
def course_details():
    """Fetches and renders course details for the logged-in student."""
    if 'logged_in' not in session or session.get('user_type') != 'student':
        flash('Access denied. Please log in as a student.', 'error')
        return redirect(url_for('index'))
    
    conn = None
    cursor = None
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error.', 'error')
            return redirect(url_for('student_dashboard'))
        
        cursor = conn.cursor(dictionary=True)  # Use dictionary cursor for easier access
        cursor.execute("SELECT Semester, Department FROM STUDENT WHERE SID = %s", (user_id,))
        student_info = cursor.fetchone()

        if not student_info:
            flash('Student information not found.', 'error')
            return redirect(url_for('student_dashboard'))
        
        semester = student_info['Semester']
        dept = student_info['Department']
        courses = []

        # Fetch courses based on department and semester
        query = """
            SELECT c.Code, c.Course_Name, c.Semester, l.Lab_Name 
            FROM COURSE c
            LEFT JOIN OFFERS o ON c.Code = o.Code
            LEFT JOIN LAB l ON o.RoomNo = l.RoomNo
            WHERE c.Semester = %s
        """
        cursor.execute(query, (semester,))
        courses = cursor.fetchall()

        if not courses:
            flash('No courses found for your semester.', 'info')

        return render_template('course_details.html', 
                            courses=courses,
                            semester=semester,
                            department=dept)
    
    except mysql.connector.Error as err:
        flash(f'Database error: {err}', 'error')
        return redirect(url_for('student_dashboard'))
    except Exception as e:
        flash(f'An unexpected error occurred: {e}', 'error')
        return redirect(url_for('student_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()





# @app.route('/course_details')
# def course_details():
#     """Fetches and renders course details for the logged-in student."""
#     if 'logged_in' not in session or session.get('user_type') != 'student':
#         return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)

#         courses = []
#         labnames = []

#         cursor.execute("SELECT Semester, Department FROM STUDENT WHERE SID = %s", (user_id,))
#         result = cursor.fetchone()

#         if result:
#             semester = result[0]
#             dept = result[1]

#             if dept == 'CSE':
#                 cursor.execute("SELECT Code, Course_Name, Semester FROM COURSE WHERE Semester = %s", (semester,))
#                 courses_data = cursor.fetchall()
                
#                 for course_code, course_name, course_semester in courses_data:
#                     cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (course_code,))
#                     roomno_result = cursor.fetchone()
                    
#                     lab_name = 'N/A'
#                     if roomno_result:
#                         roomno = int(roomno_result[0])
#                         cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                         labname_result = cursor.fetchone()
#                         if labname_result:
#                             lab_name = labname_result[0]
                    
#                     courses.append({'Code': course_code, 'Course_Name': course_name, 'Semester': course_semester, 'Lab_Name': lab_name})
#             else: # For other departments like ECE, EEE
#                 # The original logic had a specific check for semester == 2 and then N/A for others.
#                 # Assuming you want to fetch courses for non-CSE students as well, but only if they offer courses.
#                 # If specific courses are tied to non-CSE departments and specific semesters,
#                 # you'd need to adjust the query logic here. For now, mirroring original behavior.
#                 if semester == 2: # Example for a specific semester in other departments
#                     cursor.execute("SELECT Code, Course_Name, Semester FROM COURSE WHERE Semester = %s", (semester,))
#                     courses_data = cursor.fetchall()
#                     for course_code, course_name, course_semester in courses_data:
#                         cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (course_code,))
#                         roomno_result = cursor.fetchone()
                        
#                         lab_name = 'N/A'
#                         if roomno_result:
#                             roomno = int(roomno_result[0])
#                             cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                             labname_result = cursor.fetchone()
#                             if labname_result:
#                                 lab_name = labname_result[0]
#                         courses.append({'Code': course_code, 'Course_Name': course_name, 'Semester': course_semester, 'Lab_Name': lab_name})
#                 # If not semester 2 and not CSE, then courses and labnames remain empty, matching original logic.
        
#         return render_template('course_details.html', courses=courses) # Changed to send 'courses' directly
    
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Handles password reset verification and rendering the reset form."""
    conn = None
    cursor = None
    try:
        if request.method == 'POST':
            sid = request.form.get('sid')
            dob = request.form.get('dob') # Ensure DOB format matches your database 'YYYY-MM-DD'

            if sid and dob:
                conn = get_db_connection()
                if conn is None:
                    return "Database connection error.", 500
                cursor = conn.cursor(buffered=True)
                cursor.execute("SELECT SID FROM STUDENT WHERE SID = %s AND DOB = %s", (sid, dob))
                student_exists = cursor.fetchone()

                if student_exists:
                    session['reset_sid'] = sid # Store SID temporarily for password update
                    return render_template('reset_password.html', sid=sid, verified=True)
                else:
                    return "Verification failed! Invalid SID or Date of Birth.", 401
            else:
                return "SID and Date of Birth are required!", 400

        return render_template('reset_password.html', verified=False)
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/update_password', methods=['POST'])
def update_password():
    """Handles updating the password for a student after verification."""
    conn = None
    cursor = None
    try:
        # Assuming the SID for update comes from a hidden field in the reset_password.html form
        # or from the session if it was stored there after verification.
        # It's safer to use a session variable for security.
        sid_to_update = session.get('reset_sid') 
        if not sid_to_update:
            return "Unauthorized password update attempt.", 403

        old_password = request.form['old_password'] # This field might not be present if it's a "forgot password" flow.
                                                  # If it's a *reset* flow after verification, old_password isn't needed.
                                                  # Assuming it's for verification against current password.
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return "New passwords do not match!", 400

        conn = get_db_connection()
        if conn is None:
            return "Database connection error.", 500
        cursor = conn.cursor(buffered=True)

        # First, verify the old password (if applicable in your reset flow)
        cursor.execute("SELECT Password FROM STUDENT WHERE SID = %s", (sid_to_update,))
        result = cursor.fetchone()

        if result is None:
            return "Student not found!", 404

        stored_password = result[0]
        # If this is a *forgot* password flow, you might not check old_password.
        # If it's a "change password while logged in" flow, you'd check old_password.
        # Given your 'reset_password' context, it's likely a *forgot* flow, so checking old_password here might be wrong.
        # I'm keeping the check based on your original code, but consider if 'old_password' is truly required in this context.
        if stored_password != old_password:
            return "Old password is incorrect!", 401

        cursor.execute("UPDATE STUDENT SET Password = %s WHERE SID = %s", (new_password, sid_to_update))
        conn.commit()

        # Clear the temporary session variable after successful reset
        session.pop('reset_sid', None) 
        return redirect(url_for('index', message='Password updated successfully. Please login with your new password.'))

    except mysql.connector.Error as err:
        print(f"Database Error during password update: {err}")
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/staff_dashboard')
def staff_dashboard():
    """Renders the staff dashboard if authenticated as staff."""
    # Check if logged in and if user_type is 'staff'
    if 'logged_in' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('index', error='Access denied. Please log in as staff.'))
    
    conn = None
    cursor = None
    try:
        user_id = session['user_id']
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('index', error='Database connection error.'))
        cursor = conn.cursor(buffered=True)

        cursor.execute("SELECT Name FROM LABSTAFF WHERE ID = %s", (user_id,))
        staff_name_result = cursor.fetchone()
        
        staff_name = staff_name_result[0] if staff_name_result else "Unknown Staff"
        
        return render_template('staff_dashboard.html', staff_name=staff_name, staff_id=user_id) # Pass staff_id too
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/student_details')
def student_details():
    """Fetches and renders all student details (accessible by staff)."""
    # Assuming this route is for staff, add a check
    if 'logged_in' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('index', error='Access denied. Please log in as staff.'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('index', error='Database connection error.'))
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT * FROM STUDENT")
        students = cursor.fetchall()
        return render_template('student_details.html', students=students)
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/component_details')
def component_details():
    """Fetches and renders all component details (accessible by staff)."""
    # Assuming this route is for staff, add a check
    if 'logged_in' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('index', error='Access denied. Please log in as staff.'))

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('index', error='Database connection error.'))
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT * FROM COMPONENTS")
        components = cursor.fetchall()
        return render_template('component_details.html', components=components)
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()


@app.route('/staff_signup', methods=['GET', 'POST'])
def staff_signup():
    """Handles staff registration."""
    conn = None
    cursor = None
    try:
        if request.method == 'POST':
            staff_id = request.form['id']
            name = request.form['name']
            role = request.form['role']
            password = request.form['password']
            confirm_password = request.form['confirm_password']

            if password != confirm_password:
                return "Passwords do not match!", 400

            conn = get_db_connection()
            if conn is None:
                return "Database connection error.", 500
            cursor = conn.cursor()
            
            cursor.execute("INSERT INTO LABSTAFF (ID, Name, Roles, Password) VALUES (%s, %s, %s, %s)", 
                           (staff_id, name, role, password))
            conn.commit()
            return redirect(url_for('index')) # Redirect to the main login page after signup (no staff_login route needed)
        
        return render_template('staff_signup.html')
    except mysql.connector.Error as err:
        return f"Database Error: {err}", 500
    except Exception as e:
        return f"An unexpected error occurred: {e}", 500
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()




# Add these new routes to your existing app.py

@app.route('/take_attendance', methods=['GET', 'POST'])
def take_attendance():
    if 'logged_in' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('index', error='Access denied. Please log in as staff.'))
    
    conn = None
    cursor = None
    try:
        staff_id = session['user_id']
        
        if request.method == 'POST':
            student_id   = request.form['student_id']
            status       = request.form['status']
            lab_room     = request.form['lab_room']
            # defer computer_number to student; insert NULL for now if Present
            computer_number = None if status == 'Present' else 'N/A'
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ATTENDANCE (student_id, staff_id, lab_room, computer_number, attendance_date, status) "
                "VALUES (%s, %s, %s, %s, CURDATE(), %s)",
                (student_id, staff_id, lab_room, computer_number, status)
            )
            conn.commit()
            flash('Attendance recorded successfully!', 'success')
            return redirect(url_for('take_attendance'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all students
        cursor.execute("SELECT SID, Name FROM STUDENT")
        students = cursor.fetchall()
        
        # Get all labs
        cursor.execute("SELECT RoomNo, Lab_Name FROM LAB")
        labs = cursor.fetchall()
        
        return render_template('take_attendance.html', students=students, labs=labs)
    
    except mysql.connector.Error as err:
        flash(f'Database error: {err}', 'error')
        return redirect(url_for('staff_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/view_attendance')
def view_attendance():
    if 'logged_in' not in session or session.get('user_type') != 'staff':
        return redirect(url_for('index', error='Access denied. Please log in as staff.'))
    
    conn = None
    cursor = None
    try:
        date_filter = request.args.get('date', '')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT a.*, s.Name as student_name, s.Semester, s.Department, l.Lab_Name
            FROM ATTENDANCE a
            JOIN STUDENT s ON a.student_id = s.SID
            JOIN LAB l ON a.lab_room = l.RoomNo
            WHERE a.staff_id = %s
        """
        params = [session['user_id']]
        
        if date_filter:
            query += " AND a.attendance_date = %s"
            params.append(date_filter)
        
        query += " ORDER BY a.attendance_date DESC"
        
        cursor.execute(query, params)
        attendance_records = cursor.fetchall()
        
        return render_template('view_attendance.html', attendance_records=attendance_records)
    
    except mysql.connector.Error as err:
        flash(f'Database error: {err}', 'error')
        return redirect(url_for('staff_dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/student_attendance')
def student_attendance():
    if 'logged_in' not in session or session.get('user_type') != 'student':
        return redirect(url_for('index', error='Access denied. Please log in as student.'))
    
    conn = None
    cursor = None
    try:
        student_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get total classes and present count
        cursor.execute("""
            SELECT 
                COUNT(*) as total_classes,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count
            FROM ATTENDANCE
            WHERE student_id = %s
        """, (student_id,))
        stats = cursor.fetchone()
        
        # Get recent attendance
        cursor.execute("""
            SELECT a.*, l.Lab_Name, ls.Name as staff_name
            FROM ATTENDANCE a
            JOIN LAB l ON a.lab_room = l.RoomNo
            JOIN LABSTAFF ls ON a.staff_id = ls.ID
            WHERE a.student_id = %s
            ORDER BY a.attendance_date DESC
            LIMIT 10
        """, (student_id,))
        recent_attendance = cursor.fetchall()
        
        return render_template('student_attendance.html', 
                            stats=stats,
                            recent_attendance=recent_attendance)
    
    except mysql.connector.Error as err:
        flash(f'Database error: {err}', 'error')
        return redirect(url_for('dashboard'))
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

@app.route('/submit_computer_number', methods=['POST'])
def submit_computer_number():
    if 'logged_in' not in session or session.get('user_type') != 'student':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        attendance_id = data['attendance_id']
        computer_number = data['computer_number']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ATTENDANCE SET computer_number = %s WHERE id = %s AND student_id = %s",
            (computer_number, attendance_id, session['user_id'])
        )
        conn.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()


@app.route('/check_pending_attendance')
def check_pending_attendance():
    if 'logged_in' not in session or session.get('user_type') != 'student':
        return jsonify({'attendance_id': None})

    student_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id 
        FROM ATTENDANCE 
        WHERE student_id = %s
          AND status = 'Present'
          AND (computer_number IS NULL OR computer_number = '')
        ORDER BY attendance_date DESC
        LIMIT 1
        """,
        (student_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return jsonify({'attendance_id': row[0] if row else None})







@app.route('/logout')
def logout():
    """Logs out the current user by clearing session variables."""
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('user_type', None)
    session.pop('reset_sid', None) # Clear reset_sid if it exists
    return redirect(url_for('index', message='You have been logged out.'))


if __name__ == '__main__':
    app.run(debug=True)
























# from datetime import datetime
# from flask import Flask, render_template, request, jsonify, redirect, url_for, session
# import mysql.connector

# app = Flask(__name__)
# app.secret_key = 'your_secret_key' 

# db = mysql.connector.connect(
#     host="localhost",
#     user="root",  
#     password="", 
#     database="LAB_MANAGEMENT"
# )
# cursor = db.cursor()

# @app.route('/')
# def index():
#     return render_template('index.html')


# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         sid = request.form['sid']
#         password = request.form['password']
        
#         cursor.execute("SELECT * FROM STUDENT WHERE SID = %s AND Password = %s", (sid, password))
#         student = cursor.fetchone()
        
#         if student:
#             session['sid'] = student[0]  
#             return redirect(url_for('dashboard'))  
#         else:
#             return "Invalid SID or Password!", 401
    
#     return render_template('login.html')



# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         sid = request.form['sid']
#         roll_no = int(request.form['roll_no'])
#         name = request.form['name']
#         semester = int(request.form['semester'])
#         department = request.form['department']
#         dob = request.form['dob']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']

#         if not (1 <= roll_no <= 200):
#             return "Roll number must be between 001 and 200!", 400

#         if not (1 <= semester <= 8):
#             return "Semester must be between 1 and 8!", 400

#         dob_date = datetime.strptime(dob, '%Y-%m-%d')
#         age = (datetime.now() - dob_date).days // 365
#         if age < 17:
#             return "You must be at least 17 years old!", 400

#         if password != confirm_password:
#             return "Passwords do not match!", 400

#         try:
#             cursor.execute("INSERT INTO STUDENT (SID, RollNo, Name, Semester, Department, DOB, Password) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
#                            (sid, roll_no, name, semester, department, dob, password))
#             db.commit()
#             return redirect(url_for('login')) 
#         except mysql.connector.Error as err:
#             return f"Error: {err}", 400

#     return render_template('signup.html')

# @app.route('/dashboard')
# def dashboard():
#     if 'sid' not in session:
#         return redirect(url_for('login')) 
    
#     sid = session['sid']
#     cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (sid,))
#     student = cursor.fetchone()
    
#     return render_template('dashboard.html', student=student)

# @app.route('/personal_details')
# def personal_details():
#     if 'sid' not in session:
#         return redirect(url_for('login'))
    
#     sid = session['sid']
#     cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (sid,))
#     student = cursor.fetchone()
#     formatted_dob = student[5].strftime('%d-%m-%Y')

#     return jsonify({
#         'SID': student[0],
#         'RollNo': student[1],
#         'Name': student[2],
#         'Semester': student[3],
#         'Department': student[4],
#         'DOB': formatted_dob,
#     })

# @app.route('/course_details')
# def course_details():
#     courses = []
#     labnames = []
#     if 'sid' not in session:
#         return redirect(url_for('login'))
    
#     sid = session['sid']
#     cursor.execute("SELECT Semester, Department FROM STUDENT WHERE SID = %s", (sid,))
#     result = cursor.fetchone()

#     semester = result[0]
#     dept = result[1]
#     if dept == 'CSE':
#         cursor.execute("SELECT * FROM COURSE WHERE Semester = %s", (semester,))
#         courses = cursor.fetchall()
#         length = len(courses)
        
#         for course in courses:
#             code = course[0]
#             cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (code,))
#             roomno_result = cursor.fetchone()
            
#             if roomno_result:
#                 roomno = int(roomno_result[0])
#                 cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                 labname = cursor.fetchone()
#                 labnames.append(labname)
#     else:
#         if semester == 2:
#             cursor.execute("SELECT * FROM COURSE WHERE Semester = %s", (semester,))
#             courses = cursor.fetchall()
#             length = len(courses)
            
#             for course in courses:
#                 code = course[0]
#                 cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (code,))
#                 roomno_result = cursor.fetchone()
                
#                 if roomno_result:
#                     roomno = int(roomno_result[0])
#                     cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                     labname = cursor.fetchone()
#                     labnames.append(labname)
#         else:
#             labnames=None
#             courses=None
#             length=0 
    
    

#     return render_template('course_details.html', length=length, courses=courses, labnames=labnames)

# @app.route('/reset_password', methods=['GET', 'POST'])
# def reset_password():
#     if request.method == 'POST':
#         sid = request.form.get('sid')
#         dob = request.form.get('dob')

#         if sid and dob:
#             cursor.execute("SELECT * FROM STUDENT WHERE SID = %s AND DOB = %s", (sid, dob))
#             student = cursor.fetchone()

#             if student:
#                 session['sid'] = sid
#                 return render_template('reset_password.html', sid=sid, verified=True)
#             else:
#                 return "Verification failed! Invalid SID or DOB.", 401
#         else:
#             return "SID and Date of Birth are required!", 400

#     return render_template('reset_password.html', verified=False)

# @app.route('/update_password', methods=['POST'])
# def update_password():
#     sid = request.form['sid']
#     old_password = request.form['old_password']
#     new_password = request.form['new_password']
#     confirm_password = request.form['confirm_password']

#     print(f"Received SID: {sid}, Old Password: {old_password}, New Password: {new_password}, Confirm Password: {confirm_password}") 

#     if new_password != confirm_password:
#         return "New passwords do not match!", 400

#     cursor.execute("SELECT Password FROM STUDENT WHERE SID = %s", (sid,))
#     result = cursor.fetchone()

#     if result is None:
#         return "Student not found!", 404

#     stored_password = result[0]
#     if stored_password != old_password:
#         return "Old password is incorrect!", 401

#     cursor.execute("UPDATE STUDENT SET Password = %s WHERE SID = %s", (new_password, sid))
#     db.commit()
#     return redirect(url_for('login')) 


# def staff_dashboard():
    
#     if 'id' not in session:
#         return redirect(url_for('staff_login'))
    
#     id = session['id']
#     cursor.execute("SELECT Name FROM LABSTAFF WHERE ID = %s", (id,))
#     staff = cursor.fetchone()
    
#     return render_template('staff_dashboard.html',  staff_name=staff)

# @app.route('/student_details')
# def student_details():
#     cursor.execute("SELECT * FROM STUDENT")
#     students = cursor.fetchall()
#     return render_template('student_details.html', students=students)

# @app.route('/component_details')
# def component_details():
#     cursor.execute("SELECT * FROM COMPONENTS")
#     components = cursor.fetchall()
#     return render_template('component_details.html', components=components)

# @app.route('/staff_signup', methods=['GET', 'POST'])
# def staff_signup():
#     if request.method == 'POST':
#         staff_id = request.form['id']
#         name = request.form['name']
#         role = request.form['role']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']

#         if password != confirm_password:
#             return "Passwords do not match!", 400

#         try:
#             cursor.execute("INSERT INTO LABSTAFF (ID, Name, Roles, Password) VALUES (%s, %s, %s, %s)", 
#                            (staff_id, name, role, password))
#             db.commit()
#             return redirect(url_for('staff_login'))  
#         except mysql.connector.Error as err:
#             return f"Error: {err}", 400

#     return render_template('staff_signup.html')

# if __name__ == '__main__':
#     app.run(debug=True)






































































































































































































































































































# from datetime import datetime
# from flask import Flask, render_template, request, jsonify, redirect, url_for, session
# import mysql.connector

# app = Flask(__name__)
# # ***IMPORTANT: CHANGE THIS TO A STRONG, UNIQUE KEY IN PRODUCTION***
# # You can generate a good key with: import os; os.urandom(24).hex()
# app.secret_key = 'your_super_secret_key_here_a_much_longer_and_random_string'

# # --- Database Configuration ---
# # Replace with your MySQL database credentials
# DB_CONFIG = {
#     'host': 'localhost',  # Or your database host (e.g., '127.0.0.1' or a remote IP)
#     'user': 'root', # Your MySQL username
#     'password': '', # Your MySQL password
#     'database': 'LAB_MANAGEMENT' # The name of your database
# }

# # Function to get a database connection
# def get_db_connection():
#     try:
#         conn = mysql.connector.connect(**DB_CONFIG)
#         return conn
#     except mysql.connector.Error as err:
#         print(f"Error connecting to database: {err}")
#         return None

# @app.route('/')
# def index():
#     return render_template('login.html')


# @app.route('/login', methods=['GET','POST'])
# def login():
#     """Handles user login authentication against the database for both students and staff."""
#     conn = None
#     cursor = None
#     try:
#         # The HTML input has name="email", so use request.form['email']
#         user_id_from_form = request.form['email'] # This will be SID for students, ID for staff  
#         password = request.form['password']
#         # This 'user_type' comes from the hidden input added by JavaScript in index.html
#         user_type_from_client = request.form['user_type'] 

#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error. Please try again later.'))
        
#         cursor = conn.cursor(buffered=True) # Use buffered=True to fetch results before closing cursor

#         authenticated = False
#         stored_user_type = None

#         if user_type_from_client == 'student':
#             query = "SELECT SID, Password FROM STUDENT WHERE SID = %s AND Password = %s"
#             cursor.execute(query, (user_id_from_form, password))
#             result = cursor.fetchone()

#             if result:
#                 authenticated = True
#                 stored_user_type = 'student'
#             else:
#                 print(f"Student login failed for ID: {user_id_from_form}")

#         elif user_type_from_client == 'staff':
#             query = "SELECT ID, Password FROM LABSTAFF WHERE ID = %s AND Password = %s"
#             cursor.execute(query, (user_id_from_form, password))
#             result = cursor.fetchone()

#             if result:
#                 authenticated = True
#                 stored_user_type = 'staff'
#             else:
#                 print(f"Staff login failed for ID: {user_id_from_form}")
#         else:
#             print(f"Invalid user type received: {user_type_from_client}")
#             return redirect(url_for('index', error='Invalid user type specified.'))

#         if authenticated:
#             session['logged_in'] = True
#             session['user_id'] = user_id_from_form # Store the SID or ID
#             session['user_type'] = stored_user_type

#             if stored_user_type == 'student':
#                 return redirect(url_for('dashboard'))
#             elif stored_user_type == 'staff':
#                 return redirect(url_for('staff_dashboard'))
#         else:
#             # Authentication failed
#             return redirect(url_for('index', error='Invalid ID or Password.'))

#     except mysql.connector.Error as err:
#         print(f"Database query error during login: {err}")
#         return redirect(url_for('index', error='An internal database error occurred. Please try again.'))
#     except KeyError as e:
#         # Catches errors if 'email', 'password', or 'user_type' are not in the form
#         print(f"Missing form data: {e}")
#         return redirect(url_for('index', error='Missing login credentials. Please fill all fields.'))
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     """Handles student registration."""
#     conn = None
#     cursor = None
#     try:
#         if request.method == 'POST':
#             sid = request.form['sid']
#             roll_no = int(request.form['roll_no'])
#             name = request.form['name']
#             semester = int(request.form['semester'])
#             department = request.form['department']
#             dob = request.form['dob']
#             password = request.form['password']
#             confirm_password = request.form['confirm_password']

#             if not (1 <= roll_no <= 200):
#                 return "Roll number must be between 001 and 200!", 400

#             if not (1 <= semester <= 8):
#                 return "Semester must be between 1 and 8!", 400

#             dob_date = datetime.strptime(dob, '%Y-%m-%d')
#             age = (datetime.now() - dob_date).days // 365
#             if age < 17:
#                 return "You must be at least 17 years old!", 400

#             if password != confirm_password:
#                 return "Passwords do not match!", 400

#             conn = get_db_connection()
#             if conn is None:
#                 return "Database connection error.", 500
#             cursor = conn.cursor()
            
#             cursor.execute("INSERT INTO STUDENT (SID, RollNo, Name, Semester, Department, DOB, Password) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
#                            (sid, roll_no, name, semester, department, dob, password))
#             conn.commit()
#             return redirect(url_for('index')) # Redirect to the main login page after signup
        
#         return render_template('signup.html')
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/dashboard')
# def dashboard():
#     """Renders the student dashboard if authenticated as a student."""
#     if 'logged_in' not in session or session.get('user_type') != 'student':
#         return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)
#         cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (user_id,))
#         student = cursor.fetchone()
        
#         return render_template('dashboard.html', student=student)
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/personal_details')
# def personal_details():
#     """Fetches and returns current student's personal details as JSON."""
#     if 'logged_in' not in session or session.get('user_type') != 'student':
#         return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return jsonify({'error': 'Database connection error.'}), 500
#         cursor = conn.cursor(buffered=True)
#         cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (user_id,))
#         student = cursor.fetchone()
        
#         if student:
#             formatted_dob = student[5].strftime('%d-%m-%Y')
#             return jsonify({
#                 'SID': student[0],
#                 'RollNo': student[1],
#                 'Name': student[2],
#                 'Semester': student[3],
#                 'Department': student[4],
#                 'DOB': formatted_dob,
#             })
#         else:
#             return jsonify({'error': 'Student not found.'}), 404
#     except mysql.connector.Error as err:
#         return jsonify({'error': f"Database Error: {err}"}), 500
#     except Exception as e:
#         return jsonify({'error': f"An unexpected error occurred: {e}"}), 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/course_details')
# def course_details():
#     """Fetches and renders course details for the logged-in student."""
#     if 'logged_in' not in session or session.get('user_type') != 'student':
#         return redirect(url_for('index', error='Access denied. Please log in as a student.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)

#         courses = []
#         labnames = []

#         cursor.execute("SELECT Semester, Department FROM STUDENT WHERE SID = %s", (user_id,))
#         result = cursor.fetchone()

#         if result:
#             semester = result[0]
#             dept = result[1]

#             if dept == 'CSE':
#                 cursor.execute("SELECT Code, Course_Name, Semester FROM COURSE WHERE Semester = %s", (semester,))
#                 courses_data = cursor.fetchall()
                
#                 for course_code, course_name, course_semester in courses_data:
#                     cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (course_code,))
#                     roomno_result = cursor.fetchone()
                    
#                     lab_name = 'N/A'
#                     if roomno_result:
#                         roomno = int(roomno_result[0])
#                         cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                         labname_result = cursor.fetchone()
#                         if labname_result:
#                             lab_name = labname_result[0]
                    
#                     courses.append({'Code': course_code, 'Course_Name': course_name, 'Semester': course_semester, 'Lab_Name': lab_name})
#             else: # For other departments like ECE, EEE
#                 # The original logic had a specific check for semester == 2 and then N/A for others.
#                 # Assuming you want to fetch courses for non-CSE students as well, but only if they offer courses.
#                 # If specific courses are tied to non-CSE departments and specific semesters,
#                 # you'd need to adjust the query logic here. For now, mirroring original behavior.
#                 if semester == 2: # Example for a specific semester in other departments
#                     cursor.execute("SELECT Code, Course_Name, Semester FROM COURSE WHERE Semester = %s", (semester,))
#                     courses_data = cursor.fetchall()
#                     for course_code, course_name, course_semester in courses_data:
#                         cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (course_code,))
#                         roomno_result = cursor.fetchone()
                        
#                         lab_name = 'N/A'
#                         if roomno_result:
#                             roomno = int(roomno_result[0])
#                             cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
#                             labname_result = cursor.fetchone()
#                             if labname_result:
#                                 lab_name = labname_result[0]
#                         courses.append({'Code': course_code, 'Course_Name': course_name, 'Semester': course_semester, 'Lab_Name': lab_name})
#                 # If not semester 2 and not CSE, then courses and labnames remain empty, matching original logic.
        
#         return render_template('course_details.html', courses=courses) # Changed to send 'courses' directly
    
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/reset_password', methods=['GET', 'POST'])
# def reset_password():
#     """Handles password reset verification and rendering the reset form."""
#     conn = None
#     cursor = None
#     try:
#         if request.method == 'POST':
#             sid = request.form.get('sid')
#             dob = request.form.get('dob') # Ensure DOB format matches your database 'YYYY-MM-DD'

#             if sid and dob:
#                 conn = get_db_connection()
#                 if conn is None:
#                     return "Database connection error.", 500
#                 cursor = conn.cursor(buffered=True)
#                 cursor.execute("SELECT SID FROM STUDENT WHERE SID = %s AND DOB = %s", (sid, dob))
#                 student_exists = cursor.fetchone()

#                 if student_exists:
#                     session['reset_sid'] = sid # Store SID temporarily for password update
#                     return render_template('reset_password.html', sid=sid, verified=True)
#                 else:
#                     return "Verification failed! Invalid SID or Date of Birth.", 401
#             else:
#                 return "SID and Date of Birth are required!", 400

#         return render_template('reset_password.html', verified=False)
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/update_password', methods=['POST'])
# def update_password():
#     """Handles updating the password for a student after verification."""
#     conn = None
#     cursor = None
#     try:
#         # Assuming the SID for update comes from a hidden field in the reset_password.html form
#         # or from the session if it was stored there after verification.
#         # It's safer to use a session variable for security.
#         sid_to_update = session.get('reset_sid') 
#         if not sid_to_update:
#             return "Unauthorized password update attempt.", 403

#         old_password = request.form['old_password'] # This field might not be present if it's a "forgot password" flow.
#                                                   # If it's a *reset* flow after verification, old_password isn't needed.
#                                                   # Assuming it's for verification against current password.
#         new_password = request.form['new_password']
#         confirm_password = request.form['confirm_password']

#         if new_password != confirm_password:
#             return "New passwords do not match!", 400

#         conn = get_db_connection()
#         if conn is None:
#             return "Database connection error.", 500
#         cursor = conn.cursor(buffered=True)

#         # First, verify the old password (if applicable in your reset flow)
#         cursor.execute("SELECT Password FROM STUDENT WHERE SID = %s", (sid_to_update,))
#         result = cursor.fetchone()

#         if result is None:
#             return "Student not found!", 404

#         stored_password = result[0]
#         # If this is a *forgot* password flow, you might not check old_password.
#         # If it's a "change password while logged in" flow, you'd check old_password.
#         # Given your 'reset_password' context, it's likely a *forgot* flow, so checking old_password here might be wrong.
#         # I'm keeping the check based on your original code, but consider if 'old_password' is truly required in this context.
#         if stored_password != old_password:
#             return "Old password is incorrect!", 401

#         cursor.execute("UPDATE STUDENT SET Password = %s WHERE SID = %s", (new_password, sid_to_update))
#         conn.commit()

#         # Clear the temporary session variable after successful reset
#         session.pop('reset_sid', None) 
#         return redirect(url_for('index', message='Password updated successfully. Please login with your new password.'))

#     except mysql.connector.Error as err:
#         print(f"Database Error during password update: {err}")
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/staff_dashboard')
# def staff_dashboard():
#     """Renders the staff dashboard if authenticated as staff."""
#     # Check if logged in and if user_type is 'staff'
#     if 'logged_in' not in session or session.get('user_type') != 'staff':
#         return redirect(url_for('index', error='Access denied. Please log in as staff.'))
    
#     conn = None
#     cursor = None
#     try:
#         user_id = session['user_id']
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)

#         cursor.execute("SELECT Name FROM LABSTAFF WHERE ID = %s", (user_id,))
#         staff_name_result = cursor.fetchone()
        
#         staff_name = staff_name_result[0] if staff_name_result else "Unknown Staff"
        
#         return render_template('staff_dashboard.html', staff_name=staff_name, staff_id=user_id) # Pass staff_id too
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/student_details')
# def student_details():
#     """Fetches and renders all student details (accessible by staff)."""
#     # Assuming this route is for staff, add a check
#     if 'logged_in' not in session or session.get('user_type') != 'staff':
#         return redirect(url_for('index', error='Access denied. Please log in as staff.'))

#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)
#         cursor.execute("SELECT * FROM STUDENT")
#         students = cursor.fetchall()
#         return render_template('student_details.html', students=students)
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/component_details')
# def component_details():
#     """Fetches and renders all component details (accessible by staff)."""
#     # Assuming this route is for staff, add a check
#     if 'logged_in' not in session or session.get('user_type') != 'staff':
#         return redirect(url_for('index', error='Access denied. Please log in as staff.'))

#     conn = None
#     cursor = None
#     try:
#         conn = get_db_connection()
#         if conn is None:
#             return redirect(url_for('index', error='Database connection error.'))
#         cursor = conn.cursor(buffered=True)
#         cursor.execute("SELECT * FROM COMPONENTS")
#         components = cursor.fetchall()
#         return render_template('component_details.html', components=components)
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()


# @app.route('/staff_signup', methods=['GET', 'POST'])
# def staff_signup():
#     """Handles staff registration."""
#     conn = None
#     cursor = None
#     try:
#         if request.method == 'POST':
#             staff_id = request.form['id']
#             name = request.form['name']
#             role = request.form['role']
#             password = request.form['password']
#             confirm_password = request.form['confirm_password']

#             if password != confirm_password:
#                 return "Passwords do not match!", 400

#             conn = get_db_connection()
#             if conn is None:
#                 return "Database connection error.", 500
#             cursor = conn.cursor()
            
#             cursor.execute("INSERT INTO LABSTAFF (ID, Name, Roles, Password) VALUES (%s, %s, %s, %s)", 
#                            (staff_id, name, role, password))
#             conn.commit()
#             return redirect(url_for('index')) # Redirect to the main login page after signup (no staff_login route needed)
        
#         return render_template('staff_signup.html')
#     except mysql.connector.Error as err:
#         return f"Database Error: {err}", 500
#     except Exception as e:
#         return f"An unexpected error occurred: {e}", 500
#     finally:
#         if cursor is not None:
#             cursor.close()
#         if conn is not None and conn.is_connected():
#             conn.close()

# @app.route('/logout')
# def logout():
#     """Logs out the current user by clearing session variables."""
#     session.pop('logged_in', None)
#     session.pop('user_id', None)
#     session.pop('user_type', None)
#     session.pop('reset_sid', None) # Clear reset_sid if it exists
#     return redirect(url_for('index', message='You have been logged out.'))


# if __name__ == '__main__':
#     app.run(debug=True)
























# # from datetime import datetime
# # from flask import Flask, render_template, request, jsonify, redirect, url_for, session
# # import mysql.connector

# # app = Flask(__name__)
# # app.secret_key = 'your_secret_key' 

# # db = mysql.connector.connect(
# #     host="localhost",
# #     user="root",  
# #     password="", 
# #     database="LAB_MANAGEMENT"
# # )
# # cursor = db.cursor()

# # @app.route('/')
# # def index():
# #     return render_template('index.html')


# # @app.route('/login', methods=['GET', 'POST'])
# # def login():
# #     if request.method == 'POST':
# #         sid = request.form['sid']
# #         password = request.form['password']
        
# #         cursor.execute("SELECT * FROM STUDENT WHERE SID = %s AND Password = %s", (sid, password))
# #         student = cursor.fetchone()
        
# #         if student:
# #             session['sid'] = student[0]  
# #             return redirect(url_for('dashboard'))  
# #         else:
# #             return "Invalid SID or Password!", 401
    
# #     return render_template('login.html')



# # @app.route('/signup', methods=['GET', 'POST'])
# # def signup():
# #     if request.method == 'POST':
# #         sid = request.form['sid']
# #         roll_no = int(request.form['roll_no'])
# #         name = request.form['name']
# #         semester = int(request.form['semester'])
# #         department = request.form['department']
# #         dob = request.form['dob']
# #         password = request.form['password']
# #         confirm_password = request.form['confirm_password']

# #         if not (1 <= roll_no <= 200):
# #             return "Roll number must be between 001 and 200!", 400

# #         if not (1 <= semester <= 8):
# #             return "Semester must be between 1 and 8!", 400

# #         dob_date = datetime.strptime(dob, '%Y-%m-%d')
# #         age = (datetime.now() - dob_date).days // 365
# #         if age < 17:
# #             return "You must be at least 17 years old!", 400

# #         if password != confirm_password:
# #             return "Passwords do not match!", 400

# #         try:
# #             cursor.execute("INSERT INTO STUDENT (SID, RollNo, Name, Semester, Department, DOB, Password) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
# #                            (sid, roll_no, name, semester, department, dob, password))
# #             db.commit()
# #             return redirect(url_for('login')) 
# #         except mysql.connector.Error as err:
# #             return f"Error: {err}", 400

# #     return render_template('signup.html')

# # @app.route('/dashboard')
# # def dashboard():
# #     if 'sid' not in session:
# #         return redirect(url_for('login')) 
    
# #     sid = session['sid']
# #     cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (sid,))
# #     student = cursor.fetchone()
    
# #     return render_template('dashboard.html', student=student)

# # @app.route('/personal_details')
# # def personal_details():
# #     if 'sid' not in session:
# #         return redirect(url_for('login'))
    
# #     sid = session['sid']
# #     cursor.execute("SELECT * FROM STUDENT WHERE SID = %s", (sid,))
# #     student = cursor.fetchone()
# #     formatted_dob = student[5].strftime('%d-%m-%Y')

# #     return jsonify({
# #         'SID': student[0],
# #         'RollNo': student[1],
# #         'Name': student[2],
# #         'Semester': student[3],
# #         'Department': student[4],
# #         'DOB': formatted_dob,
# #     })

# # @app.route('/course_details')
# # def course_details():
# #     courses = []
# #     labnames = []
# #     if 'sid' not in session:
# #         return redirect(url_for('login'))
    
# #     sid = session['sid']
# #     cursor.execute("SELECT Semester, Department FROM STUDENT WHERE SID = %s", (sid,))
# #     result = cursor.fetchone()

# #     semester = result[0]
# #     dept = result[1]
# #     if dept == 'CSE':
# #         cursor.execute("SELECT * FROM COURSE WHERE Semester = %s", (semester,))
# #         courses = cursor.fetchall()
# #         length = len(courses)
        
# #         for course in courses:
# #             code = course[0]
# #             cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (code,))
# #             roomno_result = cursor.fetchone()
            
# #             if roomno_result:
# #                 roomno = int(roomno_result[0])
# #                 cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
# #                 labname = cursor.fetchone()
# #                 labnames.append(labname)
# #     else:
# #         if semester == 2:
# #             cursor.execute("SELECT * FROM COURSE WHERE Semester = %s", (semester,))
# #             courses = cursor.fetchall()
# #             length = len(courses)
            
# #             for course in courses:
# #                 code = course[0]
# #                 cursor.execute("SELECT RoomNo FROM OFFERS WHERE Code = %s", (code,))
# #                 roomno_result = cursor.fetchone()
                
# #                 if roomno_result:
# #                     roomno = int(roomno_result[0])
# #                     cursor.execute("SELECT Lab_Name FROM LAB WHERE RoomNo = %s", (roomno,))
# #                     labname = cursor.fetchone()
# #                     labnames.append(labname)
# #         else:
# #             labnames=None
# #             courses=None
# #             length=0 
    
    

# #     return render_template('course_details.html', length=length, courses=courses, labnames=labnames)

# # @app.route('/reset_password', methods=['GET', 'POST'])
# # def reset_password():
# #     if request.method == 'POST':
# #         sid = request.form.get('sid')
# #         dob = request.form.get('dob')

# #         if sid and dob:
# #             cursor.execute("SELECT * FROM STUDENT WHERE SID = %s AND DOB = %s", (sid, dob))
# #             student = cursor.fetchone()

# #             if student:
# #                 session['sid'] = sid
# #                 return render_template('reset_password.html', sid=sid, verified=True)
# #             else:
# #                 return "Verification failed! Invalid SID or DOB.", 401
# #         else:
# #             return "SID and Date of Birth are required!", 400

# #     return render_template('reset_password.html', verified=False)

# # @app.route('/update_password', methods=['POST'])
# # def update_password():
# #     sid = request.form['sid']
# #     old_password = request.form['old_password']
# #     new_password = request.form['new_password']
# #     confirm_password = request.form['confirm_password']

# #     print(f"Received SID: {sid}, Old Password: {old_password}, New Password: {new_password}, Confirm Password: {confirm_password}") 

# #     if new_password != confirm_password:
# #         return "New passwords do not match!", 400

# #     cursor.execute("SELECT Password FROM STUDENT WHERE SID = %s", (sid,))
# #     result = cursor.fetchone()

# #     if result is None:
# #         return "Student not found!", 404

# #     stored_password = result[0]
# #     if stored_password != old_password:
# #         return "Old password is incorrect!", 401

# #     cursor.execute("UPDATE STUDENT SET Password = %s WHERE SID = %s", (new_password, sid))
# #     db.commit()
# #     return redirect(url_for('login')) 


# # def staff_dashboard():
    
# #     if 'id' not in session:
# #         return redirect(url_for('staff_login'))
    
# #     id = session['id']
# #     cursor.execute("SELECT Name FROM LABSTAFF WHERE ID = %s", (id,))
# #     staff = cursor.fetchone()
    
# #     return render_template('staff_dashboard.html',  staff_name=staff)

# # @app.route('/student_details')
# # def student_details():
# #     cursor.execute("SELECT * FROM STUDENT")
# #     students = cursor.fetchall()
# #     return render_template('student_details.html', students=students)

# # @app.route('/component_details')
# # def component_details():
# #     cursor.execute("SELECT * FROM COMPONENTS")
# #     components = cursor.fetchall()
# #     return render_template('component_details.html', components=components)

# # @app.route('/staff_signup', methods=['GET', 'POST'])
# # def staff_signup():
# #     if request.method == 'POST':
# #         staff_id = request.form['id']
# #         name = request.form['name']
# #         role = request.form['role']
# #         password = request.form['password']
# #         confirm_password = request.form['confirm_password']

# #         if password != confirm_password:
# #             return "Passwords do not match!", 400

# #         try:
# #             cursor.execute("INSERT INTO LABSTAFF (ID, Name, Roles, Password) VALUES (%s, %s, %s, %s)", 
# #                            (staff_id, name, role, password))
# #             db.commit()
# #             return redirect(url_for('staff_login'))  
# #         except mysql.connector.Error as err:
# #             return f"Error: {err}", 400

# #     return render_template('staff_signup.html')

# # if __name__ == '__main__':
# #     app.run(debug=True)