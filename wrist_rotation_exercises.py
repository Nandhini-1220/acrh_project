import cv2
import mediapipe as mp
import time
import math
import numpy as np

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# Exercise types and setup
EXERCISES = {
    "wrist_flexion": {
        "name": "Wrist Flexion",
        "description": "Bend your wrist forward (palm toward forearm)",
        "detailed_instruction": "Bend your wrist forward as far as comfortable - aim for 50-70° angle. You should feel a gentle stretch in the back of your wrist.",
        "target_angle_range": (50, 70),
        "hold_time": 5,
        "color": (0, 255, 0),  # Green
        "visual_cue": "Imagine pushing your palm down toward your forearm",
        "exercise_type": "bend"
    },
    "wrist_extension": {
        "name": "Wrist Extension", 
        "description": "Bend your wrist backward (back of hand toward forearm)",
        "detailed_instruction": "Bend your wrist backward as far as comfortable - aim for 50-70° angle. You should feel a gentle stretch in the front of your wrist.",
        "target_angle_range": (50, 70),
        "hold_time": 5,
        "color": (255, 0, 0),  # Red
        "visual_cue": "Imagine pulling your hand back toward your forearm",
        "exercise_type": "bend"
    },
    "radial_deviation": {
        "name": "Radial Deviation",
        "description": "Bend your wrist toward your thumb side",
        "detailed_instruction": "Bend your wrist toward your thumb side as far as comfortable - aim for 10-30° angle. Keep your forearm still, only move your wrist.",
        "target_angle_range": (10, 30),
        "hold_time": 5,
        "color": (0, 255, 255),  # Cyan
        "visual_cue": "Imagine pointing your thumb toward your forearm",
        "exercise_type": "bend"
    },
    "ulnar_deviation": {
        "name": "Ulnar Deviation",
        "description": "Bend your wrist toward your pinky side",
        "detailed_instruction": "Bend your wrist toward your pinky side as far as comfortable - aim for 10-30° angle. Keep your forearm still, only move your wrist.",
        "target_angle_range": (10, 30),
        "hold_time": 5,
        "color": (255, 0, 255),  # Magenta
        "visual_cue": "Imagine pointing your pinky toward your forearm",
        "exercise_type": "bend"
    },
    "wrist_rotation_clockwise": {
        "name": "Wrist Rotation (Clockwise)",
        "description": "Rotate your wrist in a clockwise circle",
        "detailed_instruction": "Slowly rotate your wrist in a clockwise circle. Keep your forearm still, only rotate your wrist. Make smooth, controlled movements.",
        "target_angle_range": (0, 360),
        "hold_time": 3,
        "color": (255, 165, 0),  # Orange
        "visual_cue": "Imagine turning a doorknob clockwise",
        "exercise_type": "rotation"
    },
    "wrist_rotation_counterclockwise": {
        "name": "Wrist Rotation (Counter-clockwise)",
        "description": "Rotate your wrist in a counter-clockwise circle",
        "detailed_instruction": "Slowly rotate your wrist in a counter-clockwise circle. Keep your forearm still, only rotate your wrist. Make smooth, controlled movements.",
        "target_angle_range": (0, 360),
        "hold_time": 3,
        "color": (128, 0, 128),  # Purple
        "visual_cue": "Imagine turning a doorknob counter-clockwise",
        "exercise_type": "rotation"
    },
    "wrist_circles": {
        "name": "Wrist Circles",
        "description": "Make large circular movements with your wrist",
        "detailed_instruction": "Make large, slow circular movements with your wrist in both directions. Keep your forearm stable, only move your wrist. Feel the full range of motion.",
        "target_angle_range": (0, 360),
        "hold_time": 2,
        "color": (0, 255, 128),  # Light Green
        "visual_cue": "Imagine drawing large circles in the air with your wrist",
        "exercise_type": "circles"
    }
}

import os
# Current exercise settings
exercise_key = os.environ.get("EXERCISE_KEY", "wrist_flexion")
print("Running Wrist Exercise:", exercise_key)

# Use exercise config directly
target_angle = EXERCISES.get(exercise_key, {}).get('target_angle_range', (60,))[0] if exercise_key in EXERCISES else 60

if exercise_key not in EXERCISES:
    print(f"Warning: Unknown exercise '{exercise_key}'. Available: {list(EXERCISES.keys())}")
    print("Defaulting to first exercise.")
    current_exercise = list(EXERCISES.keys())[0]
else:
    current_exercise = exercise_key
target_reps = 2
reps = 0
hold_time = EXERCISES[current_exercise]['hold_time']
target_angle_global = target_angle
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "setup"  # setup, exercise, rest, complete
rest_time = 3  # seconds between reps

# Session tracking
session_stats = {
    "total_exercises": 0,
    "total_reps": 0,
    "session_duration": 0,
    "exercises_completed": []
}

# Rotation tracking variables
rotation_start_angle = None
rotation_completed_degrees = 0
last_angle = 0
rotation_direction = 1  # 1 for clockwise, -1 for counter-clockwise

# Open camera
cap = cv2.VideoCapture(0)

def calculate_angle(a, b, c):
    """Calculate angle between three points (used for bend exercises)"""
    ang = math.degrees(
        math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0])
    )
    return abs(ang)

def calculate_rotation_angle(wrist, middle_finger, index_finger):
    """Calculate wrist rotation angle based on hand orientation"""
    # Calculate the angle between wrist and middle finger (hand direction)
    hand_angle = math.degrees(math.atan2(middle_finger[1] - wrist[1], middle_finger[0] - wrist[0]))
    
    # Calculate the angle between wrist and index finger (rotation indicator)
    finger_angle = math.degrees(math.atan2(index_finger[1] - wrist[1], index_finger[0] - wrist[0]))
    
    # Calculate rotation angle (difference between hand direction and finger direction)
    rotation_angle = hand_angle - finger_angle
    
    # Normalize to 0-360 degrees
    rotation_angle = (rotation_angle + 360) % 360
    
    return rotation_angle

def draw_progress_bar(image, progress, x, y, width, height, color):
    """Draw a progress bar"""
    # Background
    cv2.rectangle(image, (x, y), (x + width, y + height), (50, 50, 50), -1)
    # Progress
    progress_width = int(width * progress)
    cv2.rectangle(image, (x, y), (x + progress_width, y + height), color, -1)
    # Border
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

def draw_instruction_box(image, text, y_offset=0):
    """Draw instruction box with background"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2
    
    # Get text size
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Draw background rectangle
    padding = 10
    cv2.rectangle(image, 
                  (20, 30 + y_offset - text_height - padding), 
                  (20 + text_width + 2*padding, 30 + y_offset + padding), 
                  (0, 0, 0), -1)
    cv2.rectangle(image, 
                  (20, 30 + y_offset - text_height - padding), 
                  (20 + text_width + 2*padding, 30 + y_offset + padding), 
                  (255, 255, 255), 2)
    
    # Draw text
    cv2.putText(image, text, (20 + padding, 30 + y_offset), 
                font, font_scale, (255, 255, 255), thickness)

def update_session_stats():
    """Update session statistics"""
    global session_stats
    session_stats["total_exercises"] += 1
    session_stats["total_reps"] += reps
    session_stats["exercises_completed"].append({
        "exercise": current_exercise,
        "reps": reps,
        "timestamp": time.time()
    })
    session_stats["session_duration"] = time.time() - session_start_time

def draw_session_stats(image):
    """Draw session statistics on screen"""
    h, w, _ = image.shape
    
    # Session info box
    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (0, 0, 0), -1)
    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (255, 255, 255), 2)
    
    # Session stats
    cv2.putText(image, "Session Stats:", (w - 280, h - 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(image, f"Exercises: {session_stats['total_exercises']}", (w - 280, h - 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(image, f"Total Reps: {session_stats['total_reps']}", (w - 280, h - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Session duration
    duration_min = int(session_stats["session_duration"] // 60)
    duration_sec = int(session_stats["session_duration"] % 60)
    cv2.putText(image, f"Duration: {duration_min:02d}:{duration_sec:02d}", (w - 280, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Progress indicator
    total_possible_reps = len(EXERCISES) * target_reps
    progress = min(1.0, session_stats["total_reps"] / total_possible_reps)
    draw_progress_bar(image, progress, w - 280, h - 40, 250, 15, (0, 255, 0))
    cv2.putText(image, f"Session Progress: {int(progress * 100)}%", (w - 280, h - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

def get_bend_guidance(angle, exercise_phase, exercise_name, min_angle, max_angle):
    """Provide bend guidance for flexion/extension/deviation"""
    if exercise_phase != "exercise":
        return ""
    
    if angle < 30:
        if "flexion" in exercise_name:
            return "Bend DOWN (palm toward floor)"
        elif "extension" in exercise_name:
            return "Bend UP (back toward ceiling)"
        elif "radial" in exercise_name:
            return "Bend RIGHT (thumb side)"
        elif "ulnar" in exercise_name:
            return "Bend LEFT (pinky side)"
    elif angle < min_angle:
        return f"Bend MORE! {int(angle)}° → need {min_angle}-{max_angle}°"
    elif angle <= max_angle:
        return f"PERFECT! Hold at {int(angle)}°"
    else:
        return "Ease BACK a bit"

def get_rotation_guidance(rotation_angle, exercise_phase):
    """Provide rotation guidance based on exercise type"""
    if exercise_phase != "exercise":
        return ""
    
    exercise = EXERCISES[current_exercise]
    
    if current_exercise == "wrist_rotation_clockwise":
        return f"Rotate CLOCKWISE! {rotation_completed_degrees:.0f}° done"
    elif current_exercise == "wrist_rotation_counterclockwise":
        return f"Rotate CCW! {rotation_completed_degrees:.0f}° done"
    elif current_exercise == "wrist_circles":
        return f"CIRCLES! {rotation_completed_degrees:.0f}° done"
    
    return ""

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    
    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPosition your hand in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your wrist in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nStart with small circles, then gentle stretches."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "wrist_rotation_clockwise":
                return f"Ready! Rotate your wrist CLOCKWISE\n\n{exercise['visual_cue']}\n\nMake smooth, controlled circular movements."
            elif current_exercise == "wrist_rotation_counterclockwise":
                return f"Ready! Rotate your wrist COUNTER-CLOCKWISE\n\n{exercise['visual_cue']}\n\nMake smooth, controlled circular movements."
            elif current_exercise == "wrist_circles":
                return f"Ready! Make large CIRCLES with your wrist\n\n{exercise['visual_cue']}\n\nFeel the full range of motion."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Keep rotating! {remaining}s remaining\nRep {reps + 1}/{target_reps}\n\nYou should feel smooth movement - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps} complete!\n\nLet your wrist return to neutral position."
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your wrist gently during rest."
    elif exercise_phase == "complete":
        return f"🎉 Exercise Complete! 🎉\nYou did {reps} reps of {exercise['name']}\nPress 'n' for next exercise or 'r' to restart"
    else:
        return "Press 's' to start exercise"

warmup_time = 10  # seconds

# Global variables for timing
warmup_start = None
rest_start = None
show_help = False
show_demo = False
demo_start = None

while cap.isOpened():
    success, image = cap.read()
    if not success:
        break

    image = cv2.flip(image, 1)  # mirror view
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
    
    # Get current exercise info
    exercise = EXERCISES[current_exercise]
    current_time = time.time()
    
    # Handle exercise phases
    if exercise_phase == "warmup":
        if warmup_start is None:
            warmup_start = current_time
        elapsed_warmup = current_time - warmup_start
        if elapsed_warmup >= warmup_time:
            exercise_phase = "exercise"
            warmup_start = None
    elif exercise_phase == "rest":
        if rest_start is None:
            rest_start = current_time
        elapsed_rest = current_time - rest_start
        if elapsed_rest >= rest_time:
            exercise_phase = "exercise"
            rest_start = None

# Hand detection and exercise logic
    hand_detected = False
    if result.multi_hand_landmarks:
        hand_detected = True
        for hand_landmarks in result.multi_hand_landmarks:
            exercise_type = EXERCISES[current_exercise].get('exercise_type', 'rotation')
            
            # Common landmarks
            wrist = hand_landmarks.landmark[0]
            middle_finger = hand_landmarks.landmark[9]
            index_finger = hand_landmarks.landmark[8]
            index_mcp = hand_landmarks.landmark[5]  # For bend angle
            
            h, w, _ = image.shape
            wrist_pt = (int(w*wrist.x), int(h*wrist.y))
            middle_pt = (int(w*middle_finger.x), int(h*middle_finger.y))
            index_pt = (int(w*index_finger.x), int(h*index_finger.y))
            index_mcp_pt = (int(w*index_mcp.x), int(h*index_mcp.y))
            
            # Draw landmarks
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS, 
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))
            
            if exercise_type in ['rotation', 'circles']:
                # Rotation exercises
                rotation_angle = calculate_rotation_angle(wrist_pt, middle_pt, index_pt)
                cv2.putText(image, f"Rotation: {int(rotation_angle)}°", (wrist_pt[0] - 50, wrist_pt[1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                
                rotation_guidance = get_rotation_guidance(rotation_angle, exercise_phase)
                if rotation_guidance:
                    cv2.putText(image, rotation_guidance, (wrist_pt[0] - 150, wrist_pt[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Rotation arrows
                if exercise_phase == "exercise":
                    h, w, _ = image.shape
                    arrow_center = (w // 2, h // 2 + 100)
                    arrow_size = 80
                    
                    if current_exercise == "wrist_rotation_clockwise":
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1] - arrow_size//2), (arrow_center[0] + arrow_size//2, arrow_center[1] - arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1] - arrow_size//2), (arrow_center[0] + arrow_size//2, arrow_center[1] + arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1] + arrow_size//2), (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2), (arrow_center[0] - arrow_size//2, arrow_center[1] - arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "ROTATE CLOCKWISE", (arrow_center[0] - 80, arrow_center[1] + arrow_size//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                    elif current_exercise == "wrist_rotation_counterclockwise":
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1] - arrow_size//2), (arrow_center[0] - arrow_size//2, arrow_center[1] - arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1] - arrow_size//2), (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2), (arrow_center[0] + arrow_size//2, arrow_center[1] + arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1] + arrow_size//2), (arrow_center[0] + arrow_size//2, arrow_center[1] - arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "ROTATE CCW", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                    elif current_exercise == "wrist_circles":
                        cv2.circle(image, arrow_center, arrow_size//2, exercise["color"], 8)
                        cv2.putText(image, "MAKE CIRCLES", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                
                # Rotation logic
                if exercise_phase == "exercise":
                    if rotation_start_angle is None:
                        rotation_start_angle = rotation_angle
                        rotation_completed_degrees = 0
                        last_angle = rotation_angle
                    else:
                        angle_diff = rotation_angle - last_angle
                        if angle_diff > 180: angle_diff -= 360
                        elif angle_diff < -180: angle_diff += 360
                        rotation_completed_degrees += abs(angle_diff)
                        last_angle = rotation_angle
                    
                    if rotation_completed_degrees >= 360:
                        if start_hold is None:
                            start_hold = current_time
                            rotation_completed_degrees = 0
                        else:
                            elapsed = current_time - start_hold
                            if elapsed >= hold_time:
                                reps += 1
                                start_hold = None
                                rotation_completed_degrees = 0
                                if reps >= target_reps:
                                    exercise_phase = "complete"
                                    update_session_stats()
                                else:
                                    exercise_phase = "rest"
                                    rest_start = None
            
            elif exercise_type == 'bend':
                # Bend exercises (flexion/extension/deviation)
                angle = calculate_angle(index_mcp_pt, wrist_pt, index_pt)
                cv2.putText(image, f"Angle: {int(angle)}°", (wrist_pt[0] - 50, wrist_pt[1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                
                min_angle, max_angle = exercise["target_angle_range"]
                bend_guidance = get_bend_guidance(angle, exercise_phase, current_exercise, min_angle, max_angle)
                if bend_guidance:
                    cv2.putText(image, bend_guidance, (wrist_pt[0] - 150, wrist_pt[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Bend arrows
                if exercise_phase == "exercise":
                    h, w, _ = image.shape
                    arrow_center = (w // 2, h // 2 + 100)
                    arrow_size = 80
                    
                    if "flexion" in current_exercise:
                        cv2.arrowedLine(image, (arrow_center[0], arrow_center[1] - arrow_size//2), (arrow_center[0], arrow_center[1] + arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "BEND DOWN", (arrow_center[0] - 50, arrow_center[1] + arrow_size//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                    elif "extension" in current_exercise:
                        cv2.arrowedLine(image, (arrow_center[0], arrow_center[1] + arrow_size//2), (arrow_center[0], arrow_center[1] - arrow_size//2), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "BEND UP", (arrow_center[0] - 40, arrow_center[1] - arrow_size//2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                    elif "radial" in current_exercise:
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1]), (arrow_center[0] + arrow_size//2, arrow_center[1]), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "BEND RIGHT", (arrow_center[0] + arrow_size//2 + 10, arrow_center[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                    elif "ulnar" in current_exercise:
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1]), (arrow_center[0] - arrow_size//2, arrow_center[1]), exercise["color"], 8, tipLength=0.3)
                        cv2.putText(image, "BEND LEFT", (arrow_center[0] - arrow_size//2 - 70, arrow_center[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, exercise["color"], 2)
                
                # Target zone
                cv2.putText(image, f"Target: {min_angle}-{max_angle}°", (wrist_pt[0] - 50, wrist_pt[1] + 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                
                # Bend logic
                if exercise_phase == "exercise" and min_angle <= angle <= max_angle:
                    if start_hold is None:
                        start_hold = current_time
                    else:
                        elapsed = current_time - start_hold
                        if elapsed >= hold_time:
                            reps += 1
                            start_hold = None
                            if reps >= target_reps:
                                exercise_phase = "complete"
                                update_session_stats()
                            else:
                                exercise_phase = "rest"
                                rest_start = None
                else:
                    if start_hold is not None:
                        start_hold = None  # Reset hold if out of range

    # Draw UI elements
    h, w, _ = image.shape
    
    # Draw instruction box
    instruction_text = get_exercise_instruction()
    draw_instruction_box(image, instruction_text)
    
    # Draw exercise info
    cv2.putText(image, f"Exercise: {exercise['name']}", (20, h - 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(image, f"Reps: {reps}/{target_reps}", (20, h - 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Draw progress bars
    if exercise_phase == "exercise" and start_hold:
        hold_progress = min(1.0, (current_time - start_hold) / hold_time)
        draw_progress_bar(image, hold_progress, w - 250, 50, 200, 20, exercise["color"])
        cv2.putText(image, "Hold Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    elif exercise_phase == "rest" and rest_start:
        rest_progress = min(1.0, (current_time - rest_start) / rest_time)
        draw_progress_bar(image, rest_progress, w - 250, 50, 200, 20, (255, 255, 0))
        cv2.putText(image, "Rest Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Draw hand detection status
    if not hand_detected:
        cv2.putText(image, "No hand detected - Position your hand in front of camera", 
                   (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Draw session statistics
    draw_session_stats(image)
    
    # Draw controls
    cv2.putText(image, "Controls: 's'=start, 'n'=next exercise, 'r'=restart, ESC=exit", 
               (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow("Wrist Rotation Exercise Assistant", image)
    
    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s') and exercise_phase == "setup":
        exercise_phase = "exercise"
    elif key == ord('n') and exercise_phase == "complete":
        # Cycle to next exercise
        exercise_keys = list(EXERCISES.keys())
        current_idx = exercise_keys.index(current_exercise)
        current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        rotation_start_angle = None
        rotation_completed_degrees = 0
    elif key == ord('r'):
        # Restart current exercise
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        warmup_start = None
        rest_start = None
        rotation_start_angle = None
        rotation_completed_degrees = 0

cap.release()
cv2.destroyAllWindows()

