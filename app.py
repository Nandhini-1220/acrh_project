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
    # 1. Get legacy progress
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
        
    conn = get_db_connection()
    
    # 2. Update levels array using MAX reps from sessions (Legacy Compatibility)
    max_sessions = conn.execute('''
        SELECT level, MAX(repetitions) as max_reps 
        FROM exercise_sessions 
        WHERE patient_id = ? AND completed = 1
        GROUP BY level
    ''', (patient_id,)).fetchall()
    
    for row in max_sessions:
        try:
            lvl_idx = int(row['level']) - 1
            if 0 <= lvl_idx < 4:
                levels[lvl_idx] = max(levels[lvl_idx], row['max_reps'])
        except (ValueError, TypeError):
            pass
            
    # 3. New Phase 6 Analytics
    assignments = conn.execute('''
        SELECT id, exercise_id, level, target_repetitions 
        FROM exercise_assignments 
        WHERE patient_id = ?
    ''', (patient_id,)).fetchall()
    
    assigned_count = len(assignments)
    
    sessions = conn.execute('''
        SELECT exercise_id, level, repetitions, timestamp
        FROM exercise_sessions
        WHERE patient_id = ? AND completed = 1
        ORDER BY timestamp DESC
    ''', (patient_id,)).fetchall()
    
    total_sessions_count = len(sessions)
    latest_activity = sessions[0]['timestamp'] if sessions else "No activity yet"
    
    completed_assignments_count = 0
    total_percentage_sum = 0
    
    for a in assignments:
        a_ex_id = a['exercise_id']
        a_level = a['level']
        a_target = a['target_repetitions']
        
        a_sessions = [s for s in sessions if s['exercise_id'] == a_ex_id and s['level'] == a_level]
        if a_sessions:
            latest_reps = a_sessions[0]['repetitions']
            pct = min(100, int((latest_reps / a_target) * 100)) if a_target > 0 else 100
            total_percentage_sum += pct
            if latest_reps >= a_target:
                completed_assignments_count += 1
                
    # PRECEDENCE RULE: 
    # If the patient has explicitly assigned exercises in SQLite, use those to compute overall progress.
    # Otherwise, set progress to 0 (do not fall back to legacy data.json).
    if assigned_count > 0:
        overall_progress = int(total_percentage_sum / assigned_count)
    else:
        overall_progress = 0
        
    conn.close()
    
    return {
        'level1': levels[0],
        'level2': levels[1],
        'level3': levels[2],
        'level4': levels[3],
        'overall': overall_progress,
        'assigned_count': assigned_count,
        'completed_assignments_count': completed_assignments_count,
        'total_sessions_count': total_sessions_count,
        'latest_activity': latest_activity
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
            'name': f"Patient {row['id']}",
            'injury_type': row['injury_type'],
            'affected_area': row['affected_area'],
            'progress': prog['overall'],
            'assigned_count': prog['assigned_count'],
            'completed_assignments_count': prog['completed_assignments_count'],
            'latest_activity': prog['latest_activity']
        })
        
    return render_template('therapist_dashboard.html', patients=patients)


@app.route('/patient/<int:patient_id>')
def patient(patient_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
        
    # Use authenticated session for patient_id if available to enforce isolation
    auth_patient_id = session.get('patient_id')
    if auth_patient_id and auth_patient_id != patient_id:
        flash('You can only view your own assignments.')
        return redirect(url_for('patient', patient_id=auth_patient_id))
        
    # Get identity and assignments from DB
    conn = get_db_connection()
    db_patient = conn.execute('''
        SELECT p.id, u.name, p.injury_type 
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = ?
    ''', (patient_id,)).fetchone()
    
    if not db_patient:
        conn.close()
        flash('Patient not found.')
        return redirect(url_for('index'))
        
    assigned_exercises = conn.execute('''
        SELECT 
            ea.id, 
            ea.level, 
            ea.target_repetitions, 
            e.name as exercise_name, 
            e.body_part, 
            e.instructions,
            (SELECT repetitions FROM exercise_sessions es 
             WHERE es.patient_id = ea.patient_id 
               AND es.exercise_id = ea.exercise_id 
               AND es.level = ea.level 
               AND es.completed = 1 
             ORDER BY timestamp DESC LIMIT 1) as latest_reps
        FROM exercise_assignments ea
        JOIN exercises e ON ea.exercise_id = e.id
        WHERE ea.patient_id = ?
        ORDER BY ea.assigned_date DESC
    ''', (patient_id,)).fetchall()
    
    conn.close()
    
    injury = db_patient['injury_type'].lower() if db_patient['injury_type'] else 'unknown'
    progress = get_patient_progress(patient_id)
    
    return render_template('patient_levels.html', patient_id=patient_id, patient_name=f"Patient {patient_id}", injury=injury, progress=progress, assigned_exercises=assigned_exercises)

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
    
    if not db_patient:
        conn.close()
        flash('Patient not found.')
        return redirect(url_for('therapist'))
        
    exercises = conn.execute('SELECT id, name, body_part FROM exercises ORDER BY id').fetchall()
    conn.close()
    
    patient = {
        'id': db_patient['id'],
        'name': f"Patient {db_patient['id']}",
        'injury_type': db_patient['injury_type']
    }
    
    prog = get_patient_progress(patient_id)
    
    return render_template('patient_room.html', patient=patient, overall=prog['overall'], exercises=exercises)


@app.route('/assign_exercise/<int:patient_id>', methods=['POST'])
def assign_exercise(patient_id):
    if 'role' not in session or session['role'] != 'therapist':
        return redirect(url_for('index'))
        
    exercise_id = request.form.get('exercise_id')
    level = request.form.get('level')
    target_repetitions = request.form.get('target_repetitions')
    
    if not exercise_id or not level or not target_repetitions:
        flash('Please fill in all fields.')
        return redirect(url_for('patient_room', patient_id=patient_id))
        
    try:
        level = int(level)
        target_repetitions = int(target_repetitions)
    except ValueError:
        flash('Invalid numeric format.')
        return redirect(url_for('patient_room', patient_id=patient_id))
        
    if target_repetitions <= 0:
        flash('Target repetitions must be greater than 0.')
        return redirect(url_for('patient_room', patient_id=patient_id))
        
    therapist_user_id = session.get('user_id')
    
    conn = get_db_connection()
    
    # Verify patient exists
    patient_exists = conn.execute('SELECT id FROM patients WHERE id = ?', (patient_id,)).fetchone()
    if not patient_exists:
        flash('Patient not found.')
        conn.close()
        return redirect(url_for('therapist'))
        
    # Check for duplicate assignment
    existing = conn.execute('''
        SELECT id FROM exercise_assignments 
        WHERE patient_id = ? AND exercise_id = ? AND level = ?
    ''', (patient_id, exercise_id, level)).fetchone()
    
    if existing:
        flash('This exercise is already assigned to this patient at this level.')
    else:
        conn.execute('''
            INSERT INTO exercise_assignments (patient_id, exercise_id, therapist_id, level, target_repetitions, assigned_date)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (patient_id, exercise_id, therapist_user_id, level, target_repetitions))
        conn.commit()
        flash('Exercise successfully assigned!')
        
    conn.close()
    return redirect(url_for('patient_room', patient_id=patient_id))


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
    import uuid
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
    project_dir = os.path.dirname(os.path.abspath(__file__))
    exercise_key = request.args.get("exercise")
    level = request.args.get('level', 1)
    patient_id = session.get('patient_id')

    # Verify the exercise is actually assigned to the patient
    conn = get_db_connection()
    assigned = conn.execute('''
        SELECT 1 FROM exercise_assignments ea 
        JOIN exercises e ON ea.exercise_id = e.id 
        WHERE ea.patient_id = ? AND LOWER(REPLACE(e.name, ' ', '_')) = ? AND ea.level = ?
    ''', (patient_id, exercise_key, level)).fetchone()
    conn.close()
    
    if not assigned:
        flash("You do not have this exercise assigned at this level.")
        return redirect(url_for('patient', patient_id=patient_id))

    print("Launching:", exercise_key)
    
    # Generate token
    token = str(uuid.uuid4())
    ACTIVE_TOKENS[token] = {
        "patient_id": patient_id,
        "exercise_key": exercise_key,
        "level": level
    }

    env = {k: str(v) for k, v in os.environ.items()}
    env["EXERCISE_KEY"] = exercise_key
    env["PATIENT_ID"] = str(patient_id or '')
    env["LEVEL"] = str(level)
    env["API_TOKEN"] = token
    env["API_URL"] = request.host_url.rstrip('/') + "/api/record_session"

    print(f"Launching exercise: {exercise_key}")
    
    script_path = None
    
    # Try to get script_name from SQLite database
    if exercise_key:
        formatted_name = " ".join([w.capitalize() for w in exercise_key.split('_')])
        conn = get_db_connection()
        exercise = conn.execute('SELECT script_name FROM exercises WHERE name = ?', (formatted_name,)).fetchone()
        conn.close()
        
        if exercise and exercise['script_name']:
            script_path = os.path.join(project_dir, exercise['script_name'])
            
    # Legacy fallback if not found in database
    if not script_path:
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
    return redirect(url_for('feedback', exercise=exercise_key, level=level, token=token))


@app.route("/exercise/<exercise_key>")
def exercise_detail(exercise_key: str):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
        
    formatted_name = " ".join([w.capitalize() for w in exercise_key.split('_')])
    conn = get_db_connection()
    exercise = conn.execute('SELECT * FROM exercises WHERE name = ?', (formatted_name,)).fetchone()
    conn.close()
    
    if not exercise:
        return redirect(url_for('index'))
        
    level = request.args.get('level', 1)
    
    ex_data = {
        "name": exercise['name'],
        "instruction": exercise['instructions'],
        "target": (exercise['target_angle_min'], exercise['target_angle_max']),
        "type": exercise['body_part'].lower() if exercise['body_part'] else "",
        "key": exercise_key
    }
    
    return render_template("exercise.html", ex_key=exercise_key, ex=ex_data, level=level)


@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    patient_id = session.get('patient_id') if 'patient_id' in session else 1
    level = request.args.get('level', 1)
    exercise_key = request.args.get("exercise")
    token = request.args.get("token")
    
    if request.method == 'POST':
        if token and token not in ACTIVE_TOKENS:
            flash('Automatic result was already recorded by the camera! No duplicate saved.')
            return redirect(url_for('patient', patient_id=patient_id))
            
        if token in ACTIVE_TOKENS:
            ACTIVE_TOKENS.pop(token)
            
        reps = int(request.form.get('reps', 0))
        
        # Save newly recorded session into SQLite
        try:
            record_exercise_session(patient_id, exercise_key, level, reps, score=0, completed=True)
            flash(f'Session saved: {reps} reps for Level {level}!')
        except Exception as e:
            print("Error recording session:", e)
            flash('Error recording progress. Please try again.')
            
        return redirect(url_for('patient', patient_id=patient_id))
    
    return render_template("feedback.html", exercise_key=exercise_key, patient_id=patient_id, level=level, token=token)

# Token storage for CV script results
ACTIVE_TOKENS = {}

@app.route("/api/record_session", methods=['POST'])
def api_record_session():
    data = request.json
    if not data:
        return {"status": "error", "message": "No data provided"}, 400
        
    token = data.get("token")
    if not token or token not in ACTIVE_TOKENS:
        return {"status": "error", "message": "Invalid or already used token"}, 401
        
    session_data = ACTIVE_TOKENS.pop(token)  # Pop immediately to prevent duplicates
    
    reps = data.get("repetitions", 0)
    score = data.get("score", 0)
    completed = data.get("completed", True)
    
    patient_id = session_data["patient_id"]
    exercise_key = session_data["exercise_key"]
    level = session_data["level"]
    
    try:
        record_exercise_session(patient_id, exercise_key, level, reps, score=score, completed=completed)
        return {"status": "success", "message": "Session recorded"}, 200
    except Exception as e:
        print("API Error recording session:", e)
        return {"status": "error", "message": "Database error"}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

