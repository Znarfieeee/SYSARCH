from flask import Flask, render_template, redirect, session, url_for, request, flash, jsonify, send_file
from dbhelper import *
import urllib.request, os
from werkzeug.utils import secure_filename
from staff_app import staff_app
from datetime import datetime  # Ensure datetime is properly imported
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

app = Flask(__name__, static_folder='static')
app.secret_key = "!@#$%12345"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static/user_img'
app.register_blueprint(staff_app)

def allowed_file(filename):
    allowed_externsions = set(['png', 'jpg', 'jpeg', 'gif'])    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_externsions

@app.after_request
def addheader(response):
    response.headers['Content-Type'] = 'no-cache, no-store, must-revalidate, private'
    response.headers["Pragma"] = 'no-cache'
    response.headers["Expires"] = "0"
    return response

@app.template_filter('datetimeformat')
def datetimeformat(value, format="%b %d, %Y %H:%M"):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime(format)

# Functionalities for Student
def json_response(message, status='success', data=None, code=200):
    response = {
        'message': message,
        'status': status
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        sql = "SELECT * FROM users WHERE username = ? AND password = ?"
        user = getallprocess(sql, (username, password))

        if user:
            flash("Log in successful.", "success")
            session['logged_in'] = True
            
            # Simplify - just use points directly from users table
            session['user'] = {
                "idno": user[0]['idno'],
                "firstname": user[0]['firstname'],
                "lastname": user[0]['lastname'],
                "middlename": user[0]['middlename'] or '',
                "username": user[0]['username'],
                "email": user[0]['email'],
                "password": user[0]['password'],
                "course": user[0]['course'],
                "sessions": int(user[0]['no_session']) if user[0]['no_session'] is not None and user[0]['no_session'] != 'None' else 0,
                "yr_lvl": user[0]['yr_lvl'],
                "photo": user[0]['photo'],
                "points": int(user[0]['points']) if 'points' in user[0] and user[0]['points'] is not None else 0,
                "role": user[0]['role']
            }
            if session['user']['role'] == 'staff' or session['user']['role'] == 'admin':
                return redirect(url_for('staff_app.staff_dashboard'))
            else:
                return redirect(url_for('home'))
        elif not username :
            flash("Input Username", "error")
        
        elif not password:
            flash("Input Password", "error")
        
        else:
            flash("Invalid Username or Password.", "error")

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()    
    flash("Logged out successful.", "success")
    return redirect(url_for('login'))
        
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        idno = request.form.get('idno')
        lastname = request.form.get('lastname')
        firstname = request.form.get('firstname')
        middlename = request.form.get('middlename')
        course = request.form.get('course')
        yr_lvl = request.form.get('yr_lvl')
        email = request.form.get('email')
        password = request.form.get('password')
        username = idno
        role = 'student'
        no_session = None

        # para check sa role base sa idno
        if '-' in idno:
            prefix, number = idno.split('-')
            if prefix in ['staff']:
                role = 'staff'
            elif prefix in ['admin']:
                role = 'admin'
                
        # Validate sa length sa idno
        if role == 'student' and len(idno) != 8:
            flash("Invalid ID number. Student IDNO must be 8 digits.", "error")
            return redirect(url_for('register'))
        elif role in ['staff', 'admin'] and len(idno) != 14:
            flash("Invalid ID number. IDNO must be 14 characters.", "error")
            return redirect(url_for('register'))
        
        # Validate course and year level sa students
        if role == 'student':
            if not course or not yr_lvl:
                flash("Course and Year Level are required.", "error")
                return redirect(url_for('register'))
                
            if course in ['bsit', 'bscs', 'bscpe']:
                no_session = 30
            else:
                no_session = 15
        
        # Validate email
        allowed_domains = ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com']        
        if not any(email.endswith(domain) for domain in allowed_domains):
            flash("Invalid email address", "error")
            return redirect(url_for('register'))

        # Validate required fields
        if not idno or not lastname or not firstname  or not email or not password:
            flash("All fields are required.", "error")
                        
        success = addprocess('users', idno=idno, lastname=lastname, 
                            firstname=firstname, middlename=middlename, 
                            course=course, yr_lvl=yr_lvl, email=email, 
                            username=username, password=password, role=role, 
                            no_session=no_session)

        if success:
            flash("Registration successful.", "success")
            return redirect(url_for('login'))
        else:
            flash("Registration failed.", "error")
            return redirect(url_for('register'))

    return render_template("register.html")

# Student Navigation
@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Dashboard'
    
    sql = "select id, title, content, created_at from announcement order by created_at desc"
    success = getallprocess(sql)
    
    if success:
        announcements = [dict(row) for row in success]
    else:
        announcements = []
    
    user = session['user']
    
    # Get points DIRECTLY from users table - this is the most reliable source
    user_sql = "SELECT points, no_session FROM users WHERE idno = ?"
    user_data = getallprocess(user_sql, (user['idno'],))
    
    if user_data and len(user_data) > 0:
        # Convert to integer to avoid type issues, handle None values properly
        user['points'] = int(user_data[0]['points']) if user_data[0]['points'] is not None else 0
        # Handle no_session properly - check for both None and 'None' string
        no_session = user_data[0]['no_session']
        user['sessions'] = int(no_session) if no_session is not None and no_session != 'None' else 0
    else:
        user['points'] = 0
        user['sessions'] = 0
        
    # Update the session with the latest points
    session['user'] = user
    
    return render_template("student/dashboard.html", user=user, pagetitle=pagetitle, announcements=announcements)
    
@app.route('/history')
def history():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Sit-in History'

    
    return render_template('student/history.html', pagetitle=pagetitle)

@app.route('/sitin')
def sitin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Sit-in'
    user = session.get('user')
    
    # Get approved reservations for the current user
    sql = """
        SELECT r.*, a.start_time, a.end_time
        FROM reservations r
        LEFT JOIN attendancelog a ON r.id = a.reserve_id
        WHERE r.idno = ? AND r.status = 'approved'
        AND r.date >= date('now')
        ORDER BY r.date ASC, r.time_start ASC
    """
    reservations = getallprocess(sql, (user['idno'],))
    
    return render_template('student/sitin.html', 
                         pagetitle=pagetitle, 
                         user=user,
                         reservations=reservations)

@app.route('/reservation')
def reservation():
    pagetitle = 'Reservation'
    
    return render_template('student/reservation.html', pagetitle=pagetitle)

@app.route('/schedule')
def lab():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Schedule'
    
    # Get unique lab room numbers
    lab_rooms_sql = """
    SELECT DISTINCT labno 
    FROM lab_schedule 
    ORDER BY labno
    """
    lab_rooms_data = getallprocess(lab_rooms_sql)
    
    # Initialize an empty list for lab rooms with their schedules
    lab_rooms = []
    
    if lab_rooms_data:
        # Process each lab room
        for room_data in lab_rooms_data:
            labno = room_data['labno']
            
            # Get schedules for this lab room
            schedules_sql = """
            SELECT id, labno, time, day, created_at
            FROM lab_schedule
            WHERE labno = ?
            ORDER BY day, time
            """
            schedules_data = getallprocess(schedules_sql, (labno,))
            
            # Get PC status for this lab room
            pc_status_sql = """
            SELECT COUNT(*) as total_pcs,
                   SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available_pcs
            FROM pc_status
            WHERE lab_no = ?
            """
            pc_status_data = getallprocess(pc_status_sql, (labno,))
            
            # Extract floor from room number (assuming format like '301' where '3' is the floor)
            floor = labno[0] if len(labno) > 0 else '?'
            
            # Process schedule data
            schedules = []
            day_colors = {
                'MONDAY': 'blue',
                'TUESDAY': 'yellow',
                'WEDNESDAY': 'green',
                'THURSDAY': 'red',
                'FRIDAY': 'purple',
                'SATURDAY': 'pink',
                'SUNDAY': 'gray'
            }
            
            days = []
            
            if schedules_data:
                for schedule in schedules_data:
                    day = schedule['day'].upper()
                    days.append(day.lower())
                    
                    # Determine time category based on time value
                    time = schedule['time']
                    time_category = 'morning'
                    
                    if time:
                        # Parse the time string to determine category
                        if 'PM' in time and not time.startswith('12:'):
                            if any(hour in time for hour in ['1:', '2:', '3:', '4:', '5:']):
                                time_category = 'afternoon'
                            else:
                                time_category = 'evening'
                    
                    schedules.append({
                        'day': day,
                        'time': time,
                        'time_category': time_category,
                        'color': day_colors.get(day, 'gray'),
                        'subject_code': f"CS{labno} - Lab Session",  # Placeholder
                        'instructor': "Lab Instructor"  # Placeholder
                    })
            
            # Get PC counts
            total_pcs = 0
            available_pcs = 0
            
            if pc_status_data and len(pc_status_data) > 0:
                # Use direct indexing instead of .get() method
                total_pcs = pc_status_data[0]['total_pcs'] if 'total_pcs' in pc_status_data[0] else 0
                available_pcs = pc_status_data[0]['available_pcs'] if 'available_pcs' in pc_status_data[0] else 0
            
            # Create room object
            room = {
                'labno': labno,
                'floor': floor,
                'schedules': schedules,
                'days': list(set(days)),  # Unique days
                'total_pcs': total_pcs,
                'available_pcs': available_pcs
            }
            
            lab_rooms.append(room)
    
    return render_template('student/schedule.html', pagetitle=pagetitle, lab_rooms=lab_rooms)
        
@app.route('/resources')
def resources():
    pagetitle = 'Resources'
    
    sql_resources = "SELECT * FROM resources ORDER BY updated_at DESC"
    sql_materials = "SELECT * FROM materials ORDER BY updated_at DESC"
    
    resources = getallprocess(sql_resources)
    materials = getallprocess(sql_materials) 
    
    return render_template('student/resources.html', pagetitle=pagetitle, resources=resources, materials=materials)

@app.route('/reservation/<int:id>', methods=['DELETE'])
def delete_reservation(id):
    try:
        success = deleteprocess('reservations', id)
        
        if success:
            return json_response('Reservation cancelled successfully')
        return json_response('Failed to cancel reservation', 'error', code=400)

    except Exception as e:
        return json_response(str(e), 'error', code=500)

@app.route('/edit', methods=['POST'])
def editStudent():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    photo = request.files.get('photo')
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    middlename = request.form.get('middlename')
    yr_lvl = request.form.get('yearLevel')
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Save the current points value before updating
    current_points = session['user'].get('points', 0)
    current_sessions = session['user'].get('sessions', 0)
            
    if 'photo' in request.files and photo.filename != '':
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)
            session['user']['photo'] = photo_path
        else:
            flash("File type not allowed", "error")
            return redirect(url_for('home'))
    else:
        photo_path = session['user']['photo']
         
    
    # Check if password was provided
    if password:
        sql = "UPDATE users SET photo =?, firstname =?, lastname =?, middlename =?, yr_lvl =?, email =?, password =? WHERE idno =?"
        values = (photo_path, firstname, lastname, middlename, yr_lvl, email, password, session['user']['idno'])
    else:
        sql = "UPDATE users SET photo =?, firstname =?, lastname =?, middlename =?, yr_lvl =?, email =? WHERE idno =?"
        values = (photo_path, firstname, lastname, middlename, yr_lvl, email, session['user']['idno'])
    success = postprocess(sql, values)
    
    session['user'].update({
            "photo": photo_path,
            "firstname": firstname,
            "lastname": lastname,
            "middlename": middlename or '',
            "yr_lvl": yr_lvl,
            "email": email,
            "password": password if password else session['user']['password'],
            "points": current_points,
            "sessions": current_sessions
        })
    
    if success:
        flash("Account Profile updated.", "success")
        return redirect(url_for('home'))
    
    else:
        flash("Account Profile update failed.", "error")
        
    return redirect(url_for('home'))


@app.route('/get_reservations')
def get_reservations():
    idno = session['user']['idno']
    sql = "SELECT * FROM reservations WHERE idno = ? ORDER BY created_at DESC"
    reservations = getallprocess(sql, (idno,))
    
    data  = []
    for res in reservations:
        data.append({
            "id": res['id'],
            # "date": datetime.strptime(res['date'], '%Y %b %d').strftime('%Y-%m-%d') if res['date'] else '',
            "date": res['date'],
            "time_start": res['time_start'],
            "time_end": res['time_end'],
            "labno": res['labno'],
            "purpose": res['purpose'],
            "status": res['status'],
            "date_created": res['created_at']
        })
    
    return jsonify(data)

@app.route('/book', methods=['POST'])
def book():
    try:
        # Get idno directly from session['user']
        if not session.get('logged_in') or 'user' not in session:
            flash("Please log in to make a reservation", "error")
            return redirect(url_for('login'))
            
        idno = session['user']['idno']
        date = request.form.get('date')
        time_start = request.form.get('time-start')
        time_end = request.form.get('time-end')
        labno = request.form.get('labno')
        purpose = request.form.get('purpose')
        pcno = request.form.get('pcno')  # Get PC number from form
        status = "pending"
        
        # Validate required fields
        if not all([date, time_start, time_end, labno, purpose, pcno]):
            missing_fields = []
            if not date: missing_fields.append("date")
            if not time_start: missing_fields.append("start time")
            if not time_end: missing_fields.append("end time")
            if not labno: missing_fields.append("laboratory")
            if not purpose: missing_fields.append("purpose")
            if not pcno: missing_fields.append("PC number")
            
            flash(f"Reservation failed. Missing required fields: {', '.join(missing_fields)}", "error")
            return redirect(url_for('reservation'))
        
        # Validate time
        try:
            # Convert to time objects for comparison
            t_start = datetime.strptime(time_start, '%H:%M').time()
            t_end = datetime.strptime(time_end, '%H:%M').time()
            
            if t_start >= t_end:
                flash("End time must be after start time", "error")
                return redirect(url_for('reservation'))
        except ValueError:
            flash("Invalid time format", "error")
            return redirect(url_for('reservation'))
            
        # Check remaining sessions
        user_sql = "SELECT no_session FROM users WHERE idno = ?"
        user_data = getallprocess(user_sql, (idno,))
        
        if user_data and len(user_data) > 0:
            no_session = user_data[0]['no_session']
            sessions = int(no_session) if no_session is not None and no_session != 'None' else 0
            if sessions <= 0:
                flash("You have no remaining sessions", "error")
                return redirect(url_for('reservation'))
        
        # Check PC availability (if data exists)
        pc_sql = "SELECT is_available FROM pc_status WHERE lab_no = ? AND pc_number =?"
        pc_data = getallprocess(pc_sql, (labno, pcno))
        
        # Only check PC availability if data exists
        if pc_data and len(pc_data) > 0:
            # Convert is_available to boolean properly
            is_available = pc_data[0]['is_available']
            if isinstance(is_available, str):
                is_available = is_available.lower() in ['true', '1', 'yes']
            else:
                is_available = bool(is_available)
                
            if not is_available:
                flash("Selected PC is not available", "error")
                return redirect(url_for('reservation'))
        else:
            # If no PC status data exists, assume PC is available
            app.logger.info(f"No PC status data found for PC {pcno} in lab {labno}. Assuming PC is available.")
        
        # Check if PC is already reserved for the same time period
        existing_reservation_sql = """
            SELECT id FROM reservations 
            WHERE labno = ? AND pcno = ? AND date = ? AND status != 'denied'
            AND ((time_start <= ? AND time_end > ?) OR (time_start < ? AND time_end >= ?) OR (time_start >= ? AND time_end <= ?))
        """
        existing_reservation = getallprocess(existing_reservation_sql, 
            (labno, pcno, date, time_start, time_start, time_end, time_end, time_start, time_end))
            
        if existing_reservation and len(existing_reservation) > 0:
            flash("This PC is already reserved for the selected time period", "error")
            return redirect(url_for('reservation'))
        
        # Add additional data to reservations
        success = addprocess('reservations', idno=idno, date=date, 
                         time_start=time_start, time_end=time_end, 
                         labno=labno, purpose=purpose, status=status,
                         pcno=pcno)
        
        if success:
            flash("Reservation successful.", "success")
        else:
            flash("Reservation failed.", "error")

        return redirect(url_for('reservation'))
    except Exception as e:
        app.logger.error(f"Reservation error: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('reservation'))

@app.route('/api/sitin/active')
def get_active_sitins_route():
    try:
        if not session.get('logged_in'):
            flash("Not authenticated", "error")
            return redirect(url_for('login'))
            
        sitins = get_active_sitins()
        
        # Add additional debugging information
        if sitins:
            return jsonify([dict(row) for row in sitins])
        return jsonify([])
        
    except Exception as e:

        return jsonify({'error': str(e)}), 500

# @app.route('/api/check-in/<int:reservation_id>', methods=['POST'])
# def check_in(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the reservation details
        reservation = get_reservation_details(reservation_id)
        if not reservation:
            return jsonify({'error': 'Reservation not found'}), 404
            
        success = start_sitin(reservation_id)
        
        if success:
            return jsonify({'message': 'Check-in successful'}), 200
        return jsonify({'error': 'Failed to check in'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reservation/<int:reservation_id>/edit', methods=['POST'])
def edit_reservation(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # First check if the reservation exists and get its status
        sql = "SELECT status FROM reservations WHERE id = ?"
        reservation = getallprocess(sql, (reservation_id,))
        
        if not reservation:
            return jsonify({'error': 'Reservation not found'}), 404
            
        # Check if the status is pending
        if reservation[0]['status'] != 'pending':
            return jsonify({'error': 'Only pending reservations can be edited'}), 403

        # Retrieve form data
        date = request.form.get('date')
        time_start = request.form.get('time_start')
        time_end = request.form.get('time_end')
        labno = request.form.get('labno')
        purpose = request.form.get('purpose')

        try:
            # Convert the ISO date (YYYY-MM-DD) to the required format (YYYY Mon DD)
            parsed_date = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = parsed_date.strftime('%Y %b %d')
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # Prepare data for update
        update_data = {
            'id': reservation_id,
            'date': formatted_date,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'time_start': time_start,
            'time_end': time_end,
            'labno': labno,
            'purpose': purpose
        }

        # Update the reservation
        success = updateprocess('reservations', **update_data)

        if success:
            return jsonify({'message': 'Reservation updated successfully'}), 200
        return jsonify({'error': 'Failed to update reservation'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-sitins')
def get_user_sitins():
    try:
        # Ensure the user is logged in
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401

        # Get the user object from the session
        user = session.get('user')
        if not user or 'idno' not in user:
            return jsonify({'error': 'User information is missing'}), 400

        idno = user['idno']

        # SQL query to fetch sit-in history for a specific user
        sql = """
            SELECT 
                a.idno,
                u.firstname,
                u.lastname,
                strftime('%H:%M %p', a.start_time) AS start_time,
                strftime('%H:%M %p', a.end_time) AS end_time,
                strftime('%Y-%m-%d', a.start_time) AS date,
                a.purpose,
                a.labno
            FROM active_sitin a
            JOIN users u ON a.idno = u.idno
            WHERE a.status = 'done' AND a.idno = ?
            ORDER BY a.id DESC;
        """
        
        # Fetch data from the database
        sitins = getallprocess(sql, (idno,))
        
        # Convert the results to a list of dictionaries
        if sitins:
            result = []
            for row in sitins:
                result.append({
                    'idno': row['idno'],
                    'firstname': row['firstname'],
                    'lastname': row['lastname'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'date': row['date'],
                    'purpose': row['purpose'],
                    'labno': row['labno']
                })
            return jsonify(result), 200
        
        # Return an empty list if no sit-ins are found
        return jsonify([]), 200
    
    except Exception as e:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    
@app.route('/api/feedback', methods=['POST'])
def add_feedback(): 
    try:
        data = request.json
        
        sitin_id = data.get('sitin_id')
        rating = data.get('rating')
        idno = session['user']['idno']
        comments = data.get('comments')
        issues = ','.join(data.get('issues', [])).upper() if data.get('issues') else 'No Issues'
        
        # Get labno from active_sitin - modified to work with completed sit-ins
        sql = """
            SELECT labno 
            FROM active_sitin 
            WHERE id = ? 
            AND (status = 'active' OR status = 'done')
        """
        result = getallprocess(sql, (sitin_id,))
        if not result:
            return jsonify({
                'message': 'Could not find sit-in session', 
                'status': 'error'
            }), 404
            
        labno = result[0]['labno']
        
        if not all([sitin_id, rating, comments]):
            return jsonify({
                'message': 'Missing required fields', 
                'status': 'error',
                'details': {
                    'sitin_id': not sitin_id,
                    'rating': not rating,
                    'comments': not comments
                }
            }), 400
        
        # Check if feedback already exists for this sit-in
        check_sql = "SELECT id FROM feedbacks WHERE sitin_id = ?"
        existing_feedback = getallprocess(check_sql, (sitin_id,))
        
        if existing_feedback:
            # Update existing feedback instead of creating a new one
            update_sql = """
                UPDATE feedbacks 
                SET rating = ?, comments = ?, issues = ?, updated_at = datetime('now')
                WHERE sitin_id = ?
            """
            success = postprocess(update_sql, (rating, comments, issues, sitin_id))
            feedback_action = "updated"
        else:
            # Create new feedback
            success = addprocess('feedbacks', sitin_id=sitin_id, rating=rating, 
                            comments=comments, issues=issues, idno=idno, labno=labno)
            feedback_action = "submitted"
        
        if not success:
            return jsonify({
                'message': 'Failed to save feedback', 
                'status': 'error'
            }), 500
        
        return jsonify({
            'message': f'Feedback {feedback_action} successfully!', 
            'status': 'success'
        }), 200
    
    except Exception as e:
        print(f"Error in /api/feedback: {e}")
        return jsonify({
            'message': 'Internal server error', 
            'status': 'error',
            'details': str(e)
        }), 500

@app.route('/api/pc-status/<int:lab_no>')
def get_pc_status(lab_no):
    try:
        # Get PC status for this lab room
        pc_status_sql = """
        SELECT pc_number, is_available, updated_at
        FROM pc_status
        WHERE lab_no = ?
        ORDER BY pc_number
        """
        pc_status_data = getallprocess(pc_status_sql, (lab_no,))
        
        # Get total count and available count
        count_sql = """
        SELECT COUNT(*) as total_pcs,
               SUM(CASE WHEN is_available = 1 THEN 1 ELSE 0 END) as available_pcs
        FROM pc_status
        WHERE lab_no = ?
        """
        count_data = getallprocess(count_sql, (lab_no,))
        
        # Convert Row objects to dictionaries for proper JSON serialization
        pc_status_json = []
        if pc_status_data:
            for row in pc_status_data:
                pc_dict = dict(row)
                # Ensure consistent boolean value for is_available
                if 'is_available' in pc_dict:
                    pc_dict['is_available'] = bool(pc_dict['is_available'])
                pc_status_json.append(pc_dict)
        
        # Check if we got any data at all
        if not pc_status_json:
            # If no data exists for this lab, create some dummy entries for testing
            # This is only used in development/testing - should be removed in production
            if app.debug:
                # Create 10 dummy PCs with random availability
                import random
                for i in range(1, 11):
                    pc_status_json.append({
                        'pc_number': i,
                        'is_available': bool(random.choice([0, 1])),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        # Extract count data safely, providing defaults if missing
        total_pcs = 0
        available_pcs = 0
        
        if count_data and len(count_data) > 0:
            count_dict = dict(count_data[0])
            total_pcs = int(count_dict.get('total_pcs', 0) or 0)
            available_pcs = int(count_dict.get('available_pcs', 0) or 0)
        elif pc_status_json:  # If we have PC data but no count data
            total_pcs = len(pc_status_json)
            available_pcs = sum(1 for pc in pc_status_json if pc.get('is_available'))
            
        # Prepare result with proper type handling
        result = {
            'lab_no': lab_no,
            'pc_status': pc_status_json,
            'total_pcs': total_pcs,
            'available_pcs': available_pcs,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(result)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error(f"PC status error for lab {lab_no}: {str(e)}\n{error_details}")
        return jsonify({
            'error': str(e),
            'lab_no': lab_no,
            'pc_status': [],
            'total_pcs': 0,
            'available_pcs': 0,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@app.route('/api/download/<resource_type>/<int:resource_id>')
def download_resource(resource_type, resource_id):
    if not session.get('logged_in'):
        flash("Please log in to download resources", "error")
        return redirect(url_for('login'))
    
    try:
        if resource_type == 'resource':
            # Get resource details from database
            sql = "SELECT title, type, link FROM resources WHERE id = ? AND is_active = 1"
            resource = getallprocess(sql, (resource_id,))
            
            if not resource or len(resource) == 0:
                flash("Resource not found or inactive", "error")
                return redirect(url_for('resources'))
            
            file_path = resource[0]['link']
            title = resource[0]['title']
            
        elif resource_type == 'material':
            # Get material details from database
            sql = "SELECT title, category, file_path FROM materials WHERE id = ? AND is_active = 1"
            material = getallprocess(sql, (resource_id,))
            
            if not material or len(material) == 0:
                flash("Material not found or inactive", "error")
                return redirect(url_for('resources'))
            
            file_path = material[0]['file_path']
            title = material[0]['title']
            
        else:
            flash("Invalid resource type", "error")
            return redirect(url_for('resources'))
        
        # Check if file path exists
        if not file_path:
            flash("No file available for download", "error")
            return redirect(url_for('resources'))
        
        # Handle different file path formats
        if file_path.startswith('http://') or file_path.startswith('https://'):
            # For external URLs, redirect to the URL
            return redirect(file_path)
        else:
            # For local files
            try:
                # If file_path doesn't start with /, add the application root path
                if not file_path.startswith('/'):
                    file_path = os.path.join(app.root_path, file_path)
                
                # Check if file exists
                if not os.path.exists(file_path):
                    flash(f"File not found: {file_path}", "error")
                    return redirect(url_for('resources'))
                
                # Get file extension for content type
                file_ext = os.path.splitext(file_path)[1].lower()
                
                # Try to guess the mime type
                mimetype = None
                if file_ext in ['.pdf']:
                    mimetype = 'application/pdf'
                elif file_ext in ['.doc', '.docx']:
                    mimetype = 'application/msword'
                elif file_ext in ['.xls', '.xlsx']:
                    mimetype = 'application/vnd.ms-excel'
                elif file_ext in ['.ppt', '.pptx']:
                    mimetype = 'application/vnd.ms-powerpoint'
                elif file_ext in ['.zip', '.rar']:
                    mimetype = 'application/octet-stream'
                elif file_ext in ['.txt']:
                    mimetype = 'text/plain'
                elif file_ext in ['.jpg', '.jpeg']:
                    mimetype = 'image/jpeg'
                elif file_ext in ['.png']:
                    mimetype = 'image/png'
                    
                # Serve the file
                return send_file(
                    file_path,
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name=f"{title}{file_ext}" if title else os.path.basename(file_path)
                )
                
            except Exception as e:
                flash(f"Error downloading file: {str(e)}", "error")
                return redirect(url_for('resources'))
    
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('resources'))

@app.route('/api/user/sessions')
def get_user_sessions():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get the latest session count from the database
        sql = "SELECT no_session FROM users WHERE idno = ?"
        result = getallprocess(sql, (user['idno'],))
        
        if result and len(result) > 0:
            no_session = result[0]['no_session']
            sessions = int(no_session) if no_session is not None and no_session != 'None' else 0
            # Update the session data
            user['sessions'] = sessions
            session['user'] = user
            return jsonify({'sessions': sessions})
        else:
            return jsonify({'sessions': user.get('sessions', 0)})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        app.logger.error(f"User sessions error: {str(e)}\n{error_details}")
        return jsonify({'error': str(e), 'details': error_details}), 500

@app.route('/api/sitin/successful')
def get_successful_sitins():
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
            
        idno = session['user']['idno']
        
        # Get successful sit-ins with feedback status
        sql = """
            SELECT 
                a.id,
                a.start_time,
                a.labno,
                a.purpose,
                CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as has_feedback
            FROM active_sitin a
            LEFT JOIN feedbacks f ON a.id = f.sitin_id
            WHERE a.idno = ? AND a.status = 'done'
            ORDER BY a.start_time DESC
        """
        sitins = getallprocess(sql, (idno,))
        
        if sitins:
            return jsonify([dict(row) for row in sitins])
        return jsonify([])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sitin/<int:sitin_id>/end', methods=['POST'])
def end_sitin(sitin_id):
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
            
        # Update sit-in status to 'done'
        sql = "UPDATE active_sitin SET status = 'done', end_time = datetime('now') WHERE id = ? AND idno = ?"
        success = postprocess(sql, (sitin_id, session['user']['idno']))
        
        if success:
            return jsonify({'message': 'Sit-in session ended successfully'})
        return jsonify({'error': 'Failed to end sit-in session'}), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule/download')
def download_schedule():
    if not session.get('logged_in'):
        flash("Please log in to download the schedule", "error")
        return redirect(url_for('login'))
    
    try:
        # Get filter parameters
        day_filter = request.args.get('day', 'all')
        time_filter = request.args.get('time', 'all')
        room_filter = request.args.get('room', '')
        
        # Build the SQL query with filters
        sql = """
        SELECT ls.labno, ls.day, ls.time, ls.created_at
        FROM lab_schedule ls
        WHERE 1=1
        """
        params = []
        
        if day_filter != 'all':
            sql += " AND LOWER(ls.day) = LOWER(?)"
            params.append(day_filter)
        
        if time_filter != 'all':
            start_time, end_time = time_filter.split('-')
            sql += " AND ls.time BETWEEN ? AND ?"
            params.extend([start_time, end_time])
        
        if room_filter:
            sql += " AND ls.labno = ?"
            params.append(room_filter)
        
        sql += " ORDER BY ls.day, ls.time, ls.labno"
        
        # Get the schedule data
        schedule_data = getallprocess(sql, tuple(params))
        
        if not schedule_data:
            flash("No schedule data found for the selected filters", "error")
            return redirect(url_for('lab'))
        
        # Create a PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Add title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30
        )
        elements.append(Paragraph("Laboratory Schedule", title_style))
        elements.append(Spacer(1, 20))
        
        # Create the table data
        data = [['Laboratory', 'Day', 'Time']]
        for row in schedule_data:
            data.append([
                f"Room {row['labno']}",
                row['day'],
                row['time']
            ])
        
        # Create the table
        table = Table(data, colWidths=[2*inch, 2*inch, 2*inch])
        
        # Add table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        table.setStyle(table_style)
        elements.append(table)
        
        # Build the PDF
        doc.build(elements)
        
        # Prepare the response
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"laboratory_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Error generating schedule PDF: {str(e)}")
        flash("Error generating schedule PDF", "error")
        return redirect(url_for('lab'))

@app.route('/api/reservation/status', methods=['GET'])
def get_reservation_status_count():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
    
    try:
        idno = session['user']['idno']
        sql = """
            SELECT COUNT(*) as count 
            FROM reservations 
            WHERE idno = ? 
            AND status IN ('approved', 'denied')
            AND is_notified = 0
        """
        result = getallprocess(sql, (idno,))
        
        if result:
            return jsonify({'count': result[0]['count']})
        return jsonify({'count': 0})
        
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@app.route('/api/reservation/notifications', methods=['GET'])
def get_reservation_notifications():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
    
    try:
        idno = session['user']['idno']
        sql = """
            SELECT id, labno, date, time_start, time_end, status, created_at
            FROM reservations 
            WHERE idno = ? 
            AND status IN ('approved', 'denied')
            AND is_notified = 0
            ORDER BY created_at DESC
        """
        notifications = getallprocess(sql, (idno,))
        
        if notifications:
            # Mark notifications as read
            sql = """
                UPDATE reservations 
                SET is_notified = 1 
                WHERE idno = ? 
                AND status IN ('approved', 'denied')
                AND is_notified = 0
            """
            postprocess(sql, (idno,))
            
            return jsonify([dict(notification) for notification in notifications])
        return jsonify([])
        
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@app.route('/api/reservation/logs', methods=['GET'])
def get_reservation_logs():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
    
    try:
        sql = """
            SELECT r.id, r.idno, r.labno, r.date, r.time_start, r.time_end, r.status, r.updated_at,
                   u.firstname, u.lastname
            FROM reservations r
            JOIN users u ON r.idno = u.idno
            WHERE r.status IN ('approved', 'denied')
            ORDER BY r.updated_at DESC
        """
        logs = getallprocess(sql)
        
        if logs:
            # Format the data for JSON response
            formatted_logs = []
            for log in logs:
                formatted_log = dict(log)
                # The dates are already in string format, no need for strftime
                formatted_log['date'] = log['date']
                formatted_log['updated_at'] = log['updated_at']
                formatted_logs.append(formatted_log)
            
            return jsonify(formatted_logs)
        return jsonify([])
        
    except Exception as e:
        app.logger.error(f"Error in get_reservation_logs: {str(e)}")
        return jsonify({'message': str(e), 'status': 'error'}), 500

# Add is_notified column to reservations table if it doesn't exist
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if is_notified column exists
        cursor.execute("PRAGMA table_info(reservations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_notified' not in columns:
            cursor.execute("ALTER TABLE reservations ADD COLUMN is_notified INTEGER DEFAULT 0")
            conn.commit()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
    finally:
        conn.close()

# Call init_db when the application starts
init_db()

if __name__ == '__main__':
    app.run(debug=True)
    # app.run(debug=True, host='172.19.131.161', port=5000)