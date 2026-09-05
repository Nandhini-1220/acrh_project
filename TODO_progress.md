# Progress Tracking System

## Plan:
**Info Gathered:**
- data.json: list patients with id, name, injury_type, progress %, level1-4 reps
- patient_levels.html: hard-coded levels, no progress display
- therapist_dashboard.html: loops patients, shows name/injury/progress%/Enter Room
- patient_room.html: shows level_progress[0-3]/10, overall %
- app.py: /patient reads nothing from data.json, /therapist reads data.json list
- feedback.html: simple summary, links home
- forearm.py: reps tracked in session_stats['total_reps'], no save

**Files to Edit:**
1. app.py: /patient/<id> load data.json patient data/progress to template; /feedback POST save_progress
2. templates/patient_levels.html: show progress.reps for each level card
3. templates/therapist_dashboard.html: enhance to show level1-4 summary
4. templates/feedback.html: add form POST reps/level to /save_progress?patient_id&level
5. data.json: convert to {"patients": {...}} if needed (currently list)

**Followup:** Test login → levels (show progress) → exercise → feedback (save reps) → therapist/patient_room (updated)

Step 3 complete: feedback save_progress, run_camera passes patient_id/level to scripts env vars.

