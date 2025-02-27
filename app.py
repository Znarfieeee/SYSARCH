from flask import Flask, render_template, redirect, session, url_for, request, flash
from dbhelper import *
import urllib.request, os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "!@#$%12345"
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static/user_img'

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
    
    user = session.get('user')
    
    if user['role'] =='student':
        return render_template("dashboard.html", user=user, pagetitle=pagetitle)
    elif user['role'] =='staff':
        return render_template("/staff/sDashboard.html", user=user, pagetitle=pagetitle)
    

@app.route('/history')
def history():
    pagetitle = 'History'
    
    return render_template('history.html', pagetitle=pagetitle)

@app.route('/reservation')
def reservation():
    pagetitle = 'Reservation'
    
    return render_template('reservation.html', pagetitle=pagetitle)

@app.route('/schedule')
def schedule():
    pagetitle = 'Schedule'
    
    return render_template('schedule.html', pagetitle=pagetitle)


if __name__ == '__main__':
    app.run(debug=True)