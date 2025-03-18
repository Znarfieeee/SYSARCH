from flask import Flask, render_template, redirect, session, url_for, request, flash, jsonify
from dbhelper import *
import urllib.request, os
from werkzeug.utils import secure_filename
from staff_app import staff_app

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
            flash("Successfully logged in.", "success")
            session['logged_in'] = True
            session['user'] = {
                "idno": user[0]['idno'],
                "firstname": user[0]['firstname'],
                "lastname": user[0]['lastname'],
                "middlename": user[0]['middlename'] or '',
                "username": user[0]['username'],
                "email": user[0]['email'],
                "password": user[0]['password'],
                "course": user[0]['course'],
                "sessions": user[0]['no_session'],
                "yr_lvl": user[0]['yr_lvl'],
                "photo": user[0]['photo'],
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
    flash("You have been logged out.", "success")
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

# Functionalities for Student
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
            "password": password if password else session['user']['password']
        })
    
    
    print(session['user'])
    
    if success:
        flash("Account Profile updated.", "success")
        return redirect(url_for('home'))
    
    else:
        flash("Account Profile update failed.", "error")
        

    return redirect(url_for('home'))

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
    
    user = session.get('user')
    return render_template("student/dashboard.html", user=user, pagetitle=pagetitle, announcements=announcements)
    

@app.route('/history')
def history():
    pagetitle = 'History'
    
    return render_template('student/history.html', pagetitle=pagetitle)

@app.route('/reservation')
def reservation():
    pagetitle = 'Reservation'
    
    return render_template('student/reservation.html', pagetitle=pagetitle)

@app.route('/get_reservations')
def get_reservations():
    idno = session['user']['idno']
    sql = "SELECT * FROM reservations WHERE idno = ? ORDER BY date DESC"
    reservations = getallprocess(sql, (idno,))
    
    data  = []
    for res in reservations:
        data.append({
            "id": res['id'],
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
    idno = session.get('idno') or session['user']['idno']
    date = request.form.get('date')
    time_start = request.form.get('time-start')
    time_end = request.form.get('time-end')
    labno = request.form.get('labno')
    purpose = request.form.get('purpose')
    status = "pending"

    success = addprocess('reservations', idno=idno, date=date, 
                         time_start=time_start, time_end=time_end, 
                         labno=labno, purpose=purpose, status=status)
    
    if success:
        flash("Reservation successful.", "success")
    else:
        flash("Reservation failed.", "error")

    return redirect(url_for('reservation'))

@app.route('/sitin')
def sitin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Sit-in'
    user = session.get('user')
    
    # Get approved reservations for the current user
    sql = """
        SELECT r.*, a.check_in_time, a.check_out_time
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

@app.route('/api/check-in/<int:reservation_id>', methods=['POST'])
def check_in(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the reservation details
        reservation = get_reservation_details(reservation_id)
        if not reservation:
            return jsonify({'error': 'Reservation not found'}), 404
            
        # Start the sit-in
        pc_number = request.json.get('pc_number')
        if not pc_number:
            return jsonify({'error': 'PC number is required'}), 400
            
        success = start_sitin(reservation_id, pc_number)
        
        if success:
            return jsonify({'message': 'Check-in successful'}), 200
        return jsonify({'error': 'Failed to check in'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-out/<int:reservation_id>', methods=['POST'])
def check_out(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the active sit-in for this reservation
        sql = "SELECT id FROM active_sitin WHERE reservation_id = ? AND status = 'active'"
        sitin = getallprocess(sql, (reservation_id,))
        
        if not sitin:
            return jsonify({'error': 'No active sit-in found'}), 404
            
        success = end_sitin(sitin[0]['id'])
        
        if success:
            return jsonify({'message': 'Check-out successful'}), 200
        return jsonify({'error': 'Failed to check out'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reservation/<int:reservation_id>/edit', methods=['POST'])
def edit_reservation(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Retrieve form data
        date = request.form.get('date')
        time_start = request.form.get('time_start')
        time_end = request.form.get('time_end')
        labno = request.form.get('labno')
        purpose = request.form.get('purpose')

        # Prepare data for update
        update_data = {
            'id': reservation_id,  # Use 'id' as the key for the reservation ID
            'date': date,
            'time_start': time_start,
            'time_end': time_end,
            'labno': labno,
            'purpose': purpose
        }

        # Call updateprocess function
        success = updateprocess('reservations', **update_data)

        if success:
            return jsonify({'message': 'Reservation updated successfully'}), 200
        return jsonify({'error': 'Failed to update reservation'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
    # app.run(debug=True, host='172.19.131.161', port=5000)