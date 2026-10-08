import requests
import re

print('=== STARTING TESTS ===')

s = requests.Session()
# Therapist login
s.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
r = s.get('http://localhost:5000/therapist')

print('TEST 1 & 2 - Therapist dashboard shows Patient N:', 'Patient 1' in r.text and 'Patient 5' in r.text and 'John Doe' not in r.text)

# Patient 1 login
s1 = requests.Session()
s1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
r1 = s1.get('http://localhost:5000/patient/1')
print('TEST 3 - Patient 1 sees only assignments, no hardcoded:', 'Welcome, Patient 1' in r1.text and 'Level 1: Shoulder Flexion' not in r1.text)

# Assignment
s.post('http://localhost:5000/assign_exercise/1', data={
    'exercise_id': '5', # Shoulder Flexion
    'level': '1',
    'target_repetitions': '10'
})
r1_again = s1.get('http://localhost:5000/patient/1')
print('TEST 4 - Assigned exercise appears:', 'Shoulder Flexion' in r1_again.text)

# Exercise launch & Feedback testing
# (Testing feedback mechanism independently since subprocess blocks in requests test)
r_fb = s1.post('http://localhost:5000/feedback', data={
    'exercise': 'shoulder_flexion',
    'level': '1',
    'repetitions': '5'
}, allow_redirects=True)
r1_after_fb = s1.get('http://localhost:5000/patient/1')
print('TEST 6 & 7 - Feedback recorded and progress updated:', '5 / 10 reps' in r1_after_fb.text and '50%' in r1_after_fb.text)

# Patient isolation
s2 = requests.Session()
s2.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '2'})
r2 = s2.get('http://localhost:5000/patient/2')
print('TEST 8 - Patient 2 cannot see Patient 1 progress:', 'Shoulder Flexion' not in r2.text)

print('=== TESTS COMPLETE ===')
