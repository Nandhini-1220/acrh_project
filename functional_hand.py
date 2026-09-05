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
    "grasp_and_release": {
        "name": "Grasp and Release",
        "description": "Open and close your fist repeatedly",
        "detailed_instruction": "Make a tight fist with all fingers, then fully open your hand. Repeat this grasping and releasing motion. Aim for full range of motion in your fingers and palm.",
        "target_distance": (50, 150),  # Distance between thumb and index finger
        "hold_time": 2,
        "color": (0, 255, 0),  # Green
        "visual_cue": "Imagine grasping an object and then releasing it",
        "exercise_type": "grasp_release"
    },
    "pinch_movement": {
        "name": "Pinch Movement",
        "description": "Touch your thumb to your index finger repeatedly",
        "detailed_instruction": "Touch your thumb to your index finger, then separate them. Repeat this pinching motion. Keep your other fingers relaxed. Aim for precise contact between thumb and index finger.",
        "target_distance": (10, 30),  # Distance between thumb and index finger
        "hold_time": 2,
        "color": (255, 0, 0),  # Blue
        "visual_cue": "Imagine picking up a small object with your thumb and index finger",
        "exercise_type": "pinch"
    },
    "finger_coordination": {
        "name": "Finger Coordination",
        "description": "Tap each finger on your thumb sequentially",
        "detailed_instruction": "Tap each finger (index, middle, ring, pinky) on your thumb one by one. Keep a steady rhythm. This improves finger dexterity and coordination.",
        "target_sequence": ["index", "middle", "ring", "pinky"],
        "hold_time": 1,
        "color": (0, 255, 255),  # Yellow
        "visual_cue": "Imagine playing notes on a small keyboard",
        "exercise_type": "coordination"
    }
}

# Current exercise settings
current_exercise = "grasp_and_release"
target_reps = 3
reps = 0
hold_time = EXERCISES[current_exercise]["hold_time"]
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "setup"  # setup, warmup, exercise, rest, complete
warmup_time = 10  # seconds
rest_time = 3  # seconds between reps

# Session tracking
session_stats = {
    "total_exercises": 0,
    "total_reps": 0,
    "session_duration": 0,
    "exercises_completed": []
}

# Finger tracking variables
last_thumb_index_distance = 0
tap_detected = False
tapped_fingers = []
current_target_finger = 0
last_tap_time = 0

# Open camera
cap = cv2.VideoCapture(0)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def get_finger_tip_positions(hand_landmarks):
    """Get positions of finger tips and thumb"""
    finger_tips = {
        "thumb": hand_landmarks.landmark[4],
        "index": hand_landmarks.landmark[8],
        "middle": hand_landmarks.landmark[12],
        "ring": hand_landmarks.landmark[16],
        "pinky": hand_landmarks.landmark[20]
    }
    return finger_tips

def detect_grasp_release(thumb_index_distance, target_range):
    """Detect if hand is in grasp or release position"""
    min_dist, max_dist = target_range
    if thumb_index_distance <= min_dist:
        return "grasp"
    elif thumb_index_distance >= max_dist:
        return "release"
    else:
        return "transition"

def detect_pinch(thumb_index_distance, target_range):
    """Detect pinch movement"""
    min_dist, max_dist = target_range
    if thumb_index_distance <= max_dist:
        return "pinch"
    else:
        return "release"

def detect_finger_tap(thumb_pos, finger_pos, tap_threshold=25):
    """Detect if a finger is tapping the thumb"""
    distance = calculate_distance((thumb_pos.x, thumb_pos.y), (finger_pos.x, finger_pos.y))
    return distance <= tap_threshold

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

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    
    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPosition your hand in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your fingers in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nStart with opening and closing your hand slowly."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "grasp_and_release":
                return f"Ready! Make a tight FIST, then fully OPEN your hand\n\n{exercise['visual_cue']}\n\nRepeat the grasp and release motion."
            elif current_exercise == "pinch_movement":
                return f"Ready! Touch thumb to INDEX finger, then separate\n\n{exercise['visual_cue']}\n\nRepeat the pinch motion."
            elif current_exercise == "finger_coordination":
                target_sequence = exercise["target_sequence"]
                current_finger = target_sequence[current_target_finger]
                return f"Ready! Tap {current_finger.upper()} finger on thumb\n\n{exercise['visual_cue']}\n\nTap each finger in sequence."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Hold position! {remaining}s remaining\nRep {reps + 1}/{target_reps}\n\nKeep steady - this is building strength!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps} complete!\n\nLet your hand return to neutral position."
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your hand gently during rest."
    elif exercise_phase == "complete":
        return f"🎉 Exercise Complete! 🎉\nYou did {reps} reps of {exercise['name']}\nPress 'n' for next exercise or 'r' to restart"
    else:
        return "Press 's' to start exercise"

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
            # Get finger positions
            finger_tips = get_finger_tip_positions(hand_landmarks)
            
            # Convert to pixel coordinates
            h, w, _ = image.shape
            thumb_pos = (int(w * finger_tips["thumb"].x), int(h * finger_tips["thumb"].y))
            index_pos = (int(w * finger_tips["index"].x), int(h * finger_tips["index"].y))
            middle_pos = (int(w * finger_tips["middle"].x), int(h * finger_tips["middle"].y))
            ring_pos = (int(w * finger_tips["ring"].x), int(h * finger_tips["ring"].y))
            pinky_pos = (int(w * finger_tips["pinky"].x), int(h * finger_tips["pinky"].y))
            
            # Calculate thumb-index distance
            thumb_index_distance = calculate_distance(thumb_pos, index_pos)
            
            # Draw hand landmarks with exercise-specific color
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS, 
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))
            
            # Draw distance indicator
            cv2.putText(image, f"Thumb-Index: {int(thumb_index_distance)}px", (thumb_pos[0] - 50, thumb_pos[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
            
            # Exercise-specific logic
            if exercise_phase == "exercise":
                if current_exercise == "grasp_and_release":
                    state = detect_grasp_release(thumb_index_distance, exercise["target_distance"])
                    if state == "grasp" and last_thumb_index_distance >= exercise["target_distance"][1]:
                        # Transition from release to grasp
                        if start_hold is None:
                            start_hold = current_time
                    elif state == "release" and last_thumb_index_distance <= exercise["target_distance"][0]:
                        # Transition from grasp to release
                        if start_hold is not None:
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
                    
                    last_thumb_index_distance = thumb_index_distance
                    
                elif current_exercise == "pinch_movement":
                    state = detect_pinch(thumb_index_distance, exercise["target_distance"])
                    if state == "pinch" and last_thumb_index_distance >= exercise["target_distance"][1]:
                        # Transition to pinch
                        if start_hold is None:
                            start_hold = current_time
                    elif state == "release" and last_thumb_index_distance <= exercise["target_distance"][0]:
                        # Transition from pinch to release
                        if start_hold is not None:
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
                    
                    last_thumb_index_distance = thumb_index_distance
                    
                elif current_exercise == "finger_coordination":
                    target_sequence = exercise["target_sequence"]
                    current_finger = target_sequence[current_target_finger]
                    
                    # Check for tap on current target finger
                    if current_finger == "index":
                        tap_detected = detect_finger_tap(finger_tips["thumb"], finger_tips["index"])
                    elif current_finger == "middle":
                        tap_detected = detect_finger_tap(finger_tips["thumb"], finger_tips["middle"])
                    elif current_finger == "ring":
                        tap_detected = detect_finger_tap(finger_tips["thumb"], finger_tips["ring"])
                    elif current_finger == "pinky":
                        tap_detected = detect_finger_tap(finger_tips["thumb"], finger_tips["pinky"])
                    
                    if tap_detected and not tap_detected_last:
                        if start_hold is None:
                            start_hold = current_time
                        else:
                            elapsed = current_time - start_hold
                            if elapsed >= hold_time:
                                reps += 1
                                tapped_fingers.append(current_finger)
                                current_target_finger = (current_target_finger + 1) % len(target_sequence)
                                start_hold = None
                                if reps >= target_reps:
                                    exercise_phase = "complete"
                                    update_session_stats()
                                else:
                                    exercise_phase = "rest"
                                    rest_start = None
                    
                    tap_detected_last = tap_detected

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
    if exercise_phase == "warmup" and warmup_start:
        warmup_progress = min(1.0, (current_time - warmup_start) / warmup_time)
        draw_progress_bar(image, warmup_progress, w - 250, 50, 200, 20, (0, 255, 255))
        cv2.putText(image, "Warm-up Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    elif exercise_phase == "exercise" and start_hold:
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

    cv2.imshow("Functional Hand Exercise Assistant", image)
    
    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s') and exercise_phase == "setup":
        exercise_phase = "warmup"
        warmup_start = None
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
        tapped_fingers = []
        current_target_finger = 0
    elif key == ord('r'):
        # Restart current exercise
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        warmup_start = None
        rest_start = None
        tapped_fingers = []
        current_target_finger = 0

cap.release()
cv2.destroyAllWindows()
