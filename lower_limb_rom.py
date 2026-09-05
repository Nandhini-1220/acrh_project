import cv2
import mediapipe as mp
import time
import math
import numpy as np

# Mediapipe setup for pose detection
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7)

# Lower-limb physiotherapy exercises and ROM targets
EXERCISES = {
    "hip_flexion": {
        "name": "Hip Flexion",
        "description": "Lift your thigh toward your chest",
        "detailed_instruction": "Standing or lying, slowly lift your thigh toward your chest while keeping your trunk stable. Aim for 90-110° of hip flexion.",
        "target_angle_range": (90, 110),
        "color": (0, 255, 0),  # Green
        "joint": "hip",
    },
    "knee_flexion": {
        "name": "Knee Flexion",
        "description": "Bend your knee to flex the leg",
        "detailed_instruction": "Slowly bend your knee, bringing your heel toward your buttock. Aim for 140-160° of knee flexion.",
        "target_angle_range": (140, 160),
        "color": (255, 255, 0),  # Yellow
        "joint": "knee",
    },
    "ankle_plantarflexion": {
        "name": "Ankle Plantarflexion",
        "description": "Point your toes downward",
        "detailed_instruction": "From a neutral ankle position, slowly point your toes downward as if pressing a gas pedal. Aim for 30-50° of plantarflexion.",
        "target_angle_range": (30, 50),
        "color": (255, 165, 0),  # Orange
        "joint": "ankle",
    },
    "ankle_dorsiflexion": {
        "name": "Ankle Dorsiflexion",
        "description": "Pull your toes toward your shin",
        "detailed_instruction": "From a neutral ankle position, slowly pull your toes toward your shin. Aim for 20-40° of dorsiflexion.",
        "target_angle_range": (20, 40),
        "color": (128, 0, 255),  # Purple
        "joint": "ankle",
    },
}

EXERCISE_ORDER = list(EXERCISES.keys())

current_exercise = EXERCISE_ORDER[0]
exercise_phase = "setup"  # setup, exercise
show_demo = False


def calculate_angle(a, b, c):
    """Calculate angle (in degrees) at point b given three 2D points."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    angle = math.degrees(math.acos(cos_angle))
    return angle


def draw_progress_bar(image, value, min_val, max_val, x, y, width, height, color):
    """Draw a simple progress bar for how close current angle is to target range."""
    # Normalize distance: 0 when in range, increases as we move away
    if min_val <= value <= max_val:
        progress = 1.0
    else:
        if value < min_val:
            dist = min_val - value
        else:
            dist = value - max_val
        # Assume 30° away -> 0 progress
        progress = max(0.0, 1.0 - dist / 30.0)

    cv2.rectangle(image, (x, y), (x + width, y + height), (40, 40, 40), -1)
    filled = int(width * progress)
    cv2.rectangle(image, (x, y), (x + filled, y + height), color, -1)
    cv2.rectangle(image, (x, y), (x + width, y + height), (255, 255, 255), 2)

    pct = int(progress * 100)
    cv2.putText(
        image,
        f"{pct}%",
        (x + width // 2 - 20, y + height + 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )


def draw_instruction_box(image, text):
    """Draw multi-line instruction box."""
    h, w, _ = image.shape
    lines = text.split("\n")
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2

    sizes = [cv2.getTextSize(line, font, font_scale, thickness)[0] for line in lines]
    max_width = max(s[0] for s in sizes) if sizes else 0
    line_height = sizes[0][1] if sizes else 24

    padding = 16
    box_w = max_width + 2 * padding
    box_h = len(lines) * (line_height + 8) + 2 * padding

    x1 = 20
    y1 = 40
    x2 = x1 + box_w
    y2 = y1 + box_h

    overlay = image.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
    cv2.rectangle(image, (x1, y1), (x2, y2), (255, 255, 255), 2)

    y_text = y1 + padding + line_height
    for line in lines:
        cv2.putText(
            image,
            line,
            (x1 + padding, y_text),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
        )
        y_text += line_height + 8


def get_instruction_text():
    ex = EXERCISES[current_exercise]
    if exercise_phase == "setup":
        return (
            f"{ex['name']}\n"
            f"{ex['detailed_instruction']}\n\n"
            "Press 's' to start tracking, 'd' for a text demo,\n"
            "'n' for next exercise, ESC to exit."
        )
    else:
        return (
            f"Move slowly into the target range.\n"
            f"Target: {ex['target_angle_range'][0]}-{ex['target_angle_range'][1]}°.\n"
            "Keep movements controlled and pain-free."
        )


def draw_demo_mode(image):
    """Full-screen textual demo overlay."""
    h, w, _ = image.shape
    ex = EXERCISES[current_exercise]

    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

    lines = [
        f"DEMO: {ex['name']}",
        "",
        ex["description"],
        "",
        ex["detailed_instruction"],
        "",
        f"Target ROM: {ex['target_angle_range'][0]}–{ex['target_angle_range'][1]}°",
        "",
        "Tips:",
        "- Move slowly and avoid bouncing.",
        "- Stop if you feel sharp pain.",
        "- Use support (chair / wall) if balance is an issue.",
        "",
        "Press 'd' again to close this demo.",
    ]

    y_start = 80
    for i, line in enumerate(lines):
        color = (255, 255, 255) if i == 0 else (200, 200, 200)
        font_scale = 0.9 if i == 0 else 0.7
        thickness = 2 if i == 0 else 1
        cv2.putText(
            image,
            line,
            (60, y_start + i * 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
        )


cap = cv2.VideoCapture(0)

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = pose.process(rgb)

    h, w, _ = frame.shape
    angle_val = None

    if result.pose_landmarks:
        lm = result.pose_landmarks.landmark

        # Use right side landmarks by default
        hip = lm[mp_pose.PoseLandmark.RIGHT_HIP]
        knee = lm[mp_pose.PoseLandmark.RIGHT_KNEE]
        ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE]
        shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        foot = lm[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX]

        hip_pt = (int(w * hip.x), int(h * hip.y))
        knee_pt = (int(w * knee.x), int(h * knee.y))
        ankle_pt = (int(w * ankle.x), int(h * ankle.y))
        shoulder_pt = (int(w * shoulder.x), int(h * shoulder.y))
        foot_pt = (int(w * foot.x), int(h * foot.y))

        ex = EXERCISES[current_exercise]
        joint = ex["joint"]

        if joint == "hip":
            # Angle at hip between trunk and thigh
            angle_val = calculate_angle(shoulder_pt, hip_pt, knee_pt)
            joint_label_pt = hip_pt
        elif joint == "knee":
            # Angle at knee between thigh and calf
            angle_val = calculate_angle(hip_pt, knee_pt, ankle_pt)
            joint_label_pt = knee_pt
        else:  # ankle
            # Angle at ankle between leg and foot
            angle_val = calculate_angle(knee_pt, ankle_pt, foot_pt)
            joint_label_pt = ankle_pt

        mp_drawing.draw_landmarks(
            frame,
            result.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=ex["color"], thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=ex["color"], thickness=2),
        )

        if angle_val is not None:
            cv2.putText(
                frame,
                f"Angle: {int(angle_val)}°",
                (joint_label_pt[0] - 40, joint_label_pt[1] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                ex["color"],
                2,
            )

            tmin, tmax = ex["target_angle_range"]
            status_text = "Move into range"
            status_color = (0, 0, 255)
            if tmin <= angle_val <= tmax:
                status_text = "In target ROM"
                status_color = (0, 255, 0)
            elif angle_val < tmin:
                status_text = "Increase movement"
            else:
                status_text = "Ease back slightly"

            cv2.putText(
                frame,
                status_text,
                (joint_label_pt[0] - 60, joint_label_pt[1] + 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                status_color,
                2,
            )

            draw_progress_bar(
                frame,
                angle_val,
                tmin,
                tmax,
                x=w - 260,
                y=60,
                width=220,
                height=20,
                color=ex["color"],
            )
    else:
        cv2.putText(
            frame,
            "No body detected - stand where the camera can see you",
            (40, h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
        )

    # Instruction box
    draw_instruction_box(frame, get_instruction_text())

    # Exercise name and controls
    ex = EXERCISES[current_exercise]
    cv2.putText(
        frame,
        f"Exercise: {ex['name']}",
        (20, h - 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        "Controls: 's'=start, 'd'=demo, 'n'=next, ESC=exit",
        (20, h - 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (200, 200, 200),
        1,
    )

    # Demo overlay
    if show_demo:
        draw_demo_mode(frame)

    cv2.namedWindow("Lower Limb ROM Assistant", cv2.WINDOW_NORMAL)
    cv2.imshow("Lower Limb ROM Assistant", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord("s"):
        exercise_phase = "exercise"
    elif key == ord("n"):
        idx = EXERCISE_ORDER.index(current_exercise)
        current_exercise = EXERCISE_ORDER[(idx + 1) % len(EXERCISE_ORDER)]
        exercise_phase = "setup"
        show_demo = False
    elif key == ord("d"):
        show_demo = not show_demo

cap.release()
cv2.destroyAllWindows()

