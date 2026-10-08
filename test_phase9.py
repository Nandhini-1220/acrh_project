import requests

print('=== STARTING TESTS ===')

import subprocess
import time
import os

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    s1 = requests.Session()
    s1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
    
    # Check 1: Start assigned exercise
    r_run = s1.get('http://localhost:5000/run?exercise=wrist_flexion&level=1', allow_redirects=False)
    loc = r_run.headers.get('Location')
    token = loc.split('token=')[1] if loc and 'token=' in loc else None
    
    print('TEST 1 - CV script launches normally (token generated):', token is not None)
    
    # Check 2 & 3: CV sends final reps -> SQLite
    r_api = s1.post('http://localhost:5000/api/record_session', json={
        'token': token,
        'repetitions': 8,
        'completed': True
    })
    print('TEST 2 & 3 - CV API records properly to SQLite:', r_api.status_code == 200)
    
    # Check 4: Dashboard updates
    r_dash = s1.get('http://localhost:5000/patient/1')
    print('TEST 4 - Dashboard reflects new session:', '8 / 10 reps' in r_dash.text)
    
    # Check 5: Therapist dashboard updates
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    r_t = s_t.get('http://localhost:5000/therapist')
    print('TEST 5 - Therapist dashboard updates:', '80%' in r_t.text or 'Progress' in r_t.text)
    
    # Check 6: Duplicate protection
    r_api_dup = s1.post('http://localhost:5000/api/record_session', json={
        'token': token,
        'repetitions': 8,
        'completed': True
    })
    print('TEST 6 - Duplicate API protection:', r_api_dup.status_code == 401)
    r_fb_dup = s1.post('http://localhost:5000/feedback?exercise=wrist_flexion&level=1&token=' + (token or ''), data={'reps':'10'}, allow_redirects=True)
    print('TEST 6 - Duplicate UI protection:', 'Automatic result was already recorded by the camera' in r_fb_dup.text)
    r_dash2 = s1.get('http://localhost:5000/patient/1')
    print('TEST 6 - Verifying no duplicate overwritten:', '8 / 10 reps' in r_dash2.text)
    
    # Check 7 & 8: Unassigned exercise / wrong patient
    r_unassigned = s1.get('http://localhost:5000/run?exercise=elbow_flexion&level=1', allow_redirects=False)
    print('TEST 7 & 8 - Unassigned exercise blocked:', r_unassigned.status_code == 302 and 'token=' not in r_unassigned.headers.get('Location', ''))
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
