import cv2
import mediapipe as mp
import time
import math
import numpy as np
import os
import webbrowser

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

# Exercise order (includes both wrist and finger exercises)
EXERCISE_ORDER = [
    "wrist_flexion",
    "wrist_extension",
    "radial_deviation",
    "ulnar_deviation",
    "finger_spread",
    "thumb_opposition",
    "finger_taps",
    "finger_flexion"
]

# Per-exercise target reps
REPS_PER_EXERCISE = {
    "wrist_flexion": 2,
    "wrist_extension": 2,
    "finger_spread": 3,
    "thumb_opposition": 2,
    "finger_taps": 3,
    "finger_flexion": 3
}

# Current exercise settings
# Allow preselect via environment variable EXERCISE_KEY
env_selected = os.environ.get("EXERCISE_KEY")
if env_selected in EXERCISES:
    current_exercise = env_selected
else:
    current_exercise = EXERCISE_ORDER[0]
default_target_reps = 2
reps = 0
hold_time = EXERCISES[current_exercise]["hold_time"]
start_hold = None
paused_time = 0
pause_start = None
session_start_time = time.time()
exercise_phase = "setup"  # setup, warmup, exercise, rest, complete
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

# Game state (for gamified experience)
score = 0
streak = 0
level = 1
last_rep_time = None
combo_window_sec = 6
exercise_points_earned = 0

# Open camera
cap = cv2.VideoCapture(0)

# Make the display window larger and resizable so all text fits
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("Physiotherapy Exercise Assistant", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Physiotherapy Exercise Assistant", 1600, 900)

def calculate_angle(a, b, c):
    """Calculate angle between three points"""
    ang = math.degrees(
        math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0])
    )
    return abs(ang)

def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

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

def draw_reference_skeleton(image, wrist_pt, hand_landmarks, color=(255, 255, 255), thickness=4):
    """Draw white reference skeleton for wrist flexion exercise.
    
    Args:
        image: The image to draw on
        wrist_pt: Tuple (x, y) of wrist position
        hand_landmarks: MediaPipe hand landmarks (to calculate hand width)
        color: Color of the reference skeleton (white by default)
        thickness: Line thickness
    """
    # Get image dimensions
    h, w, _ = image.shape
    
    # Extract Index MCP (landmark 5) and Pinky MCP (landmark 17) positions
    index_mcp = hand_landmarks.landmark[5]
    pinky_mcp = hand_landmarks.landmark[17]
    
    index_mcp_pt = (int(w * index_mcp.x), int(h * index_mcp.y))
    pinky_mcp_pt = (int(w * pinky_mcp.x), int(h * pinky_mcp.y))
    
    # Calculate hand width using Euclidean distance
    hand_width = calculate_distance(index_mcp_pt, pinky_mcp_pt)
    
    # Compute scaling factor
    scale = hand_width * 0.8
    
    # Calculate reference points based on wrist position and scale
    # ref_index = (wrist_x + scale, wrist_y - scale)
    # ref_pinky = (wrist_x - scale, wrist_y - scale)
    wrist_x, wrist_y = wrist_pt
    ref_index_pt = (int(wrist_x + scale), int(wrist_y - scale))
    ref_pinky_pt = (int(wrist_x - scale), int(wrist_y - scale))
    
    # Draw reference points as circles with radius 8
    cv2.circle(image, ref_index_pt, 8, color, -1)
    cv2.circle(image, ref_pinky_pt, 8, color, -1)
    cv2.circle(image, wrist_pt, 8, color, -1)
    
    # Draw lines: wrist → ref_index, wrist → ref_pinky
    cv2.line(image, wrist_pt, ref_index_pt, color, thickness)
    cv2.line(image, wrist_pt, ref_pinky_pt, color, thickness)

def calculate_alignment_error(user_index_mcp_pt, wrist_pt, hand_landmarks):
    """Calculate alignment error between user's index MCP and reference position.
    
    Args:
        user_index_mcp_pt: Tuple (x, y) of user's index MCP position
        wrist_pt: Tuple (x, y) of wrist position
        hand_landmarks: MediaPipe hand landmarks (to calculate hand width)
        
    Returns:
        Float value representing the Euclidean distance error
    """
    # Get image dimensions
    h, w, _ = [720, 1280, 3]  # Default dimensions, will be overridden by actual image
    
    # Extract Index MCP (landmark 5) and Pinky MCP (landmark 17) positions
    index_mcp = hand_landmarks.landmark[5]
    pinky_mcp = hand_landmarks.landmark[17]
    
    index_mcp_pt = (int(w * index_mcp.x), int(h * index_mcp.y))
    pinky_mcp_pt = (int(w * pinky_mcp.x), int(h * pinky_mcp.y))
    
    # Calculate hand width using Euclidean distance
    hand_width = calculate_distance(index_mcp_pt, pinky_mcp_pt)
    
    # Compute scaling factor
    scale = hand_width * 0.8
    
    # Calculate dynamic reference position: ref_index = (wrist_x + scale, wrist_y - scale)
    wrist_x, wrist_y = wrist_pt
    ref_index_pt = (int(wrist_x + scale), int(wrist_y - scale))
    
    # Calculate Euclidean distance between user's index MCP and reference
    error = calculate_distance(user_index_mcp_pt, ref_index_pt)
    
    return error

def draw_alignment_feedback(image, error, wrist_pt, threshold=30):
    """Draw alignment feedback text based on error value.
    
    Args:
        image: The image to draw on
        error: The alignment error value
        wrist_pt: Tuple (x, y) of wrist position
        threshold: Error threshold for good alignment
    """
    if error < threshold:
        # Good alignment - show green text
        feedback_text = "GOOD ALIGNMENT"
        color = (0, 255, 0)  # Green
    else:
        # Poor alignment - show red text
        feedback_text = "ADJUST WRIST POSITION"
        color = (0, 0, 255)  # Red
    
    # Draw feedback text near wrist position
    cv2.putText(image, feedback_text, (wrist_pt[0] - 80, wrist_pt[1] + 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

def draw_reference_instruction(image, y_offset=50):
    """Draw instruction text at the top of the screen.
    
    Args:
        image: The image to draw on
        y_offset: Y position for the text
    """
    instruction_text = "Match the white skeleton and hold for 5 seconds."
    
    # Get text size
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    (text_width, text_height), _ = cv2.getTextSize(instruction_text, font, font_scale, thickness)
    
    h, w, _ = image.shape
    x = (w - text_width) // 2  # Center horizontally
    
    # Draw background rectangle for better visibility
    padding = 10
    cv2.rectangle(image, (x - padding, y_offset - text_height - padding), 
                  (x + text_width + padding, y_offset + padding), (0, 0, 0), -1)
    
    # Draw text
    cv2.putText(image, instruction_text, (x, y_offset), font, font_scale, (255, 255, 255), thickness)

def draw_progress_bar(image, progress, x, y, width, height, color):
    """Draw a progress bar"""
    # Background
    cv2.rectangle(image, (x, y), (x + width, y + height), (50, 50, 50), -1)
    # Progress
    progress_width = int(width * progress)
    cv2.rectangle(image, (x, y), (x + progress_width, y + height), color, -1)
    # Border
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

def draw_angle_progress_bar(image, current_angle, target_min, target_max, x, y, width, height):
    """Draw progress bar for angle with color based on closeness to target"""
    # Calculate progress and color
    tolerance = 20  # degrees tolerance for partial progress

    if target_min <= current_angle <= target_max:
        progress = 1.0
        color = (0, 255, 0)  # Green - target reached
    elif current_angle < target_min:
        distance = target_min - current_angle
        progress = max(0.0, 1.0 - (distance / tolerance))
        if progress > 0.5:
            color = (0, 255, 255)  # Yellow - close
        else:
            color = (0, 0, 255)  # Red - far
    else:  # current_angle > target_max
        distance = current_angle - target_max
        progress = max(0.0, 1.0 - (distance / tolerance))
        if progress > 0.5:
            color = (0, 255, 255)  # Yellow - close
        else:
            color = (0, 0, 255)  # Red - far

    # Draw progress bar
    cv2.rectangle(image, (x, y), (x + width, y + height), (50, 50, 50), -1)
    progress_width = int(width * progress)
    cv2.rectangle(image, (x, y), (x + progress_width, y + height), color, -1)
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

    # Draw percentage below
    percentage = int(progress * 100)
    cv2.putText(image, f"{percentage}%", (x + width//2 - 20, y + height + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

def draw_instruction_box(image, text, y_offset=0):
    """Draw instruction box with background"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.8  # Reduced font size to avoid blocking face
    thickness = 2     # Reduced thickness for smaller text

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

# Demo image loading helpers
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
ALT_ASSETS_DIR = os.path.join(os.getcwd(), "assets")
_DEMO_IMAGE_CACHE = {}

def _possible_demo_paths(exercise_key: str):
    name_variants = [
        exercise_key,
        exercise_key.replace("_", "-"),
        exercise_key.replace("_", " ")
    ]
    exts = [".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"]
    dirs = [ASSETS_DIR, ALT_ASSETS_DIR]
    candidates = []
    for d in dirs:
        for nv in name_variants:
            for ext in exts:
                candidates.append(os.path.join(d, nv + ext))
    return candidates

def get_demo_image_for(exercise_key: str):
    if exercise_key in _DEMO_IMAGE_CACHE:
        return _DEMO_IMAGE_CACHE[exercise_key]
    # Try load from multiple candidate paths
    for path in _possible_demo_paths(exercise_key):
        if os.path.isfile(path):
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                _DEMO_IMAGE_CACHE[exercise_key] = img
                return img
    _DEMO_IMAGE_CACHE[exercise_key] = None
    return None

def draw_demo_thumbnail(image):
    h, w, _ = image.shape
    thumb = get_demo_image_for(current_exercise)
    margin = 20
    target_width = 300
    if thumb is not None:
        th, tw = thumb.shape[:2]
        if tw == 0 or th == 0:
            return
        scale = target_width / float(tw)
        resized_h = max(1, int(th * scale))
        resized = cv2.resize(thumb, (target_width, resized_h))
        x1 = w - target_width - margin
        y1 = margin
        x2 = w - margin
        y2 = y1 + resized_h
        # Background and border for visibility
        cv2.rectangle(image, (x1 - 6, y1 - 6), (x2 + 6, y2 + 6), (0, 0, 0), -1)
        cv2.rectangle(image, (x1 - 6, y1 - 6), (x2 + 6, y2 + 6), (255, 255, 255), 2)
        # Paste image
        roi = image[y1:y2, x1:x2]
        resized = resized[:roi.shape[0], :roi.shape[1]]
        image[y1:y2, x1:x2] = resized
    else:
        # Placeholder box if image missing
        x1 = w - target_width - margin
        y1 = margin
        x2 = w - margin
        y2 = y1 + 180
        cv2.rectangle(image, (x1, y1), (x2, y2), (30, 30, 30), -1)
        cv2.rectangle(image, (x1, y1), (x2, y2), (80, 80, 80), 2)
        cv2.putText(image, "Demo image not found", (x1 + 10, y1 + 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(image, f"assets/{current_exercise}.png", (x1 + 10, y1 + 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

def get_target_reps_for_current() -> int:
    """Return target reps for the current exercise, using per-exercise overrides."""
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
    # Compute progress using the planned exercise order and per-exercise reps
    total_possible_reps = 0
    for ex_key in EXERCISE_ORDER:
        total_possible_reps += REPS_PER_EXERCISE.get(ex_key, default_target_reps)
    total_possible_reps = max(total_possible_reps, 1)
    progress = min(1.0, session_stats["total_reps"] / total_possible_reps)
    draw_progress_bar(image, progress, w - 280, h - 40, 250, 15, (0, 255, 0))
    cv2.putText(image, f"Session Progress: {int(progress * 100)}%", (w - 280, h - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

def draw_game_hud(image):
    h, w, _ = image.shape
    hud_w = 280
    hud_h = 120
    x1 = w - hud_w - 20  # Move to top-right
    y1 = 20
    x2 = x1 + hud_w
    y2 = y1 + hud_h
    # Background
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 2)
    # Text
    cv2.putText(image, f"Score: {score}", (x1 + 10, y1 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(image, f"Streak: 🔥{streak}", (x1 + 10, y1 + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(image, f"Level: {level}", (x1 + 10, y1 + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

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
        "WRIST EXERCISES:",
        "- Wrist Flexion - Bend wrist forward",
        "- Radial Deviation - Bend toward thumb",
        "- Ulnar Deviation - Bend toward pinky",
        "",
        "FINGER EXERCISES:",
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
    if current_exercise in ["wrist_flexion", "radial_deviation", "ulnar_deviation"]:
        demo_text = [
            f"DEMO: {exercise['name']}",
            "",
            "DIRECTIONAL GUIDANCE:",
            f"- {exercise['detailed_instruction']}",
            "",
            "STEP-BY-STEP:",
            f"- Start: 0 deg (neutral position)",
            f"- Move: {exercise['visual_cue']}",
            f"- Target: {exercise['target_angle_range'][0]}-{exercise['target_angle_range'][1]} deg",
            f"- Hold: 5 seconds in target zone",
            "",
            "WHAT YOU'LL SEE:",
            "- 'BEND DOWN' - move palm toward floor",
            "- 'BEND RIGHT' - move toward thumb side",
            "- 'BEND LEFT' - move toward pinky side",
            "- 'PERFECT!' - when in target zone",
            "",
            "Press 'd' to close this demo"
        ]
    else:
        demo_text = [
            f"DEMO: {exercise['name']}",
            "",
            "DIRECTIONAL GUIDANCE:",
            f"- {exercise['detailed_instruction']}",
            "",
            "STEP-BY-STEP:",
            f"- Start: Neutral position",
            f"- Move: {exercise['visual_cue']}",
            f"- Target: {exercise.get('target_distance_range', exercise.get('target_angle_range', 'specific position'))}",
            f"- Hold: {exercise['hold_time']} seconds in target zone",
            "",
            "WHAT YOU'LL SEE:",
            "- Real-time feedback on your form",
            "- Progress bars and timers",
            "- Points earned for good performance",
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

def draw_intro_banner(image):
    """Draw intro banner for exercise start"""
    h, w, _ = image.shape
    exercise = EXERCISES[current_exercise]

    # Semi-transparent overlay
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.8, image, 0.2, 0, image)

    # Intro content
    intro_text = [
        f"GET READY FOR: {exercise['name'].upper()}",
        "",
        f"{exercise['description']}",
        "",
        f"TARGET: {exercise.get('target_angle_range', exercise.get('target_distance_range', 'specific position'))}",
        f"HOLD TIME: {exercise['hold_time']} seconds",
        f"REPS: {get_target_reps_for_current()}",
        "",
        "Starting in 3 seconds...",
        "",
        "Position your hand and get ready!"
    ]

    # Draw intro text centered
    y_start = h // 2 - 150
    for i, line in enumerate(intro_text):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 1.2 if i == 0 else 0.8
        thickness = 3 if i == 0 else 2
        text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        x_pos = (w - text_size[0]) // 2
        cv2.putText(image, line, (x_pos, y_start + i * 40),
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
            return f"Keep bending DOWN! You're at {int(angle)} deg - need {min_angle}-{max_angle} deg"
        elif current_exercise == "wrist_extension":
            return f"Keep bending UP! You're at {int(angle)} deg - need {min_angle}-{max_angle} deg"
        elif current_exercise == "radial_deviation":
            return f"Keep bending RIGHT! You're at {int(angle)} deg - need {min_angle}-{max_angle} deg"
        elif current_exercise == "ulnar_deviation":
            return f"Keep bending LEFT! You're at {int(angle)} deg - need {min_angle}-{max_angle} deg"
    elif angle <= max_angle:
        return f"PERFECT! Hold this position at {int(angle)} deg - you should feel a stretch!"
    elif angle < 120:
        if current_exercise == "wrist_flexion":
            return "Good stretch! Hold steady - ease back UP slightly if needed"
        elif current_exercise == "wrist_extension":
            return "Good stretch! Hold steady - ease back DOWN slightly if needed"
        elif current_exercise == "radial_deviation":
            return "Good stretch! Hold steady - ease back LEFT slightly if needed"
        elif current_exercise == "ulnar_deviation":
            return "Good stretch! Hold steady - ease back RIGHT slightly if needed"
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
        return f"Start bending your wrist - aim for {min_angle}-{max_angle} deg"
    elif angle < min_angle:
        return f"Good start! Bend more - you're at {int(angle)} deg, need {min_angle}-{max_angle} deg"
    elif angle <= max_angle:
        return f"Perfect! Hold at {int(angle)} deg - you should feel a stretch!"
    elif angle < 120:
        return f"Good stretch! Hold steady at {int(angle)} deg"
    else:
        return "Ease back slightly - that's too much bend"

def get_exercise_instruction():
    """Get current instruction based on exercise phase"""
    exercise = EXERCISES[current_exercise]
    target_reps_current = get_target_reps_for_current()

    if exercise_phase == "setup":
        return f"Welcome! We'll do {exercise['name']} exercises.\n{exercise['detailed_instruction']}\n\n{exercise['visual_cue']}\n\nPress 'd' to see a demo of the proper range of motion.\nPosition your hand in front of the camera."
    elif exercise_phase == "warmup":
        return f"Warm-up: Gently move your hand in all directions\nfor {warmup_time} seconds to prepare your muscles.\n\nStart with small circles, then gentle stretches."
    elif exercise_phase == "exercise":
        if start_hold is None:
            if current_exercise in ["wrist_flexion", "radial_deviation", "ulnar_deviation"]:
                rng = f"{exercise['target_angle_range'][0]}-{exercise['target_angle_range'][1]} deg"
                if current_exercise == "wrist_flexion":
                    return f"Ready! Bend your wrist DOWN (palm toward floor)\n\n{exercise['visual_cue']}\n\nHold when you reach {rng}."
                elif current_exercise == "radial_deviation":
                    return f"Ready! Bend your wrist RIGHT (toward your thumb)\n\n{exercise['visual_cue']}\n\nHold when you reach {rng}."
                elif current_exercise == "ulnar_deviation":
                    return f"Ready! Bend your wrist LEFT (toward your pinky)\n\n{exercise['visual_cue']}\n\nHold when you reach {rng}."
            elif current_exercise == "finger_spread":
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
                return f"⏳ Hold steady! {remaining}s remaining\nRep {reps + 1}/{target_reps_current}\n\nYou should feel a gentle stretch - this is working!"
            else:
                return f"Great! Relax and prepare for next rep.\nRep {reps + 1}/{target_reps_current} complete!\n\nLet your hand return to neutral position."
    elif exercise_phase == "rest":
        target_reps_current = get_target_reps_for_current()
        return f"Rest for {rest_time} seconds\nNext rep: {reps + 1}/{target_reps_current}\n\nShake out your hand gently during rest."
    elif exercise_phase == "complete":
        return (f"Exercise Complete!\n"
                f"You did {reps} reps of {exercise['name']}\n"
                f"Points this exercise: {exercise_points_earned}\n"
                f"Current streak: 🔥{streak}  Level: {level}\n"
                f"Press 'n' for next exercise or 'r' to restart")
    else:
        return "Press 's' to start exercise"

# Global variables for timing
warmup_start = None
rest_start = None
show_help = False
show_demo = False
demo_start = None
intro_start = None
show_intro = False

# Finger tracking variables
last_finger_positions = {}
current_opposition_target = 0
opposition_sequence = ["index", "middle", "ring", "pinky"]
tapped_fingers = set()

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
    if exercise_phase == "setup" and show_intro:
        if intro_start is None:
            intro_start = current_time
        elapsed_intro = current_time - intro_start
        if elapsed_intro >= 3:
            show_intro = False
            intro_start = None
            exercise_phase = "warmup"
    elif exercise_phase == "warmup":
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
        # Auto-advance to next exercise after brief pause
        if current_time - complete_start >= 2:
            exercise_keys = EXERCISE_ORDER
            current_idx = exercise_keys.index(current_exercise)
            current_exercise = exercise_keys[(current_idx + 1) % len(exercise_keys)]
            exercise_phase = "setup"
            reps = 0
            start_hold = None
            paused_time = 0
            pause_start = None
            warmup_start = None
            rest_start = None
            hold_time = EXERCISES[current_exercise]["hold_time"]
            complete_start = None
            show_intro = False
            intro_start = None

    # Hand detection and exercise logic
    hand_detected = False
    if result.multi_hand_landmarks:
        hand_detected = True
        for hand_landmarks in result.multi_hand_landmarks:
            h, w, _ = image.shape

            # Draw hand landmarks
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2, circle_radius=2),
                                    mp_drawing.DrawingSpec(color=exercise["color"], thickness=2))

            # Exercise-specific logic
            if current_exercise in ["wrist_flexion", "wrist_extension", "radial_deviation", "ulnar_deviation"]:
                # Wrist exercises - use angle calculation
                wrist = hand_landmarks.landmark[0]
                index_mcp = hand_landmarks.landmark[5]
                index_tip = hand_landmarks.landmark[8]
                pinky_mcp = hand_landmarks.landmark[17]

                wrist_pt = (int(w*wrist.x), int(h*wrist.y))
                mcp_pt = (int(w*index_mcp.x), int(h*index_mcp.y))
                tip_pt = (int(w*index_tip.x), int(h*index_tip.y))
                pinky_mcp_pt = (int(w*pinky_mcp.x), int(h*pinky_mcp.y))

                angle = calculate_angle(mcp_pt, wrist_pt, tip_pt)

                # Draw reference skeleton for wrist_flexion exercise
                if current_exercise == "wrist_flexion" and exercise_phase == "exercise":
                    # Draw white reference skeleton
                    draw_reference_skeleton(image, wrist_pt, hand_landmarks, color=(255, 255, 255), thickness=4)
                    
                    # Draw user's skeleton (green) - highlight index MCP and pinky MCP
                    cv2.circle(image, mcp_pt, 6, (0, 255, 0), -1)  # Green index MCP
                    cv2.circle(image, pinky_mcp_pt, 6, (0, 255, 0), -1)  # Green pinky MCP
                    
                    # Calculate alignment error between user's index MCP and reference position
                    alignment_error = calculate_alignment_error(mcp_pt, wrist_pt, hand_landmarks)
                    
                    # Draw alignment feedback
                    draw_alignment_feedback(image, alignment_error, wrist_pt, threshold=30)
                    
                    # Draw instruction text at the top
                    draw_reference_instruction(image, y_offset=50)

                # Draw angle indicator
                cv2.putText(image, f"Angle: {int(angle)} deg", (wrist_pt[0] - 50, wrist_pt[1] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                # Draw directional guidance
                directional_guidance = get_directional_guidance(angle, exercise_phase)
                if directional_guidance:
                    guidance_color = (0, 255, 0) if "PERFECT" in directional_guidance else (255, 255, 0) if "Keep bending" in directional_guidance or "Bend your wrist" in directional_guidance else (255, 0, 0) if "Too much" in directional_guidance else (255, 255, 255)
                    cv2.putText(image, directional_guidance, (wrist_pt[0] - 150, wrist_pt[1] + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, guidance_color, 2)

                # Draw large directional arrow
                if exercise_phase == "exercise" and angle < 60:
                    arrow_center = (w // 2, h // 2 + 100)
                    arrow_size = 80

                    if current_exercise == "wrist_flexion":
                        cv2.arrowedLine(image, (arrow_center[0], arrow_center[1] - arrow_size//2), (arrow_center[0], arrow_center[1] + arrow_size//2), (255, 255, 0), 8, tipLength=0.3)
                        cv2.putText(image, "BEND DOWN", (arrow_center[0] - 60, arrow_center[1] + arrow_size//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                    elif current_exercise == "radial_deviation":
                        cv2.arrowedLine(image, (arrow_center[0] - arrow_size//2, arrow_center[1]), (arrow_center[0] + arrow_size//2, arrow_center[1]), (255, 255, 0), 8, tipLength=0.3)
                        cv2.putText(image, "BEND RIGHT", (arrow_center[0] + arrow_size//2 + 20, arrow_center[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                    elif current_exercise == "ulnar_deviation":
                        cv2.arrowedLine(image, (arrow_center[0] + arrow_size//2, arrow_center[1]), (arrow_center[0] - arrow_size//2, arrow_center[1]), (255, 255, 0), 8, tipLength=0.3)
                        cv2.putText(image, "BEND LEFT", (arrow_center[0] - arrow_size//2 - 120, arrow_center[1] + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)

                # Draw target zone indicator and angle progress bar
                if exercise_phase == "exercise":
                    min_angle, max_angle = exercise["target_angle_range"]
                    target_text = f"Target: {min_angle}-{max_angle} deg"
                    cv2.putText(image, target_text, (wrist_pt[0] - 50, wrist_pt[1] + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                    # Draw angle progress bar
                    draw_angle_progress_bar(image, angle, min_angle, max_angle, wrist_pt[0] - 100, wrist_pt[1] + 100, 200, 20)

                    if min_angle <= angle <= max_angle:
                        status_text = "✅ IN TARGET ZONE"
                        status_color = (0, 255, 0)
                    elif angle < min_angle:
                        status_text = "❌ BEND MORE"
                        status_color = (255, 255, 0)
                    else:
                        status_text = "❌ EASE BACK"
                        status_color = (255, 0, 0)

                    cv2.putText(image, status_text, (wrist_pt[0] - 60, wrist_pt[1] + 140), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)

                # Wrist exercise logic
                if exercise_phase == "exercise":
                    min_angle, max_angle = exercise["target_angle_range"]
                    if min_angle < angle < max_angle:
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

            elif current_exercise in ["finger_spread", "thumb_opposition", "finger_taps", "finger_flexion"]:
                # Finger exercises
                tips = get_finger_tip_positions(hand_landmarks, (h, w))
                mcps = get_finger_mcp_positions(hand_landmarks, (h, w))

                if current_exercise == "finger_spread":
                    spread_distance = calculate_finger_spread(tips)
                    min_dist, max_dist = exercise["target_distance_range"]
                    cv2.putText(image, f"Spread Distance: {int(spread_distance)} px", (50, h - 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

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

                    cv2.putText(image, f"Target: Touch {target_finger} finger", (50, h - 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)
                    if touching_finger:
                        cv2.putText(image, f"Touching: {touching_finger}", (50, h - 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                elif current_exercise == "finger_taps":
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

                    cv2.putText(image, f"Tapped: {len(tapped_fingers)}/4 fingers", (50, h - 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

                elif current_exercise == "finger_flexion":
                    flexion_angles = calculate_finger_flexion_angles(hand_landmarks, (h, w))
                    avg_angle = sum(flexion_angles.values()) / len(flexion_angles) if flexion_angles else 0
                    min_angle, max_angle = exercise["target_angle_range"]

                    cv2.putText(image, f"Flexion Angle: {int(avg_angle)} deg", (50, h - 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, exercise["color"], 2)

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

    # Draw UI elements
    h, w, _ = image.shape
    
    # Draw instruction box
    instruction_text = get_exercise_instruction()
    draw_instruction_box(image, instruction_text)
    
    # Draw exercise info
    cv2.putText(image, f"Exercise: {exercise['name']}", (20, h - 140),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(image, f"Reps: {reps}/{get_target_reps_for_current()}", (20, h - 110),
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
    # Draw game HUD
    draw_game_hud(image)
    
    # Draw help screen if enabled
    if show_help:
        draw_help_screen(image)

    # Draw intro banner if enabled
    if show_intro and exercise_phase == "setup":
        draw_intro_banner(image)

    # Draw demo if enabled
    if show_demo:
        # Only draw full demo overlay in setup (no image thumbnail)
        if exercise_phase == "setup":
            draw_demo_mode(image)

    # Draw demo thumbnail if in setup phase (removed per user request)
    
    # Draw controls (moved up for better visibility on some screens)
    cv2.putText(image, "Controls: 's'=start, 'd'=demo, 'n'=next, 'r'=restart, 'h'=help, ESC=exit", 
               (20, h - 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    cv2.imshow("Physiotherapy Exercise Assistant", image)
    
    # Handle key presses
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('s') and exercise_phase == "setup":
        exercise_phase = "exercise"
    elif key == ord('n') and exercise_phase == "complete":
        # Cycle to next exercise based on predefined order
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
        current_opposition_target = 0
        tapped_fingers = set()
        show_intro = False
        intro_start = None
    elif key == ord('r'):
        # Restart current exercise
        exercise_phase = "setup"
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
        show_intro = False
        intro_start = None
    elif key == ord('h'):
        # Show help
        show_help = not show_help
    elif key == ord('d'):
        # Toggle demo mode (available in any phase)
        show_demo = not show_demo
        if show_demo:
            demo_start = time.time()

cap.release()
cv2.destroyAllWindows()
