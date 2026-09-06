import os
import re

files = ["wrist_rotation_exercises.py", "shoulder.py", "elbow_exercises.py", "finger.py"]

for filename in files:
    if not os.path.exists(filename): continue
    
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    content = content.replace("Â°", "")
    content = content.replace("°", "")
    
    if "from shared_ui import ExerciseUI" not in content:
        content = content.replace("import cv2", "import cv2\nfrom shared_ui import ExerciseUI\nui_renderer = ExerciseUI()")
        
    content = content.replace('exercise_phase = "setup"', 'exercise_phase = "exercise"')
    
    pattern = r"# Draw UI elements.*?cv2\.imshow\([^,]+,\s*image\)"
    
    injection = """# Draw UI elements (Delegated to shared_ui.py)
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
    cv2.imshow("Exercise", image)"""
    
    content = re.sub(pattern, injection, content, flags=re.DOTALL)
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"Fixed {filename}")
