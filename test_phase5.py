import requests
import sqlite3

# Test A: Therapist Login
s_therapist = requests.Session()
r = s_therapist.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
print('Therapist Login status:', r.status_code)

# Test B: Therapist Dashboard
r = s_therapist.get('http://localhost:5000/therapist')
print('Therapist Dashboard loads:', r.status_code == 200)

# Test C: View patient room
r = s_therapist.get('http://localhost:5000/patient_room/1')
print('Exercises in patient room UI:', 'Wrist Flexion' in r.text)

# Test D: Assign Exercise
r = s_therapist.post('http://localhost:5000/assign_exercise/1', data={
    'exercise_id': '1', 
    'level': '1', 
    'target_repetitions': '10'
})
print('Assign exercise redirect status:', r.status_code)

conn = sqlite3.connect('acrh.db')
ea = conn.cursor().execute('SELECT * FROM exercise_assignments ORDER BY assigned_date DESC LIMIT 1').fetchone()
print('Latest assignment in DB:', ea)

# Test E: Patient Login
s_patient = requests.Session()
r = s_patient.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
r = s_patient.get('http://localhost:5000/patient/1')
print('Assigned exercise in patient dashboard?', 'Target: 10 reps' in r.text and 'Wrist Flexion' in r.text)

# Test F: Patient Isolation
r = s_patient.get('http://localhost:5000/patient/2')
print('Patient 1 trying to access Patient 2 dashboard redirect?', 'You can only view your own assignments' in r.text or r.url.endswith('/patient/1'))

# Test H: Duplicate Assignment
r = s_therapist.post('http://localhost:5000/assign_exercise/1', data={
    'exercise_id': '1', 
    'level': '1', 
    'target_repetitions': '10'
})
r = s_therapist.get('http://localhost:5000/patient_room/1')
print('Duplicate assignment prevented?', 'already assigned' in r.text)
