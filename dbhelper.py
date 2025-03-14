from sqlite3 import connect, Row
import sqlite3
from datetime import datetime

database = 'app.db'

def getallprocess(sql: str, params=()) -> list:
    db = connect(database)
    db.row_factory = Row
    cursor = db.cursor()
    cursor.execute(sql, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return data

def postprocess(sql: str, params=()) -> bool:
    db = connect(database)
    cursor = db.cursor()
    cursor.execute(sql, params)
    db.commit()
    cursor.close()
    db.close()
    return True if cursor.rowcount > 0 else False

def addprocess(table, **kwargs) -> dict:
    keys = list(kwargs.keys())
    values = [f"'{v}'" for v in kwargs.values()]
    
    fld = "`,`".join(keys)
    dta = ",".join(values)
    sql = f"INSERT INTO `{table}` (`{fld}`) VALUES ({ dta })"
    
    return postprocess(sql)

def updateprocess(table, **kwargs) -> bool:
    id_value = kwargs.pop('id')  # Remove id from kwargs and store it
    updates = []
    
    # Create update statements for each field
    for key, value in kwargs.items():
        if value is None:
            updates.append(f"`{key}` = NULL")
        else:
            updates.append(f"`{key}` = '{value}'")
    
    update_str = ", ".join(updates)
    # Use idno for users table, id for others
    id_field = "idno" if table == "users" else "id"
    sql = f"UPDATE {table} SET {update_str} WHERE {id_field} = ?"
    
    return postprocess(sql, (id_value,))
    
def gethistory(sql: str, params=()) -> list:
    db = connect(database)
    db.row_factory = Row
    cursor = db.cursor()
    cursor.execute(sql, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return data

def getstat(sql, params=())-> list:
    conn = connect(database)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_db_connection():
    conn = connect(database)
    conn.row_factory = Row
    return conn

def get_student_reservations(idno):
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
    return getallprocess(sql, (idno,))

def get_reservation_details(reservation_id):
    sql = """
        SELECT r.*, u.no_session, 
               (SELECT COUNT(*) FROM reservations 
                WHERE idno = r.idno AND status = 'completed') as used_sessions
        FROM reservations r
        JOIN users u ON r.idno = u.idno
        WHERE r.id = ?
    """
    return getallprocess(sql, (reservation_id,))

def update_reservation_status(reservation_id, status, staff_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    success = False
    
    try:
        # Update reservation status
        cursor.execute("""
            UPDATE reservations 
            SET status = ? 
            WHERE id = ?
        """, (status, reservation_id))
        
        # Add entry to history table
        cursor.execute("""
            INSERT INTO history (reservation_id, status, updated_at)
            VALUES (?, ?, datetime('now', 'localtime'))
        """, (reservation_id, status))
        
        # Log staff verification
        cursor.execute("""
            INSERT INTO staffverlog (staff_id, reservation_id, action, timestamp)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        """, (staff_id, reservation_id, f"Reservation {status}"))
        
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return success

def get_reservation_history():
    sql = """
        SELECT 
            r.id,
            r.idno,
            u.firstname,
            u.lastname,
            r.date,
            r.time_start,
            r.time_end,
            r.purpose,
            r.labno,
            r.status,
            a.check_in_time,
            a.check_out_time,
            h.updated_at as status_updated_at,
            s.firstname as staff_firstname,
            s.lastname as staff_lastname
        FROM reservations r
        JOIN users u ON r.idno = u.idno
        LEFT JOIN attendancelog a ON r.id = a.reserve_id
        LEFT JOIN history h ON r.id = h.reservation_id
        LEFT JOIN staffverlog sv ON r.id = sv.reservation_id
        LEFT JOIN users s ON sv.staff_id = s.idno
        WHERE r.status IN ('approved', 'completed')
        ORDER BY h.updated_at DESC
    """
    return getallprocess(sql)

def get_dashboard_statistics():
    sql = """
        SELECT 
            total_registered_students,
            currently_sit_in,
            total_sit_in,
            updated_at
        FROM statistics 
        WHERE id = 1
    """
    return getallprocess(sql)

def get_reservation_statistics():
    sql = """
        SELECT purpose, COUNT(*) as count
        FROM reservations
        WHERE status IN ('approved', 'completed')
        GROUP BY purpose
        ORDER BY count DESC
    """
    return getstat(sql)

def check_student_sessions(idno):
    sql = """
        SELECT 
            u.no_session,
            COUNT(r.id) as used_sessions
        FROM users u
        LEFT JOIN reservations r ON u.idno = r.idno
        WHERE u.idno = ? AND r.status = 'completed'
        GROUP BY u.idno, u.no_session
    """
    return getallprocess(sql, (idno,))

def log_attendance(reservation_id, check_type, time=None):
    if time is None:
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if check_type == 'in':
        sql = """
            INSERT INTO attendancelog (reserve_id, idno, check_in_time)
            SELECT id, idno, ? FROM reservations WHERE id = ?
        """
    else:  # check_type == 'out'
        sql = """
            UPDATE attendancelog 
            SET check_out_time = ?
            WHERE reserve_id = ?
        """
    
    return postprocess(sql, (time, reservation_id))

def update_statistics_after_attendance(check_type):
    if check_type == 'in':
        sql = """
            UPDATE statistics
            SET currently_sit_in = currently_sit_in + 1,
                total_sit_in = total_sit_in + 1,
                updated_at = datetime('now', 'localtime')
            WHERE id = 1
        """
    else:  # check_type == 'out'
        sql = """
            UPDATE statistics
            SET currently_sit_in = currently_sit_in - 1,
                updated_at = datetime('now', 'localtime')
            WHERE id = 1
        """
    
    return postprocess(sql)

def get_detailed_history():
    sql = """
        SELECT 
            r.id,
            r.idno,
            u.firstname,
            u.lastname,
            r.date,
            r.time_start,
            r.time_end,
            r.purpose,
            r.labno,
            r.status,
            a.check_in_time,
            a.check_out_time,
            h.updated_at as status_updated_at,
            s.firstname as staff_firstname,
            s.lastname as staff_lastname,
            CASE 
                WHEN a.check_out_time IS NOT NULL THEN 
                    round((julianday(a.check_out_time) - julianday(a.check_in_time)) * 24 * 60, 0)
                ELSE NULL 
            END as duration_minutes
        FROM reservations r
        JOIN users u ON r.idno = u.idno
        JOIN attendancelog a ON r.id = a.reserve_id
        LEFT JOIN history h ON r.id = h.reservation_id
        LEFT JOIN staffverlog sv ON r.id = sv.reservation_id
        LEFT JOIN users s ON sv.staff_id = s.idno
        WHERE r.status = 'completed'
        ORDER BY r.date DESC, r.time_start DESC
    """
    return getallprocess(sql)

def start_sitin(reservation_id, pc_number):
    conn = get_db_connection()
    cursor = conn.cursor()
    success = False
    
    try:
        # Get reservation details and verify it's approved
        cursor.execute("""
            SELECT r.*, u.idno 
            FROM reservations r
            JOIN users u ON r.idno = u.idno
            WHERE r.id = ? AND r.status = 'approved'
        """, (reservation_id,))
        reservation = cursor.fetchone()
        
        if not reservation:
            raise Exception('Invalid or unapproved reservation')
            
        # Check if already has active sit-in
        cursor.execute("""
            SELECT id FROM active_sitin 
            WHERE reservation_id = ? AND status = 'active'
        """, (reservation_id,))
        
        if cursor.fetchone():
            raise Exception('Sit-in already active for this reservation')
            
        # Start sit-in
        cursor.execute("""
            INSERT INTO active_sitin (
                reservation_id, 
                idno, 
                lab_pc_number, 
                start_time,
                expected_end_time,
                status
            )
            VALUES (?, ?, ?, datetime('now', 'localtime'), ?, 'active')
        """, (
            reservation_id, 
            reservation['idno'], 
            pc_number,
            reservation['time_end']
        ))
        
        # Update reservation status
        cursor.execute("""
            UPDATE reservations 
            SET status = 'in_progress' 
            WHERE id = ?
        """, (reservation_id,))
        
        # Add entry to attendancelog
        cursor.execute("""
            INSERT INTO attendancelog (reserve_id, idno, check_in_time)
            VALUES (?, ?, datetime('now', 'localtime'))
        """, (reservation_id, reservation['idno']))
        
        # Update statistics
        cursor.execute("""
            UPDATE statistics
            SET currently_sit_in = currently_sit_in + 1,
                total_sit_in = total_sit_in + 1,
                updated_at = datetime('now', 'localtime')
            WHERE id = 1
        """)
        
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return success

def end_sitin(sitin_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    success = False
    
    try:
        # Get sit-in details
        cursor.execute("""
            SELECT s.*, r.id as reservation_id, r.idno
            FROM active_sitin s
            JOIN reservations r ON s.reservation_id = r.id
            WHERE s.id = ? AND s.status = 'active'
        """, (sitin_id,))
        sitin = cursor.fetchone()
        
        if not sitin:
            raise Exception('Invalid or inactive sit-in')
            
        # End sit-in
        cursor.execute("""
            UPDATE active_sitin 
            SET status = 'completed',
                end_time = datetime('now', 'localtime')
            WHERE id = ?
        """, (sitin_id,))
        
        # Update reservation status
        cursor.execute("""
            UPDATE reservations 
            SET status = 'completed' 
            WHERE id = ?
        """, (sitin['reservation_id'],))
        
        # Update attendancelog
        cursor.execute("""
            UPDATE attendancelog 
            SET check_out_time = datetime('now', 'localtime')
            WHERE reserve_id = ?
        """, (sitin['reservation_id'],))
        
        # Update statistics
        cursor.execute("""
            UPDATE statistics
            SET currently_sit_in = currently_sit_in - 1,
                updated_at = datetime('now', 'localtime')
            WHERE id = 1
        """)
        
        conn.commit()
        success = True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return success

def get_student_sitins(idno):
    sql = """
        SELECT 
            s.*,
            r.date,
            r.labno,
            r.time_start,
            r.time_end,
            r.purpose,
            a.check_in_time,
            a.check_out_time
        FROM active_sitin s
        JOIN reservations r ON s.reservation_id = r.id
        LEFT JOIN attendancelog a ON r.id = a.reserve_id
        WHERE s.idno = ?
        ORDER BY s.start_time DESC
    """
    return getallprocess(sql, (idno,))

def get_active_sitins():
    sql = """
        SELECT 
            s.*,
            r.date,
            r.labno,
            r.time_start,
            r.time_end,
            r.purpose,
            u.firstname,
            u.lastname,
            u.course,
            u.yr_lvl
        FROM active_sitin s
        JOIN reservations r ON s.reservation_id = r.id
        JOIN users u ON s.idno = u.idno
        WHERE s.status = 'active'
        ORDER BY s.start_time DESC
    """
    return getallprocess(sql)

def get_sitin_details(sitin_id):
    sql = """
        SELECT 
            s.*,
            r.date,
            r.labno,
            r.time_start,
            r.time_end,
            r.purpose,
            u.firstname,
            u.lastname,
            u.course,
            u.yr_lvl,
            a.check_in_time,
            a.check_out_time
        FROM active_sitin s
        JOIN reservations r ON s.reservation_id = r.id
        JOIN users u ON s.idno = u.idno
        LEFT JOIN attendancelog a ON r.id = a.reserve_id
        WHERE s.id = ?
    """
    return getallprocess(sql, (sitin_id,))

def get_active_sitin_for_reservation(reservation_id):
    sql = """
        SELECT s.*, r.date, r.time_start, r.time_end, r.labno
        FROM active_sitin s
        JOIN reservations r ON s.reservation_id = r.id
        WHERE s.reservation_id = ? AND s.status = 'active'
    """
    return getallprocess(sql, (reservation_id,))

def get_student_active_sitins(idno):
    sql = """
        SELECT s.*, r.date, r.time_start, r.time_end, r.labno, r.purpose
        FROM active_sitin s
        JOIN reservations r ON s.reservation_id = r.id
        WHERE s.idno = ? AND s.status = 'active'
    """
    return getallprocess(sql, (idno,))