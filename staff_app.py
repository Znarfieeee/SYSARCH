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
from reportlab.lib.pagesizes import letter, landscape, legal
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

staff_app = Blueprint('staff_app', __name__)

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
        WHERE u.role = 'student'
        ORDER BY u.idno
    """
    
    students = getallprocess(sql)
    
    if students:
        students_list = []
        for student in students:
            student_dict = dict(student)
            student_dict['sessions'] = student_dict.get('sessions', 0)
            student_dict['remaining_sessions'] = student_dict.get('no_session', 0) - student_dict['sessions']
            students_list.append(student_dict)
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

@staff_app.route('/staff/reports/level')
def staff_reports_level():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    students = get_total_sitins_level()
    
    if students:
        students_list = []
        for student in students:
            student_dict = dict(student)
            # Ensure all fields are included for filtering
            student_dict['yr_lvl'] = student_dict.get('yr_lvl', '')
            student_dict['date'] = student_dict.get('date', '')
            students_list.append(student_dict)
    else:
        students_list = []
    
    return render_template("staff/reports-pl.html", 
                           pagetitle='Reports per Level',
                           students=students_list)

@staff_app.route('/staff/feedbacks')
def staff_feedbacks():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("staff/feedbacks.html", pagetitle='Feedbacks')

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

@staff_app.route('/api/student/<int:idno>')
def get_student(idno):
    sql = "SELECT * FROM users WHERE idno = ?"
    student = getallprocess(sql, (idno,))
    if student:
        return jsonify(dict(student[0]))
    return jsonify({'message': 'Student not found!', 'status': 'error'}), 404

@staff_app.route('/api/student/<int:idno>/edit', methods=['POST'])
def update_student(idno):
    try:
        # Handle photo deletion
        should_delete_photo = request.form.get('delete_photo') == 'true'
        
        # Get current user data
        sql = "SELECT photo FROM users WHERE idno = ?"
        current_user = getallprocess(sql, (idno,))
        
        update_data = {
            'id': idno,  # This will be used as idno in updateprocess
            'firstname': request.form.get('firstname'),
            'middlename': request.form.get('middlename'),
            'lastname': request.form.get('lastname'),
            'course': request.form.get('course'),
            'yr_lvl': request.form.get('yr_lvl'),
            'email': request.form.get('email')
        }
        
        if should_delete_photo and current_user:
            # Delete the physical file if it exists
            old_photo = current_user[0]['photo']
            if old_photo and os.path.exists(old_photo):
                try:
                    os.remove(old_photo)
                except:
                    pass  # Ignore file deletion errors
            update_data['photo'] = None
        
        success = updateprocess('users', **update_data)
        
        if success:
            return jsonify({'message': 'Student update succesfully', 'status': 'success'}), 200

        
        return jsonify({'message': 'Failed to update student!', 'status': 'error'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@staff_app.route('/api/student/add', methods=['POST'])
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
        
        sql = "SELECT id, idno FROM active_sitin WHERE id = ? AND status = 'active'"
        sitin = getallprocess(sql, (sitin_id,))
        
        if not sitin:
            return jsonify({'message': 'No active sit-in found', 'status': 'error'}), 404
        
        sitin_id = sitin[0]['id']
        student_idno = sitin[0]['idno']
        
        success = end_sitin(sitin_id)
        
        if success:
            update_sessions(student_idno)
            return jsonify({'message': 'Sit-in ended successfully', 'status': 'success'}), 200
        
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
        students = get_pending_reservations()
        return jsonify([dict(student) for student in students] if students else [])
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
        if success:
            return jsonify({'message': 'Student sessions reset successfully', 'status': 'success'}), 200
        
        return jsonify({'message': 'Failed to reset student sessions', 'status': 'error'}), 400
        
    except Exception as e:
        return jsonify({'message': f'Error resetting sessions: {str(e)}', 'status': 'error'}), 500

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
        level = data.get('level')
        date = data.get('date')
        page = data.get('page')
        
        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").strftime("%B %d, %Y")
            except ValueError:
                return jsonify({'message': 'Invalid date format'}), 400
        else:
            date = "ALL DATES"
        
        if page == 'pl':
            if level:
                report_title = f"REPORT FOR LEVEL {level} ON {date}"
            else:  
                report_title = f"REPORT FOR ALL LEVELS {date}"
        elif page == 'pp':
            if purpose: 
                report_title = f"REPORT FOR {purpose.upper()} ON {date}"
            else:
                report_title = f"REPORT FOR ALL PURPOSES ON {date}"
        else:
            report_title = f"RERORT FOR ALL STUDENTS"

        # Create buffer here before any file type handling
        buffer = BytesIO()

        if file_type == 'csv':
            try:
                text_buffer = io.StringIO()
                writer = csv.writer(text_buffer)
                writer.writerow([report_title])
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

                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#D3D3D3',  # Light grey background like PDF
                    'font_color': '#000000', # Black text like PDF
                    'font_size': 14,         # Match PDF font size
                    'font_name': 'Helvetica',
                    'align': 'left',         # Left align like PDF
                    'border_color': '#D3D3D3', # Light grey border like PDF
                    'bottom': 1,             # Bottom border only like PDF
                    'text_wrap': True,       # Enable text wrapping
                })

                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 18,         # Match PDF title size
                    'font_name': 'Helvetica',
                    'align': 'center',
                    'valign': 'vcenter',
                })

                data_format = workbook.add_format({
                    'font_size': 12,         # Match PDF body text size
                    'font_name': 'Helvetica',
                    'align': 'left',
                    'border_color': '#D3D3D3',
                    'bottom': 1,             # Bottom border only
                    'text_wrap': True,       # Enable text wrapping
                    'valign': 'vcenter',     # Vertically center wrapped text
                })

                # Add extra space after title
                worksheet.set_row(0, 30)  # Taller row for title
                worksheet.set_row(1, 20)  # Empty row for spacing

                # Write title
                worksheet.merge_range(0, 0, 0, len(headers) - 1, report_title, title_format)
                worksheet.write_blank(1, 0, None) 

                # Write headers
                for col, header in enumerate(headers):
                    worksheet.write(2, col, header, header_format)

                # Write data with consistent formatting
                for row_idx, row in enumerate(rows, start=3):
                    worksheet.set_row(row_idx, 30)  # Match PDF row height
                    for col_idx, cell in enumerate(row):
                        worksheet.write(row_idx, col_idx, cell, data_format)

                # Adjust column widths based on content with padding
                for col_idx, header in enumerate(headers):
                    max_width = len(header)
                    for row in rows:
                        cell_content = str(row[col_idx])
                        # Calculate width based on full cell content
                        content_width = len(cell_content)
                        max_width = max(max_width, content_width)
                    
                    # Add left and right padding (3 characters each side)
                    padded_width = max_width + 6
                    
                    # Set minimum width to ensure readability
                    final_width = max(padded_width, 10)
                    
                    # Set column width with automatic text wrapping
                    worksheet.set_column(col_idx, col_idx, final_width, None, {'text_wrap': True})

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
                
                # Add title with smaller font
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=getSampleStyleSheet()['Title'],
                    fontSize=18,
                    spaceAfter=20,
                    alignment=1  # Center alignment
                )
                title = Paragraph(report_title, title_style)
                elements.append(title)
                
                # Create table with adjusted style
                table_data = [headers] + rows
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 20),  # Increased gap
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('LINEBELOW', (0, 0), (-1, -1), 1, colors.lightgrey),  # Bottom border only in light grey
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5)
                ])
                
                # Calculate column widths based on content
                table = Table(table_data)
                table.setStyle(table_style)
                
                # Create table without repeating headers
                table = Table(table_data)
                table.setStyle(table_style)
                elements.append(table)
                
                # Build the PDF
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