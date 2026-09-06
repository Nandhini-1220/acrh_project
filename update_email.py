import sqlite3
conn = sqlite3.connect('acrh.db')
cur = conn.cursor()
cur.execute('UPDATE users SET email = ? WHERE role = ? AND (email IS NULL OR email = "")', ('therapist@acrh.com', 'THERAPIST'))
conn.commit()
print('Rows updated:', cur.rowcount)
