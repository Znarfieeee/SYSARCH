-- Student Points Table
CREATE TABLE student_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idno INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    total_sitins INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE
);

-- Points History Table
CREATE TABLE points_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idno INTEGER NOT NULL,
    sitin_id INTEGER NOT NULL,
    points_earned INTEGER NOT NULL,
    action_type TEXT NOT NULL, -- 'reward' or 'sitin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    staff_id INTEGER NOT NULL,
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE,
    FOREIGN KEY (sitin_id) REFERENCES active_sitin(id) ON DELETE CASCADE,
    FOREIGN KEY (staff_id) REFERENCES users(idno)
);

-- Create trigger to initialize student_points when new user is added
CREATE TRIGGER init_student_points
AFTER INSERT ON users
WHEN NEW.role = 'student'
BEGIN
    INSERT INTO student_points (idno)
    VALUES (NEW.idno);
END;

-- Create trigger to update student_points when points are earned
CREATE TRIGGER update_student_points
AFTER INSERT ON points_history
BEGIN
    UPDATE student_points 
    SET 
        points = points + NEW.points_earned,
        total_sitins = CASE 
            WHEN NEW.action_type = 'sitin' THEN total_sitins + 1
            ELSE total_sitins
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE idno = NEW.idno;
END;

-- Add points column to users table
ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN total_sitins INTEGER DEFAULT 0;

-- Create views for different leaderboard rankings
CREATE VIEW leaderboard_points AS
SELECT 
    idno,
    firstname,
    lastname,
    course,
    yr_lvl,
    points,
    total_sitins,
    CAST(points AS FLOAT) / CASE WHEN total_sitins = 0 THEN 1 ELSE total_sitins END as points_per_sitin
FROM users
WHERE role = 'student'
ORDER BY points DESC;

CREATE VIEW leaderboard_sitins AS
SELECT 
    idno,
    firstname,
    lastname,
    course,
    yr_lvl,
    total_sitins,
    points
FROM users
WHERE role = 'student'
ORDER BY total_sitins DESC;

CREATE VIEW leaderboard_percentage AS
SELECT 
    idno,
    firstname,
    lastname,
    course,
    yr_lvl,
    points,
    total_sitins,
    CAST(points AS FLOAT) / CASE WHEN total_sitins = 0 THEN 1 ELSE total_sitins END * 100 as percentage
FROM users
WHERE role = 'student'
ORDER BY percentage DESC; 