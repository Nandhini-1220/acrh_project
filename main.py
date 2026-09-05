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
        "color": (255, 0, 0),  # Blue
        "visual_cue": "Imagine pulling your hand back toward your forearm",
        "exercise_type": "bend"
    },
    "radial_deviation": {
        "name": "Radial Deviation",
        "description": "Bend your wrist toward your thumb side",
        "detailed_instruction": "Bend your wrist toward your thumb side as far as comfortable - aim for 10-30° angle. Keep your forearm still, only move your wrist.",
        "target_angle_range": (10, 30),
        "hold_time": 5,
        "color": (0, 255, 255),  # Yellow
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

# Current exercise settings
current_exercise = "wrist_flexion"
target_reps = 5
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

# Open camera
cap = cv2.VideoCapture(0)

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
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

def draw_help_screen(image):
    """Draw help screen with instructions"""
    h, w, _ = image.shape
    
    # Semi-transparent overlay
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
    
    # Help content
    help_text = [
        "PHYSIOTHERAPY EXERCISE ASSISTANT",
        "",
        "EXERCISES:",
        "• Wrist Flexion - Bend wrist forward",
        "• Wrist Extension - Bend wrist backward", 
        "• Radial Deviation - Bend toward thumb",
        "• Ulnar Deviation - Bend toward pinky",
        "",
        "CONTROLS:",
        "• 's' - Start exercise",
        "• 'd' - Demo proper range of motion",
        "• 'n' - Next exercise",
        "• 'r' - Restart current exercise",
        "• 'h' - Toggle this help",
        "• ESC - Exit program",
        "",
        "SAFETY TIPS:",
        "• Always warm up before exercising",
        "• Stop if you feel pain",
        "• Keep movements slow and controlled",
        "• Maintain proper form",
        "",
        "Press 'h' to close this help screen"
    ]
    
    # Draw help text
    y_start = 50
    for i, line in enumerate(help_text):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 0.8 if i == 0 else 0.6
        thickness = 2 if i == 0 else 1
        cv2.putText(image, line, (50, y_start + i * 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_demo_mode(image):
    """Draw demo mode showing proper range of motion"""
    h, w, _ = image.shape
    exercise = EXERCISES[current_exercise]
    
    # Semi-transparent overlay
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
    
    # Demo content
    demo_text = [
        f"DEMO: {exercise['name']}",
        "",
        "DIRECTIONAL GUIDANCE:",
        f"• {exercise['detailed_instruction']}",
        "",
        "STEP-BY-STEP:",
        f"• Start: 0° (neutral position)",
        f"• Move: {exercise['visual_cue']}",
        f"• Target: {exercise['target_angle_range'][0]}-{exercise['target_angle_range'][1]}°",
        f"• Hold: 5 seconds in target zone",
        "",
        "WHAT YOU'LL SEE:",
        "• 'Bend DOWN' - move palm toward floor",
        "• 'Bend UP' - move back of hand toward ceiling", 
        "• 'Bend RIGHT' - move toward thumb side",
        "• 'Bend LEFT' - move toward pinky side",
        "• 'PERFECT!' - when in target zone",
        "",
        "Press 'd' to close this demo"
    ]
    
    # Draw demo text
    y_start = 100
    for i, line in enumerate(demo_text):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 0.8 if i == 0 else 0.6
        thickness = 2 if i == 0 else 1
        cv2.putText(image, line, (50, y_start + i * 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def get_directional_guidance(angle, exercise_phase):
    """Provide directional guidance based on exercise type and current angle"""
    if exercise_phase != "exercise":
        return ""
    
    exercise = EXERCISES[current_exercise]
    min_angle, max_angle = exercise["target_angle_range"]
    
    if angle < 30:
        if current_exercise == "wrist_flexion":
            return "Bend your wrist DOWN (palm toward floor)"
        elif current_exercise == "wrist_extension":
            return "Bend your wrist UP (back of hand toward ceiling)"
        elif current_exercise == "radial_deviation":
            return "Bend your wrist to the RIGHT (toward your thumb)"
        elif current_exercise == "ulnar_deviation":
            return "Bend your wrist to the LEFT (toward your pinky)"
    elif angle < min_angle:
        if current_exercise == "wrist_flexion":
            return f"Keep bending DOWN! You're at {int(angle)}° - need 60-90°"
        elif current_exercise == "wrist_extension":
            return f"Keep bending UP! You're at {int(angle)}° - need 60-90°"
        elif current_exercise == "radial_deviation":
            return f"Keep bending RIGHT! You're at {int(angle)}° - need 60-90°"
        elif current_exercise == "ulnar_deviation":
            return f"Keep bending LEFT! You're at {int(angle)}° - need 60-90°"
    elif angle <= max_angle:
        return f"PERFECT! Hold this position at {int(angle)}° - you should feel a stretch!"
    elif angle < 120:
        if current_exercise == "wrist_flexion":
            return f"Good stretch! Hold steady - ease back UP slightly if needed"
        elif current_exercise == "wrist_extension":
            return f"Good stretch! Hold steady - ease back DOWN slightly if needed"
        elif current_exercise == "radial_deviation":
            return f"Good stretch! Hold steady - ease back LEFT slightly if needed"
        elif current_exercise == "ulnar_deviation":
            return f"Good stretch! Hold steady - ease back RIGHT slightly if needed"
    else:
        if current_exercise == "wrist_flexion":
            return "Too much bend! Ease back UP toward neutral"
        elif current_exercise == "wrist_extension":
            return "Too much bend! Ease back DOWN toward neutral"
        elif current_exercise == "radial_deviation":
            return "Too much bend! Ease back LEFT toward neutral"
        elif current_exercise == "ulnar_deviation":
            return "Too much bend! Ease back RIGHT toward neutral"
    
    return ""

def get_form_feedback(angle, exercise_phase):
    """Provide form feedback based on angle and exercise type"""
    if exercise_phase != "exercise":
        return ""
    
    exercise = EXERCISES[current_exercise]
    min_angle, max_angle = exercise["target_angle_range"]
    
    if angle < 30:
        return "Start bending your wrist - aim for 60-90°"
    elif angle < min_angle:
        return f"Good start! Bend more - you're at {int(angle)}°, need 60-90°"
    elif angle <= max_angle:
        return f"Perfect! Hold at {int(angle)}° - you should feel a stretch!"
    elif angle < 120:
        return f"Good stretch! Hold steady at {int(angle)}°"
    else:
        return "Ease back slightly - that's too much bend"

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    
    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPress 'd' to see a demo of the proper range of motion.\nPosition your hand in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your wrist in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nStart with small circles, then gentle stretches."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise == "wrist_flexion":
                return f"Ready! Bend your wrist DOWN (palm toward floor)\n\n{exercise['visual_cue']}\n\nHold when you reach 60-90° angle."
            elif current_exercise == "wrist_extension":
                return f"Ready! Bend your wrist UP (back of hand toward ceiling)\n\n{exercise['visual_cue']}\n\nHold when you reach 60-90° angle."
            elif current_exercise == "radial_deviation":
                return f"Ready! Bend your wrist RIGHT (toward your thumb)\n\n{exercise['visual_cue']}\n\nHold when you reach 60-90° angle."
            elif current_exercise == "ulnar_deviation":
                return f"Ready! Bend your wrist LEFT (toward your pinky)\n\n{exercise['visual_cue']}\n\nHold when you reach 60-90° angle."
        else:
            elapsed = time.time() - start_hold + paused_time
            remaining = hold_time - int(elapsed)
            if remaining > 0:
                return f"Hold steady! {remaining}s remaining\nRep {reps + 1}/{target_reps}\n\nYou should feel a gentle stretch - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps} complete!\n\nLet your wrist return to neutral position."
    elif exercise_phase == "rest":
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps}\n\nShake out your wrist gently during rest."
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

# Rotation tracking variables
rotation_start_angle = None
rotation_completed_degrees = 0
last_angle = 0
rotation_direction = 1  # 1 for clockwise, -1 for counter-clockwise

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
            # Extract key points (wrist, index MCP, index tip)
            wrist = hand_landmarks.landmark[0]
            index_mcp = hand_landmarks.landmark[5]
            index_tip = hand_landmarks.landmark[8]

            # Convert to pixel coords
            h, w, _ = image.shape
            wrist_pt = (int(w*wrist.x), int(h*wrist.y))
            mcp_pt = (int(w*index_mcp.x), int(h*index_mcp.y))
            tip_pt = (int(w*index_tip.x), int(h*index_tip.y))

            # Calculate angle at wrist
            angle = calculate_angle(mcp_pt, wrist_pt, tip_pt)
            
            # Draw hand landmarks with exercise-specific color
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS, 
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))
            
            # Draw angle indicator
            cv2.putText(image, f"Angle: {int(angle)}°", (wrist_pt[0] - 50, wrist_pt[1] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
            
            # Draw directional guidance
            directional_guidance = get_directional_guidance(angle, exercise_phase)
            if directional_guidance:
                # Choose color based on guidance type
                if "PERFECT" in directional_guidance:
                    guidance_color = (0, 255, 0)  # Green
                elif "Keep bending" in directional_guidance or "Bend your wrist" in directional_guidance:
                    guidance_color = (255, 255, 0)  # Yellow
                elif "Too much" in directional_guidance:
                    guidance_color = (255, 0, 0)  # Red
                else:
                    guidance_color = (255, 255, 255)  # White
                
                cv2.putText(image, directional_guidance, (wrist_pt[0] - 150, wrist_pt[1] + 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, guidance_color, 2)
            
            # Draw large directional arrow
            if exercise_phase == "exercise" and angle < 60:
                h, w, _ = image.shape
                arrow_center = (w // 2, h // 2 + 100)
                arrow_size = 80
                
                if current_exercise == "wrist_flexion":
                    # Down arrow
                    cv2.arrowedLine(image, 
                                   (arrow_center[0], arrow_center[1] - arrow_size//2),
                                   (arrow_center[0], arrow_center[1] + arrow_size//2),
                                   (255, 255, 0), 8, tipLength=0.3)
                    cv2.putText(image, "BEND DOWN", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                elif current_exercise == "wrist_extension":
                    # Up arrow
                    cv2.arrowedLine(image, 
                                   (arrow_center[0], arrow_center[1] + arrow_size//2),
                                   (arrow_center[0], arrow_center[1] - arrow_size//2),
                                   (255, 255, 0), 8, tipLength=0.3)
                    cv2.putText(image, "BEND UP", (arrow_center[0] - 50, arrow_center[1] - arrow_size//2 - 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                elif current_exercise == "radial_deviation":
                    # Right arrow
                    cv2.arrowedLine(image, 
                                   (arrow_center[0] - arrow_size//2, arrow_center[1]),
                                   (arrow_center[0] + arrow_size//2, arrow_center[1]),
                                   (255, 255, 0), 8, tipLength=0.3)
                    cv2.putText(image, "BEND RIGHT", (arrow_center[0] + arrow_size//2 + 20, arrow_center[1] + 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                elif current_exercise == "ulnar_deviation":
                    # Left arrow
                    cv2.arrowedLine(image, 
                                   (arrow_center[0] + arrow_size//2, arrow_center[1]),
                                   (arrow_center[0] - arrow_size//2, arrow_center[1]),
                                   (255, 255, 0), 8, tipLength=0.3)
                    cv2.putText(image, "BEND LEFT", (arrow_center[0] - arrow_size//2 - 120, arrow_center[1] + 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
            
            # Draw target zone indicator
            if exercise_phase == "exercise":
                min_angle, max_angle = exercise["target_angle_range"]
                target_text = f"Target: {min_angle}-{max_angle}°"
                cv2.putText(image, target_text, (wrist_pt[0] - 50, wrist_pt[1] + 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                
                # Draw angle status indicator with directional guidance
                if min_angle <= angle <= max_angle:
                    status_text = "✓ IN TARGET ZONE"
                    status_color = (0, 255, 0)
                elif angle < min_angle:
                    if current_exercise == "wrist_flexion":
                        status_text = "↓ BEND DOWN MORE"
                    elif current_exercise == "wrist_extension":
                        status_text = "↑ BEND UP MORE"
                    elif current_exercise == "radial_deviation":
                        status_text = "→ BEND RIGHT MORE"
                    elif current_exercise == "ulnar_deviation":
                        status_text = "← BEND LEFT MORE"
                    else:
                        status_text = "↑ BEND MORE"
                    status_color = (255, 255, 0)
                else:
                    if current_exercise == "wrist_flexion":
                        status_text = "↑ EASE UP"
                    elif current_exercise == "wrist_extension":
                        status_text = "↓ EASE DOWN"
                    elif current_exercise == "radial_deviation":
                        status_text = "← EASE LEFT"
                    elif current_exercise == "ulnar_deviation":
                        status_text = "→ EASE RIGHT"
                    else:
                        status_text = "↓ EASE BACK"
                    status_color = (255, 0, 0)
                
                cv2.putText(image, status_text, (wrist_pt[0] - 60, wrist_pt[1] + 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
            
            # Exercise logic
            if exercise_phase == "exercise":
                min_angle, max_angle = exercise["target_angle_range"]
                if min_angle < angle < max_angle:  # In target range
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
        hold_progress = min(1.0, (current_time - start_hold + paused_time) / hold_time)
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
    
    # Draw help screen if enabled
    if show_help:
        draw_help_screen(image)
    
    # Draw demo mode if enabled
    if show_demo and exercise_phase == "setup":
        draw_demo_mode(image)
    
    # Draw controls
    cv2.putText(image, "Controls: 's'=start, 'd'=demo, 'n'=next exercise, 'r'=restart, 'h'=help, ESC=exit", 
               (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    cv2.imshow("Physiotherapy Exercise Assistant", image)
    
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
    elif key == ord('r'):
        # Restart current exercise
        exercise_phase = "setup"
        reps = 0
        start_hold = None
        paused_time = 0
        pause_start = None
        warmup_start = None
        rest_start = None
    elif key == ord('h'):
        # Show help
        show_help = not show_help
    elif key == ord('d') and exercise_phase == "setup":
        # Toggle demo mode
        show_demo = not show_demo
        if show_demo:
            demo_start = time.time()

cap.release()
cv2.destroyAllWindows()
