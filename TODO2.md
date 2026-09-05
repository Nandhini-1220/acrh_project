# Patient 2 (Shoulder) Extension

## Plan Status
✅ User approved extension plan

Patient 2 already in data.json (Shoulder Sprain)

## Steps:
1. **Update TODO.md** - Mark previous complete, note extension
2. **Edit app.py** 
   - index(): Accept patient_id=='2', redirect /patient/2
   - start_exercise(): If session['patient_id']==2 → placeholder.html
3. **Edit templates/patient_levels.html** - Conditional: wrist (1) vs shoulder levels (2)
4. **Create templates/placeholder.html** - "Shoulder exercise module coming soon" with back link
5. **Test**:
   - ID=1: wrist unchanged
   - ID=2: shoulder levels → start_exercise → placeholder
   - Therapist dashboard shows Patient 2

## Progress
- [x] Create TODO2.md
- [x] Edit app.py login and start_exercise
- [ ] Edit patient_levels.html
- [x] Create placeholder.html
- [ ] Test
