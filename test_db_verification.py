import sqlite3

query = '''
SELECT
    ea.id,
    ea.patient_id,
    u.name AS patient_name,
    ea.exercise_id,
    e.name AS exercise_name,
    ea.therapist_id,
    ea.level,
    ea.target_repetitions,
    ea.assigned_date
FROM exercise_assignments ea
JOIN patients p ON ea.patient_id = p.id
JOIN users u ON p.user_id = u.id
JOIN exercises e ON ea.exercise_id = e.id
ORDER BY ea.assigned_date DESC;
'''

conn = sqlite3.connect('acrh.db')
for row in conn.execute(query).fetchall():
    print(row)
