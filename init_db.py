import sqlite3

def init_db():
    conn = sqlite3.connect('acrh.db')
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        password TEXT,
        role TEXT NOT NULL CHECK(role IN ('PATIENT', 'THERAPIST')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        injury_type TEXT,
        affected_area TEXT,
        therapist_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (therapist_id) REFERENCES users (id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        body_part TEXT,
        description TEXT,
        instructions TEXT,
        difficulty INTEGER,
        target_repetitions INTEGER,
        duration INTEGER,
        script_name TEXT
    )
    ''')
    
    # Safe migration for exercises table
    try:
        c.execute('ALTER TABLE exercises ADD COLUMN target_angle_min INTEGER')
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute('ALTER TABLE exercises ADD COLUMN target_angle_max INTEGER')
    except sqlite3.OperationalError:
        pass

    c.execute('''
    CREATE TABLE IF NOT EXISTS exercise_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        exercise_id INTEGER,
        therapist_id INTEGER,
        level INTEGER,
        target_repetitions INTEGER,
        assigned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (exercise_id) REFERENCES exercises (id),
        FOREIGN KEY (therapist_id) REFERENCES users (id)
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS exercise_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        exercise_id INTEGER,
        level INTEGER,
        repetitions INTEGER,
        score INTEGER,
        completed BOOLEAN,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients (id),
        FOREIGN KEY (exercise_id) REFERENCES exercises (id)
    )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Database initialized/migrated safely.')
