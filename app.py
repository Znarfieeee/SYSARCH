from flask import Flask, render_template, redirect, session, url_for, request, flash
from dbhelper import *

app = Flask(__name__)
app.secret_key = "!@#$%12345"

@app.after_request
def addheader(response):
    response.headers['Content-Type'] = 'no-cache, no-store, must-revalidate, private'
    response.headers["Pragma"] = 'no-cache'
    response.headers["Expires"] = "0"
    return response

@app.route('/home')
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    user = session.get('user')
    return render_template("dashboard.html", user=user)
    
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
                "username": user[0]['username'],
                "email": user[0]['email'],
                "course": user[0]['course'],
                "sessions": user[0]['no_session'],
                "yr_lvl": user[0]['yr_lvl']
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

if __name__ == '__main__':
    app.run(debug=True)