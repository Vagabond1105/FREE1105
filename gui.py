# below is gui.py

import pygame
import numpy as np
from constants_for_all_files import *

# --- UI CONFIGURATION ---
FONT_NAME = 'Consolas'
FONT_SIZE = 16
COL_BG = (240, 240, 240)
COL_BORDER = (0, 0, 0)
COL_ACTIVE = (50, 150, 255) # Blue highlight
COL_INACTIVE = (150, 150, 150)
COL_TEXT = (0, 0, 0)

# Standard UI Colors (ON/OFF)
COL_TRUE_STD = (50, 200, 50)    # Green
COL_FALSE_STD = (200, 50, 50)   # Red

# Physics Colors (Positive/Negative)
COL_POS = (200, 0, 0)   # Red
COL_NEG = (0, 0, 200)   # Blue

class ResetButton:
    def __init__(self):
        # Bottom Left Placement
        self.rect = pygame.Rect(20, SH - 60, 100, 40)
        self.font = pygame.font.SysFont('Arial', 20, bold=True)
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return True
        return False

    def render(self, screen):
        color = (200, 50, 50) if self.hovered else (150, 50, 50)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)
        
        text = self.font.render("RESET", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

class StartButton:
    def __init__(self):
        # Placed next to ResetButton
        self.rect = pygame.Rect(1380, SH - 60, 100, 40)
        self.font = pygame.font.SysFont('Roboto', 24, bold=True)
        self.hovered = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return True
        return False

    def render(self, screen):
        # Green Color for Start/Run
        color = (50, 150, 50) if self.hovered else (50, 100, 50)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)
        
        text = self.font.render("START", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

class PauseButton: 

    def __init__(self):
        # Placed instead of StartButton
        self.rect = pygame.Rect(1380, SH - 60, 100, 40)
        self.font = pygame.font.SysFont('Roboto', 24, bold=True)
        self.hovered = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered:
                return True
        return False

    def render(self, screen):
        # Yellow Color for Pause
        color = (200, 200, 50) if self.hovered else (150, 150, 50)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)
        
        text = self.font.render("PAUSE", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

class UnpauseButton(PauseButton):

    def render(self, screen):
        # Green Color for Unpause
        color = (50, 150, 50) if self.hovered else (50, 100, 50)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)
        self.rect = pygame.Rect(1380, SH - 60, 100, 40)
        text = self.font.render("UNPAUSE", True, (255, 255, 255))
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)

class WallCORSlider:
    """Slider for wall coefficient of restitution (0.0 to 1.0)"""
    def __init__(self, x, y, width, height, initial_value=0.9):
        self.rect = pygame.Rect(x, y, width, height)
        self.slider_rect = pygame.Rect(x, y + height // 2 - 5, width, 10)
        self.knob_radius = 8
        self.value = initial_value
        self.dragging = False
        self.font = pygame.font.SysFont('Arial', 14)
        self.label = "Wall Bounce:"
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob_x = self.slider_rect.x + self.value * self.slider_rect.width
            knob_rect = pygame.Rect(knob_x - self.knob_radius, self.slider_rect.y - self.knob_radius, 
                                   self.knob_radius * 2, self.knob_radius * 2)
            if knob_rect.collidepoint(event.pos):
                self.dragging = True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            # Update value based on mouse position
            relative_x = event.pos[0] - self.slider_rect.x
            self.value = max(0.0, min(1.0, relative_x / self.slider_rect.width))
            
    def render(self, screen):
        # Draw label
        #label_surf = self.font.render(self.label, True, (0, 0, 0))
        #screen.blit(label_surf, (self.rect.x, self.rect.y - 20))
        
        # Draw track
        pygame.draw.rect(screen, (200, 200, 200), self.slider_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.slider_rect, 1)
        
        # Draw filled portion (progress bar)
        filled_width = self.slider_rect.width * self.value
        filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, filled_width, self.slider_rect.height)
        pygame.draw.rect(screen, (100, 150, 255), filled_rect)
        
        # Draw knob
        knob_x = self.slider_rect.x + self.value * self.slider_rect.width
        knob_color = (50, 100, 200) if self.dragging else (100, 150, 255)
        pygame.draw.circle(screen, knob_color, (int(knob_x), int(self.slider_rect.centery)), self.knob_radius)
        pygame.draw.circle(screen, (0, 0, 0), (int(knob_x), int(self.slider_rect.centery)), self.knob_radius, 2)
        
        # Draw value text
        value_text = self.font.render(f"{self.value:.2f}", True, (0, 0, 0))
        screen.blit(value_text, (self.slider_rect.right + 10, self.slider_rect.centery - 7))

class ContextMenu:
    def __init__(self):
        self.active = False
        self.pos = (0, 0)
        self.rect = pygame.Rect(0, 0, 160, 30)
        self.font = pygame.font.SysFont('Arial', 16)

    def show(self, pos):
        self.active = True
        self.pos = pos
        self.rect.topleft = pos

    def handle_event(self, event):
        if not self.active: return None
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return "open_creator" # Clicked "Point Charge"
            else:
                self.active = False # Clicked away
        return None

    def render(self, screen):
        if not self.active: return
        pygame.draw.rect(screen, (240, 240, 240), self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 1)
        text = self.font.render("Create Charge", True, (0,0,0))
        screen.blit(text, (self.rect.x + 10, self.rect.y + 5))

# --- TEXT/TOGGLE COMPONENTS ---

class ScientificTextBox:
    """A text box that strictly accepts scientific notation inputs."""
    def __init__(self, x, y, w, h, default_text="1.0e-6"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = default_text
        self.active = False
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
                
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Strict filter: Digits, ., -, +, e, E
                if event.unicode in "0123456789.-+eE":
                    self.text += event.unicode

    def get_value(self):
        """Returns float if valid, None otherwise."""
        try:
            return float(self.text)
        except ValueError:
            return None

    def render(self, screen):
        # Border color indicates focus
        color = COL_ACTIVE if self.active else COL_INACTIVE
        pygame.draw.rect(screen, (255, 255, 255), self.rect)
        pygame.draw.rect(screen, color, self.rect, 2)
        
        # Text rendering
        text_surf = self.font.render(self.text, True, COL_TEXT)
        # Center text vertically
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 5, self.rect.centery))
        screen.blit(text_surf, text_rect)

class MantissaTextBox:
    """Text box that enforces x.y format (max 2 digits before decimal)."""
    def __init__(self, x, y, w, h, default_text="1.0"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = default_text
        self.active = False
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        self.allow0 = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
                
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Allow digits and one decimal point
                if event.unicode in "0123456789.":
                    # Prevent multiple decimal points
                    if event.unicode == "." and "." in self.text:
                        return
                    # Prevent more than 2 digits before decimal
                    if event.unicode.isdigit():
                        parts = self.text.split(".")
                        if len(parts[0]) >= 2:
                            return
                    self.text += event.unicode

    def get_value(self):
        """Returns float if valid, None otherwise."""
        try:
            val = float(self.text)
            if self.allow0:
                return val if val >= 0 else None
            else:
                return val if val > 0 else None
        except ValueError:
            return None

    def render(self, screen):
        color = COL_ACTIVE if self.active else COL_INACTIVE
        pygame.draw.rect(screen, (255, 255, 255), self.rect)
        pygame.draw.rect(screen, color, self.rect, 2)
        
        text_surf = self.font.render(self.text, True, COL_TEXT)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 5, self.rect.centery))
        screen.blit(text_surf, text_rect)

class ExponentTextBox:
    """Text box that enforces integer exponent from -99 to 99."""
    def __init__(self, x, y, w, h, default_text="0"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = default_text
        self.active = False
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
                
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Allow digits and one minus sign at the start
                if event.unicode in "0123456789-":
                    # Minus sign only at start and only one
                    if event.unicode == "-":
                        if len(self.text) == 0 or self.text[0] == "-":
                            if len(self.text) == 0:
                                self.text = "-"
                        return
                    # Limit to 2 digits (+ potential minus sign)
                    max_len = 3 if self.text.startswith("-") else 2
                    if len(self.text) < max_len:
                        self.text += event.unicode

    def get_value(self):
        """Returns float if valid, None otherwise."""
        try:
            val = int(self.text)
            return float(val) if -99 <= val <= 99 else None
        except ValueError:
            return None

    def render(self, screen):
        color = COL_ACTIVE if self.active else COL_INACTIVE
        pygame.draw.rect(screen, (255, 255, 255), self.rect)
        pygame.draw.rect(screen, color, self.rect, 2)
        
        text_surf = self.font.render(self.text, True, COL_TEXT)
        text_rect = text_surf.get_rect(midleft=(self.rect.x + 5, self.rect.centery))
        screen.blit(text_surf, text_rect)

class BinaryToggle:
    """A generic toggle button with customizable colors and text."""
    def __init__(self, x, y, w, h, label, initial_state=True, 
                 text_true="ON", text_false="OFF", 
                 col_true=COL_TRUE_STD, col_false=COL_FALSE_STD):
        
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label
        self.state = initial_state
        self.font = pygame.font.SysFont('Arial', 14, bold=True)
        
        # Custom Configuration
        self.text_true = text_true
        self.text_false = text_false
        self.col_true = col_true
        self.col_false = col_false

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                return True
        return False

    def render(self, screen):
        # Determine Color and Text based on state
        if self.state:
            bg_col = self.col_true
            status_txt = self.text_true
        else:
            bg_col = self.col_false
            status_txt = self.text_false
            
        pygame.draw.rect(screen, bg_col, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)
        
        # Status Text inside button
        txt_surf = self.font.render(status_txt, True, (255,255,255))
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        screen.blit(txt_surf, txt_rect)
        
        # Label Text above button
        if self.label:
            label_surf = self.font.render(self.label, True, (0,0,0))
            screen.blit(label_surf, (self.rect.x, self.rect.y - 18))

class TrailsToggle:
    """A simple toggle button labeled 'TRAILS' with white text and red/green background."""
    def __init__(self, x=140, y=SH-60, w=100, h=40, initial_state=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.state = initial_state
        self.font = pygame.font.SysFont('Arial', 18, bold=True)
        self.hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                return True
        return False

    def render(self, screen):
        # Background: green when ON, red when OFF
        bg = (50, 200, 50) if self.state else (200, 50, 50)
        # Slight brighten on hover
        if self.hovered:
            bg = tuple(min(255, int(c * 1.05)) for c in bg)
        pygame.draw.rect(screen, bg, self.rect)
        pygame.draw.rect(screen, (0,0,0), self.rect, 2)

        # White label centered
        txt = self.font.render("TRAILS", True, (255, 255, 255))
        txt_rect = txt.get_rect(center=self.rect.center)
        screen.blit(txt, txt_rect)

# --- NEW COMPONENT: ANGLE WHEEL ---
class AngleWheel:
    
    def __init__(self, x, y, radius=35, initial_angle=0.0):
        self.center = (x, y)
        self.radius = radius
        self.angle = initial_angle
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        self.dragging = False
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            dist = np.linalg.norm(np.array(event.pos) - np.array(self.center))
            if dist <= self.radius:
                self.dragging = True
                self.update_angle(event.pos)
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_angle(event.pos)
            return True
        return False

    def update_angle(self, mouse_pos):
        dx = mouse_pos[0] - self.center[0]
        dy = mouse_pos[1] - self.center[1]
        # Pygame Y is down, so mathematical angle needs adjustment if we want standard trig
        self.angle = np.arctan2(dy, dx)   
        
    def render(self, screen):
        # Update rect position in case center moved (e.g. when form moves)
        self.rect.topleft = (self.center[0] - self.radius, self.center[1] - self.radius)
        
        pygame.draw.circle(screen, (220, 220, 220), self.center, self.radius)
        pygame.draw.circle(screen, (0, 0, 0), self.center, self.radius, 2)
        
        end_x = self.center[0] + self.radius * np.cos(self.angle)
        end_y = self.center[1] + self.radius * np.sin(self.angle)
        pygame.draw.line(screen, (200, 0, 0), self.center, (end_x, end_y), 3)
        pygame.draw.circle(screen, (0, 0, 0), self.center, 4)

class CreationForm:
    def __init__(self):
        self.active = False
        self.rect = pygame.Rect(0, 0, 380, 500) # INCREASED HEIGHT to 500
        self.target_pos = (0,0)
        self.font = pygame.font.SysFont('Arial', 16, bold=True)
        self.edit_mode = False
        self.editing_particle = None
        
        self.creation_memory = {} 

        # --- COMPONENTS ---
        self.btn_remember = BinaryToggle(0, 0, 120, 25, "Remember Input", False)
        self.btn_charge_sign = BinaryToggle(0, 0, 50, 30, "", True, text_true="+", text_false="-", col_true=COL_POS, col_false=COL_NEG)
        self.input_charge_mantissa = MantissaTextBox(0, 0, 80, 30, "1.0")
        self.input_charge_mantissa.allow0 = True
        self.input_charge_exponent = ExponentTextBox(0, 0, 60, 30, "0")
        self.input_mass_mantissa = MantissaTextBox(0, 0, 80, 30, "1.0")
        self.input_mass_exponent = ExponentTextBox(0, 0, 60, 30, "0")
        self.btn_env = BinaryToggle(0, 0, 60, 30, "Env", True)
        self.btn_static = BinaryToggle(0, 0, 60, 30, "Static", False)
        self.slider_restitution = WallCORSlider(0, 0, 160, 20, initial_value=1.0) # change its label
        self.slider_restitution.label = "Restitution:"
        
        # --- VELOCITY COMPONENTS ---
        self.angle_wheel = AngleWheel(0, 0, 35, initial_angle=0.0) # Radius 35
        self.input_vel_mantissa = MantissaTextBox(0, 0, 80, 30, "0")
        self.input_vel_mantissa.allow0 = True
        self.input_vel_exponent = ExponentTextBox(0, 0, 60, 30, "0")
        
        # Buttons
        self.btn_submit = pygame.Rect(0,0, 100, 30)
        self.btn_cancel = pygame.Rect(0,0, 100, 30)
        self.btn_delete = pygame.Rect(0,0, 100, 30)

    def show(self, pos, particle=None):
        self.active = True
        self.target_pos = pos
        self.edit_mode = particle is not None
        self.editing_particle = particle
        self.rect.center = (SW//2, SH//2)
        
        if self.edit_mode and particle:
            charge_val = abs(particle.charge)
            if charge_val == 0: c_mantissa, c_exponent = 0.0, 0
            else:
                import math
                c_exponent = int(math.floor(math.log10(charge_val)))
                c_mantissa = charge_val / (10 ** c_exponent)
            
            mass_val = particle.mass
            if mass_val == 0: m_mantissa, m_exponent = 1.0, 0
            else:
                import math
                m_exponent = int(math.floor(math.log10(mass_val)))
                m_mantissa = mass_val / (10 ** m_exponent)
            
            # Velocity load
            vel_vector = particle.vel_0
            vel_mag = np.linalg.norm(vel_vector)
            vel_angle = np.arctan2(vel_vector[1], vel_vector[0])
            
            if vel_mag == 0: v_mantissa, v_exponent = 0.0, 0
            else:
                import math
                v_exponent = int(math.floor(math.log10(vel_mag)))
                v_mantissa = vel_mag / (10 ** v_exponent)

            self.input_charge_mantissa.text = f"{c_mantissa:.1f}"
            self.input_charge_exponent.text = str(c_exponent)
            self.input_mass_mantissa.text = f"{m_mantissa:.1f}"
            self.input_mass_exponent.text = str(m_exponent)
            
            self.input_vel_mantissa.text = f"{v_mantissa:.1f}"
            self.input_vel_exponent.text = str(v_exponent)
            self.angle_wheel.angle = vel_angle
            
            self.btn_charge_sign.state = particle.charge >= 0
            self.btn_env.state = particle.environmental
            self.btn_static.state = particle.static
            try:
                self.slider_restitution.value = float(particle.e)
            except Exception:
                self.slider_restitution.value = 1.0

        elif self.btn_remember.state and self.creation_memory:
            # LOAD FROM MEMORY
            self.input_charge_mantissa.text = self.creation_memory.get('c_man', "1.0")
            self.input_charge_exponent.text = self.creation_memory.get('c_exp', "0")
            self.input_mass_mantissa.text = self.creation_memory.get('m_man', "1.0")
            self.input_mass_exponent.text = self.creation_memory.get('m_exp', "0")
            self.input_vel_mantissa.text = self.creation_memory.get('v_man', "0.0")
            self.input_vel_exponent.text = self.creation_memory.get('v_exp', "0")
            self.angle_wheel.angle = self.creation_memory.get('v_angle', 0.0)
            
            self.btn_charge_sign.state = self.creation_memory.get('sign', True)
            self.btn_env.state = self.creation_memory.get('env', True)
            self.btn_static.state = self.creation_memory.get('static', True)
            self.slider_restitution.value = self.creation_memory.get('restitution', 1.0)

        else:
            # DEFAULT
            self.input_charge_mantissa.text = "1.0"
            self.input_charge_exponent.text = "0"
            self.input_mass_mantissa.text = "1.0"
            self.input_mass_exponent.text = "0"
            self.input_vel_mantissa.text = "0.0"
            self.input_vel_exponent.text = "0"
            self.angle_wheel.angle = 0.0
            
            self.btn_charge_sign.state = True
            self.btn_env.state = True  
            self.btn_static.state = False
            self.slider_restitution.value = 1.0
            
        # --- LAYOUT CALCULATION (FIXED SPACING) ---
        rx, ry = self.rect.x, self.rect.y
        self.btn_remember.rect.topright = (self.rect.right - 20, ry + 35)
        
        # Charge (Y=100)
        self.btn_charge_sign.rect.topleft = (rx + 40, ry + 100)
        self.input_charge_mantissa.rect.topleft = (rx + 100, ry + 100)
        self.input_charge_exponent.rect.topleft = (rx + 290, ry + 100) # Pushed Right
        
        # Mass (Y=170)
        self.input_mass_mantissa.rect.topleft = (rx + 100, ry + 170)
        self.input_mass_exponent.rect.topleft = (rx + 290, ry + 170) # Pushed Right
        
        # Restitution, need to fix the labels
        self.slider_restitution.rect.topleft = (rx + 100, ry + 240)
        self.slider_restitution.slider_rect.topleft = (rx + 100, ry + 240 + 20 // 2 - 5)
        
        # Velocity (Y=310)
        self.angle_wheel.center = (rx + 75, ry + 300 + 15) # Centered for 35px height box
        self.input_vel_mantissa.rect.topleft = (rx + 140, ry + 300)
        self.input_vel_exponent.rect.topleft = (rx + 270, ry + 300) # Pushed Right

        # Toggles (Y=390)
        self.btn_env.rect.topleft = (rx + 50, ry + 380)
        self.btn_static.rect.topleft = (rx + 200, ry + 380)
        
        # Buttons
        self.btn_submit.bottomleft = (rx + 30, self.rect.bottom - 25)
        self.btn_delete.midbottom = (self.rect.centerx, self.rect.bottom - 25)
        self.btn_cancel.bottomright = (self.rect.right - 30, self.rect.bottom - 25)

    def handle_event(self, event):
        if not self.active: return None

        self.input_charge_mantissa.handle_event(event)
        self.input_charge_exponent.handle_event(event)
        self.input_mass_mantissa.handle_event(event)
        self.input_mass_exponent.handle_event(event)
        self.input_vel_mantissa.handle_event(event)
        self.input_vel_exponent.handle_event(event)
        self.angle_wheel.handle_event(event)
        
        self.btn_remember.handle_event(event)
        self.btn_charge_sign.handle_event(event)
        self.btn_env.handle_event(event)
        self.btn_static.handle_event(event)
        self.slider_restitution.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_submit.collidepoint(event.pos):
                c_man = self.input_charge_mantissa.get_value()
                c_exp = self.input_charge_exponent.get_value()
                m_man = self.input_mass_mantissa.get_value()
                m_exp = self.input_mass_exponent.get_value()
                v_man = self.input_vel_mantissa.get_value()
                v_exp = self.input_vel_exponent.get_value()
                cor_val = getattr(self.slider_restitution, 'value', 1.0)
                
                # Validation
                if (c_man is not None and c_exp is not None and 
                    m_man is not None and m_exp is not None and
                    v_man is not None and v_exp is not None):
                    
                    if c_man >= 0 and c_man <= 9.9 and 1.0 <= m_man <= 9.9 and v_man >= 0:
                        
                        if self.btn_remember.state and not self.edit_mode:
                            self.creation_memory = {
                                'c_man': self.input_charge_mantissa.text,
                                'c_exp': self.input_charge_exponent.text,
                                'm_man': self.input_mass_mantissa.text,
                                'm_exp': self.input_mass_exponent.text,
                                'v_man': self.input_vel_mantissa.text,
                                'v_exp': self.input_vel_exponent.text,
                                'v_angle': self.angle_wheel.angle,
                                'sign': self.btn_charge_sign.state,
                                'env': self.btn_env.state,
                                'static': self.btn_static.state,
                                'restitution': cor_val
                            }

                        charge = c_man * (10 ** c_exp)
                        if not self.btn_charge_sign.state: charge = -charge
                        mass = m_man * (10 ** m_exp)
                        
                        vel_mag = v_man * (10 ** v_exp)
                        angle = self.angle_wheel.angle
                        vx = vel_mag * np.cos(angle)
                        vy = vel_mag * np.sin(angle)
                        velocity_vector = np.array([vx, vy], dtype=float)
                        
                        if mass > 0:
                            self.active = False
                            result = {
                                "pos": self.target_pos,
                                "charge": charge,
                                "mass": mass,
                                "velocity": velocity_vector,
                                "environmental": self.btn_env.state,
                                "static": self.btn_static.state,
                                "e": np.clip(cor_val, 0.0, 2.0)
                            }
                            
                            if self.edit_mode:
                                result["particle"] = self.editing_particle
                                result["edit"] = True
                            else:
                                result["position"] = np.array(self.target_pos, dtype=float)
                                result["delete"] = False
                            return result
            
            elif self.edit_mode and self.btn_delete.collidepoint(event.pos):
                self.active = False
                return {"delete": True, "particle": self.editing_particle}

            elif self.btn_cancel.collidepoint(event.pos):
                self.active = False
                return None
        return None

    def render(self, screen):
        if not self.active: return
        pygame.draw.rect(screen, COL_BG, self.rect)
        pygame.draw.rect(screen, COL_BORDER, self.rect, 2)
        
        title_text = "Edit Charge" if self.edit_mode else "Create Charge"
        title = self.font.render(title_text, True, COL_TEXT)
        screen.blit(title, (self.rect.x + 20, self.rect.y + 20))
        
        # Labels
        l_chg = self.font.render("Charge:", True, COL_TEXT)
        screen.blit(l_chg, (self.rect.x + 100, self.input_charge_mantissa.rect.top - 20))
        l_mass = self.font.render("Mass:", True, COL_TEXT)
        screen.blit(l_mass, (self.rect.x + 100, self.input_mass_mantissa.rect.top - 20))
        l_cor = self.font.render("Bounce:", True, COL_TEXT)
        screen.blit(l_cor, (self.rect.x + 100, self.slider_restitution.rect.top - 20))
        
        l_vel = self.font.render("Initial Velocity:", True, COL_TEXT)
        screen.blit(l_vel, (self.rect.x + 140, self.input_vel_mantissa.rect.top - 20))

        # Exponent Labels (x 10 ^)
        exp_c = self.font.render("x 10 ^", True, COL_TEXT)
        screen.blit(exp_c, (self.input_charge_mantissa.rect.right + 10, self.input_charge_mantissa.rect.centery - 8))
        exp_m = self.font.render("x 10 ^", True, COL_TEXT)
        screen.blit(exp_m, (self.input_mass_mantissa.rect.right + 10, self.input_mass_mantissa.rect.centery - 8))
        exp_v = self.font.render("x 10 ^", True, COL_TEXT)
        screen.blit(exp_v, (self.input_vel_mantissa.rect.right + 10, self.input_vel_mantissa.rect.centery - 8))

        # Render Components
        self.btn_remember.render(screen)
        self.btn_charge_sign.render(screen)
        self.input_charge_mantissa.render(screen)
        self.input_charge_exponent.render(screen)
        self.input_mass_mantissa.render(screen)
        self.input_mass_exponent.render(screen)
        self.slider_restitution.render(screen)
        self.angle_wheel.render(screen)
        self.input_vel_mantissa.render(screen)
        self.input_vel_exponent.render(screen)
        
        self.btn_env.render(screen)
        self.btn_static.render(screen)
        
        pygame.draw.rect(screen, (100, 200, 100), self.btn_submit)
        pygame.draw.rect(screen, (0,0,0), self.btn_submit, 1)
        submit_text = "CHANGE" if self.edit_mode else "SPAWN"
        ts = self.font.render(submit_text, True, (0,0,0))
        ts_rect = ts.get_rect(center=self.btn_submit.center)
        screen.blit(ts, ts_rect)
        
        pygame.draw.rect(screen, (200, 100, 100), self.btn_cancel)
        pygame.draw.rect(screen, (0,0,0), self.btn_cancel, 1)
        tc = self.font.render("CANCEL", True, (0,0,0))
        tc_rect = tc.get_rect(center=self.btn_cancel.center)
        screen.blit(tc, tc_rect)

        if self.edit_mode:
            pygame.draw.rect(screen, (50, 50, 50), self.btn_delete)
            pygame.draw.rect(screen, (0,0,0), self.btn_delete, 1)
            td = self.font.render("DELETE", True, (255,255,255))
            td_rect = td.get_rect(center=self.btn_delete.center)
            screen.blit(td, td_rect)

# for more sliders

class GenericSlider:
    """A reusable slider for any numeric value."""
    def __init__(self, x, y, width, height, min_val, max_val, initial_val, label, fmt="{:.4f}"):
        self.rect = pygame.Rect(x, y, width, height)
        self.slider_rect = pygame.Rect(x, y + height // 2 - 5, width, 10)
        self.knob_radius = 8
        
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.fmt = fmt # Format string for text (e.g., 4 decimal places)
        self.label = label
        
        self.dragging = False
        self.font = pygame.font.SysFont('Arial', 14)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check knob collision based on current value
            val_norm = (self.value - self.min_val) / (self.max_val - self.min_val)
            knob_x = self.slider_rect.x + val_norm * self.slider_rect.width
            knob_rect = pygame.Rect(knob_x - self.knob_radius, self.slider_rect.y - self.knob_radius, 
                                   self.knob_radius * 2, self.knob_radius * 2)
            
            # Allow clicking anywhere on the bar to jump
            if knob_rect.collidepoint(event.pos) or self.slider_rect.collidepoint(event.pos):
                self.dragging = True
                self.update_from_mouse(event.pos)
                return True
                
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_from_mouse(event.pos)
            return True
        return False

    def update_from_mouse(self, mouse_pos):
        relative_x = mouse_pos[0] - self.slider_rect.x
        ratio = max(0.0, min(1.0, relative_x / self.slider_rect.width))
        self.value = self.min_val + ratio * (self.max_val - self.min_val)

    def render(self, screen):
        # Label
        label_surf = self.font.render(self.label, True, (0, 0, 0))
        screen.blit(label_surf, (self.rect.x, self.rect.y - 20))
        
        # Track
        pygame.draw.rect(screen, (200, 200, 200), self.slider_rect)
        pygame.draw.rect(screen, (0, 0, 0), self.slider_rect, 1)
        
        # Normalized position for drawing
        val_norm = (self.value - self.min_val) / (self.max_val - self.min_val)
        
        # Filled portion
        filled_width = self.slider_rect.width * val_norm
        filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, filled_width, self.slider_rect.height)
        pygame.draw.rect(screen, (100, 150, 255), filled_rect)
        
        # Knob
        knob_x = self.slider_rect.x + val_norm * self.slider_rect.width
        knob_color = (50, 100, 200) if self.dragging else (100, 150, 255)
        pygame.draw.circle(screen, knob_color, (int(knob_x), int(self.slider_rect.centery)), self.knob_radius)
        pygame.draw.circle(screen, (0, 0, 0), (int(knob_x), int(self.slider_rect.centery)), self.knob_radius, 2)
        
        # Value Text
        value_text = self.font.render(self.value_text(), True, (0, 0, 0))
        screen.blit(value_text, (self.slider_rect.right + 10, self.slider_rect.centery - 7))

    def value_text(self):
        return self.fmt.format(self.value)

class LogSlider(GenericSlider):
    """A GenericSlider whose knob moves linearly in log10(value), for quantities
    that span many orders of magnitude. self.value holds log10; use real_value."""
    def __init__(self, x, y, width, height, min_val, max_val, initial_val, label):
        super().__init__(x, y, width, height, np.log10(min_val), np.log10(max_val),
                         np.log10(initial_val), label)

    @property
    def real_value(self):
        return 10.0 ** self.value

    def value_text(self):
        return f"{self.real_value:.2e}"
