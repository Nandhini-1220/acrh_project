import requests
import sqlite3

s = requests.Session()
s.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
r = s.get('http://localhost:5000/patient/1')
text = r.text

print('TEST A - Assigned exercise appears:', 'Assigned Exercises' in text and 'Wrist Flexion' in text)
print('TEST B & C - Target comparison (7 / 10 reps, 70%):', '7 / 10 reps' in text and '70%' in text)

# Insert a new assignment with no session
conn = sqlite3.connect('acrh.db')
conn.execute('''
    INSERT INTO exercise_assignments (patient_id, exercise_id, therapist_id, level, target_repetitions, assigned_date)
    VALUES (1, 2, 6, 2, 12, CURRENT_TIMESTAMP)
''')
conn.commit()

r = s.get('http://localhost:5000/patient/1')
text = r.text
print('TEST D - No session:', 'Not completed yet' in text)

print('TEST E - Multiple exercises: Did wrist extension steal wrist flexion progress?', '12 reps' in text and 'Not completed yet' in text)

s2 = requests.Session()
s2.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '2'})
r2 = s2.get('http://localhost:5000/patient/2')
print('TEST F - Patient isolation:', 'Wrist Flexion' not in r2.text)

s3 = requests.Session()
s3.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
r3 = s3.get('http://localhost:5000/therapist')
print('TEST G - Therapist dashboard displays progress:', 'Assigned: 2 | <strong>Completed:</strong> 0' in r3.text)

print('TEST H - Legacy fallback:', 'Overall Progress:' in r2.text) # patient 2 still has legacy progress 
