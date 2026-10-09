import requests
import subprocess
import time
import os

print('=== STARTING TESTS ===')

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    s_t.post('http://localhost:5000/assign_exercise/1', data={'exercise_id': '1', 'level': '1', 'target_repetitions': '10'})
    print('Test 1: Therapist assigned Wrist Flexion (ID=1) to Patient 1 with Level=1, Reps=10')

    s_p1 = requests.Session()
    s_p1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
    
    r_run = s_p1.get('http://localhost:5000/run?exercise=wrist_flexion&level=1', allow_redirects=False)
    loc = r_run.headers.get('Location')
    token = loc.split('token=')[1] if loc and 'token=' in loc else None
    
    print('Test 2: Patient 1 started exercise, token generated:', token is not None)
    
    r_api = s_p1.post('http://localhost:5000/api/record_session', json={
        'token': token,
        'repetitions': 10,
        'completed': True
    })
    print('Test 6 & 7: CV API recorded 10 reps successfully:', r_api.status_code == 200)
    
    r_dash1 = s_p1.get('http://localhost:5000/patient/1')
    print('Test 8: Patient dashboard updates to 10/10:', '10 / 10 reps' in r_dash1.text)
    
    r_dash_t = s_t.get('http://localhost:5000/therapist')
    print('Test 9: Therapist dashboard updates:', '100% Complete' in r_dash_t.text)
    
    r_api_dup = s_p1.post('http://localhost:5000/api/record_session', json={'token': token, 'repetitions': 15, 'completed': True})
    print('Test 10: Duplicate token rejected:', r_api_dup.status_code == 401)
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
