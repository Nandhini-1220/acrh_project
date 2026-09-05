import cv2
import mediapipe as mp
import time
import math
import numpy as np

# Mediapipe setup for pose detection
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Exercise types and setup
EXERCISES = {
    "marching_in_place": {
        "name": "Marching in Place",
        "description": "Lift knees alternately while maintaining balance",
        "detailed_instruction": "Stand with feet shoulder-width apart. Lift one knee at a time toward your chest while keeping the other foot planted. Alternate legs. Maintain upright posture and balance.",
        "target_angles": {"knee_lift": 90},  # Minimum knee lift angle
        "color": (0, 255, 255),  # Yellow
        "exercise_type": "marching_in_place"
    }
}

# Current exercise settings
current_exercise = "marching_in_place"
target_reps = 20  # Total steps (10 per leg)
reps = 0
session_start_time = time.time()
exercise_phase = "setup"  # setup, warmup, exercise, rest, complete
warmup_time = 10  # seconds
rest_time = 3  # seconds between sets

# Session tracking
session_stats = {
    "total_exercises": 0,
    "total_reps": 0,
    "session_duration": 0,
    "exercises_completed": []
}

# Rep tracking for marching
rep_state = "waiting"  # waiting, left_up, right_up, rep_complete
last_leg = None  # Track which leg was last lifted

# Open camera
cap = cv2.VideoCapture(0)

def calculate_knee_angle(hip, knee, ankle):
    """Calculate knee angle between thigh and calf"""
    thigh = np.array([knee[0] - hip[0], knee[1] - hip[1]])
    calf = np.array([ankle[0] - knee[0], ankle[1] - ankle[1]])
    cos_angle = np.dot(thigh, calf) / (np.linalg.norm(thigh) * np.linalg.norm(calf))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle

def calculate_torso_stability(shoulder_left, shoulder_right, hip_left, hip_right):
    """Calculate torso stability (minimal side tilt)"""
    # Calculate shoulder and hip midpoints
    shoulder_mid = ((shoulder_left[0] + shoulder_right[0]) / 2, (shoulder_left[1] + shoulder_right[1]) / 2)
    hip_mid = ((hip_left[0] + hip_right[0]) / 2, (hip_left[1] + hip_right[1]) / 2)

    # Calculate torso angle from vertical
    torso_vector = np.array([hip_mid[0] - shoulder_mid[0], hip_mid[1] - shoulder_mid[1]])
    vertical = np.array([0, 1])  # Downward
    cos_angle = np.dot(torso_vector, vertical) / (np.linalg.norm(torso_vector) * np.linalg.norm(vertical))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle < 15  # Consider stable if tilt < 15°

def check_standing_leg_stability(standing_ankle, standing_knee):
    """Check if standing leg remains stable"""
    # Simple check: if ankle and knee are reasonably aligned vertically
    x_diff = abs(standing_ankle[0] - standing_knee[0])
    return x_diff < 30  # pixels threshold

def draw_progress_bar(image, progress, x, y, width, height, color):
    """Draw a progress bar"""
    cv2.rectangle(image, (x, y), (x + width, y + height), (50, 50, 50), -1)
    progress_width = int(width * progress)
    cv2.rectangle(image, (x, y), (x + progress_width, y + height), color, -1)
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

def draw_instruction_box(image, text, y_offset=0):
    """Draw instruction box with background"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8
    thickness = 2
    (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
    padding = 10
    cv2.rectangle(image,
                  (20, 30 + y_offset - text_height - padding),
                  (20 + text_width + 2*padding, 30 + y_offset + padding),
                  (0, 0, 0), -1)
    cv2.rectangle(image,
                  (20, 30 + y_offset - text_height - padding),
                  (20 + text_width + 2*padding, 30 + y_offset + padding),
                  (255, 255, 255), 2)
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
    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (0, 0, 0), -1)
    cv2.rectangle(image, (w - 300, h - 150), (w - 20, h - 20), (255, 255, 255), 2)
    cv2.putText(image, "Session Stats:", (w - 280, h - 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(image, f"Exercises: {session_stats['total_exercises']}", (w - 280, h - 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(image, f"Total Steps: {session_stats['total_reps']}", (w - 280, h - 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    duration_min = int(session_stats["session_duration"] // 60)
    duration_sec = int(session_stats["session_duration"] % 60)
    cv2.putText(image, f"Duration: {duration_min:02d}:{duration_sec:02d}", (w - 280, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    total_possible_reps = target_reps
    progress = min(1.0, session_stats["total_reps"] / total_possible_reps)
    draw_progress_bar(image, progress, w - 280, h - 40, 250, 15, (0, 255, 0))
    cv2.putText(image, f"Session Progress: {int(progress * 100)}%", (w - 280, h - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

def get_feedback_text(left_knee_angle, right_knee_angle, torso_stable, standing_stable, rep_state):
    """Get feedback text based on current form"""
    exercise = EXERCISES[current_exercise]
    min_lift_angle = exercise["target_angles"]["knee_lift"]

    if rep_state == "waiting":
        return "Stand with feet shoulder-width apart. Get ready to march in place."

    if not torso_stable:
        return "Keep your torso upright - don't lean to the sides"

    if not standing_stable:
        return "Keep your standing leg stable - don't shift weight too much"

    if left_knee_angle >= min_lift_angle and right_knee_angle < min_lift_angle:
        return "Good left knee lift! Now lower and lift right knee."
    elif right_knee_angle >= min_lift_angle and left_knee_angle < min_lift_angle:
        return "Good right knee lift! Now lower and lift left knee."
    elif left_knee_angle >= min_lift_angle and right_knee_angle >= min_lift_angle:
        return "Lift one knee at a time - lower one before lifting the other"
    else:
        return "Lift your knee higher toward your chest"

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]

    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\nStand facing the camera with good posture."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently march in place slowly\nfor {warmup_time} seconds to prepare your legs.\n\nFocus on balance and control."
    elif exercise_phase == "exercise":
        if rep_state == "waiting":
            return f"Ready! Stand tall with both feet on ground.\n\nLift one knee at a time toward your chest."
        elif rep_state in ["left_up", "right_up"]:
            return f"Good! Keep alternating legs.\n\nLift each knee to at least 90° while maintaining balance."
        elif rep_state == "rep_complete":
            return f"Great step! Continue marching.\nSteps: {reps}/{target_reps}"
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nContinue marching: {reps + 1}/{target_reps}\n\nShake out your legs gently."
    elif exercise_phase == "complete":
        return f"🎉 Exercise Complete! 🎉\nYou did {reps} steps of {exercise['name']}\nPress 'r' to restart"
    else:
        return "Press 's' to start exercise"

# Global variables for timing
warmup_start = None
rest_start = None

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Camera read failed, retrying...")
        time.sleep(0.1)
        continue

    image = cv2.flip(image, 1)  # mirror view
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

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
            rep_state = "waiting"

    # Pose detection and exercise logic
    body_detected = False
    feedback_color = (255, 255, 255)  # Default white
    if result.pose_landmarks:
        body_detected = True
        landmarks = result.pose_landmarks.landmark
        h, w, _ = image.shape

        # Get key points
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]
        right_ankle = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE]
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

        # Convert to pixel coordinates
        left_hip_pt = (int(w * left_hip.x), int(h * left_hip.y))
        left_knee_pt = (int(w * left_knee.x), int(h * left_knee.y))
        left_ankle_pt = (int(w * left_ankle.x), int(h * left_ankle.y))
        right_hip_pt = (int(w * right_hip.x), int(h * right_hip.y))
        right_knee_pt = (int(w * right_knee.x), int(h * right_knee.y))
        right_ankle_pt = (int(w * right_ankle.x), int(h * right_ankle.y))
        left_shoulder_pt = (int(w * left_shoulder.x), int(h * left_shoulder.y))
        right_shoulder_pt = (int(w * right_shoulder.x), int(h * right_shoulder.y))

        # Calculate angles and stability
        left_knee_angle = calculate_knee_angle(left_hip_pt, left_knee_pt, left_ankle_pt)
        right_knee_angle = calculate_knee_angle(right_hip_pt, right_knee_pt, right_ankle_pt)

        torso_stable = calculate_torso_stability(left_shoulder_pt, right_shoulder_pt, left_hip_pt, right_hip_pt)

        # Determine which leg is standing and check its stability
        if left_knee_angle < right_knee_angle:
            # Left leg is more extended (standing)
            standing_stable = check_standing_leg_stability(left_ankle_pt, left_knee_pt)
        else:
            # Right leg is more extended (standing)
            standing_stable = check_standing_leg_stability(right_ankle_pt, right_knee_pt)

        # Draw pose landmarks
        mp_drawing.draw_landmarks(image, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

        # Draw angle indicators
        cv2.putText(image, f"Left Knee: {int(left_knee_angle)}°", (left_knee_pt[0] - 50, left_knee_pt[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
        cv2.putText(image, f"Right Knee: {int(right_knee_angle)}°", (right_knee_pt[0] - 50, right_knee_pt[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

        # Exercise logic for marching in place
        if exercise_phase == "exercise":
            min_lift_angle = exercise["target_angles"]["knee_lift"]

            left_lifted = left_knee_angle >= min_lift_angle
            right_lifted = right_knee_angle >= min_lift_angle

            form_good = torso_stable and standing_stable

            if form_good:
                feedback_color = (0, 255, 0)  # Green for correct

                if left_lifted and not right_lifted and rep_state != "left_up":
                    if last_leg != "left":
                        reps += 1
                        last_leg = "left"
                        if reps >= target_reps:
                            exercise_phase = "complete"
                            update_session_stats()
                        else:
                            rep_state = "left_up"
                elif right_lifted and not left_lifted and rep_state != "right_up":
                    if last_leg != "right":
                        reps += 1
                        last_leg = "right"
                        if reps >= target_reps:
                            exercise_phase = "complete"
                            update_session_stats()
                        else:
                            rep_state = "right_up"
            else:
                feedback_color = (0, 0, 255)  # Red for incorrect
                if rep_state in ["left_up", "right_up"]:
                    # Reset if form breaks
                    rep_state = "waiting"

        # Draw feedback
        feedback_text = get_feedback_text(left_knee_angle, right_knee_angle, torso_stable, standing_stable, rep_state)
        cv2.putText(image, feedback_text, (left_knee_pt[0] - 150, left_knee_pt[1] + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, feedback_color, 2)

    # Draw UI elements
    h, w, _ = image.shape

    # Draw instruction box
    instruction_text = get_exercise_instruction()
    draw_instruction_box(image, instruction_text)

    # Draw exercise info
    cv2.putText(image, f"Exercise: {exercise['name']}", (20, h - 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(image, f"Steps: {reps}/{target_reps}", (20, h - 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Draw progress bars
    if exercise_phase == "warmup" and warmup_start:
        warmup_progress = min(1.0, (current_time - warmup_start) / warmup_time)
        draw_progress_bar(image, warmup_progress, w - 250, 50, 200, 20, (0, 255, 255))
        cv2.putText(image, "Warm-up Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    elif exercise_phase == "rest" and rest_start:
        rest_progress = min(1.0, (current_time - rest_start) / rest_time)
        draw_progress_bar(image, rest_progress, w - 250, 50, 200, 20, (255, 255, 0))
        cv2.putText(image, "Rest Progress", (w - 250, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Draw body detection status
    if not body_detected:
        cv2.putText(image, "No body detected - Position yourself in front of camera",
                   (w//2 - 250, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Draw session statistics
    draw_session_stats(image)

    # Draw controls
    cv2.putText(image, "Controls: 's'=start, 'r'=restart, ESC=exit",
               (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.namedWindow("Marching in Place Exercise Assistant", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Marching in Place Exercise Assistant", cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
    cv2.imshow("Marching in Place Exercise Assistant", image)

    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s') and exercise_phase == "setup":
        exercise_phase = "warmup"
        warmup_start = None
    elif key == ord('r'):
        # Restart exercise
        exercise_phase = "setup"
        reps = 0
        rep_state = "waiting"
        last_leg = None
        warmup_start = None
        rest_start = None

cap.release()
cv2.destroyAllWindows()
