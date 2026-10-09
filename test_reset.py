import requests
import subprocess
import time
import os

flask_proc = subprocess.Popen(['python', 'app.py'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)

try:
    # 1. Therapist login
    s_t = requests.Session()
    s_t.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
    r_tdash = s_t.get('http://localhost:5000/therapist')
    
    # 2. Check 0% Complete for all
    print('Therapist dashboard zeros:', r_tdash.text.count('0% Complete'))
    print('Therapist dashboard Assigned: 0:', r_tdash.text.count('Assigned:</strong> 0'))
    print('Therapist dashboard No activity yet:', r_tdash.text.count('No activity yet'))
    
    # 3. Patient 1 dashboard
    s_p1 = requests.Session()
    s_p1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
    r_pdash = s_p1.get('http://localhost:5000/patient/1')
    
    # 4. Check Patient dashboard
    print('Patient dashboard message:', 'No exercises have been assigned yet.' in r_pdash.text)
    print('Patient dashboard no old stuff:', 'wrist_flexion' not in r_pdash.text.lower())
    
finally:
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(flask_proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        flask_proc.kill()
