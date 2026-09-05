import cv2
import subprocess
import sys
import os
import numpy as np

def draw_menu(image, selected_option, options):
    """Draw the main menu"""
    h, w, _ = image.shape

    # Clear background
    cv2.rectangle(image, (0, 0), (w, h), (30, 30, 30), -1)

    # Title
    cv2.putText(image, "PHYSIOTHERAPY AI ASSISTANT", (w//2 - 300, h//2 - 150),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # Menu options
    option_y = h//2 - 50
    for i, option in enumerate(options):
        color = (0, 255, 0) if i == selected_option else (200, 200, 200)
        thickness = 3 if i == selected_option else 2

        # Draw selection indicator
        if i == selected_option:
            cv2.circle(image, (w//2 - 200, option_y + 15), 10, (0, 255, 0), -1)

        cv2.putText(image, option, (w//2 - 150, option_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, thickness)
        option_y += 60

    # Instructions
    cv2.putText(image, "Use UP/DOWN arrows to select, ENTER to choose, ESC to exit",
               (w//2 - 350, h - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)

    # Footer
    cv2.putText(image, "Developed with Mediapipe & OpenCV",
               (w//2 - 200, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 2)

def main():
    # Menu options
    options = ["Wrist Exercises", "Finger Exercises", "Forearm Exercises", "Exit"]
    selected_option = 0

    # Create window
    cv2.namedWindow("Physiotherapy Menu", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Physiotherapy Menu", 1200, 800)

    # Create a blank image for menu
    menu_image = cv2.imread(os.path.join(os.path.dirname(__file__), "static", "menu_bg.jpg"))
    if menu_image is None:
        # Create blank image if background not found
        menu_image = cv2.imread("menu_bg.jpg")
    if menu_image is None:
        # Create solid color background
        menu_image = cv2.imread("menu_bg.png")
    if menu_image is None:
        # Last resort: create blank image
        menu_image = np.zeros((800, 1200, 3), dtype=np.uint8)
        cv2.rectangle(menu_image, (0, 0), (1200, 800), (40, 40, 60), -1)

    while True:
        # Create a copy for drawing
        display_image = menu_image.copy()

        # Draw menu
        draw_menu(display_image, selected_option, options)

        cv2.imshow("Physiotherapy Menu", display_image)

        key = cv2.waitKey(0) & 0xFF

        if key == 27:  # ESC
            break
        elif key == 82 or key == ord('w'):  # UP arrow or W
            selected_option = (selected_option - 1) % len(options)
        elif key == 84 or key == ord('s'):  # DOWN arrow or S
            selected_option = (selected_option + 1) % len(options)
        elif key == 13:  # ENTER
            if selected_option == 0:  # Wrist Exercises
                print("Launching Wrist Exercises...")
                try:
                    subprocess.Popen([sys.executable, "index.py"])
                    break
                except Exception as e:
                    print(f"Error launching wrist exercises: {e}")
            elif selected_option == 1:  # Finger Exercises
                print("Launching Finger Exercises...")
                try:
                    subprocess.Popen([sys.executable, "finger.py"])
                    break
                except Exception as e:
                    print(f"Error launching finger exercises: {e}")
            elif selected_option == 2:  # Forearm Exercises
                print("Launching Forearm Exercises...")
                try:
                    subprocess.Popen([sys.executable, "forearm.py"])
                    break
                except Exception as e:
                    print(f"Error launching forearm exercises: {e}")
            elif selected_option == 3:  # Exit
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
