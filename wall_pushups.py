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
    "wall_pushups": {
        "name": "Wall Push-Ups",
        "description": "Push against wall with bent elbows",
        "detailed_instruction": "Stand facing a wall with hands at shoulder height. Bend elbows to lean toward wall, then push back to start. Keep body straight. Aim for controlled movement.",
        "target_angles": {"down": (50, 70), "up": (150, 170)},
        "color": (255, 0, 0),  # Blue
        "exercise_type": "wall_pushups"
    }
}

# Current exercise settings
current_exercise = "wall_pushups"
target_reps = 10
reps = 0
session_start_time = time.time()
exercise_phase = "setup"  # setup, warmup, exercise, rest, complete
warmup_time = 10  # seconds
rest_time = 2  # seconds between reps

# Session tracking
session_stats = {
    "total_exercises": 0,
    "total_reps": 0,
    "session_duration": 0,
    "exercises_completed": []
}

# Rep tracking for wall push-ups
rep_state = "waiting"  # waiting, up, down, rep_complete

# Open camera
cap = cv2.VideoCapture(0)

def calculate_elbow_angle(shoulder, elbow, wrist):
    """Calculate elbow angle between upper arm and forearm"""
    upper_arm = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
    forearm = np.array([wrist[0] - elbow[0], wrist[1] - elbow[1]])
    cos_angle = np.dot(upper_arm, forearm) / (np.linalg.norm(upper_arm) * np.linalg.norm(forearm))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle

def calculate_body_straightness(shoulder, hip):
    """Calculate if body is straight (shoulder-hip alignment)"""
    # Body vector from shoulder to hip
    body = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
    vertical = np.array([0, 1])  # Downward vertical
    cos_angle = np.dot(body, vertical) / (np.linalg.norm(body) * np.linalg.norm(vertical))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle < 20  # Consider straight if angle < 20°

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
    cv2.putText(image, f"Total Reps: {session_stats['total_reps']}", (w - 280, h - 80),
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

def get_feedback_text(elbow_angle, body_straight, rep_state):
    """Get feedback text based on current form"""
    exercise = EXERCISES[current_exercise]
    down_min, down_max = exercise["target_angles"]["down"]
    up_min, up_max = exercise["target_angles"]["up"]

    if rep_state == "waiting":
        return "Stand facing wall with hands at shoulder height. Get ready to bend elbows."

    if not body_straight:
        return "Keep your body straight - don't sag hips or arch back"

    if elbow_angle >= up_min and elbow_angle <= up_max:
        return "Good starting position. Now bend your elbows slowly."
    elif elbow_angle >= down_min and elbow_angle <= down_max:
        return "Good! Now push back to start position."
    else:
        if elbow_angle > up_max:
            return "Bend elbows more toward the wall"
        else:
            return "Push back to straighten arms"

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]

    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\nStand facing a wall with arms extended."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your arms and practice\nslow push-up movements for {warmup_time} seconds.\n\nFocus on controlled movements."
    elif exercise_phase == "exercise":
        if rep_state == "waiting":
            return f"Ready! Stand with arms straight.\n\nWait for 'Good starting position' feedback,\nthen bend elbows slowly."
        elif rep_state == "up":
            return f"Good! Now bend your elbows to lean toward the wall.\n\nKeep body straight."
        elif rep_state == "down":
            return f"Excellent! Now push back to straighten arms.\n\nControl the movement."
        elif rep_state == "rep_complete":
            return f"Great repetition! Rest briefly.\nRep {reps}/{target_reps} complete!"
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your arms gently."
    elif exercise_phase == "complete":
        return f"🎉 Exercise Complete! 🎉\nYou did {reps} reps of {exercise['name']}\nPress 'r' to restart"
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

        # Get key points for both arms
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

        # Convert to pixel coordinates
        left_shoulder_pt = (int(w * left_shoulder.x), int(h * left_shoulder.y))
        left_elbow_pt = (int(w * left_elbow.x), int(h * left_elbow.y))
        left_wrist_pt = (int(w * left_wrist.x), int(h * left_wrist.y))
        right_shoulder_pt = (int(w * right_shoulder.x), int(h * right_shoulder.y))
        right_elbow_pt = (int(w * right_elbow.x), int(h * right_elbow.y))
        right_wrist_pt = (int(w * right_wrist.x), int(h * right_wrist.y))
        left_hip_pt = (int(w * left_hip.x), int(h * left_hip.y))
        right_hip_pt = (int(w * right_hip.x), int(h * right_hip.y))

        # Calculate angles
        left_elbow_angle = calculate_elbow_angle(left_shoulder_pt, left_elbow_pt, left_wrist_pt)
        right_elbow_angle = calculate_elbow_angle(right_shoulder_pt, right_elbow_pt, right_wrist_pt)
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2  # Average

        left_body_straight = calculate_body_straightness(left_shoulder_pt, left_hip_pt)
        right_body_straight = calculate_body_straightness(right_shoulder_pt, right_hip_pt)
        body_straight = left_body_straight and right_body_straight

        # Draw pose landmarks
        mp_drawing.draw_landmarks(image, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

        # Draw angle indicators
        cv2.putText(image, f"Elbow Angle: {int(elbow_angle)}°", (left_elbow_pt[0] - 50, left_elbow_pt[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

        # Exercise logic for wall push-ups
        if exercise_phase == "exercise":
            down_min, down_max = exercise["target_angles"]["down"]
            up_min, up_max = exercise["target_angles"]["up"]

            is_up = up_min <= elbow_angle <= up_max and body_straight
            is_down = down_min <= elbow_angle <= down_max and body_straight

            if is_up:
                feedback_color = (0, 255, 0)  # Green for correct
                if rep_state == "waiting":
                    rep_state = "up"
                elif rep_state == "down":
                    # Completed rep
                    reps += 1
                    rep_state = "rep_complete"
                    if reps >= target_reps:
                        exercise_phase = "complete"
                        update_session_stats()
                    else:
                        exercise_phase = "rest"
                        rest_start = None
            elif is_down:
                feedback_color = (0, 255, 0)  # Green for correct
                if rep_state == "up":
                    rep_state = "down"
            else:
                feedback_color = (0, 0, 255)  # Red for incorrect
                if rep_state in ["up", "down"]:
                    # Reset if form breaks
                    rep_state = "waiting"

        # Draw feedback
        feedback_text = get_feedback_text(elbow_angle, body_straight, rep_state)
        cv2.putText(image, feedback_text, (left_elbow_pt[0] - 150, left_elbow_pt[1] + 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, feedback_color, 2)

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

    cv2.namedWindow("Wall Push-Ups Exercise Assistant", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Wall Push-Ups Exercise Assistant", cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
    cv2.imshow("Wall Push-Ups Exercise Assistant", image)

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
        warmup_start = None
        rest_start = None

cap.release()
cv2.destroyAllWindows()
