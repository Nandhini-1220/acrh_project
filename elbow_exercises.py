import cv2
from shared_ui import ExerciseUI
ui_renderer = ExerciseUI()
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
    "elbow_flexion": {
        "name": "Elbow Flexion",
        "description": "Bend your elbow to bring your hand toward your shoulder",
        "detailed_instruction": "Slowly bend your elbow to bring your hand toward your shoulder. Keep your upper arm still, only move your forearm. Aim for 90-120 angle.",
        "target_angle_range": (90, 120),
        "hold_time": 5,
        "color": (0, 255, 0),  # Green
        "visual_cue": "Imagine doing a bicep curl without weights",
        "exercise_type": "flexion"
    },
    "elbow_extension": {
        "name": "Elbow Extension",
        "description": "Straighten your elbow to extend your arm",
        "detailed_instruction": "Slowly straighten your elbow to extend your arm. Keep your upper arm still, only move your forearm. Aim for 0-30 angle (straight arm).",
        "target_angle_range": (0, 30),
        "hold_time": 5,
        "color": (255, 0, 0),  # Blue
        "visual_cue": "Imagine pushing something away from you",
        "exercise_type": "extension"
    },
    "elbow_rotation_inward": {
        "name": "Elbow Rotation (Inward)",
        "description": "Rotate your forearm inward (pronation)",
        "detailed_instruction": "Keep your elbow bent at 90 and rotate your forearm inward so your palm faces down. Keep your upper arm still.",
        "target_angle_range": (0, 90),
        "hold_time": 3,
        "color": (255, 165, 0),  # Orange
        "visual_cue": "Imagine turning a screwdriver inward",
        "exercise_type": "rotation"
    },
    "elbow_rotation_outward": {
        "name": "Elbow Rotation (Outward)",
        "description": "Rotate your forearm outward (supination)",
        "detailed_instruction": "Keep your elbow bent at 90 and rotate your forearm outward so your palm faces up. Keep your upper arm still.",
        "target_angle_range": (0, 90),
        "hold_time": 3,
        "color": (128, 0, 128),  # Purple
        "visual_cue": "Imagine turning a screwdriver outward",
        "exercise_type": "rotation"
    },
    "elbow_circles": {
        "name": "Elbow Circles",
        "description": "Make circular movements with your bent elbow",
        "detailed_instruction": "Keep your elbow bent at 90 and make slow circular movements with your forearm. Keep your upper arm stable.",
        "target_angle_range": (0, 360),
        "hold_time": 2,
        "color": (0, 255, 128),  # Light Green
        "visual_cue": "Imagine drawing circles in the air with your forearm",
        "exercise_type": "circles"
    }
}

import os
# Current exercise settings
exercise_key = os.environ.get("EXERCISE_KEY", "elbow_flexion")
print("Running Exercise:", exercise_key)
if exercise_key not in EXERCISES:
    exercise_key = "elbow_flexion"
    print("Warning: Unknown exercise, using default:", exercise_key)

current_exercise = exercise_key
target_reps = 2
reps = 0
hold_time = EXERCISES[current_exercise]["hold_time"]
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "exercise"  # setup, warmup, exercise, rest, complete
warmup_time = 10  # seconds
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

def calculate_elbow_angle(shoulder, elbow, wrist):
    """Calculate elbow angle between upper arm and forearm"""
    # Calculate vectors
    upper_arm = np.array([elbow[0] - shoulder[0], elbow[1] - shoulder[1]])
    forearm = np.array([wrist[0] - elbow[0], wrist[1] - elbow[1]])
    
    # Calculate angle between vectors
    cos_angle = np.dot(upper_arm, forearm) / (np.linalg.norm(upper_arm) * np.linalg.norm(forearm))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Avoid numerical errors
    angle = math.degrees(math.acos(cos_angle))
    
    return angle

def calculate_forearm_rotation_angle(elbow, wrist, hand_landmarks):
    """Calculate forearm rotation angle based on hand orientation"""
    if hand_landmarks is None:
        return 0
    
    # Get hand landmarks for rotation calculation
    # Use wrist, middle finger MCP, and index finger MCP for rotation
    wrist_pt = hand_landmarks.landmark[0]
    middle_mcp = hand_landmarks.landmark[9]
    index_mcp = hand_landmarks.landmark[5]
    
    # Convert to pixel coordinates
    h, w = 480, 640  # Default dimensions
    wrist_coords = (int(w * wrist_pt.x), int(h * wrist_pt.y))
    middle_coords = (int(w * middle_mcp.x), int(h * middle_mcp.y))
    index_coords = (int(w * index_mcp.x), int(h * index_mcp.y))
    
    # Calculate rotation angle
    hand_angle = math.degrees(math.atan2(middle_coords[1] - wrist_coords[1], middle_coords[0] - wrist_coords[0]))
    finger_angle = math.degrees(math.atan2(index_coords[1] - wrist_coords[1], index_coords[0] - wrist_coords[0]))
    
    rotation_angle = hand_angle - finger_angle
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

def get_directional_guidance(angle, exercise_phase):
    """Provide directional guidance based on exercise type and current angle"""
    if exercise_phase != "exercise":
        return ""
    
    exercise = EXERCISES[current_exercise]
    min_angle, max_angle = exercise["target_angle_range"]
    
    if current_exercise == "elbow_flexion":
        if angle > 150:
            return "Bend your elbow MORE - bring hand toward shoulder"
        elif angle > max_angle:
            return f"Good! Hold steady at {int(angle)} - you should feel muscle engagement"
        elif min_angle <= angle <= max_angle:
            return f"PERFECT! Hold at {int(angle)} - you should feel your bicep working!"
        elif angle < min_angle:
            return f"Great bend! Hold steady at {int(angle)}"
        else:
            return "Ease back slightly - that's too much bend"
    
    elif current_exercise == "elbow_extension":
        if angle > 30:
            return "Straighten your elbow MORE - extend your arm"
        elif angle > max_angle:
            return f"Good extension! Hold steady at {int(angle)}"
        elif min_angle <= angle <= max_angle:
            return f"PERFECT! Hold at {int(angle)} - arm is straight!"
        elif angle < min_angle:
            return f"Excellent! Hold at {int(angle)} - full extension!"
        else:
            return "Ease back slightly - don't hyperextend"
    
    elif current_exercise in ["elbow_rotation_inward", "elbow_rotation_outward"]:
        if angle < 30:
            return "Rotate your forearm MORE - turn your hand"
        elif min_angle <= angle <= max_angle:
            return f"PERFECT! Hold at {int(angle)} - good rotation!"
        else:
            return f"Good rotation! Hold steady at {int(angle)}"
    
    return ""

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    
    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPosition your arm in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your elbow in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nStart with small bends, then gentle stretches."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "elbow_flexion":
                return f"Ready! Bend your elbow to bring hand toward shoulder\n\n{exercise['visual_cue']}\n\nHold when you reach 90-120 angle."
            elif current_exercise == "elbow_extension":
                return f"Ready! Straighten your elbow to extend your arm\n\n{exercise['visual_cue']}\n\nHold when you reach 0-30 angle."
            elif current_exercise == "elbow_rotation_inward":
                return f"Ready! Rotate your forearm INWARD (palm down)\n\n{exercise['visual_cue']}\n\nKeep elbow bent at 90."
            elif current_exercise == "elbow_rotation_outward":
                return f"Ready! Rotate your forearm OUTWARD (palm up)\n\n{exercise['visual_cue']}\n\nKeep elbow bent at 90."
            elif current_exercise == "elbow_circles":
                return f"Ready! Make CIRCLES with your forearm\n\n{exercise['visual_cue']}\n\nKeep elbow bent at 90."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Hold steady! {remaining}s remaining\nRep {reps + 1}/{target_reps}\n\nYou should feel muscle engagement - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps} complete!\n\nLet your arm return to neutral position."
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your arm gently during rest."
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
    result = pose.process(rgb)
    
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

    # Pose detection and exercise logic
    arm_detected = False
    if result.pose_landmarks:
        arm_detected = True
        
        # Extract key points for elbow angle calculation
        landmarks = result.pose_landmarks.landmark
        
        # Get shoulder, elbow, and wrist points (using right arm as default)
        shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
        
        # Convert to pixel coordinates
        h, w, _ = image.shape
        shoulder_pt = (int(w * shoulder.x), int(h * shoulder.y))
        elbow_pt = (int(w * elbow.x), int(h * elbow.y))
        wrist_pt = (int(w * wrist.x), int(h * wrist.y))
        
        # Calculate elbow angle
        elbow_angle = calculate_elbow_angle(shoulder_pt, elbow_pt, wrist_pt)
        
        # Draw pose landmarks with exercise-specific color
        mp_drawing.draw_landmarks(image, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))
        
        # Draw angle indicator
        cv2.putText(image, f"Elbow Angle: {int(elbow_angle)}", (elbow_pt[0] - 50, elbow_pt[1] - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
        
        # Draw directional guidance
        directional_guidance = get_directional_guidance(elbow_angle, exercise_phase)
        if directional_guidance:
            # Choose color based on guidance type
            if "PERFECT" in directional_guidance:
                guidance_color = (0, 255, 0)  # Green
            elif "Bend" in directional_guidance or "Straighten" in directional_guidance or "Rotate" in directional_guidance:
                guidance_color = (255, 255, 0)  # Yellow
            else:
                guidance_color = (255, 255, 255)  # White
            
            cv2.putText(image, directional_guidance, (elbow_pt[0] - 150, elbow_pt[1] + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, guidance_color, 2)
        
        # Draw large directional arrow
        if exercise_phase == "exercise":
            h, w, _ = image.shape
            arrow_center = (w // 2, h // 2 + 100)
            arrow_size = 80
            
            if current_exercise == "elbow_flexion":
                # Curl arrow (upward curve)
                cv2.arrowedLine(image, 
                               (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2),
                               (arrow_center[0], arrow_center[1] - arrow_size//2),
                               (255, 255, 0), 8, tipLength=0.3)
                cv2.putText(image, "BEND ELBOW", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
            elif current_exercise == "elbow_extension":
                # Straight arrow
                cv2.arrowedLine(image, 
                               (arrow_center[0] - arrow_size//2, arrow_center[1]),
                               (arrow_center[0] + arrow_size//2, arrow_center[1]),
                               (255, 255, 0), 8, tipLength=0.3)
                cv2.putText(image, "STRAIGHTEN ARM", (arrow_center[0] - 80, arrow_center[1] + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
            elif current_exercise == "elbow_rotation_inward":
                # Inward rotation arrow
                cv2.arrowedLine(image, 
                               (arrow_center[0] + arrow_size//2, arrow_center[1] - arrow_size//2),
                               (arrow_center[0] - arrow_size//2, arrow_center[1] + arrow_size//2),
                               (255, 255, 0), 8, tipLength=0.3)
                cv2.putText(image, "ROTATE INWARD", (arrow_center[0] - 80, arrow_center[1] + arrow_size//2 + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
            elif current_exercise == "elbow_rotation_outward":
                # Outward rotation arrow
                cv2.arrowedLine(image, 
                               (arrow_center[0] - arrow_size//2, arrow_center[1] - arrow_size//2),
                               (arrow_center[0] + arrow_size//2, arrow_center[1] + arrow_size//2),
                               (255, 255, 0), 8, tipLength=0.3)
                cv2.putText(image, "ROTATE OUTWARD", (arrow_center[0] - 80, arrow_center[1] + arrow_size//2 + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
            elif current_exercise == "elbow_circles":
                # Circle arrow
                cv2.circle(image, arrow_center, arrow_size//2, (0, 255, 128), 8)
                cv2.putText(image, "MAKE CIRCLES", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 128), 3)
        
        # Draw target zone indicator
        if exercise_phase == "exercise":
            min_angle, max_angle = exercise["target_angle_range"]
            target_text = f"Target: {min_angle}-{max_angle}"
            cv2.putText(image, target_text, (elbow_pt[0] - 50, elbow_pt[1] + 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
            
            # Draw angle status indicator
            if min_angle <= elbow_angle <= max_angle:
                status_text = "✓ IN TARGET ZONE"
                status_color = (0, 255, 0)
            elif elbow_angle < min_angle:
                if current_exercise == "elbow_flexion":
                    status_text = "↑ BEND MORE"
                elif current_exercise == "elbow_extension":
                    status_text = "→ STRAIGHTEN MORE"
                else:
                    status_text = "↑ MOVE MORE"
                status_color = (255, 255, 0)
            else:
                if current_exercise == "elbow_flexion":
                    status_text = "↓ EASE BACK"
                elif current_exercise == "elbow_extension":
                    status_text = "← EASE BACK"
                else:
                    status_text = "↓ EASE BACK"
                status_color = (255, 0, 0)
            
            cv2.putText(image, status_text, (elbow_pt[0] - 60, elbow_pt[1] + 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
        
        # Exercise logic
        if exercise_phase == "exercise":
            min_angle, max_angle = exercise["target_angle_range"]
            if min_angle <= elbow_angle <= max_angle:  # In target range
                if start_hold is None:
                    start_hold = current_time
                    paused_time = 0
                    pause_start = None
                else:
                    # Timer is running
                    elapsed = current_time - start_hold + paused_time
                    if elapsed >= hold_time:
                        # Rep completed
                        reps += 1
                        start_hold = None
                        paused_time = 0
                        if reps >= target_reps:
                            exercise_phase = "complete"
                            update_session_stats()
                        else:
                            exercise_phase = "rest"
                            rest_start = None
            else:
                # Out of position
                if start_hold is not None:
                    if pause_start is None:
                        pause_start = current_time
                    elif current_time - pause_start <= 1:  # Grace period
                        continue
                    else:
                        # Reset if out of position too long
                        start_hold = None
                        paused_time = 0
                        pause_start = None

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
        exercise_phase = "exercise"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        rotation_start_angle = None
        rotation_completed_degrees = 0
    elif key == ord('r'):
        # Restart current exercise
        exercise_phase = "exercise"
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

