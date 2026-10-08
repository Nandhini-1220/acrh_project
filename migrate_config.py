import sqlite3

config_map = {
    "Wrist Flexion": (50, 60),
    "Wrist Extension": (50, 60),
    "Radial Deviation": (15, 20),
    "Ulnar Deviation": (15, 20),
    "Shoulder Flexion": (160, 180),
    "Shoulder Hyperextension": (30, 50),
    "Shoulder Abduction": (160, 180),
    "Shoulder Adduction": (30, 50),
    "Elbow Flexion": (130, 150),
    "Elbow Extension": (0, 20)
}

conn = sqlite3.connect('acrh.db')
c = conn.cursor()

for name, target in config_map.items():
    c.execute('UPDATE exercises SET target_angle_min=?, target_angle_max=? WHERE name=?', (target[0], target[1], name))

conn.commit()

print('Migrated configurations:')
for row in c.execute('SELECT name, target_angle_min, target_angle_max FROM exercises').fetchall():
    print(row)
conn.close()
