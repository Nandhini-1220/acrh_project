import requests
import subprocess
import time
import os

print('=== STARTING TESTS ===')

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    # TEST A - Patient login
    s_p1 = requests.Session()
    s_p1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
    r_dash1 = s_p1.get('http://localhost:5000/patient/1')
    print('TEST A - Patient 1 login:', 'Welcome, Patient 1' in r_dash1.text)
    
    # TEST B - Therapist login
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    r_tdash = s_t.get('http://localhost:5000/therapist')
    print('TEST B - Therapist login:', all(f'Patient {i}' in r_tdash.text for i in range(1,6)))
    
    # TEST C - Assignment
    s_t.post('http://localhost:5000/assign_exercise/1', data={'exercise_id': '5', 'level': '2', 'target_repetitions': '10'})
    r_dash1_post = s_p1.get('http://localhost:5000/patient/1')
    print('TEST C - Assignment appears on dashboard:', 'Shoulder Flexion' in r_dash1_post.text)
    
    # TEST D - Run Shoulder exercise
    r_run = s_p1.get('http://localhost:5000/run?exercise=shoulder_flexion&level=2', allow_redirects=False)
    loc = r_run.headers.get('Location')
    token = loc.split('token=')[1] if loc and 'token=' in loc else None
    print('TEST D - Launch generates token:', token is not None)
    
    # TEST G - Auto progress via API
    r_api = s_p1.post('http://localhost:5000/api/record_session', json={'token': token, 'repetitions': 5, 'completed': False})
    print('TEST G - API returns 200:', r_api.status_code == 200)
    
    r_dash1_after = s_p1.get('http://localhost:5000/patient/1')
    print('TEST G - Progress updates to 5/10 (50%):', '5 / 10 reps' in r_dash1_after.text and '50%' in r_dash1_after.text)
    
    # TEST I - Duplicate
    r_api_dup = s_p1.post('http://localhost:5000/api/record_session', json={'token': token, 'repetitions': 10, 'completed': True})
    print('TEST I - Duplicate token rejected:', r_api_dup.status_code == 401)
    
    # TEST J - Unassigned blocked
    r_unassigned = s_p1.get('http://localhost:5000/run?exercise=shoulder_abduction&level=99', allow_redirects=False)
    print('TEST J - Unassigned exercise blocked:', r_unassigned.status_code == 302 and 'token=' not in r_unassigned.headers.get('Location', ''))
    
    # TEST K - Isolation
    s_p2 = requests.Session()
    s_p2.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '2'})
    r_dash2 = s_p2.get('http://localhost:5000/patient/2')
    print('TEST K - Patient isolation:', '5 / 10 reps' not in r_dash2.text)
    
    # TEST L - Invalid Token
    r_invalid = s_p1.post('http://localhost:5000/api/record_session', json={'token': 'fake-token', 'repetitions': 10, 'completed': True})
    print('TEST L - Invalid token rejected:', r_invalid.status_code == 401)
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
