import requests
import subprocess
import time
import os

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    
    r_dash = s_t.get('http://localhost:5000/therapist')
    print('Therapist dashboard loaded:', r_dash.status_code == 200)
    
    r_room1 = s_t.get('http://localhost:5000/patient_room/1')
    print('Patient 1 room loaded:', r_room1.status_code == 200)
    print('Old level-wise text removed:', 'Level-wise Progress' not in r_room1.text)
    print('Old levels 1-4 grids removed:', 'Level 1:' not in r_room1.text)
    print('Overall Progress still exists:', 'Overall Progress' in r_room1.text)
    
    r_room2 = s_t.get('http://localhost:5000/patient_room/2')
    print('Patient 2 room loaded:', r_room2.status_code == 200)
    
    # Check if assignment works
    r_assign = s_t.post('http://localhost:5000/assign_exercise/1', data={'exercise_id': '1', 'level': '1', 'target_repetitions': '10'}, allow_redirects=False)
    print('Assignment successful (redirect):', r_assign.status_code == 302)
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
