from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from dbhelper import *
import os
from werkzeug.utils import secure_filename

staff_app = Blueprint('staff_app', __name__)


# Routes for Admin
@staff_app.route('/staff/dashboard')
def staff_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Admin Dashboard'
    user = session.get('user')
    
    return render_template("staff/sDashboard.html", user=user, pagetitle=pagetitle)


@staff_app.route('/staff/students')
def staff_students():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("staff/studlist.html", pagetitle='Students')

@staff_app.route('/staff/reports')
def staff_reports():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("staff/reports.html", pagetitle='Reports')

@staff_app.route('/staff/feedbacks')
def staff_feedbacks():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("staff/feedback.html", pagetitle='Feedbacks')


# Functions
@staff_app.route('/staff/create_announcement', methods=['POST'])
def create_announcement():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    idno = session['user']['idno']
    announcement_title = request.form.get('title')
    announcement_content = request.form.get('content')

    success = addprocess('announcement', idno=idno, 
                         announcement_title=announcement_title, 
                         announcement_content=announcement_content)
    
    if success:
        flash('Announcement created successfully', 'success')
    else:
        flash('Failed to create announcement', 'error')
        
    return redirect(url_for('staff_dashboard'))

@staff_app.route('/api/statistics', methods=['GET'])
def get_statistics():
    sql = "SELECT total_registered_students, currently_sit_in, total_sit_in FROM statistics WHERE id = 1"
    statistics = getallprocess(sql)
    if statistics:
        statistics_dict = dict(statistics[0])
        return jsonify(statistics_dict)
    else:
        return jsonify({"error": "No statistics data found"}), 404
    
    
@staff_app.route('/statisticchart', methods=['GET'])
def get_statisticchart():
    sql = """ 
    SELECT purpose, COUNT(*) as count
    FROM reservations
    GROUP BY purpose
    """
    success = getstat(sql)
    if success: 
        reservation_stats_dict = [dict(row) for row in success]
        return jsonify(reservation_stats_dict)
    else:
        return jsonify({"error": "No reservation statistics found"}), 404