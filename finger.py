import cv2
from shared_ui import ExerciseUI
ui_renderer = ExerciseUI()
import mediapipe as mp
import time
import math
import numpy as np
import os
import webbrowser
import subprocess

exercise_key = os.environ.get("EXERCISE_KEY", "finger_spread")
print("Running Finger Exercise:", exercise_key)
if exercise_key not in EXERCISES:
    exercise_key = "finger_spread"
    print("Warning: Unknown exercise '{exercise_key}', using default: finger_spread")

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# Finger exercise types and setup
EXERCISES = {
    "finger_spread": {
        "name": "Finger Spread",
        "description": "Spread your fingers apart as wide as comfortable",
        "detailed_instruction": "Start with fingers together, then spread them apart. Hold when fully spread. Aim for maximum comfortable separation between fingers.",
        "target_distance_range": (80, 120),  # pixels between adjacent fingers
        "hold_time": 5,
        "color": (0, 255, 255),  # Yellow
        "visual_cue": "Imagine spreading your fingers like a fan",
        "exercise_type": "spread"
    },
    "thumb_opposition": {
        "name": "Thumb Opposition",
        "description": "Touch your thumb to each finger sequentially",
        "detailed_instruction": "Touch your thumb to your index finger, then middle, ring, and pinky. Make smooth transitions between fingers.",
        "target_sequence": ["index", "middle", "ring", "pinky"],
        "hold_time": 2,
        "color": (255, 0, 255),  # Magenta
        "visual_cue": "Touch thumb to each finger like counting",
        "exercise_type": "opposition"
    },
    "finger_taps": {
        "name": "Finger Taps",
        "description": "Tap each finger on your thumb sequentially",
        "detailed_instruction": "Tap your index finger on your thumb, then middle, ring, and pinky. Keep a steady rhythm and full range of motion.",
        "target_sequence": ["index", "middle", "ring", "pinky"],
        "tap_threshold": 30,  # pixels
        "hold_time": 1,
        "color": (255, 165, 0),  # Orange
        "visual_cue": "Tap each finger on your thumb like playing piano",
        "exercise_type": "taps"
    },
    "finger_flexion": {
        "name": "Finger Flexion",
        "description": "Bend your fingers into a fist and straighten them",
        "detailed_instruction": "Make a tight fist with all fingers, then fully straighten them. Focus on controlled movements and full range of motion.",
        "target_angle_range": (160, 180),  # angle between MCP and PIP joints when straight
        "hold_time": 3,
        "color": (0, 255, 128),  # Light Green
        "visual_cue": "Make a fist, then straighten fingers completely",
        "exercise_type": "flexion"
    }
}

# Exercise order
EXERCISE_ORDER = [
    "finger_spread",
    "thumb_opposition",
    "finger_taps",
    "finger_flexion"
]

# Per-exercise target reps
REPS_PER_EXERCISE = {
    "finger_spread": 3,
    "thumb_opposition": 2,
    "finger_taps": 3,
    "finger_flexion": 3
}

# Current exercise settings
current_exercise = EXERCISE_ORDER[0]
default_target_reps = 3
reps = 0
hold_time = EXERCISES[current_exercise]["hold_time"]
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "exercise"  # setup, warmup, exercise, rest, complete
warmup_time = 10  # seconds
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
cv2.namedWindow("Finger Physiotherapy Assistant", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Finger Physiotherapy Assistant", 1600, 900)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def calculate_finger_angle(mcp, pip, dip):
    """Calculate angle at finger joint"""
    return calculate_angle(mcp, pip, dip)

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

def get_finger_mcp_positions(hand_landmarks, image_shape):
    """Get positions of all finger MCP joints"""
    h, w = image_shape[:2]
    mcps = {
        "thumb": (int(w * hand_landmarks.landmark[1].x), int(h * hand_landmarks.landmark[1].y)),
        "index": (int(w * hand_landmarks.landmark[5].x), int(h * hand_landmarks.landmark[5].y)),
        "middle": (int(w * hand_landmarks.landmark[9].x), int(h * hand_landmarks.landmark[9].y)),
        "ring": (int(w * hand_landmarks.landmark[13].x), int(h * hand_landmarks.landmark[13].y)),
        "pinky": (int(w * hand_landmarks.landmark[17].x), int(h * hand_landmarks.landmark[17].y))
    }
    return mcps

def get_finger_pip_positions(hand_landmarks, image_shape):
    """Get positions of all finger PIP joints"""
    h, w = image_shape[:2]
    pips = {
        "index": (int(w * hand_landmarks.landmark[6].x), int(h * hand_landmarks.landmark[6].y)),
        "middle": (int(w * hand_landmarks.landmark[10].x), int(h * hand_landmarks.landmark[10].y)),
        "ring": (int(w * hand_landmarks.landmark[14].x), int(h * hand_landmarks.landmark[14].y)),
        "pinky": (int(w * hand_landmarks.landmark[18].x), int(h * hand_landmarks.landmark[18].y))
    }
    return pips

def calculate_finger_spread(tips):
    """Calculate average distance between adjacent fingers"""
    distances = [
        calculate_distance(tips["thumb"], tips["index"]),
        calculate_distance(tips["index"], tips["middle"]),
        calculate_distance(tips["middle"], tips["ring"]),
        calculate_distance(tips["ring"], tips["pinky"])
    ]
    return sum(distances) / len(distances)

def detect_thumb_opposition(thumb_tip, finger_tips, threshold=40):
    """Detect which finger the thumb is touching"""
    for finger, tip in finger_tips.items():
        if finger != "thumb":
            dist = calculate_distance(thumb_tip, tip)
            if dist < threshold:
                return finger
    return None

def detect_finger_taps(thumb_tip, finger_tips, last_positions, tap_threshold=30):
    """Detect finger tapping motion toward thumb"""
    tapped_fingers = []
    for finger, tip in finger_tips.items():
        if finger != "thumb" and finger in last_positions:
            prev_dist = calculate_distance(thumb_tip, last_positions[finger])
            curr_dist = calculate_distance(thumb_tip, tip)
            if prev_dist > tap_threshold and curr_dist < tap_threshold:
                tapped_fingers.append(finger)
    return tapped_fingers

def calculate_finger_flexion_angles(hand_landmarks, image_shape):
    """Calculate flexion angles for fingers"""
    h, w = image_shape[:2]

    # Get joint positions
    mcps = get_finger_mcp_positions(hand_landmarks, image_shape)
    pips = get_finger_pip_positions(hand_landmarks, image_shape)

    # Calculate angles (simplified - using MCP to PIP angle)
    angles = {}
    for finger in ["index", "middle", "ring", "pinky"]:
        if finger in mcps and finger in pips:
            # Use wrist as reference point for angle calculation
            wrist = (int(w * hand_landmarks.landmark[0].x), int(h * hand_landmarks.landmark[0].y))
            angle = calculate_angle(wrist, mcps[finger], pips[finger])
            angles[finger] = angle

    return angles

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
        "FINGER PHYSIOTHERAPY ASSISTANT",
        "",
        "EXERCISES:",
        "- Finger Spread - Spread fingers apart",
        "- Thumb Opposition - Touch thumb to each finger",
        "- Finger Taps - Tap fingers on thumb",
        "- Finger Flexion - Make fist and straighten",
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
        "- Always warm up before exercising",
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

    if exercise_phase == "setup":
        return f"Welcome to Finger Exercises!\n{exercise['name']}: {exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPress 'd' to see a demo.\nPosition your hand in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your fingers in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nMake gentle circles with each finger."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "finger_spread":
                return f"Ready! Spread your fingers apart as wide as comfortable.\n\n{exercise['visual_cue']}\n\nHold when fully spread."
            elif current_exercise == "thumb_opposition":
                return f"Ready! Touch your thumb to each finger sequentially.\n\n{exercise['visual_cue']}\n\nStart with index finger."
            elif current_exercise == "finger_taps":
                return f"Ready! Tap each finger on your thumb.\n\n{exercise['visual_cue']}\n\nKeep steady rhythm."
            elif current_exercise == "finger_flexion":
                return f"Ready! Make a fist, then straighten fingers.\n\n{exercise['visual_cue']}\n\nFocus on full range."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Hold steady! {remaining}s remaining\nRep {reps + 1}/{target_reps_current}\n\nYou should feel a gentle stretch - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps_current} complete!\n\nLet your fingers return to neutral position."
    elif exercise_phase == "rest":
        target_reps_current = get_target_reps_for_current()
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps_current}\n\nShake out your fingers gently during rest."
    elif exercise_phase == "complete":
        return (f"Exercise Complete!\n"
                f"You did {reps} reps of {exercise['name']}\n"
                f"Points this exercise: {exercise_points_earned}\n"
                f"Current streak: {streak}  Level: {level}\n"
                f"Press 'n' for next exercise, 'm' for menu, or 'r' to restart")
    else:
        return "Press 's' to start exercise"

# Global variables for timing
warmup_start = None
rest_start = None
show_help = False
show_demo = False
demo_start = None

def draw_demo_mode(image):
    """Draw demo screen showing proper range of motion for functional hand exercises"""
    h, w, _ = image.shape

    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)

    demo_text = [
        f"DEMO: {EXERCISES[current_exercise]['name']}",
        "",
        "FINGER SPREAD:",
        "- Start with fingers together, then spread them apart like a fan.",
        "- Hold the wide position briefly before relaxing.",
        "",
        "THUMB OPPOSITION:",
        "- Touch your thumb to INDEX, MIDDLE, RING, and PINKY in sequence.",
        "- Focus on precise contact rather than speed.",
        "",
        "FINGER TAPS:",
        "- Tap each finger on your thumb one at a time.",
        "- Keep a steady rhythm and full contact on each tap.",
        "",
        "FINGER FLEXION:",
        "- Make a full fist, then fully straighten your fingers.",
        "- Aim for a smooth, controlled motion through the whole range.",
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

# Finger tracking variables
last_finger_positions = {}
current_opposition_target = 0
opposition_sequence = ["index", "middle", "ring", "pinky"]
tapped_fingers = set()

while cap.isOpened():
    success, image = cap.read()
    if not success:
        break

    image = cv2.flip(image, 1)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

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
    elif exercise_phase == "complete" and complete_start is not None:
        if current_time - complete_start >= 2:
            exercise_keys = EXERCISE_ORDER
            current_idx = exercise_keys.index(current_exercise)
            current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
            exercise_phase = "exercise"
            reps = 0
            start_hold = None
            paused_time = 0
            pause_start = None
            warmup_start = None
            rest_start = None
            hold_time = EXERCISES[current_exercise]["hold_time"]
            complete_start = None
            current_opposition_target = 0
            tapped_fingers = set()

    # Hand detection and exercise logic
    hand_detected = False
    if result.multi_hand_landmarks:
        hand_detected = True
        for hand_landmarks in result.multi_hand_landmarks:
            h, w, _ = image.shape

            # Get finger positions
            tips = get_finger_tip_positions(hand_landmarks, (h, w))
            mcps = get_finger_mcp_positions(hand_landmarks, (h, w))

            # Draw hand landmarks
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

            # Exercise-specific logic
            if exercise_phase == "exercise":
                if current_exercise == "finger_spread":
                    spread_distance = calculate_finger_spread(tips)
                    min_dist, max_dist = exercise["target_distance_range"]

                    cv2.putText(image, f"Spread Distance: {int(spread_distance)} px", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                    if min_dist <= spread_distance <= max_dist:
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

                elif current_exercise == "thumb_opposition":
                    touching_finger = detect_thumb_opposition(tips["thumb"], tips)
                    target_finger = opposition_sequence[current_opposition_target]

                    if touching_finger == target_finger:
                        if start_hold is None:
                            start_hold = current_time
                            paused_time = 0
                            pause_start = None
                        else:
                            elapsed = current_time - start_hold + paused_time
                            if elapsed >= hold_time:
                                reps += 1
                                current_opposition_target = (current_opposition_target + 1) % len(opposition_sequence)
                                base_points = 150
                                if last_rep_time is not None and (current_time - last_rep_time) <= combo_window_sec:
                                    streak += 1
                                else:
                                    streak = 1
                                last_rep_time = current_time
                                combo_bonus = max(0, (streak - 1) * 15)
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

                    cv2.putText(image, f"Target: Touch {target_finger} finger", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                    if touching_finger:
                        cv2.putText(image, f"Touching: {touching_finger}", (50, h - 170),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                elif current_exercise == "finger_taps":
                    # Detect taps
                    new_taps = detect_finger_taps(tips["thumb"], tips, last_finger_positions, exercise["tap_threshold"])
                    for finger in new_taps:
                        if finger not in tapped_fingers:
                            tapped_fingers.add(finger)
                            if start_hold is None:
                                start_hold = current_time
                                paused_time = 0
                                pause_start = None
                            else:
                                elapsed = current_time - start_hold + paused_time
                                if elapsed >= hold_time:
                                    reps += 1
                                    tapped_fingers = set()
                                    base_points = 120
                                    if last_rep_time is not None and (current_time - last_rep_time) <= combo_window_sec:
                                        streak += 1
                                    else:
                                        streak = 1
                                    last_rep_time = current_time
                                    combo_bonus = max(0, (streak - 1) * 12)
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

                    cv2.putText(image, f"Tapped: {len(tapped_fingers)}/4 fingers", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                elif current_exercise == "finger_flexion":
                    flexion_angles = calculate_finger_flexion_angles(hand_landmarks, (h, w))
                    avg_angle = sum(flexion_angles.values()) / len(flexion_angles) if flexion_angles else 0
                    min_angle, max_angle = exercise["target_angle_range"]

                    cv2.putText(image, f"Flexion Angle: {int(avg_angle)} deg", (50, h - 200),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                    if min_angle <= avg_angle <= max_angle:
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

            # Update last positions for tap detection
            last_finger_positions = tips.copy()

    # Draw UI elements (Delegated to shared_ui.py)
    progress_val = None
    progress_title = ""
    if exercise_phase == "exercise" and start_hold:
        progress_val = min(1.0, (current_time - start_hold + paused_time) / hold_time)
        progress_title = "Hold Progress"
    elif exercise_phase == "rest" and rest_start:
        progress_val = min(1.0, (current_time - rest_start) / rest_time)
        progress_title = "Rest Progress"
    elif exercise_phase == "warmup" and warmup_start:
        try:
            progress_val = min(1.0, (current_time - warmup_start) / warmup_time)
            progress_title = "Warmup Progress"
        except:
            pass
            
    current_angle = None
    if 'angle' in locals(): current_angle = locals()['angle']
    elif 'shoulder_angle' in locals(): current_angle = locals()['shoulder_angle']
    elif 'elbow_angle' in locals(): current_angle = locals()['elbow_angle']
    elif 'rotation_angle' in locals(): current_angle = locals()['rotation_angle']
    
    feedback = ""
    if 'bend_guidance' in locals() and locals()['bend_guidance']: feedback = locals()['bend_guidance']
    elif 'rotation_guidance' in locals() and locals()['rotation_guidance']: feedback = locals()['rotation_guidance']
    elif 'directional_guidance' in locals() and locals()['directional_guidance']: feedback = locals()['directional_guidance']
    
    if 'hand_detected' in locals() and not locals()['hand_detected']: feedback = "No hand detected. Position hand in camera."
    elif 'arm_detected' in locals() and not locals()['arm_detected']: feedback = "No arm detected. Position arm in camera."
    
    try:
        instr = get_exercise_instruction()
    except:
        instr = ""
        
    state = {
        "exercise_name": exercise["name"],
        "level": os.environ.get("LEVEL", "1"),
        "instruction": instr,
        "angle": current_angle,
        "target_range": exercise.get("target_angle_range"),
        "reps": reps,
        "target_reps": target_reps,
        "feedback_msg": feedback,
        "progress": progress_val,
        "progress_title": progress_title,
        "session_duration": f"{int(session_stats.get('session_duration', 0) // 60):02d}:{int(session_stats.get('session_duration', 0) % 60):02d}",
        "session_reps": session_stats.get('total_reps', 0)
    }
    
    image = ui_renderer.render(image, state)
    
    cv2.namedWindow("Exercise", cv2.WINDOW_NORMAL)
    cv2.imshow("Exercise", image)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s') and exercise_phase == "setup":
        exercise_phase = "exercise"
    elif key == ord('n') and exercise_phase == "complete":
        exercise_keys = EXERCISE_ORDER
        current_idx = exercise_keys.index(current_exercise)
        current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
        exercise_phase = "exercise"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        hold_time = EXERCISES[current_exercise]["hold_time"]
        exercise_points_earned = 0
        current_opposition_target = 0
        tapped_fingers = set()
    elif key == ord('r'):
        exercise_phase = "exercise"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        warmup_start = None
        rest_start = None
        hold_time = EXERCISES[current_exercise]["hold_time"]
        exercise_points_earned = 0
        current_opposition_target = 0
        tapped_fingers = set()
    elif key == ord('h'):
        show_help = not show_help
    elif key == ord('m'):
        # Return to menu
        subprocess.Popen(["python", "menu.py"])
        break
    elif key == ord('d') and exercise_phase == "setup":
        # Toggle demo overlay
        show_demo = not show_demo

cap.release()
cv2.destroyAllWindows()
