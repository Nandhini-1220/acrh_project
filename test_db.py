import sqlite3

conn = sqlite3.connect('acrh.db')
conn.row_factory = sqlite3.Row

users = [dict(r) for r in conn.execute('SELECT * FROM users').fetchall()]
patients = [dict(r) for r in conn.execute('SELECT * FROM patients').fetchall()]
exercises = [dict(r) for r in conn.execute('SELECT * FROM exercises').fetchall()]
assignments = [dict(r) for r in conn.execute('SELECT * FROM exercise_assignments').fetchall()]
sessions = [dict(r) for r in conn.execute('SELECT * FROM exercise_sessions').fetchall()]

print('Users:', len(users))
print('Patients:', len(patients))
print('Exercises:', len(exercises))
print('Assignments:', len(assignments))
print('Sessions:', len(sessions))

invalid_patients = [p for p in patients if p['user_id'] not in [u['id'] for u in users]]
print('Invalid patients:', invalid_patients)

invalid_assignments = [a for a in assignments if a['patient_id'] not in [p['id'] for p in patients] or a['exercise_id'] not in [e['id'] for e in exercises]]
print('Invalid assignments:', invalid_assignments)

invalid_sessions = [s for s in sessions if s['patient_id'] not in [p['id'] for p in patients] or s['exercise_id'] not in [e['id'] for e in exercises]]
print('Invalid sessions:', invalid_sessions)

for e in exercises:
    print(f'Exercise: {e["name"]} -> {e["script_name"]}')

