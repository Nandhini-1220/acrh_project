import cv2
import mediapipe as mp
import time
import math
import numpy as np
import os

exercise_key = os.environ.get("EXERCISE_KEY", "forearm_pronation")
print("Running Forearm Exercise:", exercise_key)
# Set current_exercise = exercise_key later in code
import os
import subprocess

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Forearm exercise types and setup
EXERCISES = {
    "forearm_pronation": {
        "name": "Forearm Pronation",
        "description": "Rotate forearm so palm faces downward",
        "detailed_instruction": "Start with palm facing up, then rotate your forearm so the palm faces downward. Aim for 70-90° of rotation. Hold when palm is fully rotated down.",
        "target_angle_range": (70, 90),  # degrees from vertical
        "hold_time": 5,
        "color": (0, 255, 255),  # Yellow
        "visual_cue": "Imagine turning a doorknob clockwise",
        "exercise_type": "pronation"
    },
    "forearm_supination": {
        "name": "Forearm Supination",
        "description": "Rotate forearm so palm faces upward",
        "detailed_instruction": "Start with palm facing down, then rotate your forearm so the palm faces upward. Aim for 70-90° of rotation. Hold when palm is fully rotated up.",
        "target_angle_range": (70, 90),  # degrees from vertical
        "hold_time": 5,
        "color": (255, 0, 255),  # Magenta
        "visual_cue": "Imagine turning a doorknob counter-clockwise",
        "exercise_type": "supination"
    },
    "elbow_flexion": {
        "name": "Elbow Flexion",
        "description": "Bend your elbow to bring hand toward shoulder",
        "detailed_instruction": "Start with arm straight, then bend your elbow to bring your hand toward your shoulder. Aim for 130-150° angle at the elbow.",
        "target_angle_range": (130, 150),
        "hold_time": 5,
        "color": (255, 165, 0),  # Orange
        "visual_cue": "Imagine curling your arm like doing a bicep curl",
        "exercise_type": "flexion"
    },
    "elbow_extension": {
        "name": "Elbow Extension",
        "description": "Straighten your arm from bent position",
        "detailed_instruction": "Start with elbow bent, then straighten your arm fully. Aim for angle above 160° at elbow.",
        "target_angle_range": (160, 180),
        "hold_time": 5,
        "color": (0, 255, 128),  # Light Green
        "visual_cue": "Imagine pushing something away from you",
        "exercise_type": "extension"
    }
}

# Exercise order
EXERCISE_ORDER = [
    "forearm_pronation",
    "forearm_supination",
    "elbow_flexion",
    "elbow_extension"
]

# Per-exercise target reps
REPS_PER_EXERCISE = {
    "forearm_pronation": 2,
    "forearm_supination": 2,
    "elbow_flexion": 2,
    "elbow_extension": 2
}

# Current exercise settings
current_exercise = EXERCISE_ORDER[0]
default_target_reps = 2
reps = 0
hold_time = EXERCISES[current_exercise]["hold_time"]
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "exercise"  # exercise, rest, complete
rest_time = 3  # seconds between reps
complete_start = None

# Session tracking
session_stats = {
    "total_exercises": 0,
    "total_reps": 0,
    "session_duration": 0,
    "exercises_completed": []
}

# Game state
score = 0
streak = 0
level = 1
last_rep_time = None
combo_window_sec = 6
exercise_points_earned = 0

# Open camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("Forearm Physiotherapy Assistant", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Forearm Physiotherapy Assistant", 1600, 900)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    ang = math.degrees(
        math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0])
    )
    return abs(ang)

def get_finger_tip_positions(hand_landmarks, image_shape):
    """Get positions of all finger tips"""
    h, w = image_shape[:2]
    tips = {
        "thumb": (int(w * hand_landmarks.landmark[4].x), int(h * hand_landmarks.landmark[4].y)),
        "index": (int(w * hand_landmarks.landmark[8].x), int(h * hand_landmarks.landmark[8].y)),
        "middle": (int(w * hand_landmarks.landmark[12].x), int(h * hand_landmarks.landmark[12].y)),
        "ring": (int(w * hand_landmarks.landmark[16].x), int(h * hand_landmarks.landmark[16].y)),
        "pinky": (int(w * hand_landmarks.landmark[20].x), int(h * hand_landmarks.landmark[20].y))
    }
    return tips

def calculate_palm_orientation(hand_landmarks, image_shape):
    """Calculate palm orientation angle based on thumb and pinky positions"""
    h, w = image_shape[:2]

    # Get wrist and finger positions
    wrist = (int(w * hand_landmarks.landmark[0].x), int(h * hand_landmarks.landmark[0].y))
    thumb_cmc = (int(w * hand_landmarks.landmark[1].x), int(h * hand_landmarks.landmark[1].y))
    pinky_cmc = (int(w * hand_landmarks.landmark[17].x), int(h * hand_landmarks.landmark[17].y))

    # Calculate angle between wrist-thumb_cmc and wrist-pinky_cmc
    angle = calculate_angle(pinky_cmc, wrist, thumb_cmc)

    # Normalize to 0-180 degrees (palm orientation)
    if angle > 180:
        angle = 360 - angle

    return angle

def calculate_elbow_angle(pose_landmarks, image_shape):
    """Calculate elbow angle using pose landmarks"""
    h, w = image_shape[:2]

    # Get shoulder, elbow, and wrist positions
    shoulder = (int(w * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].x),
                int(h * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].y))
    elbow = (int(w * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW].x),
             int(h * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_ELBOW].y))
    wrist = (int(w * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].x),
             int(h * pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].y))

    # Calculate angle at elbow
    angle = calculate_angle(shoulder, elbow, wrist)
    return angle

def draw_progress_bar(image, progress, x, y, width, height, color):
    """Draw a progress bar"""
    cv2.rectangle(image, (x, y), (x + width, y + height), (50, 50, 50), -1)
    progress_width = int(width * progress)
    cv2.rectangle(image, (x, y), (x + progress_width, y + height), color, -1)
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

def draw_instruction_box(image, text, y_offset=0):
    """Draw instruction box with background"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.2  # Increased font size for better readability
    thickness = 3     # Increased thickness for better visibility

    # Split text into lines for better formatting
    lines = text.split('\n')

    # Calculate text size for each line
    text_sizes = []
    for line in lines:
        (text_width, text_height), _ = cv2.getTextSize(line, font, font_scale, thickness)
        text_sizes.append((text_width, text_height))

    # Use the widest line for box width
    max_width = max(size[0] for size in text_sizes) if text_sizes else 0
    line_height = text_sizes[0][1] if text_sizes else 30

    padding = 20
    box_width = max_width + 2 * padding
    box_height = len(lines) * (line_height + 10) + 2 * padding

    # Position box on the left side for better visibility
    x1 = 30
    y1 = 50 + y_offset
    x2 = x1 + box_width
    y2 = y1 + box_height

    # Draw semi-transparent black background
    overlay = image.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

    # Draw white border
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 2)

    # Draw text lines
    y_text = y1 + padding + line_height
    for line in lines:
        cv2.putText(image, line, (x1 + padding, y_text),
                   font, font_scale, (255, 255, 255), thickness)
        y_text += line_height + 10

def draw_session_stats(image):
    """Draw session statistics on screen"""
    h, w, _ = image.shape

    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (0, 0, 0), -1)
    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (255, 255, 255), 2)

    cv2.putText(image, "Session Stats:", (w - 280, h - 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(image, f"Exercises: {session_stats['total_exercises']}", (w - 280, h - 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(image, f"Total Reps: {session_stats['total_reps']}", (w - 280, h - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    duration_min = int(session_stats["session_duration"] // 60)
    duration_sec = int(session_stats["session_duration"] % 60)
    cv2.putText(image, f"Duration: {duration_min:02d}:{duration_sec:02d}", (w - 280, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    total_possible_reps = sum(REPS_PER_EXERCISE.values())
    progress = min(1.0, session_stats["total_reps"] / total_possible_reps)
    draw_progress_bar(image, progress, w - 280, h - 40, 250, 15, (0, 255, 0))
    cv2.putText(image, f"Session Progress: {int(progress * 100)}%", (w - 280, h - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

def draw_game_hud(image):
    h, w, _ = image.shape
    hud_w = 280
    hud_h = 120
    x1 = 20
    y1 = h - hud_h - 200
    x2 = x1 + hud_w
    y2 = y1 + hud_h

    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 2)

    cv2.putText(image, f"Score: {score}", (x1 + 10, y1 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(image, f"Streak: {streak}", (x1 + 10, y1 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(image, f"Level: {level}", (x1 + 10, y1 + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

def draw_help_screen(image):
    """Draw help screen with instructions"""
    h, w, _ = image.shape

    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

    help_text = [
        "FOREARM PHYSIOTHERAPY ASSISTANT",
        "",
        "EXERCISES:",
        "- Forearm Pronation - Rotate palm downward",
        "- Forearm Supination - Rotate palm upward",
        "- Elbow Flexion - Bend elbow toward shoulder",
        "- Elbow Extension - Straighten arm fully",
        "",
        "CONTROLS:",
        "- 's' - Start exercise",
        "- 'd' - Demo proper range of motion",
        "- 'n' - Next exercise",
        "- 'r' - Restart current exercise",
        "- 'h' - Toggle this help",
        "- 'm' - Return to main menu",
        "- ESC - Exit program",
        "",
        "SAFETY TIPS:",
        "- Stop if you feel pain",
        "- Keep movements slow and controlled",
        "- Maintain proper form",
        "",
        "Press 'h' to close this help screen"
    ]

    y_start = 50
    for i, line in enumerate(help_text):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 0.8 if i == 0 else 0.6
        thickness = 2 if i == 0 else 1
        cv2.putText(image, line, (50, y_start + i * 25),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_demo_mode(image):
    """Draw demo screen showing proper range of motion for forearm and elbow exercises"""
    h, w, _ = image.shape

    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)

    demo_text = [
        f"DEMO: {EXERCISES[current_exercise]['name']}",
        "",
        "FOREARM ROTATION (PRONATION / SUPINATION):",
        "- Start with elbow at 90° and upper arm by your side.",
        "- Rotate your forearm so your palm faces DOWN (pronation)",
        "  or UP (supination) without moving the upper arm.",
        "- Target range: 70-90° of rotation.",
        "",
        "ELBOW FLEXION:",
        "- Start with arm straight by your side.",
        "- Bend your elbow to bring your hand toward your shoulder.",
        "- Target range: 130-150° at the elbow.",
        "",
        "ELBOW EXTENSION:",
        "- Start with elbow bent, then straighten fully.",
        "- Avoid locking or hyperextending the joint.",
        "",
        "Press 'd' again to close this demo."
    ]

    y_start = 80
    for i, line in enumerate(demo_text):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 0.8 if i == 0 else 0.6
        thickness = 2 if i == 0 else 1
        cv2.putText(image, line, (50, y_start + i * 25),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def get_target_reps_for_current() -> int:
    """Return target reps for the current exercise"""
    return REPS_PER_EXERCISE.get(current_exercise, default_target_reps)

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

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    target_reps_current = get_target_reps_for_current()

    if exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "forearm_pronation":
                return f"Ready! Rotate your forearm so your palm faces downward.\n\n{exercise['visual_cue']}\n\nHold when palm is fully rotated down."
            elif current_exercise == "forearm_supination":
                return f"Ready! Rotate your forearm so your palm faces upward.\n\n{exercise['visual_cue']}\n\nHold when palm is fully rotated up."
            elif current_exercise == "elbow_flexion":
                return f"Ready! Bend your elbow to bring your hand toward your shoulder.\n\n{exercise['visual_cue']}\n\nHold when elbow is bent."
            elif current_exercise == "elbow_extension":
                return f"Ready! Straighten your arm fully from the bent position.\n\n{exercise['visual_cue']}\n\nHold when arm is straight."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Hold steady! {remaining}s remaining\nRep {reps + 1}/{target_reps_current}\n\nYou should feel a gentle stretch - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps_current} complete!\n\nReturn to starting position."
    elif exercise_phase == "rest":
        target_reps_current = get_target_reps_for_current()
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps_current}\n\nShake out your arm gently during rest."
    elif exercise_phase == "complete":
        return (f"Exercise Complete!\n"
                f"You did {reps} reps of {exercise['name']}\n"
                f"Points this exercise: {exercise_points_earned}\n"
                f"Current streak: {streak}  Level: {level}\n"
                f"Press 'n' for next exercise, 'm' for menu, or 'r' to restart")
    else:
        return "Position your arm in front of the camera and start exercising!"

# Global variables for timing
rest_start = None
show_help = False
show_demo = False
demo_start = None

while cap.isOpened():
    success, image = cap.read()
    if not success:
        break

    image = cv2.flip(image, 1)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Process both hands and pose
    hand_results = hands.process(rgb)
    pose_results = pose.process(rgb)

    exercise = EXERCISES[current_exercise]
    current_time = time.time()

    # Handle exercise phases
    if exercise_phase == "rest":
        if rest_start is None:
            rest_start = current_time
        elapsed_rest = current_time - rest_start
        if elapsed_rest >= rest_time:
            exercise_phase = "exercise"
            rest_start = None
    elif exercise_phase == "complete" and complete_start is not None:
        if current_time - complete_start >= 2:
            exercise_keys = EXERCISE_ORDER
            current_idx = exercise_keys.index(current_exercise)
            current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
            exercise_phase = "setup"
            reps = 0
            start_hold = None
            paused_time = 0
            pause_start = None
            rest_start = None
            hold_time = EXERCISES[current_exercise]["hold_time"]
            complete_start = None

    # Hand and pose detection
    hand_detected = hand_results.multi_hand_landmarks is not None
    pose_detected = pose_results.pose_landmarks is not None

    if hand_detected and pose_detected:
        for hand_landmarks in hand_results.multi_hand_landmarks:
            h, w, _ = image.shape

            # Draw hand landmarks
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

            # Draw pose landmarks (elbow and shoulder)
            mp_drawing.draw_landmarks(image, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2))

            # Exercise-specific logic
            if exercise_phase == "exercise":
                if current_exercise in ["forearm_pronation", "forearm_supination"]:
                    # Forearm rotation exercises
                    palm_angle = calculate_palm_orientation(hand_landmarks, (h, w))
                    min_angle, max_angle = exercise["target_angle_range"]

                    cv2.putText(image, f"Palm Angle: {int(palm_angle)} deg", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                    # For pronation (palm down), we want angle around 90-100
                    # For supination (palm up), we want angle around 80-100 but from different starting position
                    in_target = min_angle <= palm_angle <= max_angle

                    if in_target:
                        if start_hold is None:
                            start_hold = current_time
                            paused_time = 0
                            pause_start = None
                        else:
                            elapsed = current_time - start_hold + paused_time
                            if elapsed >= hold_time:
                                reps += 1
                                base_points = 100
                                if last_rep_time is not None and (current_time - last_rep_time) <= combo_window_sec:
                                    streak += 1
                                else:
                                    streak = 1
                                last_rep_time = current_time
                                combo_bonus = max(0, (streak - 1) * 10)
                                earned = base_points + combo_bonus
                                exercise_points_earned += earned
                                score += earned
                                if streak % 5 == 0:
                                    level += 1
                                start_hold = None
                                paused_time = 0
                                if reps >= get_target_reps_for_current():
                                    exercise_phase = "complete"
                                    update_session_stats()
                                    complete_start = current_time
                                else:
                                    exercise_phase = "rest"
                                    rest_start = None
                    else:
                        if start_hold is not None:
                            if pause_start is None:
                                pause_start = current_time
                            elif current_time - pause_start <= 1:
                                continue
                            else:
                                start_hold = None
                                paused_time = 0
                                pause_start = None

                    # Status feedback
                    if in_target:
                        status_text = "CORRECT - Hold steady!"
                        status_color = (0, 255, 0)
                    else:
                        status_text = "Try Again - Adjust rotation"
                        status_color = (0, 0, 255)

                    cv2.putText(image, status_text, (50, h - 170),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

                elif current_exercise in ["elbow_flexion", "elbow_extension"]:
                    # Elbow exercises
                    elbow_angle = calculate_elbow_angle(pose_results.pose_landmarks, (h, w))
                    min_angle, max_angle = exercise["target_angle_range"]

                    cv2.putText(image, f"Elbow Angle: {int(elbow_angle)} deg", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                    in_target = min_angle <= elbow_angle <= max_angle

                    if in_target:
                        if start_hold is None:
                            start_hold = current_time
                            paused_time = 0
                            pause_start = None
                        else:
                            elapsed = current_time - start_hold + paused_time
                            if elapsed >= hold_time:
                                reps += 1
                                base_points = 100
                                if last_rep_time is not None and (current_time - last_rep_time) <= combo_window_sec:
                                    streak += 1
                                else:
                                    streak = 1
                                last_rep_time = current_time
                                combo_bonus = max(0, (streak - 1) * 10)
                                earned = base_points + combo_bonus
                                exercise_points_earned += earned
                                score += earned
                                if streak % 5 == 0:
                                    level += 1
                                start_hold = None
                                paused_time = 0
                                if reps >= get_target_reps_for_current():
                                    exercise_phase = "complete"
                                    update_session_stats()
                                    complete_start = current_time
                                else:
                                    exercise_phase = "rest"
                                    rest_start = None
                    else:
                        if start_hold is not None:
                            if pause_start is None:
                                pause_start = current_time
                            elif current_time - pause_start <= 1:
                                continue
                            else:
                                start_hold = None
                                paused_time = 0
                                pause_start = None

                    # Status feedback
                    if in_target:
                        status_text = "CORRECT - Hold steady!"
                        status_color = (0, 255, 0)
                    else:
                        status_text = "Try Again - Adjust angle"
                        status_color = (0, 0, 255)

                    cv2.putText(image, status_text, (50, h - 170),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    # Draw UI elements
    h, w, _ = image.shape

    instruction_text = get_exercise_instruction()
    draw_instruction_box(image, instruction_text)

    cv2.putText(image, f"Exercise: {exercise['name']}", (20, h - 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(image, f"Reps: {reps}/{get_target_reps_for_current()}", (20, h - 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Draw progress bars
    if exercise_phase == "exercise" and start_hold:
        hold_progress = min(1.0, (current_time - start_hold + paused_time) / hold_time)
        draw_progress_bar(image, hold_progress, w - 250, 50, 200, 20, exercise["color"])
        cv2.putText(image, "Hold Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    elif exercise_phase == "rest" and rest_start:
        rest_progress = min(1.0, (current_time - rest_start) / rest_time)
        draw_progress_bar(image, rest_progress, w - 250, 50, 200, 20, (255, 255, 0))
        cv2.putText(image, "Rest Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if not hand_detected:
        cv2.putText(image, "No hand detected - Position your hand in front of camera",
                   (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    elif not pose_detected:
        cv2.putText(image, "No pose detected - Position your full arm in front of camera",
                   (w//2 - 250, h//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    draw_session_stats(image)
    draw_game_hud(image)

    if show_help:
        draw_help_screen(image)

    # Demo overlay (available primarily in setup / between reps)
    if show_demo and exercise_phase in ("setup", "exercise"):
        draw_demo_mode(image)

    cv2.putText(image, "Controls: 's'=start, 'd'=demo, 'n'=next, 'r'=restart, 'h'=help, 'm'=menu, ESC=exit",
               (20, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    cv2.imshow("Forearm Physiotherapy Assistant", image)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s'):
        exercise_phase = "exercise"
    elif key == ord('n') and exercise_phase == "complete":
        exercise_keys = EXERCISE_ORDER
        current_idx = exercise_keys.index(current_exercise)
        current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        hold_time = EXERCISES[current_exercise]["hold_time"]
        exercise_points_earned = 0
    elif key == ord('r'):
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        rest_start = None
        hold_time = EXERCISES[current_exercise]["hold_time"]
        exercise_points_earned = 0
    elif key == ord('h'):
        show_help = not show_help
    elif key == ord('d'):
        # Toggle demo overlay
        show_demo = not show_demo
    elif key == ord('m'):
        # Return to menu
        subprocess.Popen(["python", "menu.py"])
        break

cap.release()
cv2.destroyAllWindows()
