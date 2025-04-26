CREATE TABLE reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idno INTEGER NOT NULL,
    date TEXT NOT NULL,
    status VARCHAR(15),
    created_at TEXT DEFAULT (datetime('now','localtime')),
    time_start TEXT,
    time_end TEXT,
    purpose TEXT,
    labno TEXT, status_updated_at text, pcno char(5),
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE
);
CREATE INDEX idx_reservations_idno ON reservations(idno);
sqlite> .schema
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE users
( id integer primary key autoincrement,
idno text unique,
lastname text,
firstname text,
middlename text,
yr_lvl integer(5),
username text unique,
password text,
role text,
email text,
photo text,
course text, no_session integer, points INTEGER DEFAULT 0, total_sitins INTEGER DEFAULT 0);
CREATE TABLE attendancelog(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reserve_id INTEGER NOT NULL,
    idno INTEGER NOT NULL,
    start_time TEXT,
    end_time TEXT,
    verified_by TEXT,
    FOREIGN KEY (reserve_id) REFERENCES reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE
);
CREATE TABLE staffverlog(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER NOT NULL,
    reservation_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (staff_id) REFERENCES users(idno) ON DELETE CASCADE,
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE
);
CREATE TABLE reservations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idno INTEGER NOT NULL,
    date TEXT NOT NULL,
    status VARCHAR(15),
    created_at TEXT DEFAULT (datetime('now','localtime')),
    time_start TEXT,
    time_end TEXT,
    purpose TEXT,
    labno TEXT, status_updated_at text, pcno char(5),
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE
);
CREATE TABLE announcement(
id integer primary key autoincrement,
title text,
content text,
created_at text default (datetime('now', 'localtime')),
idno integer references users(idno));
CREATE TABLE statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_registered_students INTEGER DEFAULT 0,
    currently_sit_in INTEGER DEFAULT 0,
    total_sit_in INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TRIGGER update_total_registered_students
AFTER INSERT ON users
BEGIN
    UPDATE statistics
    SET total_registered_students = total_registered_students + 1,
        updated_at = datetime('now', 'localtime')
    WHERE id = 1;
END;
CREATE TRIGGER update_currently_sit_in_check_in
AFTER INSERT ON attendancelog
BEGIN
    UPDATE statistics
    SET currently_sit_in = currently_sit_in + 1,
        total_sit_in = total_sit_in + 1,
        updated_at = datetime('now', 'localtime')
    WHERE id = 1;
END;
CREATE TRIGGER update_currently_sit_in_check_out
AFTER UPDATE OF end_time ON attendancelog
BEGIN
    UPDATE statistics
    SET currently_sit_in = currently_sit_in - 1,
        updated_at = datetime('now', 'localtime')
    WHERE id = 1;
END;
CREATE TABLE history (
id integer primary key autoincrement,
status text,
updated_at timatstamp default current_timestamp,
reservation_id references reservations(id));
CREATE TABLE active_sitin(
id integer primary key autoincrement,
labno text,
start_time text default(datetime('now', 'localtime')),
end_time text,
status text default 'active',
notes text,
idno integer references users(idno) on delete cascade,
reservation_id integer references reservations(id) on delete cascade, purpose text);
CREATE INDEX idx_active_sitin_status ON active_sitin(status);
CREATE INDEX idx_active_sitin_idno ON active_sitin(idno);
CREATE INDEX idx_reservations_idno ON reservations(idno);
CREATE TABLE FEEDBACKS(
ID INTEGER PRIMARY KEY AUTOINCREMENT,
RATING INTEGER CHECK (RATING BETWEEN 1 AND 5),
COMMENTS TEXT,
ISSUES TEXT,
CREATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,
SITIN_ID INTEGER REFERENCES RESERVATIONS(ID),
IDNO INTEGER REFERENCES USERS(IDNO), labno text);
CREATE TABLE lab_schedule(
id integer primary key autoincrement,
labno varchar(5),
time varchar(20),
day varchar(20),
created_at varchar(20));
CREATE TABLE pc_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lab_no TEXT NOT NULL,
    pc_number INTEGER NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE(lab_no, pc_number)
);
CREATE TABLE resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    type TEXT NOT NULL,  -- document, video, link
    link TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, file varchar(255));
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,  -- software, hardware, tool
    description TEXT,
    file_path TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TRIGGER update_resources_timestamp
AFTER UPDATE ON resources
BEGIN
    UPDATE resources SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TRIGGER update_materials_timestamp
AFTER UPDATE ON materials
BEGIN
    UPDATE materials SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
CREATE TABLE student_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idno INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    total_sitins INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (idno) REFERENCES users(idno) ON DELETE CASCADE
);
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
CREATE TRIGGER init_student_points
AFTER INSERT ON users
WHEN NEW.role = 'student'
BEGIN
    INSERT INTO student_points (idno)
    VALUES (NEW.idno);
END;
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
ORDER BY points DESC
/* leaderboard_points(idno,firstname,lastname,course,yr_lvl,points,total_sitins,points_per_sitin) */;
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
ORDER BY total_sitins DESC
/* leaderboard_sitins(idno,firstname,lastname,course,yr_lvl,total_sitins,points) */;
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
ORDER BY percentage DESC
/* leaderboard_percentage(idno,firstname,lastname,course,yr_lvl,points,total_sitins,percentage) */;