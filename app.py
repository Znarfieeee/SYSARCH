from flask import Flask, render_template, redirect, session, url_for, request, flash
from dbhelper import *

app = Flask(__name__)
app.secret_key = "!@#$%12345"

@app.route('/home')
def home():
    if 'user' in session:
        return render_template("home.html")
    else:
        return 

@app.route('/', methods= ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        sql ="SELECT * FROM users where username = ? and password = ?"
        user = getallprocess(sql, (username, password))

        if user:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    conn = get_db_connection()
    if request.method == 'POST':
        idno = request.form.get('idno')
        lastname = request.form.get('lastname')
        firstname = request.form.get('firstname')
        middlename = request.form.get('middlename')
        course = request.form.get('course')
        yr_level = request.form.get('yr_level')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')

        data = {
            'idno': idno,
            'lastname': lastname,
            'firstname': firstname,
            'middlename': middlename,
            'course': course,
            'yr_level': yr_level,
            'email': email,
            'username': username,
            'password': password
        }

        sql = "INSERT INTO your_table ({}) VALUES ({})".format(
            ', '.join(data.keys()),
            ', '.join(['?'] * len(data))
        )
        
        success = addprocess(conn, sql, tuple(data.values()))

        if success:
            flash("Registration successful.", "success")
            conn.close()
            return redirect(url_for('login'))
        else:
            flash("Registration failed.", "error")
            conn.close()
            return redirect(url_for('register'))

    return render_template("register.html")

if __name__ == '__main__':
    app.run(debug=True)