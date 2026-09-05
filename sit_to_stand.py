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
    "sit_to_stand": {
        "name": "Sit-to-Stand",
        "description": "Stand up slowly from a chair without using hands",
        "detailed_instruction": "Sit on a chair with feet flat on floor. Slowly stand up keeping back straight, then sit back down. No hands allowed. Aim for controlled movement.",
        "target_angles": {"sitting": (80, 100), "standing": (160, 175)},
        "color": (0, 255, 0),  # Green
        "exercise_type": "sit_to_stand"
    }
}

# Current exercise settings
current_exercise = "sit_to_stand"
target_reps = 5
reps = 0
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

# Rep tracking for sit-to-stand
rep_state = "waiting"  # waiting, sitting, standing, rep_complete

# Open camera
cap = cv2.VideoCapture(0)

# Debug counter
frame_count = 0
start_time = time.time()

def calculate_knee_angle(hip, knee, ankle):
    """Calculate knee angle between thigh and calf"""
    thigh = np.array([knee[0] - hip[0], knee[1] - hip[1]])
    calf = np.array([ankle[0] - knee[0], ankle[1] - ankle[1]])
    cos_angle = np.dot(thigh, calf) / (np.linalg.norm(thigh) * np.linalg.norm(calf))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle

def calculate_torso_angle(shoulder, hip):
    """Calculate torso angle from vertical"""
    # Torso vector from shoulder to hip
    torso = np.array([hip[0] - shoulder[0], hip[1] - shoulder[1]])
    vertical = np.array([0, -1])  # Upward vertical
    cos_angle = np.dot(torso, vertical) / (np.linalg.norm(torso) * np.linalg.norm(vertical))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle

def check_knee_symmetry(left_knee, right_knee):
    """Check if knees are aligned (not collapsing inward)"""
    # Simple check: if knees are roughly at same x position
    diff = abs(left_knee[0] - right_knee[0])
    return diff < 50  # pixels threshold

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

def get_feedback_text(knee_angle, torso_angle, symmetry, rep_state):
    """Get feedback text based on current form"""
    exercise = EXERCISES[current_exercise]
    sitting_min, sitting_max = exercise["target_angles"]["sitting"]
    standing_min, standing_max = exercise["target_angles"]["standing"]

    if rep_state == "waiting":
        return "Sit on chair with feet flat. Get ready to stand up slowly."

    if knee_angle >= sitting_min and knee_angle <= sitting_max:
        if torso_angle > 20:
            return "Keep your back straight - don't lean forward"
        elif not symmetry:
            return "Keep knees aligned - don't let them collapse inward"
        else:
            return "Good sitting position. Now stand up slowly without using hands."
    elif knee_angle >= standing_min and knee_angle <= standing_max:
        if torso_angle > 15:
            return "Keep your back straight while standing"
        elif not symmetry:
            return "Keep knees aligned while standing"
        else:
            return "Good standing position. Now sit back down slowly."
    else:
        if knee_angle < sitting_min:
            return "Bend knees more to sit properly"
        else:
            return "Stand up straighter"

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]

    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\nSit on a chair facing the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your legs and practice\nstanding up slowly for {warmup_time} seconds.\n\nFocus on controlled movements."
    elif exercise_phase == "exercise":
        if rep_state == "waiting":
            return f"Ready! Sit properly on the chair.\n\nWait for 'Good sitting position' feedback,\nthen stand up slowly."
        elif rep_state == "sitting":
            return f"Good! Now stand up slowly without using hands.\n\nKeep back straight and knees aligned."
        elif rep_state == "standing":
            return f"Excellent! Now sit back down slowly.\n\nControl the descent."
        elif rep_state == "rep_complete":
            return f"Great repetition! Rest briefly.\nRep {reps}/{target_reps} complete!"
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your legs gently."
    elif exercise_phase == "complete":
        return f"🎉 Exercise Complete! 🎉\nYou did {reps} reps of {exercise['name']}\nPress 'r' to restart"
    else:
        return "Press 's' to start exercise"

# Global variables for timing
warmup_start = None
rest_start = None

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Camera read failed, retrying...")
            time.sleep(0.1)
            continue

        frame_count += 1
        elapsed_time = time.time() - start_time
        if frame_count % 30 == 0:  # Print every 30 frames (~1 second at 30fps)
            print(f"Frame {frame_count} - Elapsed: {elapsed_time:.1f}s - Phase: {exercise_phase}")

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

            # Calculate angles
            left_knee_angle = calculate_knee_angle(left_hip_pt, left_knee_pt, left_ankle_pt)
            right_knee_angle = calculate_knee_angle(right_hip_pt, right_knee_pt, right_ankle_pt)
            knee_angle = (left_knee_angle + right_knee_angle) / 2  # Average

            left_torso_angle = calculate_torso_angle(left_shoulder_pt, left_hip_pt)
            right_torso_angle = calculate_torso_angle(right_shoulder_pt, right_hip_pt)
            torso_angle = (left_torso_angle + right_torso_angle) / 2

            symmetry = check_knee_symmetry(left_knee_pt, right_knee_pt)

            # Draw pose landmarks
            mp_drawing.draw_landmarks(image, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

            # Draw angle indicators
            cv2.putText(image, f"Knee Angle: {int(knee_angle)}°", (left_knee_pt[0] - 50, left_knee_pt[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
            cv2.putText(image, f"Torso Angle: {int(torso_angle)}°", (left_shoulder_pt[0] - 50, left_shoulder_pt[1] - 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

            # Exercise logic for sit-to-stand
            if exercise_phase == "exercise":
                sitting_min, sitting_max = exercise["target_angles"]["sitting"]
                standing_min, standing_max = exercise["target_angles"]["standing"]

                is_sitting = sitting_min <= knee_angle <= sitting_max and torso_angle <= 20 and symmetry
                is_standing = standing_min <= knee_angle <= standing_max and torso_angle <= 15 and symmetry

                if is_sitting:
                    feedback_color = (0, 255, 0)  # Green for correct
                    if rep_state == "waiting":
                        rep_state = "sitting"
                    elif rep_state == "standing":
                        # Completed rep
                        reps += 1
                        rep_state = "rep_complete"
                        if reps >= target_reps:
                            exercise_phase = "complete"
                            update_session_stats()
                        else:
                            exercise_phase = "rest"
                            rest_start = None
                elif is_standing:
                    feedback_color = (0, 255, 0)  # Green for correct
                    if rep_state == "sitting":
                        rep_state = "standing"
                else:
                    feedback_color = (0, 0, 255)  # Red for incorrect
                    if rep_state in ["sitting", "standing"]:
                        # Reset if form breaks
                        rep_state = "waiting"

            # Draw feedback
            feedback_text = get_feedback_text(knee_angle, torso_angle, symmetry, rep_state)
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

        cv2.namedWindow("Sit-to-Stand Exercise Assistant", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Sit-to-Stand Exercise Assistant", cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        cv2.imshow("Sit-to-Stand Exercise Assistant", image)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("ESC key pressed - exiting")
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

except Exception as e:
    print(f"Exception occurred: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("Loop ended, releasing camera...")
    cap.release()
    cv2.destroyAllWindows()
    print("Script finished")
