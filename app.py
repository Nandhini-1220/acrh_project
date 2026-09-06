from flask import Flask, render_template, request, redirect, url_for, session, flash
import subprocess
import sys
import os
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production-12345'


import sqlite3
from werkzeug.security import check_password_hash

def get_db_connection():
    conn = sqlite3.connect('acrh.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        role = request.form.get('role')
        
        if role == 'Patient':
            patient_id = request.form.get('patient_id', '').strip()
            if not patient_id:
                flash('Please enter your Patient ID')
                return render_template('login.html')
                
            try:
                patient_id = int(patient_id)
            except ValueError:
                flash('Invalid Patient ID format')
                return render_template('login.html')
                
            conn = get_db_connection()
            db_patient = conn.execute('''
                SELECT p.id as patient_id, u.id as user_id 
                FROM patients p
                JOIN users u ON p.user_id = u.id
                WHERE p.id = ? AND u.role = 'PATIENT'
            ''', (patient_id,)).fetchone()
            conn.close()
            
            if db_patient:
                session.permanent = True
                session['user_id'] = db_patient['user_id']
                session['role'] = 'patient'
                session['patient_id'] = db_patient['patient_id']
                return redirect(url_for('patient', patient_id=db_patient['patient_id']))
            else:
                flash('Invalid Patient ID')
                
        elif role == 'Therapist':
            email = request.form.get('therapist_email', '').strip()
            if not email:
                flash('Please enter your Email')
                return render_template('login.html')
                
            conn = get_db_connection()
            user = conn.execute('SELECT id FROM users WHERE email = ? AND role = ?', 
                                (email, 'THERAPIST')).fetchone()
            conn.close()
            
            if user:
                session.permanent = True
                session['user_id'] = user['id']
                session['role'] = 'therapist'
                return redirect(url_for('therapist'))
            else:
                flash('Invalid Therapist Email')
        else:
            flash('Please select a valid role')
            
    return render_template('login.html')


def get_patient_progress(patient_id):
    # Get legacy progress
    with open('data.json', 'r') as f:
        patients_data = json.load(f)
    patient_data = next((p for p in patients_data if p['id'] == patient_id), None)
    
    levels = [0, 0, 0, 0]
    if patient_data:
        levels = [
            patient_data.get('level1', 0),
            patient_data.get('level2', 0),
            patient_data.get('level3', 0),
            patient_data.get('level4', 0)
        ]
        
    # Combine with new SQLite sessions (take max reps for each level)
    conn = get_db_connection()
    sessions = conn.execute('''
        SELECT level, MAX(repetitions) as max_reps 
        FROM exercise_sessions 
        WHERE patient_id = ? AND completed = 1
        GROUP BY level
    ''', (patient_id,)).fetchall()
    conn.close()
    
    for row in sessions:
        try:
            lvl_idx = int(row['level']) - 1
            if 0 <= lvl_idx < 4:
                levels[lvl_idx] = max(levels[lvl_idx], row['max_reps'])
        except (ValueError, TypeError):
            pass
            
    overall = min(100.0, (sum(levels) / 40.0) * 100)
    
    return {
        'level1': levels[0],
        'level2': levels[1],
        'level3': levels[2],
        'level4': levels[3],
        'overall': overall,
        'levels_array': levels
    }

def record_exercise_session(patient_id, exercise_key, level, repetitions, score=0, completed=True):
    conn = get_db_connection()
    formatted_name = " ".join([word.capitalize() for word in exercise_key.split('_')])
    exercise = conn.execute('SELECT id FROM exercises WHERE name = ?', (formatted_name,)).fetchone()
    
    if exercise:
        conn.execute('''
            INSERT INTO exercise_sessions 
            (patient_id, exercise_id, level, repetitions, score, completed) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (patient_id, exercise['id'], level, repetitions, score, completed))
        conn.commit()
    else:
        print(f"Warning: Exercise '{formatted_name}' not found in database.")
    conn.close()

@app.route('/therapist')
def therapist():
    if 'role' not in session or session['role'] != 'therapist':
        return redirect(url_for('patient', patient_id=1))
        
    # Get patient info from DB
    conn = get_db_connection()
    db_patients = conn.execute('''
        SELECT p.id, u.name, p.injury_type, p.affected_area
        FROM patients p
        JOIN users u ON p.user_id = u.id
    ''').fetchall()
    conn.close()
    
    patients = []
    for row in db_patients:
        prog = get_patient_progress(row['id'])
        patients.append({
            'id': row['id'],
            'name': row['name'],
            'injury_type': row['injury_type'],
            'affected_area': row['affected_area'],
            'progress': prog['overall']
        })
        
    return render_template('therapist_dashboard.html', patients=patients)


@app.route('/patient/<int:patient_id>')
def patient(patient_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
        
    if session.get('patient_id') and session['patient_id'] != patient_id:
        pass # Allow permissive legacy routing
    
    # Get identity from DB
    conn = get_db_connection()
    db_patient = conn.execute('''
        SELECT p.id, u.name, p.injury_type 
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    ''', (patient_id,)).fetchone()
    conn.close()
    
    if not db_patient:
        flash('Patient not found.')
        return redirect(url_for('index'))
        
    injury = db_patient['injury_type'].lower() if db_patient['injury_type'] else 'unknown'
    progress = get_patient_progress(patient_id)
    
    return render_template('patient_levels.html', patient_id=patient_id, patient_name=db_patient['name'], injury=injury, progress=progress)

@app.route('/patient_room/<int:patient_id>')
def patient_room(patient_id):
    if 'role' not in session or session['role'] != 'therapist':
        return redirect(url_for('patient', patient_id=1))
        
    # Get identity from DB
    conn = get_db_connection()
    db_patient = conn.execute('''
        SELECT p.id, u.name, p.injury_type 
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    ''', (patient_id,)).fetchone()
    conn.close()
    
    if not db_patient:
        flash('Patient not found.')
        return redirect(url_for('therapist'))
        
    patient = {
        'id': db_patient['id'],
        'name': db_patient['name'],
        'injury_type': db_patient['injury_type']
    }
    
    prog = get_patient_progress(patient_id)
    
    return render_template('patient_room.html', patient=patient, level_progress=prog['levels_array'], overall=prog['overall'])


@app.route("/start_exercise/<int:level>")
def start_exercise(level):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('index'))
    
    patient_id = session.get('patient_id')

    if patient_id == 1:
        exercises = {
            1: "wrist_flexion",
            2: "wrist_extension",
            3: "radial_deviation",
            4: "ulnar_deviation"
        }
    elif patient_id == 2:
        exercises = {
            1: "shoulder_flexion",
            2: "shoulder_hyperextension",
            3: "shoulder_abduction",
            4: "shoulder_adduction"
        }
    elif patient_id == 3:
        exercises = {
            1: "elbow_flexion",
            2: "elbow_extension"
        }
    else:
        return redirect(url_for('patient', patient_id=patient_id))

    exercise_key = exercises.get(level)

    if exercise_key:
        return redirect(url_for('exercise_detail', exercise_key=exercise_key, level=level))


@app.route("/run")
def launch_exercise():
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
    project_dir = os.path.dirname(os.path.abspath(__file__))
    exercise_key = request.args.get("exercise")
    level = request.args.get('level', 1)
    patient_id = session.get('patient_id')

    print("Launching:", exercise_key)

    env = {k: str(v) for k, v in os.environ.items()}
    env["EXERCISE_KEY"] = exercise_key
    env["PATIENT_ID"] = str(patient_id or '')
    env["LEVEL"] = str(level)

    print(f"Launching exercise: {exercise_key}")
    
    if "shoulder" in exercise_key:
        script_path = os.path.join(project_dir, "shoulder.py")
    elif "wrist" in exercise_key:
        script_path = os.path.join(project_dir, "wrist_rotation_exercises.py")
    elif "elbow" in exercise_key:
        script_path = os.path.join(project_dir, "elbow_exercises.py")
    elif "finger" in exercise_key or "forearm" in exercise_key:
        script_path = os.path.join(project_dir, "finger.py")  # or appropriate script
    else:
        script_path = os.path.join(project_dir, "index.py")

    subprocess.Popen([sys.executable, script_path], env=env)
    return redirect(url_for('feedback', exercise=exercise_key, level=level))


@app.route("/exercise/<exercise_key>")
def exercise_detail(exercise_key: str):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
    exercise_map = {
        "wrist_flexion": {
            "name": "Wrist Flexion",
            "instruction": "Bend your wrist forward up to 60 degrees",
            "target": (50, 60),
            "type": "wrist"
        },
        "wrist_extension": {
            "name": "Wrist Extension",
            "instruction": "Bend your wrist backward up to 60A",
            "target": (50, 60),
            "type": "wrist"
        },
        "radial_deviation": {
            "name": "Radial Deviation",
            "instruction": "Move wrist toward thumb side up to 20A",
            "target": (15, 20),
            "type": "wrist"
        },
        "ulnar_deviation": {
            "name": "Ulnar Deviation",
            "instruction": "Move wrist toward pinky side up to 20A",
            "target": (15, 20),
            "type": "wrist"
        },
        "shoulder_flexion": {
            "name": "Shoulder Flexion",
            "instruction": "Raise your arm forward up to 180A",
            "target": (160, 180),
            "type": "shoulder"
        },
        "shoulder_hyperextension": {
            "name": "Shoulder Hyperextension",
            "instruction": "Move your arm backward up to 50A",
            "target": (30, 50),
            "type": "shoulder"
        },
        "shoulder_abduction": {
            "name": "Shoulder Abduction",
            "instruction": "Raise your arm sideways up to 180A",
            "target": (160, 180),
            "type": "shoulder"
        },
        "shoulder_adduction": {
            "name": "Shoulder Adduction",
            "instruction": "Bring your arm toward your body up to 50A",
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
    ex = exercise_map.get(exercise_key)
    if not ex:
        return redirect(url_for('index'))
    level = request.args.get('level', 1)
    return render_template("exercise.html", ex_key=exercise_key, ex=ex, level=level)


@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    patient_id = session.get('patient_id') if 'patient_id' in session else 1
    level = request.args.get('level', 1)
    exercise_key = request.args.get("exercise")
    
    if request.method == 'POST':
        reps = int(request.form.get('reps', 0))
        
        # Save newly recorded session into SQLite
        try:
            record_exercise_session(patient_id, exercise_key, level, reps, score=0, completed=True)
            flash(f'Session saved: {reps} reps for Level {level}!')
        except Exception as e:
            print("Error recording session:", e)
            flash('Error recording progress. Please try again.')
            
        return redirect(url_for('patient', patient_id=patient_id))
    
    return render_template("feedback.html", exercise_key=exercise_key, patient_id=patient_id, level=level)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

