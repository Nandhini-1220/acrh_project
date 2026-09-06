import requests

# Test Patient Login
s = requests.Session()
r = s.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '1'})
print('Patient 1 Login status:', r.status_code)
print('Patient 1 redirect URL:', r.url)

# Test Invalid Patient Login
s = requests.Session()
r = s.post('http://localhost:5000/', data={'role': 'Patient', 'patient_id': '99'})
print('Invalid Patient Login text contains Invalid Patient ID?', 'Invalid Patient ID' in r.text)

# Test Therapist Login
s = requests.Session()
r = s.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'therapist@acrh.com'})
print('Therapist Login status:', r.status_code)
print('Therapist redirect URL:', r.url)

# Test Invalid Therapist Login
s = requests.Session()
r = s.post('http://localhost:5000/', data={'role': 'Therapist', 'therapist_email': 'wrong@acrh.com'})
print('Invalid Therapist Login text contains Invalid Therapist Email?', 'Invalid Therapist Email' in r.text)

