# Physiotherapy AI Assistant

A comprehensive computer vision-based physiotherapy exercise application that uses hand tracking to guide users through wrist and finger rehabilitation exercises with real-time feedback, progress tracking, and gamification.

## Features

### 🏥 **Professional Physiotherapy Exercises**

#### Wrist Exercises
- **Wrist Flexion**: Bend wrist forward (palm toward forearm)
- **Wrist Extension**: Bend wrist backward (back of hand toward forearm)
- **Radial Deviation**: Bend wrist toward thumb side
- **Ulnar Deviation**: Bend wrist toward pinky side

#### Finger Exercises
- **Finger Spread**: Spread fingers apart as wide as comfortable
- **Thumb Opposition**: Touch thumb to each finger sequentially
- **Finger Taps**: Tap each finger on thumb sequentially
- **Finger Flexion**: Make fist and straighten fingers

### 🎯 **Smart Exercise Guidance**
- Real-time hand tracking with MediaPipe
- Visual angle measurement and feedback
- Step-by-step instructions with clear descriptions
- Form correction feedback to ensure proper technique
- Color-coded exercise indicators
- Finger-specific detection algorithms

### 📊 **Progress Tracking**
- Session statistics (exercises completed, total reps, duration)
- Real-time progress bars for warm-up, holds, and rest periods
- Exercise completion tracking
- Session duration monitoring
- Gamified scoring system with streaks and levels

### 🛡️ **Safety Features**
- Mandatory warm-up period before exercises
- Rest periods between repetitions
- Form validation and correction feedback
- Pain-free exercise guidance
- Help system with safety tips
- Professional physiotherapy guidance

### 🎨 **User-Friendly Interface**
- Clear, easy-to-read instructions
- Visual progress indicators
- Hand detection status
- Intuitive keyboard controls
- Professional physiotherapy guidance
- Menu system for easy navigation

## Installation

1. **Install Python 3.7+** (if not already installed)

2. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python menu.py
   ```

## Usage

### Getting Started
1. **Position your hand** in front of the camera
2. **Press 's'** to start the warm-up
3. **Follow the instructions** on screen
4. **Complete the exercises** as guided

### Controls
- **'s'** - Start exercise
- **'n'** - Next exercise (after completion)
- **'r'** - Restart current exercise
- **'h'** - Toggle help screen
- **ESC** - Exit program

### Exercise Flow
1. **Setup**: Position hand and read instructions
2. **Warm-up**: 10-second gentle movement preparation
3. **Exercise**: Hold position for 5 seconds per rep
4. **Rest**: 3-second rest between reps
5. **Complete**: Move to next exercise or restart

## Exercise Instructions

### Wrist Flexion
- Bend your wrist forward so your palm moves toward your forearm
- Hold the position when the angle indicator shows 60-120°
- Keep movements slow and controlled

### Wrist Extension  
- Bend your wrist backward so the back of your hand moves toward your forearm
- Hold the position when the angle indicator shows 60-120°
- Avoid overextending

### Radial Deviation
- Bend your wrist toward your thumb side
- Keep your forearm stable
- Hold the position when the angle indicator shows 60-120°

### Ulnar Deviation
- Bend your wrist toward your pinky side
- Keep your forearm stable  
- Hold the position when the angle indicator shows 60-120°

## Safety Guidelines

⚠️ **Important Safety Information:**
- **Stop immediately** if you feel any pain
- **Always warm up** before exercising
- **Keep movements slow** and controlled
- **Maintain proper form** throughout exercises
- **Consult a healthcare professional** before starting any exercise program
- **Discontinue use** if you experience discomfort

## Technical Requirements

- **Camera**: Webcam or built-in camera
- **Python**: 3.7 or higher
- **Operating System**: Windows, macOS, or Linux
- **Dependencies**: OpenCV, MediaPipe, NumPy

## Troubleshooting

### Camera Issues
- Ensure camera is connected and not being used by other applications
- Check camera permissions in your system settings
- Try restarting the application

### Hand Detection Issues
- Ensure good lighting
- Keep hand clearly visible in camera frame
- Avoid cluttered backgrounds
- Position hand at appropriate distance from camera

### Performance Issues
- Close other applications using the camera
- Ensure adequate lighting
- Check system requirements

## Contributing

This application is designed for educational and therapeutic purposes. For medical applications, please consult with healthcare professionals and ensure proper validation.

## License

This project is for educational and therapeutic use. Please ensure compliance with local regulations for medical device usage.

---

**Disclaimer**: This application is for educational and therapeutic purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider before starting any exercise program, especially if you have existing medical conditions.

