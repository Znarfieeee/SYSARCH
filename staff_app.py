from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from dbhelper import *
import os
from werkzeug.utils import secure_filename
from datetime import datetime

staff_app = Blueprint('staff_app', __name__)


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
    return render_template("staff/reports.html", pagetitle='Reports')

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
        return redirect(url_for('login'))
    
    
    idno = session['user']['idno']
    title = request.form.get('title')
    content = request.form.get('content')

    success = addprocess('announcement', idno=idno, 
                         title=title, 
                         content=content)
    
    if success:
        return jsonify({'message': 'Announcement created successfully'}), 200
    return jsonify({'message': 'Failed to create announcement'}), 400

@staff_app.route('/announcement/<int:id>', methods=['DELETE'])
def delete_announcement(id):
    sql = f"DELETE FROM announcement WHERE id = ?"
    success = postprocess(sql, (id,))
    
    if success:
        return jsonify({'message': 'Announcement deleted successfully'}), 200
    return jsonify({'message': 'Failed to delete announcement'}), 400

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
            return jsonify({'message': 'Announcement updated successfully'}), 200
        return jsonify({'message': 'Failed to update announcement'}), 400
            
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@staff_app.route('/api/book', methods=['POST'])
def book_res():
    idno = request.form.get('idno')
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

    return redirect(url_for('staff_app.staff_students_pending'))

@staff_app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        stats = get_dashboard_statistics()
        if stats:
            stats_dict = dict(stats[0])
            # Ensure values are not None and non-negative
            stats_dict = {
                'total_registered_students': max(0, stats_dict.get('total_registered_students', 0) -1),
                'currently_sit_in': max(0, stats_dict.get('currently_sit_in', 0)),
                'total_sit_in': max(0, stats_dict.get('currently_sit_in', 0) + stats_dict.get('completed_sit_ins', 0) -1)
            }
            return jsonify(stats_dict)
        return jsonify({
            'total_registered_students': 0,
            'currently_sit_in': 0,
            'total_sit_in': 0
        })
    except Exception as e:
        print(f"Error in get_statistics: {str(e)}")
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
        return jsonify({"error": "No reservation statistics found"}), 404

@staff_app.route('/api/student/<int:idno>')
def get_student(idno):
    sql = "SELECT * FROM users WHERE idno = ?"
    student = getallprocess(sql, (idno,))
    if student:
        return jsonify(dict(student[0]))
    return jsonify({'error': 'Student not found'}), 404

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
            return jsonify({'message': 'Student updated successfully'}), 200
        return jsonify({'error': 'Failed to update student'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/student/<int:idno>', methods=['DELETE'])
def delete_student(idno):
    try:
        sql = "DELETE FROM users WHERE idno = ?"
        success = postprocess(sql, (idno,))
        
        if success:
            return jsonify({'message': 'Student deleted successfully'}), 200
        return jsonify({'error': 'Failed to delete student'}), 400
    
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
            'middlename': request.form.get('middlename'),
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
        
        if success:
            return jsonify({'message': 'Student added successfully'}), 200
        return jsonify({'error': 'Failed to add student'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/student/<int:idno>/reservations')
def get_student_reservations(idno):
    try:
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
            return jsonify(formatted_reservations)
        return jsonify([])
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/reservation/<int:reservation_id>/status', methods=['POST'])
def update_reservation_status_route(reservation_id):
    try:
        status = request.json.get('status')
        staff_id = session.get('user', {}).get('idno')
        
        if not staff_id:
            return jsonify({'error': 'Staff not authenticated'}), 401
            
        if status not in ['approved', 'denied']:
            return jsonify({'error': 'Invalid status'}), 400
            
        # Get reservation details and check sessions
        reservation = get_reservation_details(reservation_id)
        if not reservation:
            return jsonify({'error': 'Reservation not found'}), 404
            
        # Check remaining sessions if approving
        if status == 'approved':
            sessions = check_student_sessions(reservation[0]['idno'])
            if sessions and sessions[0]['used_sessions'] >= sessions[0]['no_session']:
                return jsonify({'error': 'Student has no remaining sessions'}), 400
        
        # Update the reservation status
        success = update_reservation_status(reservation_id, status, staff_id)
        
        if success:
            return jsonify({'message': f'Reservation {status} successfully'}), 200
        return jsonify({'error': 'Failed to update reservation'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/history')
def get_history_route():
    try:
        history = get_reservation_history()
        return jsonify([dict(row) for row in history] if history else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            return jsonify({'error': 'Not authenticated'}), 401
            
        data = request.json
        idno = data.get('idno')
        end_time = data.get('expected_end_time')
        notes = data.get('notes')
        reservation_id = data.get('reservation_id')
        labno = data.get('labno')
        purpose = data.get('purpose')
        
        # Validate required fields
        if not all([labno, purpose, idno, end_time]):
            return jsonify({'error': 'Missing required data'}), 400
        
        # Start the sit-in
        success = start_sitin(
            idno=idno,
            end_time=end_time,
            notes=notes,
            reservation_id=reservation_id,
            pc_number=labno,
            purpose=purpose
        )
        
        if success:
            return jsonify({'message': 'Sit-in started successfully'}), 200
        return jsonify({'error': 'Failed to start sit-in'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/sitin/<int:sitin_id>/end', methods=['POST'])
def end_sitin_route(sitin_id):
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Get the sit-in details
        sql = "SELECT id, idno FROM active_sitin WHERE id = ? AND status = 'active'"
        sitin = getallprocess(sql, (sitin_id,))
        
        if not sitin:
            return jsonify({'error': 'No active sit-in found'}), 404
        
        sitin_id = sitin[0]['id']
        student_idno = sitin[0]['idno']
        
        # End the sit-in
        success = end_sitin(sitin_id)
        
        if success:
            update_sessions(student_idno)
            
            return jsonify({'message': 'Sit-in ended successfully and session deducted'}), 200
        return jsonify({'error': 'Failed to end sit-in'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@staff_app.route('/api/sitin/active')
def get_active_sitins_route():
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401
            
        sitins = get_active_sitins()
        
        # Add additional debugging information
        if sitins:
            return jsonify([dict(row) for row in sitins])
        return jsonify([])
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_active_sitins_route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/check-in/<int:reservation_id>', methods=['POST'])
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

@staff_app.route('/api/check-out/<int:reservation_id>', methods=['POST'])
def check_out(reservation_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get the active sit-in for this reservation
        sql = "SELECT id, idno FROM active_sitin WHERE reservation_id = ? AND status = 'active'"
        sitin = getallprocess(sql, (reservation_id,))
        
        if not sitin:
            return jsonify({'error': 'No active sit-in found'}), 404
        
        sitin_id = sitin[0]['id']
        student_idno = sitin[0]['idno']
        
        # End the sit-in
        success = end_sitin(sitin_id)
        
        if success:
            # Deduct one session from the student's remaining sessions
            update_sessions_sql = """
                UPDATE users
                SET no_session = no_session - 1
                WHERE idno = ? AND no_session > 0
            """
            postprocess(update_sessions_sql, (student_idno,))
            
            return jsonify({'message': 'Check-out successful and session deducted'}), 200
        return jsonify({'error': 'Failed to check out'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/sitin/add', methods=['POST'])
def add_sitin():
    try:
        if not session.get('logged_in'):
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.json
        idno = data.get('idno')
        
        # First, check if the student exists
        student = check_student_exist(idno)
        
        if not student:
            return jsonify({'error': 'Student not registered in the system'}), 404
                
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
            return jsonify({'error': 'Student is already in a sit-in'}), 400
        else:
            success = addprocess('active_sitin', **sitin_data)

        if success:
            return jsonify({'message': 'Sit-in added successfully'}), 200
        return jsonify({'error': 'Failed to add sit-in'}), 400

    except Exception as e:
        print(f"Add sit-in error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@staff_app.route('/api/reservation_count', methods=['GET'])
def get_reservation_count():
    if not session.get('logged_in'):
        return jsonify({'error': 'Not authenticated'}), 401

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

