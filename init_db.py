import sqlite3
import json
import datetime
import os

DB_PATH = 'acrh.db'
JSON_PATH = 'data.json'

def create_tables(cursor):
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        password TEXT,
        role TEXT NOT NULL CHECK(role IN ('PATIENT', 'THERAPIST')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
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

    cursor.execute('''
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

    cursor.execute('''
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

    cursor.execute('''
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

def populate_exercises(cursor):
    exercise_map = {
        "wrist_flexion": {
            "name": "Wrist Flexion",
            "instruction": "Bend your wrist forward up to 60°",
            "target": (50, 60),
            "type": "wrist"
        },
        "wrist_extension": {
            "name": "Wrist Extension",
            "instruction": "Bend your wrist backward up to 60°",
            "target": (50, 60),
            "type": "wrist"
        },
        "radial_deviation": {
            "name": "Radial Deviation",
            "instruction": "Move wrist toward thumb side up to 20°",
            "target": (15, 20),
            "type": "wrist"
        },
        "ulnar_deviation": {
            "name": "Ulnar Deviation",
            "instruction": "Move wrist toward pinky side up to 20°",
            "target": (15, 20),
            "type": "wrist"
        },
        "shoulder_flexion": {
            "name": "Shoulder Flexion",
            "instruction": "Raise your arm forward up to 180°",
            "target": (160, 180),
            "type": "shoulder"
        },
        "shoulder_hyperextension": {
            "name": "Shoulder Hyperextension",
            "instruction": "Move your arm backward up to 50°",
            "target": (30, 50),
            "type": "shoulder"
        },
        "shoulder_abduction": {
            "name": "Shoulder Abduction",
            "instruction": "Raise your arm sideways up to 180°",
            "target": (160, 180),
            "type": "shoulder"
        },
        "shoulder_adduction": {
            "name": "Shoulder Adduction",
            "instruction": "Bring your arm toward your body up to 50°",
            "target": (30, 50),
            "type": "shoulder"
        },
        "elbow_flexion": {
            "name": "Elbow Flexion",
            "instruction": "Bend your elbow and bring your hand toward your shoulder",
            "target": (130, 150),
            "type": "elbow"
        },
        "elbow_extension": {
            "name": "Elbow Extension",
            "instruction": "Straighten your arm fully",
            "target": (0, 20),
            "type": "elbow"
        }
    }
    
    exercises_to_insert = []
    
    for key, ex in exercise_map.items():
        script_name = ""
        if ex["type"] == "shoulder":
            script_name = "shoulder.py"
        elif ex["type"] == "wrist":
            script_name = "wrist_rotation_exercises.py"
        elif ex["type"] == "elbow":
            script_name = "elbow_exercises.py"
            
        exercises_to_insert.append((
            key, # This maps better as name or id? we can use id from auto increment, store key somewhere if needed, but 'name' is in schema.
            ex["name"],
            ex["type"],
            None, # description
            ex["instruction"],
            None, # difficulty
            None, # target_repetitions
            None, # duration
            script_name
        ))
        
    for ex_data in exercises_to_insert:
        # Check if already exists
        cursor.execute("SELECT id FROM exercises WHERE name = ?", (ex_data[1],))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO exercises (name, body_part, description, instructions, difficulty, target_repetitions, duration, script_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ex_data[1], ex_data[2], ex_data[3], ex_data[4], ex_data[5], ex_data[6], ex_data[7], ex_data[8]))

def populate_patients(cursor):
    with open(JSON_PATH, 'r') as f:
        data = json.load(f)
        
    for p in data:
        # Create user
        cursor.execute("SELECT id FROM users WHERE name = ? AND role = 'PATIENT'", (p["name"],))
        user_row = cursor.fetchone()
        
        if not user_row:
            cursor.execute("INSERT INTO users (name, role) VALUES (?, ?)", (p["name"], "PATIENT"))
            user_id = cursor.lastrowid
        else:
            user_id = user_row[0]
            
        # Determine affected area from injury_type if possible
        injury = p.get("injury_type", "")
        affected_area = ""
        if "wrist" in injury.lower():
            affected_area = "wrist"
        elif "shoulder" in injury.lower():
            affected_area = "shoulder"
        elif "elbow" in injury.lower():
            affected_area = "elbow"
        elif "finger" in injury.lower():
            affected_area = "finger"
        elif "forearm" in injury.lower():
            affected_area = "forearm"
            
        # Create patient
        cursor.execute("SELECT id FROM patients WHERE user_id = ?", (user_id,))
        patient_row = cursor.fetchone()
        
        if not patient_row:
            cursor.execute("""
                INSERT INTO patients (id, user_id, injury_type, affected_area)
                VALUES (?, ?, ?, ?)
            """, (p["id"], user_id, injury, affected_area))
            patient_id = p["id"]
        else:
            patient_id = patient_row[0]
            
def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    create_tables(cursor)
    populate_exercises(cursor)
    populate_patients(cursor)
    
    conn.commit()
    conn.close()
    print("Database initialization and migration completed successfully.")

if __name__ == "__main__":
    main()
