import requests
import subprocess
import time
import os

print('=== STARTING TESTS ===')

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    # 1. Therapist login & assign
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    s_t.post('http://localhost:5000/assign_exercise/1', data={'exercise_id': '1', 'level': '1', 'target_repetitions': '10'})

    # 2. Patient 1 start exercise
    s_p1 = requests.Session()
    s_p1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
    r_run = s_p1.get('http://localhost:5000/run?exercise=wrist_flexion&level=1', allow_redirects=False)
    
    loc = r_run.headers.get('Location')
    token = loc.split('token=')[1].split('&')[0] if loc and 'token=' in loc else None
    
    # 3. Visit feedback immediately
    r_feed1 = s_p1.get(f'http://localhost:5000/feedback?exercise=wrist_flexion&level=1&token={token}')
    print('Test 4: Form removed:', '<form' not in r_feed1.text.lower())
    print('Test 5: No Save Progress button:', 'Save Progress' not in r_feed1.text)
    print('Waiting text visible:', 'Waiting for camera session' in r_feed1.text)
    
    # 4. API records result
    r_api = s_p1.post('http://localhost:5000/api/record_session', json={
        'token': token,
        'repetitions': 10,
        'completed': True
    })
    print('Test 9: API record success:', r_api.status_code == 200)
    
    # 5. Visit feedback again
    r_feed2 = s_p1.get(f'http://localhost:5000/feedback?exercise=wrist_flexion&level=1&token={token}')
    print('Recorded reps text visible:', 'Repetitions completed: 10' in r_feed2.text)
    
    # 6. Verify duplicates rejected
    r_api_dup = s_p1.post('http://localhost:5000/api/record_session', json={'token': token, 'repetitions': 15, 'completed': True})
    print('Test 8: Duplicate token rejected:', r_api_dup.status_code == 401)
    
    # 7. Check if manually POSTing to feedback fails/redirects harmlessly
    # (Since we removed methods=['GET', 'POST'], a POST to /feedback should be 405 Method Not Allowed)
    r_feed_post = s_p1.post(f'http://localhost:5000/feedback?exercise=wrist_flexion&level=1&token={token}', data={'reps': 50})
    print('Test 2: Manual POST to /feedback rejected (405):', r_feed_post.status_code == 405)
    
    # 8. Check dashboards
    r_dash1 = s_p1.get('http://localhost:5000/patient/1')
    print('Test 6: Patient dash updates:', '10 / 10' in r_dash1.text)
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
