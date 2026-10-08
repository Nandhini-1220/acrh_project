import sqlite3

conn = sqlite3.connect('acrh.db')
c = conn.cursor()

print("--- exercise_assignments ---")
for r in c.execute('SELECT * FROM exercise_assignments ORDER BY assigned_date DESC LIMIT 2').fetchall():
    print(r)
    
print("\n--- exercise_sessions ---")
for r in c.execute('SELECT * FROM exercise_sessions ORDER BY timestamp DESC LIMIT 2').fetchall():
    print(r)
    
print("\n--- Combined Progress Query ---")
query = '''
SELECT
    ea.patient_id,
    u.name,
    e.name AS exercise_name,
    ea.level,
    ea.target_repetitions,
    (SELECT MAX(repetitions) FROM exercise_sessions es WHERE es.patient_id = ea.patient_id AND es.exercise_id = ea.exercise_id AND es.level = ea.level AND es.completed=1) as max_reps
FROM exercise_assignments ea
JOIN patients p ON ea.patient_id = p.id
JOIN users u ON p.user_id = u.id
JOIN exercises e ON ea.exercise_id = e.id
'''
for r in c.execute(query).fetchall():
    print(r)
