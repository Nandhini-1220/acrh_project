import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import platform

class ExerciseUI:
    def __init__(self):
        try:
            if platform.system() == "Windows":
                font_path = "arial.ttf"
            elif platform.system() == "Darwin":
                font_path = "Arial.ttf"
            else:
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
                
            self.font_title = ImageFont.truetype(font_path, 36)
            self.font_large = ImageFont.truetype(font_path, 28)
            self.font_medium = ImageFont.truetype(font_path, 22)
            self.font_small = ImageFont.truetype(font_path, 16)
        except Exception:
            default = ImageFont.load_default()
            self.font_title = default
            self.font_large = default
            self.font_medium = default
            self.font_small = default

    def _draw_text_pil(self, draw, text, position, font, text_color=(255, 255, 255), outline_color=(0, 0, 0)):
        x, y = position
        if outline_color is not None:
            outline_width = 2
            for dx in range(-outline_width, outline_width+1):
                for dy in range(-outline_width, outline_width+1):
                    if dx != 0 or dy != 0:
                        draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
        draw.text((x, y), text, font=font, fill=text_color)

    def draw_rounded_rect(self, draw, xy, radius, fill):
        draw.rounded_rectangle(xy, radius, fill=fill)

    def render(self, frame_bgr, state, window_name="Exercise"):
        try:
            rect = cv2.getWindowImageRect(window_name)
            if rect and rect[2] > 100 and rect[3] > 100:
                win_w, win_h = rect[2], rect[3]
            else:
                win_w, win_h = 1280, 720
        except cv2.error:
            # Window not created yet
            win_w, win_h = 1280, 720
            
        canvas = np.zeros((win_h, win_w, 3), dtype=np.uint8)
        cam_h, cam_w = frame_bgr.shape[:2]
        scale = min(win_w / cam_w, win_h / cam_h)
        new_w = int(cam_w * scale)
        new_h = int(cam_h * scale)
        
        resized_cam = cv2.resize(frame_bgr, (new_w, new_h))
        x_offset = (win_w - new_w) // 2
        y_offset = (win_h - new_h) // 2
        
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized_cam
        
        img_pil = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil, "RGBA")
        w, h = img_pil.size
        
        panel_bg = (0, 0, 0, 160)
        
        # 1. TOP HEADER
        header_h = max(80, int(h * 0.15))
        self.draw_rounded_rect(draw, [(10, 10), (w - 10, header_h)], 10, panel_bg)
        title_text = f"{state.get('exercise_name', 'Exercise')} (Level {state.get('level', 1)})"
        self._draw_text_pil(draw, title_text, (25, 20), self.font_title, (255, 215, 0))
        instruction = state.get('instruction') or ''
        self._draw_text_pil(draw, instruction, (25, 65), self.font_medium, (200, 255, 200))
        
        # 2. SIDE HUD
        hud_w = min(300, int(w * 0.35))
        hud_h = min(400, int(h * 0.5))
        hud_x = w - hud_w - 10
        hud_y = header_h + 20
        self.draw_rounded_rect(draw, [(hud_x, hud_y), (w - 10, hud_y + hud_h)], 10, panel_bg)
        
        y_offset = hud_y + 15
        self._draw_text_pil(draw, "STATUS", (hud_x + 15, y_offset), self.font_large, (100, 200, 255))
        y_offset += 45
        
        angle = state.get('angle')
        if angle is not None:
            self._draw_text_pil(draw, f"Angle: {int(angle)}\u00B0", (hud_x + 15, y_offset), self.font_large)
            y_offset += 40
            
        target = state.get('target_range')
        if target:
            self._draw_text_pil(draw, f"Target: {target[0]}\u00B0 - {target[1]}\u00B0", (hud_x + 15, y_offset), self.font_medium, (200, 200, 200))
            y_offset += 40
            
        reps = state.get('reps', 0)
        t_reps = state.get('target_reps', 0)
        self._draw_text_pil(draw, f"Reps: {reps} / {t_reps}", (hud_x + 15, y_offset), self.font_large, (0, 255, 100))
        y_offset += 50
        
        progress = state.get('progress')
        if progress is not None:
            p_title = state.get('progress_title', 'Progress')
            self._draw_text_pil(draw, p_title, (hud_x + 15, y_offset), self.font_small)
            y_offset += 25
            bar_w = hud_w - 30
            bar_h = 20
            draw.rectangle([(hud_x + 15, y_offset), (hud_x + 15 + bar_w, y_offset + bar_h)], fill=(50, 50, 50, 255), outline=(255,255,255,255))
            fill_w = int(bar_w * max(0.0, min(1.0, progress)))
            draw.rectangle([(hud_x + 15, y_offset), (hud_x + 15 + fill_w, y_offset + bar_h)], fill=(0, 255, 0, 255))
        
        # 3. VISUAL FEEDBACK
        feedback = state.get('feedback_msg')
        if feedback:
            bbox = draw.textbbox((0, 0), feedback, font=self.font_large)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            fx = (w - tw) // 2
            fy = h - max(80, int(h * 0.15)) - th - 30
            draw.rounded_rectangle([(fx - 15, fy - 10), (fx + tw + 15, fy + th + 10)], 8, fill=(255, 100, 0, 220))
            self._draw_text_pil(draw, feedback, (fx, fy), self.font_large, (255, 255, 255), outline_color=None)

        # 4. BOTTOM PANEL
        bottom_h = max(60, int(h * 0.12))
        bottom_y = h - bottom_h - 10
        self.draw_rounded_rect(draw, [(10, bottom_y), (w - 10, h - 10)], 10, panel_bg)
        
        session_info = f"Session Time: {state.get('session_duration', '00:00')} | Total Session Reps: {state.get('session_reps', 0)}"
        controls = "Controls: ESC to Exit"
        
        self._draw_text_pil(draw, session_info, (25, bottom_y + 15), self.font_medium)
        bbox_ctrl = draw.textbbox((0, 0), controls, font=self.font_medium)
        self._draw_text_pil(draw, controls, (w - 25 - (bbox_ctrl[2]-bbox_ctrl[0]), bottom_y + 15), self.font_medium, (150, 150, 150))
        
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
