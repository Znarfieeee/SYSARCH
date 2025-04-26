import sqlite3
from datetime import datetime

def initialize_pc_status():
    """Initialize PC status table with dummy data for lab 526"""
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    
    # First check if the table exists, if not create it
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pc_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lab_no INTEGER NOT NULL,
        pc_number INTEGER NOT NULL,
        is_available INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(lab_no, pc_number)
    )
    ''')
    
    # Add dummy data for lab 526
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Clear existing data for lab 526
    cursor.execute("DELETE FROM pc_status WHERE lab_no = 526")
    
    # Insert 30 PCs for lab 526
    for pc_num in range(1, 31):
        # Randomly make some PCs unavailable
        is_available = 1 if pc_num % 3 != 0 else 0
        
        cursor.execute('''
        INSERT OR REPLACE INTO pc_status 
        (lab_no, pc_number, is_available, created_at, updated_at) 
        VALUES (?, ?, ?, ?, ?)
        ''', (526, pc_num, is_available, current_time, current_time))
    
    conn.commit()
    conn.close()
    print("PC status data initialized for lab 526!")

if __name__ == "__main__":
    initialize_pc_status() 