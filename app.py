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
        user_id = request.form.get('user_id', '').strip()
        passcode = request.form.get('passcode', '').strip()
        
        if not role or not user_id or not passcode:
            flash('Please fill in all fields')
            return render_template('login.html')
            
        try:
            user_id = int(user_id)
        except ValueError:
            flash('Invalid ID format')
            return render_template('login.html')
            
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ? AND role = ?', 
                            (user_id, role.upper())).fetchone()
                            
        if user and check_password_hash(user['password'], passcode):
            session.permanent = True
            session['user_id'] = user['id']
            session['role'] = role.lower()
            
            if role == 'Patient':
                # Also lookup the patient ID (from patients table) for legacy route compatibility
                patient = conn.execute('SELECT id FROM patients WHERE user_id = ?', (user['id'],)).fetchone()
                if patient:
                    session['patient_id'] = patient['id']
                    conn.close()
                    return redirect(url_for('patient', patient_id=patient['id']))
                else:
                    flash('No patient record found for this user.')
            elif role == 'Therapist':
                conn.close()
                return redirect(url_for('therapist'))
        else:
            flash('Invalid ID, Role, or Passcode')
            
        conn.close()
    return render_template('login.html')


@app.route('/therapist')
def therapist():
    if 'role' not in session or session['role'] != 'therapist':
        return redirect(url_for('patient', patient_id=1))
    with open('data.json', 'r') as f:
        patients = json.load(f)
    return render_template('therapist_dashboard.html', patients=patients)


@app.route('/patient/<int:patient_id>')
def patient(patient_id):
    if 'role' not in session or session['role'] != 'patient':
        return redirect(url_for('therapist'))
    
    with open('data.json', 'r') as f:
        patients_data = json.load(f)
    
    patient_data = next((p for p in patients_data if p['id'] == patient_id), None)
    if patient_data:
        progress = {
            'level1': patient_data.get('level1', 0),
            'level2': patient_data.get('level2', 0),
            'level3': patient_data.get('level3', 0),
            'level4': patient_data.get('level4', 0)
        }
    else:
        progress = {'level1': 0, 'level2': 0, 'level3': 0, 'level4': 0}
    
    injury = patient_data['injury_type'].lower() if patient_data else 'unknown'
    return render_template('patient_levels.html', patient_id=patient_id, injury=injury, progress=progress)

@app.route('/patient_room/<int:patient_id>')
def patient_room(patient_id):
    if 'role' not in session or session['role'] != 'therapist':
        return redirect(url_for('patient', patient_id=1))
    with open('data.json', 'r') as f:
        patients = json.load(f)
    patient = next(p for p in patients if p['id'] == patient_id)
    level_progress = [
        patient.get('level1', 0),
        patient.get('level2', 0),
        patient.get('level3', 0),
        patient.get('level4', 0)
    ]
    overall = sum(level_progress) / 40 * 100
    return render_template('patient_room.html', patient=patient, level_progress=level_progress, overall=overall)


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
        level_key = f'level{level}'
        
        # Load data.json
        with open('data.json', 'r') as f:
            patients_data = json.load(f)
        
        # Update reps for patient
        for p in patients_data:
            if p['id'] == patient_id:
                p[level_key] = reps
                # Update overall progress (average of levels / 40 * 100)
                levels_sum = sum(p.get(f'level{i}', 0) for i in range(1,5))
                p['progress'] = (levels_sum / 40) * 100
                break
        
        # Save back
        with open('data.json', 'w') as f:
            json.dump(patients_data, f, indent=2)
        
        flash(f'Progress saved: {reps} reps for {level_key}')
        return redirect(url_for('patient', patient_id=patient_id))
    
    return render_template("feedback.html", exercise_key=exercise_key, patient_id=patient_id, level=level)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

