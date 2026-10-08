import requests

s1 = requests.Session()
s1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
r1 = s1.get('http://localhost:5000/patient/1')
print('TEST 1 - Assigned exercises appear:', 'Wrist Flexion' in r1.text)

r2 = s1.get('http://localhost:5000/exercise/wrist_flexion?level=1')
print('TEST 2 & 5 - Wrist Flexion config loads from DB:', '50-60 deg' in r2.text)

r3 = s1.get('http://localhost:5000/exercise/shoulder_flexion?level=1')
print('TEST 3 - Shoulder Flexion config loads from DB:', '160-180 deg' in r3.text)

r4 = s1.get('http://localhost:5000/exercise/elbow_extension?level=1')
print('TEST 4 - Elbow Extension config loads from DB:', '0-20 deg' in r4.text)

# We can't really test the subprocess Popen via requests, but we know it hits /run which redirects to /feedback
r_run = s1.get('http://localhost:5000/run?exercise=wrist_flexion&level=1', allow_redirects=False)
print('TEST - Run redirects to feedback:', r_run.status_code == 302 and '/feedback' in r_run.headers['Location'])

s_therapist = requests.Session()
s_therapist.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
r_assign = s_therapist.post('http://localhost:5000/assign_exercise/1', data={
    'exercise_id': '10', # Elbow extension
    'level': '1',
    'target_repetitions': '10'
}, allow_redirects=True)
print('TEST 6 - Therapist assignment works:', 'Elbow Extension' in r_assign.text)

r_fb = s1.post('http://localhost:5000/feedback?exercise=wrist_flexion&level=1', data={'reps': '9'}, allow_redirects=True)
print('TEST 7, 8 & 9 - Feedback, Sessions, Progress works:', '9 / 10 reps' in r_fb.text and '90%' in r_fb.text)

s2 = requests.Session()
s2.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '2'})
r_iso = s2.get('http://localhost:5000/patient/2')
print('TEST 10 - Patient isolation:', 'Wrist Flexion' not in r_iso.text)
