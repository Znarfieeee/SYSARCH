from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from dbhelper import *
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import io
from io import BytesIO
import csv
import xlsxwriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, legal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

staff_app = Blueprint('staff_app', __name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads/materials'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', 'exe', 'msi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def json_response(message, status='success', data=None, code=200):
    response = {
        'message': message,
        'status': status
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code

# Routes for Admin
@staff_app.route('/staff/dashboard')
def staff_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    pagetitle = 'Admin Dashboard'
    user = session.get('user')
    
    sql = "select id, title, content, created_at from announcement order by created_at desc"
    success = getallprocess(sql)
    
    if success:
        announcements = [dict(row) for row in success]
    else:
        announcements = []
        
    return render_template("staff/sDashboard.html", user=user, pagetitle=pagetitle, announcements=announcements)

@staff_app.route('/staff/students')
def staff_students():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    sql = """
        SELECT u.idno, u.firstname, u.middlename, u.lastname, u.course, u.yr_lvl, u.email, 
               COALESCE(r.session_count, 0) as sessions,
               u.no_session - COALESCE(r.session_count, 0) as remaining_sessions
        FROM users u
        LEFT JOIN (
            SELECT idno, COUNT(*) as session_count
            FROM reservations
            WHERE status = 'completed'
            GROUP BY idno
        ) r ON u.idno = r.idno
        WHERE u.role = 'student'
        ORDER BY u.idno
    """
    
    students = getallprocess(sql)
    
    if students:
        students_list = [dict(student) for student in students]
    else:
        students_list = []
    
    return render_template("staff/studlist.html", 
                           pagetitle='Students',
                           students=students_list)

@staff_app.route('/staff/reports')
def staff_reports():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    students = get_total_sitins()
    
    if students:
        students_list = []
        for student in students:
            student_dict = dict(student)
            students_list.append(student_dict)
    else:
        students_list = []
    
    return render_template('staff/reports.html', 
                           pagetitle='Sit-in Reports', 
                           students=students_list)
    
@staff_app.route('/staff/laboratory')
def staff_laboratory():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    
    return render_template("staff/laboratory.html", 
                           pagetitle='Laboratory')

@staff_app.route('/staff/laboratory/schedule')
def staff_lab_schedules():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    sql = "SELECT * FROM lab_schedule ORDER BY labno"
    schedule = getallprocess(sql)
    
    
    return render_template("staff/lab-schedules.html", 
                           pagetitle='Laboratory Schedule', schedules=schedule)
    

@staff_app.route('/staff/laboratory/schedule', methods=['POST'])
def add_lab_schedule():
    try:
        data = request.json
        
        labno = data.get('lab_no')
        days = data.get('days')  # This will be an array of selected days ['M', 'T', 'W', etc.]
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if not all([labno, days, start_time, end_time]):
            return jsonify({
                "message": "All fields are required", 
                "status": "error"
            }), 400

        # Join all days with a comma and store in one row
        days_str = ', '.join(days)
        schedule_data = {
            'labno': labno,
            'day': days_str,
            'time': f"{start_time} - {end_time}",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        result = addprocess('lab_schedule', **schedule_data)

        if result:
            return jsonify({
                "message": "Schedule added successfully", 
                "status": "success"
            }), 200
        else:
            return jsonify({
                "message": "Failed to add schedule", 
                "status": "error"
            }), 400

    except Exception as e:
        return jsonify({
            "message": f"Error adding schedule: {str(e)}", 
            "status": "error"
        }), 500

@staff_app.route('/staff/laboratory/schedule/<int:id>', methods=['DELETE'])
def delete_lab_schedule(id):
    try:
        sql = "DELETE FROM lab_schedule WHERE id = ?"
        success = postprocess(sql, (id,))

        if success:
            return jsonify({
                "message": "Schedule deleted successfully", 
                "status": "success"
            }), 200
        else:
            return jsonify({
                "message": "Failed to delete schedule", 
                "status": "error"
            }), 400
    except Exception as e:
        return jsonify({"message": f"Server Error: {str(e)}", "status": "error"}), 500

@staff_app.route('/staff/laboratory/schedule/<int:id>', methods=['GET'])
def get_lab_schedule(id):
    try:
        sql = "SELECT * FROM lab_schedule WHERE id = ?"
        schedule = getallprocess(sql, (id,))
        
        if schedule:
            return jsonify(dict(schedule[0]))
        return jsonify({"message": "Schedule not found", "status": "error"}), 404
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}", "status": "error"}), 500

@staff_app.route('/staff/laboratory/schedule/<int:id>/edit', methods=['PATCH'])
def update_lab_schedule(id):
    try:
        data = request.json
        labno = data.get('lab_no')
        days = data.get('days')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        days_str = ', '.join(days)
        schedule_data = {
            'id': id,
            'labno': labno,
            'day': days_str,
            'time': f"{start_time} - {end_time}",
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        result = updateprocess('lab_schedule', **schedule_data)

        if result:
            return jsonify({
                "message": "Schedule updated successfully",
                "status": "success"
            }), 200
        else:
            return jsonify({
                "message": "Failed to update schedule",
                "status": "error"
            }), 400

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}", "status": "error"}), 500

@staff_app.route('/staff/laboratory/resources', methods=['GET'])
def get_resources():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
    
    try:
        sql = """
            SELECT id, title, type, link, is_active, created_at, updated_at 
            FROM resources 
            ORDER BY created_at DESC
        """
        resources = getallprocess(sql)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if resources:
                return jsonify([dict(resource) for resource in resources])
            return jsonify([])
            
        return render_template("staff/lab-resources.html", 
                           pagetitle='Laboratory Resources', 
                           resources=resources)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'message': str(e), 'status': 'error'}), 500
        flash('Error loading resources', 'error')
        return render_template("staff/lab-resources.html", 
                           pagetitle='Laboratory Resources', 
                           resources=[])

@staff_app.route('/staff/laboratory/resources', methods=['POST'])
def add_resource():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        title = request.form.get('title')
        type_ = request.form.get('type')
        link = request.form.get('link')

        if not all([title, type_ ]):
            return jsonify({'message': 'All fields are required', 'status': 'error'}), 400

        success = addprocess('resources', 
            title=title,
            type=type_,
            link=link,
            is_active=True
        )

        if success:
            return jsonify({'message': 'Resource added successfully', 'status': 'success'})
        return jsonify({'message': 'Failed to add resource', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/laboratory/resources/<int:id>/toggle', methods=['POST'])
def toggle_resource(id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        data = request.json
        new_status = data.get('status', False)

        sql = "UPDATE resources SET is_active = ? WHERE id = ?"
        success = postprocess(sql, (new_status, id))

        if success:
            return jsonify({'message': 'Resource status updated', 'status': 'success'})
        return jsonify({'message': 'Failed to update resource status', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/laboratory/resources/<int:id>', methods=['DELETE'])
def delete_resource(id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        sql = "DELETE FROM resources WHERE id = ?"
        success = postprocess(sql, (id,))

        if success:
            return jsonify({'message': 'Resource deleted successfully', 'status': 'success'}), 200
        return jsonify({'message': 'Failed to delete resource', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

# Materials routes
@staff_app.route('/staff/laboratory/materials', methods=['GET'])
def get_materials():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        sql = """
            SELECT id, title, category, description, file_path, is_active, created_at, updated_at 
            FROM materials 
            ORDER BY created_at DESC
        """
        materials = getallprocess(sql)
        
        if materials:
            return jsonify([dict(material) for material in materials])
        return jsonify([])
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/laboratory/materials', methods=['POST'])
def add_material():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        title = request.form.get('title')
        category = request.form.get('category')
        description = request.form.get('description')
        file = request.files.get('file')

        if not all([title, category]):
            return jsonify({'message': 'Title and category are required', 'status': 'error'}), 400

        file_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to prevent duplicates
            filename = f"{int(datetime.now().timestamp())}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)

        success = addprocess('materials',
            title=title,
            category=category,
            description=description,
            file_path=file_path,
            is_active=True
        )

        if success:
            return jsonify({'message': 'Material added successfully', 'status': 'success'})
        return jsonify({'message': 'Failed to add material', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/laboratory/materials/<int:id>/toggle', methods=['POST'])
def toggle_material(id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        data = request.json
        new_status = data.get('status', False)

        sql = "UPDATE materials SET is_active = ? WHERE id = ?"
        success = postprocess(sql, (new_status, id))

        if success:
            return jsonify({'message': 'Material status updated', 'status': 'success'})
        return jsonify({'message': 'Failed to update material status', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/laboratory/materials/download/<int:id>')
def download_material(id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        sql = "SELECT file_path, title FROM materials WHERE id = ?"
        material = getallprocess(sql, (id,))

        if not material or not material[0]['file_path']:
            return jsonify({'message': 'File not found', 'status': 'error'}), 404

        file_path = material[0]['file_path']
        if not os.path.exists(file_path):
            return jsonify({'message': 'File not found', 'status': 'error'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path).split('_', 1)[1]  # Remove timestamp from filename
        )

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/staff/reports/purpose')
def staff_reports_purpose():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    students = get_total_sitins_purpose()
    
    if students:
        students_list = []
        for student in students:
            student_dict = dict(student)
            # Ensure all fields are included for filtering
            student_dict['purpose'] = student_dict.get('purpose', '')
            student_dict['date'] = student_dict.get('date', '')
            students_list.append(student_dict)
    else:
        students_list = []
    
    return render_template("staff/reports-pp.html", 
                           pagetitle='Reports per Purpose',
                           students=students_list)

@staff_app.route('/staff/reports/lab')
def staff_reports_level():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    students = get_total_sitins_lab()
    
    if students:
        students_list = []
        for student in students:
            student_dict = dict(student)
            # Ensure all fields are included for filtering
            student_dict['labno'] = student_dict.get('labno', '')
            student_dict['date'] = student_dict.get('date', '')
            students_list.append(student_dict)
    else:
        students_list = []
    
    return render_template("staff/reports-pl.html", 
                           pagetitle='Reports per Lab',
                           students=students_list)

@staff_app.route('/staff/feedbacks')
def staff_feedbacks():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    feedbacks = getallprocess("SELECT * FROM feedbacks ORDER BY created_at DESC")

    if not feedbacks: 
        return jsonify({'message': 'Failed to fetch feedbacks.', 'status': 'error'}), 500
    
    return render_template("staff/feedbacks.html", pagetitle='Feedbacks', feedbacks = feedbacks)

@staff_app.route('/staff/history')
def staff_history():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    history = get_detailed_history()
    
    if history:
        history_list = []
        for record in history:
            record_dict = dict(record)
            # Format dates and times
            if record_dict['date']:
                try:
                    date_obj = datetime.strptime(record_dict['date'], '%Y-%m-%d')
                    record_dict['date'] = date_obj.strftime('%B %d, %Y')
                except:
                    pass
            history_list.append(record_dict)
    else:
        history_list = []
        
    return render_template("staff/history.html", 
                         pagetitle='Sit-in History',
                         history=history_list)

@staff_app.route('/staff/students/current')
def staff_students_current():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template("staff/studlist-cs.html", 
                         pagetitle='Current Sit-in Students')

@staff_app.route('/staff/students/pending')
def staff_students_pending():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template("staff/studlist-pr.html", 
                         pagetitle='Pending Reservations')

@staff_app.route('/staff/students/total')
def staff_students_total():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    return render_template("staff/studlist-ts.html", 
                         pagetitle='Total Reservations')

# Functions
@staff_app.route('/announcement', methods=['POST'])
def create_announcement():
    if not session.get('logged_in'):
        return json_response('Not authenticated', 'error', code=401)
    
    idno = session['user']['idno']
    title = request.form.get('title')
    content = request.form.get('content')

    success = addprocess('announcement', idno=idno, 
                         title=title, 
                         content=content)
    
    if success:
        return json_response('Announcement created successfully')
    return json_response('Failed to create announcement', 'error', code=400)

@staff_app.route('/announcement/<int:id>', methods=['DELETE'])
def delete_announcement(id):
    sql = f"DELETE FROM announcement WHERE id = ?"
    success = postprocess(sql, (id,))
    
    if success:
        return jsonify({'message': 'Announcement deleted successfully.', 'status': 'success'}), 200
    
    return jsonify({'message': 'Failed to delete announcement.', 'status': 'error'}), 400

@staff_app.route('/announcement/<int:id>/edit', methods=['POST'])
def edit_announcement(id):
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        success = updateprocess('announcement', 
                              id=id,
                              title=title, 
                              content=content)
        
        if success:
            return jsonify({'message': 'Announcement updated successfully', 'status': 'success'}), 200
        
        return jsonify({'message': 'Failed to update announcement', 'status': 'error'}), 400
            
    except Exception as e:
        return jsonify({'message': f"Error updating announcement: {str(e)}", 'status': 'error'}), 500

@staff_app.route('/api/book', methods=['POST'])
def book_res():
    idno = request.form.get('idno')
    date = request.form.get('resdate')
    time_start = request.form.get('time-start')
    time_end = request.form.get('time-end')
    labno = request.form.get('labno')
    purpose = request.form.get('purpose')
    status = "pending"

    success = addprocess('reservations', idno=idno, date=date, 
                         time_start=time_start, time_end=time_end, 
                         labno=labno, purpose=purpose, status=status)
    
    if success:
        return jsonify({'message': 'Reservation successful.', 'status': 'success'}), 200
    
    return jsonify({'message': 'Reservation failed.', 'status': 'error'}), 400

@staff_app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = get_dashboard_statistics()
        if stats:
            stats_dict = dict(stats[0])
            # Ensure values are not None and non-negative
            stats_dict = {
                'total_registered_students': max(0, stats_dict.get('total_registered_students', 0)),
                'currently_sit_in': max(0, stats_dict.get('currently_sit_in', 0)),
                'total_sit_in': max(0, stats_dict.get('completed_sit_ins', 0))
            }
            return jsonify(stats_dict)
        return jsonify({
            'total_registered_students': 0,
            'currently_sit_in': 0,
            'total_sit_in': 0
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch statistics',
            'total_registered_students': 0,
            'currently_sit_in': 0,
            'total_sit_in': 0
        }), 500
    
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
        return jsonify({'message': 'Failed to fetch reservation statistics.', 'status': 'error'}), 500

@staff_app.route('/api/student/<int:idno>', methods=['GET'])
def get_student(idno):
    try:
        sql = f"SELECT * FROM users WHERE IDNO = ?"
        success = getallprocess(sql, (idno,))

        if not success:
            return jsonify({'message': 'Failed to fetch student data!', 'status': 'error'}), 400
        
        student = [dict(row) for row in success]

        return jsonify(student)
    except Exception as e:
        return jsonify({'message': str(e), 'status':'error'}), 500

@staff_app.route('/api/student/<int:idno>', methods=['DELETE'])
def delete_student(idno):
    try:
        sql = "DELETE FROM users WHERE idno = ?"
        success = postprocess(sql, (idno,))

        if success:
            return jsonify({'message': 'Student deleted successfully', 'status': 'success'}), 200

        return jsonify({'message': 'Failed to delete student!', 'status': 'error'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/student', methods=['POST'])
def add_student():
    try:
        idno = request.form.get('idno')
        course = request.form.get('course')
  
        if course in ['bsit', 'bscs', 'bscpe']:
            no_session = 30
        else:
            no_session = 15
            
        data = {
            'idno': idno,
            'firstname': request.form.get('firstname'),
            'lastname': request.form.get('lastname'),
            'username': idno,
            'course': course,
            'yr_lvl': request.form.get('yr_lvl'),
            'email': request.form.get('email'),
            'password': idno, 
            'role': 'student',
            'no_session': no_session 
        }
       
        success = addprocess('users', **data)      

        if not success:
            return jsonify({'message': 'Failed to add student', 'status': 'error'}), 400

        # Return the student data along with the success message
        student_data = {
            **data,
            'remaining_sessions': no_session,  # Add remaining sessions for display
            'sessions': 0  # Initial sessions count
        }
        return jsonify({
            'message': 'Student added successfully', 
            'status': 'success',
            'student': student_data
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/student/<int:idno>/edit', methods=['POST'])
def update_student(idno):
    try:
        # Get form data
        data = {
            'firstname': request.form.get('firstname'),
            'middlename': request.form.get('middlename'),
            'lastname': request.form.get('lastname'),
            'course': request.form.get('course'),
            'yr_lvl': request.form.get('yr_lvl'),
            'email': request.form.get('email')
        }
        
        # Create SQL query
        sql = """
            UPDATE users 
            SET firstname = ?, 
                middlename = ?, 
                lastname = ?, 
                course = ?, 
                yr_lvl = ?, 
                email = ? 
            WHERE idno = ?
        """
        
        # Execute update query
        params = (
            data['firstname'],
            data['middlename'],
            data['lastname'],
            data['course'],
            data['yr_lvl'],
            data['email'],
            idno
        )
        
        success = postprocess(sql, params)
        
        if success:
            # Fetch updated student data
            sql = """
                SELECT u.*, 
                       COALESCE(r.session_count, 0) as sessions,
                       u.no_session - COALESCE(r.session_count, 0) as remaining_sessions
                FROM users u
                LEFT JOIN (
                    SELECT idno, COUNT(*) as session_count
                    FROM reservations
                    WHERE status = 'completed'
                    GROUP BY idno
                ) r ON u.idno = r.idno
                WHERE u.idno = ?
            """
            updated_student = getallprocess(sql, (idno,))
            
            if updated_student:
                student_data = dict(updated_student[0])
                return jsonify({
                    'message': 'Student updated successfully',
                    'status': 'success',
                    'student': student_data
                }), 200
                
        return jsonify({
            'message': 'Failed to update student',
            'status': 'error'
        }), 400
    
    except Exception as e:
        print(f"Error updating student: {str(e)}")  # Add this for debugging
        return jsonify({
            'message': str(e),
            'status': 'error'
        }), 500

@staff_app.route('/api/student/<int:idno>/reservations')
def get_student_reservations(idno):
    try:
        if not session.get('logged_in'):
            return json_response('Not authenticated', 'error', code=401)
            
        sql = """
            SELECT 
                r.id,
                r.idno,
                r.date,
                r.time_start,
                r.time_end,
                r.purpose,
                r.status,
                r.created_at,
                r.labno,
                u.firstname,
                u.lastname,
                COALESCE(a.check_in_time, '') as check_in_time,
                COALESCE(a.check_out_time, '') as check_out_time,
                COALESCE(h.updated_at, '') as last_updated
            FROM reservations r 
            JOIN users u ON r.idno = u.idno 
            LEFT JOIN attendancelog a ON r.id = a.reserve_id
            LEFT JOIN history h ON r.id = h.reservation_id
            WHERE r.idno = ? 
            ORDER BY r.date DESC, r.time_start DESC
        """
        reservations = getallprocess(sql, (idno,))
        
        if reservations:
            formatted_reservations = []
            for res in reservations:
                res_dict = dict(res)
                # Format date if it exists
                if res_dict['date']:
                    try:
                        date_obj = datetime.strptime(res_dict['date'], '%Y-%m-%d')
                        res_dict['date'] = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                formatted_reservations.append(res_dict)
            return json_response('Reservations retrieved successfully', data=formatted_reservations)
        return json_response('No reservations found', data=[])
        
    except Exception as e:
        return json_response(str(e), 'error', code=500)

@staff_app.route('/api/reservation/<int:reservation_id>/status', methods=['POST'])
def update_reservation_status_route(reservation_id):
    try:
        status = request.json.get('status')
        staff_id = session.get('user', {}).get('idno')
        
        if not staff_id:
            return jsonify({'message': 'Account type is not authenticated', 'status': 'error'}), 401
            
        reservation = get_reservation_details(reservation_id)
        if not reservation:
            return jsonify({'message': 'Reservation not found', 'status': 'error'}), 404
            
        if status == 'approved':
            sessions = check_student_sessions(reservation[0]['idno'])
            if sessions and sessions[0]['used_sessions'] >= sessions[0]['no_session']:
                return jsonify({'message': 'Student has no remaining sessions', 'status': 'error'}), 400
        
        success = update_reservation_status(reservation_id, status, staff_id)
        
        if success:
            return jsonify({'message': 'Reservation status updated successfully', 'status': 'success'}), 200
        
        return jsonify({'message': 'Failed to update reservation status', 'status': 'error'}), 400
            
    except Exception as e:
        return jsonify({'message': f'Error updating reservation status: {str(e)}', 'status': 'error'}), 500

@staff_app.route('/api/history')
def get_history_route():
    try:
        history = get_reservation_history()
        return jsonify([dict(row) for row in history] if history else [])
    except Exception as e:
        return jsonify({'message': 'Error fetching history: ' + str(e), 'status': 'error'}), 400

@staff_app.route('/api/statistics')
def get_statistics_route():
    try:
        stats = get_reservation_statistics()
        return jsonify([dict(row) for row in stats] if stats else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/statisticchart')
def get_statistics_chart_route():
    try:
        stats = get_reservation_statistics()
        return jsonify([dict(row) for row in stats] if stats else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/sitin/start', methods=['POST'])
def start_sitin_route():
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
            
        data = request.json
        idno = data.get('idno')
        end_time = data.get('expected_end_time')
        notes = data.get('notes')
        reservation_id = data.get('reservation_id')
        labno = data.get('labno')
        purpose = data.get('purpose')
        
        if not all([labno, purpose, idno, end_time]):
            return jsonify({'message': 'All fields are required', 'status': 'error'}), 400
        
        success = start_sitin(
            idno=idno,
            end_time=end_time,
            notes=notes,
            reservation_id=reservation_id,
            pc_number=labno,
            purpose=purpose
        )
        
        if success:
            return jsonify({'message': 'Sit-in started successfully', 'status': 'success'}), 200
        
        return jsonify({'message': 'Failed to start sit-in', 'status': 'error'}), 400
            
    except Exception as e:
        return jsonify({'message': f'Error starting sit-in: {str(e)}', 'status': 'error'}), 500

@staff_app.route('/api/sitin/<int:sitin_id>/end', methods=['POST'])
def end_sitin_route(sitin_id):
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
        
        sql = "SELECT id, idno, labno FROM active_sitin WHERE id = ? AND status = 'active'"
        sitin = getallprocess(sql, (sitin_id,))
        
        if not sitin:
            return jsonify({'message': 'No active sit-in found', 'status': 'error'}), 404
        
        sitin_id = sitin[0]['id']
        student_idno = sitin[0]['idno']
        labno = sitin[0]['labno']
        
        success = end_sitin(sitin_id)
        
        if success:
            update_sessions(student_idno)
            return jsonify({
                'message': 'Sit-in ended successfully', 
                'status': 'success',
                'labno': labno
            }), 200
        
        return jsonify({'message': 'Failed to end sit-in', 'status': 'error'}), 400
            
    except Exception as e:
        return jsonify({'message': f'Error ending sit-in: {str(e)}', 'status': 'error'}), 500

@staff_app.route('/api/student/<int:idno>/sitin')
def get_student_sitins_route(idno):
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
            
        sitins = get_student_sitins(idno)
        
        if sitins:
            formatted_sitins = []
            for sitin in sitins:
                sitin_dict = dict(sitin)
                # Format dates for display
                if sitin_dict['date']:
                    try:
                        date_obj = datetime.strptime(sitin_dict['date'], '%Y-%m-%d')
                        sitin_dict['date'] = date_obj.strftime('%B %d, %Y')
                    except:
                        pass
                formatted_sitins.append(sitin_dict)
            return jsonify(formatted_sitins)
        return jsonify([])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/sitin/add', methods=['POST'])
def add_sitin():
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated!', 'status': 'error'}), 400

        data = request.json
        idno = data.get('idno')
        
        # First, check if the student exists
        student = check_student_exist(idno)
        
        if not student:
            return jsonify({'message': 'Student not registered!', 'status': 'error'}), 400
                
        # Extract the data from the request
        sitin_data = {
            'idno': idno,
            'labno': data.get('labno'),
            'end_time': data.get('end_time'),
            'notes': data.get('notes'),
            'status': 'active',
            'purpose': data.get('purpose'),
            'reservation_id': data.get('reservation_id')
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE statistics
                SET currently_sit_in = currently_sit_in + 1,
                    total_sit_in = total_sit_in + 1,
                    updated_at = datetime('now', 'localtime')
                WHERE id = 1
            """)
            conn.commit()
        except Exception as e:
            print(f"Statistics update error: {str(e)}")
        finally:
            conn.close()

        # Add the sit-in record to the database\
        active = check_student_sitin(idno)
        if active:
            return jsonify({'message': 'Student has an active sit in!', 'status': 'error'}), 400
        
        else:
            success = addprocess('active_sitin', **sitin_data)

        if success:
            return jsonify({'message':'Sit in started successfully.', 'status': 'success'}), 200
        
        return jsonify({'message': 'Failed to start sit in.', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/reservation_count', methods=['GET'])
def get_reservation_count():
    if not session.get('logged_in'):
        return jsonify({'message': 'Student has an active sit in!', 'status': 'error'}), 400

    count = get_pending_reservation_count()
    return jsonify({'count': count})

@staff_app.route('/api/reservation_students', methods=['GET'])
def get_reservation_students():
    try:
        # Get approved reservations that do not have an active sit-in
        sql = """
            SELECT 
                r.id as reservation_id,
                r.idno,
                r.date,
                r.time_start,
                r.time_end,
                r.purpose,
                r.status,
                r.labno,
                u.firstname,
                u.lastname,
                u.course,
                u.yr_lvl
            FROM reservations r
            JOIN users u ON r.idno = u.idno
            WHERE r.status = 'approved'
            AND NOT EXISTS (
                SELECT 1 FROM active_sitin a
                WHERE a.reservation_id = r.id AND a.status = 'active'
            )
            ORDER BY r.date ASC, r.time_start ASC
        """
        approved_reservations = getallprocess(sql)

        # Optionally, you can also include pending reservations if needed
        # pending_reservations = get_pending_reservations()
        # reservations = (approved_reservations or []) + (pending_reservations or [])

        return jsonify([dict(res) for res in approved_reservations] if approved_reservations else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@staff_app.route('/api/students/total_sitins', methods=['GET'])
def get_students_total_sitins():
    try:
        students = get_total_sitins()
        return jsonify([dict(student) for student in students] if students else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/reset_session', methods=['GET'])
def reset_sessions():
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
        
        if not session.get('user', {}).get('role') == 'admin':
            return jsonify({'message': 'Only admin can reset sessions', 'status': 'error'}), 403
        
        password = request.form.get('password')
        if not password:
            return jsonify({'message': 'Password is required', 'status': 'error'}), 400
            
        admin_idno = session.get('user', {}).get('idno')
        sql = "SELECT * FROM users WHERE idno = ?"
        admin = getallprocess(sql, (admin_idno,))
        
        if not admin or admin[0]['password'] != password:
            return jsonify({'message': 'Invalid password', 'status': 'error'}), 403
        
        success = reset_sessions()
        if not success:
            return jsonify({'message': 'Failed to reset student sessions', 'status': 'error'}), 400
        
        return jsonify({'message': 'Student sessions reset successfully', 'status': 'success'}), 200
        
    except Exception as e:
        return jsonify({'message': f'Error resetting sessions: {str(e)}', 'status': 'error'}), 500

@staff_app.route('/reset_sessions/<int:idno>', methods=['POST'])
def reset_session_by_id(idno):
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
        
        if not session.get('user', {}).get('role') == 'admin':
            return jsonify({'message': 'Only admin can reset sessions', 'status': 'error'}), 403
        
        password = request.form.get('password')
        if not password:
            return jsonify({'message': 'Password is required', 'status': 'error'}), 400
            
        admin_idno = session.get('user', {}).get('idno')
        sql = "SELECT * FROM users WHERE idno = ?"
        admin = getallprocess(sql, (admin_idno,))
        
        if not admin or admin[0]['password'] != password:
            return jsonify({'message': 'Invalid password', 'status': 'error'}), 403
        
        sql = "SELECT * FROM users WHERE idno = ?"
        student = getallprocess(sql, (idno,))

        # Ensure the student exists
        if not student or len(student) == 0:
            return jsonify({'message': 'Student not found', 'status': 'error'}), 404

        # Convert the first record to a dictionary
        student_dict = dict(student[0])
        course = student_dict.get('course')
        if not course:
            return jsonify({'message': 'Course information is missing', 'status': 'error'}), 400

        session_count = 30 if course.lower() in ['bsit', 'bscs', 'bscpe'] else 15

        # Update the session count for the student
        sql_update = "UPDATE users SET no_session = ? WHERE idno = ?"
        success = postprocess(sql_update, (session_count, idno))

        if success:
            return jsonify({'message': 'Student sessions reset successfully', 'status': 'success'}), 200

        return jsonify({'message': f'Failed to reset student {idno} sessions', 'status': 'error'}), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error.'
        }), 500

@staff_app.route('/staff/generate-report', methods=['POST'])
def generate_report():
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated'}), 401
    
    try:
        data = request.json
        file_type = data.get('fileType')
        headers = data.get('headers')
        rows = data.get('data')
        purpose = data.get('purpose')
        labno = data.get('lab')
        date = data.get('date')
        page = data.get('page')
        
        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
            except ValueError:
                return jsonify({'message': 'Invalid date format'}), 400
        else:
            date = "ALL DATES"
        
        report_header = "University of Cebu - Main Campus"
        report_header2 = "College of Computer Studies"
        report_header3 = "Computer Laboratory Sit-in Monitoring System Report"

        # Create buffer here before any file type handling
        buffer = BytesIO()

        if file_type == 'csv':
            try:
                text_buffer = io.StringIO()
                writer = csv.writer(text_buffer)

                writer.writerow([report_header])
                writer.writerow([report_header2])
                writer.writerow([report_header3])
                writer.writerow([])
                writer.writerow([])  # Empty row for spacing
                writer.writerow(headers)
                writer.writerows(rows)

                # Convert the StringIO content to bytes
                buffer = BytesIO(text_buffer.getvalue().encode('utf-8'))
                mimetype = 'text/csv'
                filename = 'report.csv'

            except Exception as e:
                return jsonify({'message': f'Error generating CSV: {str(e)}'}), 500

        elif file_type == 'excel':
            try:
                workbook = xlsxwriter.Workbook(buffer)
                worksheet = workbook.add_worksheet()

                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',  
                    'font_color': '#000000', 
                    'font_size': 14,         
                    'font_name': 'Helvetica',
                    'align': 'left',         
                    'border_color': '#D3D3D3', 
                    'bottom': 1,             
                    'text_wrap': True,      
                })

                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 18,         
                    'font_name': 'Helvetica',
                    'align': 'center',
                    'valign': 'vcenter',
                })

                data_format = workbook.add_format({
                    'font_size': 12,         
                    'font_name': 'Helvetica',
                    'align': 'left',
                    'border_color': '#D3D3D3',
                    'bottom': 1,             
                    'text_wrap': True,      
                    'valign': 'vcenter',     
                })

                # Add header with formatting
                worksheet.write_blank(0, 0, None)  # Empty row
                worksheet.merge_range(1, 0, 1, len(headers) - 1, report_header, title_format)
                worksheet.merge_range(2, 0, 2, len(headers) - 1, report_header2, title_format)
                worksheet.merge_range(3, 0, 3, len(headers) - 1, report_header3, title_format)
                worksheet.write_blank(4, 0, None)  # Empty row before title
                worksheet.merge_range(5, 0, 5, len(headers) - 1, title_format)
                worksheet.write_blank(6, 0, None)  # Empty row before data
                
                # Write headers
                for col, header in enumerate(headers):
                    worksheet.write(4, col, header, header_format)

                # Write data with consistent formatting
                for row_idx, row in enumerate(rows, start=5):
                    worksheet.set_row(row_idx, 30)  # Match PDF row height
                    for col_idx, cell in enumerate(row):
                        worksheet.write(row_idx, col_idx, cell, data_format)

                workbook.close()
                mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                filename = 'report.xlsx'

            except Exception as e:
                return jsonify({'message': f'Error generating Excel: {str(e)}'}), 500

        elif file_type == 'pdf':
            try:
                # Use landscape orientation and adjust page size
                doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(legal),
                leftMargin=20,
                rightMargin=20,
                topMargin=20,
                bottomMargin=20
                )
                elements = []
                
                # Add header
                header_style = ParagraphStyle(
                    'CustomHeader',
                    parent=getSampleStyleSheet()['Title'],
                    fontSize=14,
                    leading=16,
                    alignment=1,  # Left alignment
                    textColor=colors.black
                )
                
                # Create header paragraphs
                elements.append(Paragraph(report_header, header_style))
                elements.append(Paragraph(report_header2, header_style))
                elements.append(Paragraph(report_header3, header_style))
                elements.append(Spacer(1, 20))  # Add spacing
                
                # Create table with adjusted style
                table_data = [headers] + rows
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('LINEBELOW', (0, 0), (-1, -1), 1, colors.lightgrey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5)
                ])
                
                table = Table(table_data)
                table.setStyle(table_style)
                elements.append(table)

                doc.build(elements)
                mimetype = 'application/pdf'
                filename = 'report.pdf'

            except Exception as e:
                print(f"Error generating PDF: {str(e)}")
                return jsonify({'message': f'Error generating PDF: {str(e)}'}), 500
        
        else:
            return jsonify({'message': 'Invalid file type'}), 400

        buffer.seek(0)
        return send_file(
            buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'message': f'Error generating report: {str(e)}'}), 500

@staff_app.route('/reservation/<int:id>', methods=['DELETE'])
def delete_reservation(id):
    try:
        sql = "DELETE FROM reservations WHERE id = ?"
        success = postprocess(sql, (id,))

        if not success:
            return jsonify({
                'message': 'Failed to delete reservation.', 
                'status': 'error'
            }), 400

        return jsonify({
            'message': 'Reservation cancelled successfully.', 
            'status': 'success'
        }), 200

    except Exception as e:
        return jsonify({
            'message': f'Error deleting reservation: {str(e)}', 
            'status': 'error'
        }), 500

@staff_app.route('/staff/laboratory/pc/toggle', methods=['POST'])
def toggle_pc_status():
    try:
        data = request.json
        lab_no = data.get('lab_no')
        pc_number = data.get('pc_number')
        is_available = data.get('is_available')

        if not all([lab_no, pc_number is not None, is_available is not None]):
            return jsonify({
                "message": "Missing required fields",
                "status": "error"
            }), 400

        # Check if PC exists in database
        sql = "SELECT * FROM pc_status WHERE lab_no = ? AND pc_number = ?"
        pc = getallprocess(sql, (lab_no, pc_number))

        if pc:
            # Update existing PC status
            sql = """
                UPDATE pc_status 
                SET is_available = ?, updated_at = datetime('now', 'localtime')
                WHERE lab_no = ? AND pc_number = ?
            """
            success = postprocess(sql, (is_available, lab_no, pc_number))
        else:
            # Insert new PC status
            sql = """
                INSERT INTO pc_status (lab_no, pc_number, is_available, created_at, updated_at)
                VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
            """
            success = postprocess(sql, (lab_no, pc_number, is_available))

        if success:
            return jsonify({
                "message": "PC status updated successfully",
                "status": "success"
            }), 200
        else:
            return jsonify({
                "message": "Failed to update PC status",
                "status": "error"
            }), 400

    except Exception as e:
        return jsonify({
            "message": f"Error updating PC status: {str(e)}",
            "status": "error"
        }), 500

@staff_app.route('/staff/laboratory/pc/status/<lab_no>', methods=['GET'])
def get_pc_status(lab_no):
    try:
        sql = "SELECT * FROM pc_status WHERE lab_no = ? ORDER BY pc_number"
        pcs = getallprocess(sql, (lab_no,))
        
        if pcs:
            return jsonify({
                "status": "success",
                "data": [dict(pc) for pc in pcs]
            }), 200
        
        return jsonify({
            "status": "success",
            "data": []
        }), 200

    except Exception as e:
        return jsonify({
            "message": f"Error fetching PC status: {str(e)}",
            "status": "error"
        }), 500

@staff_app.route('/staff/laboratory/materials/<int:id>', methods=['DELETE'])
def delete_material(id):
    if not session.get('logged_in'):
        return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401

    try:
        # First get the material to check if it has a file to delete
        sql = "SELECT file_path FROM materials WHERE id = ?"
        material = getallprocess(sql, (id,))
        
        if material and material[0]['file_path']:
            try:
                # Try to delete the file if it exists
                os.remove(material[0]['file_path'])
            except OSError:
                # If file doesn't exist, just continue
                pass

        # Delete the material from database
        sql = "DELETE FROM materials WHERE id = ?"
        success = postprocess(sql, (id,))

        if success:
            return jsonify({'message': 'Material deleted successfully', 'status': 'success'}), 200
        return jsonify({'message': 'Failed to delete material', 'status': 'error'}), 400

    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500

@staff_app.route('/api/sitin/<int:sitin_id>/reward', methods=['POST'])
def reward_student(sitin_id):
    if not session.get('user'):
        return json_response('Unauthorized', 'error', code=401)
    
    staff_id = session['user']['idno']
    
    try:
        print(f"Attempting to reward student for sit-in ID: {sitin_id}")
        
        # Get the sit-in details
        sitin = get_active_sitin_by_id(sitin_id)
        
        # Debug logging
        print(f"Sit-in data: {sitin}")
        
        if not sitin:
            print(f"Sit-in not found for ID: {sitin_id}")
            return json_response('Sit-in not found', 'error', code=404)
        
        # Check if sit-in is active - sitin is a list of Row objects
        if sitin[0]['status'] != 'active':
            print(f"Sit-in is not active. Status: {sitin[0]['status']}")
            return json_response('Cannot reward an inactive sit-in', 'error', code=400)
        
        student_idno = sitin[0]['idno']
        labno = sitin[0]['labno']
        print(f"Found student ID: {student_idno} for sit-in {sitin_id}")
        
        # Check if student has available sessions
        student = get_student_points(student_idno)
        if not student:
            print(f"Student not found with ID: {student_idno}")
            return json_response('Student not found', 'error', code=404)
            
        if student[0]['no_session'] <= 0:
            print(f"Student {student_idno} has no available sessions")
            return json_response('No available sessions', 'error', code=400)
        
        # Reward the student
        print(f"Rewarding student {student_idno} for sit-in {sitin_id}")
        success = reward_student_points(student_idno, sitin_id, staff_id)
        
        if success:
            # End the sit-in session after rewarding
            print(f"Ending sit-in session {sitin_id} after rewarding")
            end_success = end_sitin(sitin_id)
            
            if end_success:
                return json_response('Student rewarded and session ended successfully')
            else:
                # The reward was successful but ending the session failed
                print(f"Failed to end sit-in session {sitin_id} after rewarding")
                return json_response('Student rewarded but failed to end session', 'warning', code=200)
        
        print(f"Failed to reward student {student_idno} for sit-in {sitin_id}")
        return json_response('Failed to reward student', 'error', code=500)
            
    except Exception as e:
        import traceback
        print(f"Error in reward_student: {str(e)}")
        print(traceback.format_exc())
        return json_response(str(e), 'error', code=500)

@staff_app.route('/api/leaderboard/<string:type>')
def get_leaderboard(type):
    if type not in ['points', 'sitins', 'percentage']:
        return json_response('Invalid leaderboard type', 'error', code=400)
    
    try:
        if type == 'points':
            data = get_leaderboard_points()
        elif type == 'sitins':
            data = get_leaderboard_sitins()
        else:  # percentage
            data = get_leaderboard_percentage()
        
        # Convert the SQLite Row objects to dictionaries
        if data:
            serializable_data = [dict(row) for row in data]
            return json_response('Success', data=serializable_data)
        else:
            return json_response('Success', data=[])
    except Exception as e:
        return json_response(str(e), 'error', code=500)

@staff_app.route('/staff/leaderboard')
def staff_leaderboard():
    if not session.get('user') or session['user']['role'] != 'staff':
        return redirect(url_for('login'))
    return render_template('staff/leaderboard.html')

@staff_app.route('/api/reservation/<int:reservation_id>', methods=['GET'])
def get_reservation_details_route(reservation_id):
    try:
        if not session.get('logged_in'):
            return jsonify({'message': 'Not authenticated', 'status': 'error'}), 401
            
        reservation = get_reservation_details(reservation_id)
        if not reservation:
            return jsonify({'message': 'Reservation not found', 'status': 'error'}), 404
            
        return jsonify(dict(reservation[0]))
        
    except Exception as e:
        return jsonify({'message': str(e), 'status': 'error'}), 500