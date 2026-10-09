from wrist_rotation_exercises import calculate_angle
import math

# Simulate points that would give roughly 301 degrees raw difference
# angle1 = math.atan2(c[1]-b[1], c[0]-b[0])
# angle2 = math.atan2(a[1]-b[1], a[0]-b[0])

# We can just test the function directly
# Let b be origin (0,0)
# Let a be at angle 0 (1, 0)
# Let c be at angle 301 degrees -> cos(301), sin(301)
a = (1, 0)
b = (0, 0)
c = (math.cos(math.radians(301)), math.sin(math.radians(301)))

angle = calculate_angle(a, b, c)
print(f'Calculated angle for 301 degrees raw: {angle}')
print(f'Test 3 Pass: {abs(angle - 59) < 0.1}')
