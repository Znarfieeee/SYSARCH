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

        if not username or not password:
            flash("Input username and password", "error")

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
                "yr_lvl": user[0]['yr_lvl']
            }
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")

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
        username = request.form.get('username')
        password = request.form.get('password')

        if not idno or not lastname or not firstname or not course or not yr_lvl or not email or not username or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))
        
        success = addprocess('users', idno=idno, lastname=lastname, 
                             firstname=firstname, middlename=middlename, 
                             course=course, yr_lvl=yr_lvl, email=email, 
                             username=username, password=password)

        if success:
            flash("Registration successful.", "success")
            return redirect(url_for('login'))
        else:
            flash("Registration failed.", "error")
            return redirect(url_for('register'))

    return render_template("register.html")

if __name__ == '__main__':
    app.run(debug=True)