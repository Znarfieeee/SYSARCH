from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from dbhelper import *
import os
from werkzeug.utils import secure_filename

staff_app = Blueprint('staff_app', __name__)

@staff_app.route('/staff/dashboard')
def staff_dashboard():
    # if not session.get('logged_in'):
    #     return redirect(url_for('staff_app.staff_login'))
    
    pagetitle = 'Staff Dashboard'
    user = session.get('user')
    return render_template("staff/sDashboard.html", user=user, pagetitle=pagetitle)


@staff_app.route('/staff/students')
def staff_students():
    return render_template("staff/staff_login.html", pagetitle='Students')