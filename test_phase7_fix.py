import requests

print('=== STARTING TESTS ===')
s1 = requests.Session()
s1.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
s1.post('http://localhost:5000/feedback?exercise=shoulder_flexion&level=1', data={'reps': '5'}, allow_redirects=True)
r1_after_fb = s1.get('http://localhost:5000/patient/1')
print('TEST 6 & 7 - Feedback recorded and progress updated:', '5 / 10 reps' in r1_after_fb.text and '50%' in r1_after_fb.text)
