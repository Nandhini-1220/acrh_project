import requests
import sqlite3
import time

s = requests.Session()
r = s.post('http://localhost:5000/', data={'role': 'Patient', 'user_id': '1', 'passcode': 'dev123'})
print('Patient Login status:', r.status_code)

r = s.get('http://localhost:5000/start_exercise/1')
print('Start exercise URL:', r.url)

print('\n--- Submitting Feedback ---')
r = s.post('http://localhost:5000/feedback?exercise=wrist_flexion&level=1', data={'reps': '7'})
print('Feedback submitted, redirect URL:', r.url)

r = s.get('http://localhost:5000/patient/1')
print('Patient progress contains 7/10 reps?', '7/10 reps' in r.text or '7 / 10' in r.text)

s2 = requests.Session()
s2.post('http://localhost:5000/', data={'role': 'Therapist', 'user_id': '6', 'passcode': 'dev123'})
r2 = s2.get('http://localhost:5000/therapist')
print('Therapist dashboard loaded:', r2.status_code == 200)

conn = sqlite3.connect('acrh.db')
c = conn.cursor()
sessions = c.execute('SELECT * FROM exercise_sessions ORDER BY timestamp DESC LIMIT 1').fetchall()
print('\n--- Database Check ---')
print('Latest exercise session:', sessions)
