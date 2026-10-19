# below is point_charges.py

# necessary imports

import pygame 
import numpy as np
import colorsys
from constants_for_all_files import *
from collections import deque

# --- ARROW CLASS (ENCAPSULATED) ---
class Arrow:
    def __init__(self, start_pos, length, angle, color=(0, 0, 0), thickness=2):
        self.start_pos = np.array(start_pos, dtype=float)
        self.length = length
        self.angle = angle 
        self.color = color
        self.thickness = thickness

    def update(self, start_pos, length, angle):
        self.start_pos = np.array(start_pos, dtype=float)
        self.length = length
        self.angle = angle

    def render(self, screen):
        if self.length < 1: return 

        # 1. Calculate End Point
        end_x = self.start_pos[0] + self.length * np.cos(self.angle)
        end_y = self.start_pos[1] + self.length * np.sin(self.angle)
        end_pos = (end_x, end_y)

        # 2. Draw Shaft
        pygame.draw.line(screen, self.color, self.start_pos, end_pos, self.thickness)

        # 3. Draw Head
        head_len = 10 
        head_angle = np.radians(150) 
        
        p1_x = end_x + head_len * np.cos(self.angle + head_angle)
        p1_y = end_y + head_len * np.sin(self.angle + head_angle)

        p2_x = end_x + head_len * np.cos(self.angle - head_angle)
        p2_y = end_y + head_len * np.sin(self.angle - head_angle)

        pygame.draw.polygon(screen, self.color, [end_pos, (p1_x, p1_y), (p2_x, p2_y)])


# Point Charge Class

class PointCharge:

    def __init__(self, pos_0, charge, mass, environmental, static, pc_id, e, vel0):
        self.position = np.array(pos_0, dtype=float)
        self.vel = np.array(vel0, dtype=float)
        self.pos_0 = np.array(pos_0, dtype=float)
        self.vel_0 = np.array(vel0, dtype=float)
        self.charge = charge
        self.mass = mass
        self.environmental = environmental
        self.static = static
        self.pc_id = pc_id
        self.dragging = False
        self.e = e

        # Larmor radiation state, written by the physics engine each step
        self.rad_power = 0.0
        self.rad_accel = np.zeros(2)
        self.rad_timer = 0.0     # simulated seconds until this charge's next wavefront is drawn

        # Radius setup
        self.core_radius = 15
        self.border_radius = 6
        self.total_radius = self.core_radius + self.border_radius

        if charge > 0:
            self.color = (200, 0, 0)
        elif charge < 0:
            self.color = (0, 0, 200)
        else:
            self.color = (80, 80, 80)  # Darker grey for neutral

        # Trails
        self.history = deque(maxlen=TRAIL_LENGTH)
        self.frame_counter = 0
        self.ghost_surf = pygame.Surface((self.total_radius*2, self.total_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.ghost_surf, self.color, (self.total_radius, self.total_radius), int(self.core_radius))

        # --- ARROW SETUP (FIXED) ---
        # Arrow color: black for positive, white for negative
        arrow_color = (0, 0, 0) if charge > 0 else (255, 255, 255)
        self.arrow_obj = Arrow(self.position, 0, 0, color=arrow_color, thickness=3)
        self.arrow_display = True

    @property
    def pos(self):
        """Property to always return current position (for compatibility with electric_field.py)."""
        return self.position
    
    def update_relative_scale(self, all_charges):
        if not all_charges: return

        # --- 1. Radius Calculation (Existing) ---
        # Neutral charges (charge == 0) get middle core radius (12.5px)
        if self.charge == 0:
            self.core_radius = 12.5
        else:
            max_q = max(abs(pc.charge) for pc in all_charges)
            min_q = min(abs(pc.charge) for pc in all_charges)
            q_range = max_q - min_q
            
            current_q = abs(self.charge)
            norm_q = (current_q - min_q) / q_range if q_range != 0 else 0.5
            self.core_radius = 5 + (norm_q * 15)

        # --- 2. Border Calculation (Existing) ---
        max_m = max(pc.mass for pc in all_charges)
        min_m = min(pc.mass for pc in all_charges)
        m_range = max_m - min_m
        
        current_m = self.mass
        norm_m = (current_m - min_m) / m_range if m_range != 0 else 0.5
        self.border_radius = 1 + (norm_m * 4)
        self.total_radius = self.core_radius + self.border_radius
        
        # Update ghost surf
        self.ghost_surf = pygame.Surface((int(self.total_radius*2), int(self.total_radius*2)), pygame.SRCALPHA)
        pygame.draw.circle(self.ghost_surf, self.color, (int(self.total_radius), int(self.total_radius)), int(self.core_radius))

        # --- 3. ARROW UPDATE (New) ---
        # Only update arrows for dynamic particles
        if not self.static:
            # Get magnitude of initial velocity
            my_vel_mag = np.linalg.norm(self.vel_0)
            
            # Find max/min velocity in the system for relative scaling
            velocities = [np.linalg.norm(p.vel_0) for p in all_charges if not p.static]
            if not velocities:
                max_v, min_v = 0, 0
            else:
                max_v, min_v = max(velocities), min(velocities)
            
            # Scale arrow length between 30px and 100px based on relative speed
            v_range = max_v - min_v
            if v_range == 0:
                scale = 0.5 if max_v > 0 else 0
            else:
                scale = (my_vel_mag - min_v) / v_range
            
            length = 0 if my_vel_mag == 0 else 30 + (scale * 70)
            angle = np.arctan2(self.vel_0[1], self.vel_0[0])
            
            # Update the internal Arrow object
            self.arrow_obj.update(self.position, length, angle)

    def reset(self):
        # Always revert to initial state (position and velocity)
        self.position = self.pos_0.copy()
        self.vel = self.vel_0.copy()
        self.rad_power = 0.0
        self.rad_accel = np.zeros(2)
        self.rad_timer = 0.0
        # also reset trail history when resetting particle
        try:
            self.history.clear()
            self.frame_counter = 0
        except Exception:
            pass

    # Helper for angle calc
    @staticmethod
    def calc_phi(v): 
        # returns angle in radians for vector v
        if v[0] == 0 and v[1] == 0: return 0.0
        return np.arctan2(v[1], v[0])

    def update_arrow(self, all_charges):
        """Calculates arrow length and angle based on relative velocity."""
        if not all_charges: return

        if self.charge < 0:
            self.arrow_obj.color = (255, 255, 255)  # White for negative charges
        else:
            self.arrow_obj.color = (0, 0, 0)  # Black for positive charges

        angle = PointCharge.calc_phi(self.vel_0)

        # Scaling logic for length
        # Find max velocity in the system to normalize arrow length
        max_v0 = max(np.linalg.norm(pc.vel_0) for pc in all_charges)
        min_v0 = min(np.linalg.norm(pc.vel_0) for pc in all_charges)
        
        # Avoid zero range div
        if max_v0 == 0:
            length = 0
        else:
            this_v0_mag = np.linalg.norm(self.vel_0)
            # Scale between 20px and 80px
            if max_v0 == min_v0:
                scale = 1.0 if max_v0 > 0 else 0
            else:
                scale = (this_v0_mag - min_v0) / (max_v0 - min_v0)
            
            # Base length 20, max add 60
            length = 20 + (scale * 60) if this_v0_mag > 0 else 0

        self.arrow_obj.update(self.position, length, angle)
    
    def render(self, screen):
        # --- RENDER ARROW FIRST (underneath particle) ---
        # Only if enabled, not static, and velocity is not zero
        if self.arrow_display and not self.static and np.linalg.norm(self.vel_0) > 0:
            self.arrow_obj.render(screen)
        
        # Draw Border
        if self.charge > 0: border_col = (220, 90, 90)
        elif self.charge < 0: border_col = (130, 20, 130)
        else: border_col = (255, 182, 193)  # Light pink for neutral
            
        pygame.draw.circle(screen, border_col, self.position.astype(int), int(self.total_radius))
        
        # Draw Core
        pygame.draw.circle(screen, self.color, self.position.astype(int), int(self.core_radius))
        
        # Selection Highlight
        if self.dragging:
            pygame.draw.circle(screen, (255, 255, 255), self.position.astype(int), int(self.total_radius + 2), 2)
            self.position = np.array(pygame.mouse.get_pos(), dtype=float)

    def record_trail(self, enabled=False):
        """Record current position into history when enabled.
        Records every TRAIL_SKIP frames. Clears history immediately when disabled.
        """
        if enabled:
            self.frame_counter += 1
            if self.frame_counter % TRAIL_SKIP == 0:
                # store a copy to avoid mutation
                self.history.append(self.position.copy())
        else:
            # Clear history immediately when disabled
            if self.history:
                self.history.clear()
            self.frame_counter = 0

    def render_trails(self, screen):
        """Render the stored trail positions with a simple fade effect.
        Older positions are more transparent. Uses small temporary surfaces with per-surface alpha.
        """
        if not self.history:
            return

        length = len(self.history)
        # Draw from oldest to newest so newer points appear on top
        for i, pos in enumerate(self.history):
            if length > 1:
                t = i / (length - 1)
            else:
                t = 1.0
            # Alpha from 40 (oldest) -> 230 (newest)
            alpha = int(40 + (230 - 40) * t)

            # Draw a small filled circle using a temporary surface to allow alpha
            r = max(1, int(self.core_radius))
            surf_size = r * 2 + 4
            surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            col = (self.color[0], self.color[1], self.color[2], alpha)
            pygame.draw.circle(surf, col, (surf_size // 2, surf_size // 2), r)
            blit_pos = (int(pos[0] - surf_size // 2), int(pos[1] - surf_size // 2))
            screen.blit(surf, blit_pos)

    def resolve_collision(self, other):
        """
        Resolves elastic collision with another PointCharge.
        Handles position correction (un-sticking) and velocity impulse.
        """
        # 1. Get distance vector and magnitude
        diff = self.position - other.position
        dist_sq = np.dot(diff, diff)
        min_dist = self.total_radius + other.total_radius
        
        # Optimization: Check squared distance first to avoid sqrt() if not needed
        if dist_sq >= min_dist * min_dist:
            return

        # --- COLLISION DETECTED! ---
        dist = np.sqrt(dist_sq)

        # 2. Position Correction (Prevent Sticking/Ghosting)
        # If distance is 0 (exact overlap), pick random direction to avoid divide-by-zero
        if dist == 0:
            n = np.array([1.0, 0.0])
            overlap = min_dist
        else:
            n = diff / dist # Normal vector (Direction of collision)
            overlap = min_dist - dist
        
        # Move particles apart so they just touch
        # If one is static, the other moves the full distance
        if not self.static and not other.static:
            self.position += n * (overlap / 2.0)
            other.position -= n * (overlap / 2.0)
        elif not self.static and other.static:
            self.position += n * overlap
        elif self.static and not other.static:
            other.position -= n * overlap
        else:
            return # Both static, nothing happens

        # 3. Velocity Response (1D Elastic Collision along the Normal)
        # Relative velocity
        v_rel = self.vel - other.vel
        
        # Velocity along the normal
        vel_along_normal = np.dot(v_rel, n)

        # Do not resolve if velocities are separating (they are already moving away)
        if vel_along_normal > 0:
            return

        # Elasticity (1.0 = Perfectly Elastic, 0.0 = Sticky)
        # Use an effective restitution combining both bodies (choose the smaller)
        try:
            e = min(float(self.e), float(other.e))
        except Exception:
            e = 1.0

        # Calculate Impulse Scalar (J)
        # J = -(1 + e) * (v_rel . n) / (1/m1 + 1/m2)
        inv_mass1 = 0 if self.static else 1.0 / self.mass
        inv_mass2 = 0 if other.static else 1.0 / other.mass
        
        # Infinite mass check
        if inv_mass1 + inv_mass2 == 0:
            return

        j = -(1 + e) * vel_along_normal
        j /= (inv_mass1 + inv_mass2)

        # Apply Impulse Vector
        impulse = j * n
        
        if not self.static:
            self.vel += impulse * inv_mass1
        if not other.static:
            other.vel -= impulse * inv_mass2

    def exert_force(self, other):

        # Calculate the electric force exerted on this charge by another charge
        k = 8.9875517873681764e9 # Coulomb's constant in N·m²/C²
        diff = other.position - self.position
        dist = np.linalg.norm(diff)
        if dist == 0:
            return np.array([0.0, 0.0]) # Avoid divide by zero

        force_magnitude = k * abs(self.charge * other.charge) / (dist ** 2)
        force_direction = diff / dist

        # Determine if the force is attractive or repulsive
        if self.charge * other.charge > 0:
            force_direction = -force_direction # Repulsive force

        force = force_direction * force_magnitude
        return force


# --- RADIATION RENDERING ---

HUE_RED = 0.0           # slowest motion on screen
HUE_VIOLET = 0.76       # fastest motion on screen (~273 deg, spectral violet)
OMEGA_DECADES = 4       # hue range spans at most 4 decades of omega below the fastest
POWER_DECADES = 6       # charges radiating < 1e-6 of the strongest are not drawn

ARC_HALF_ANGLE = np.radians(45)  # 90 deg arcs: sin^2(theta) >= 1/2 for theta in 45..135 deg (half-power width)
ARC_SEGMENTS = 10                # brightness steps along each arc (bright centre, fading ends)
RIPPLES_PER_CYCLE = 1   # wavefronts per cycle of the motion: 1 = the ripple frequency IS the motion's frequency
WAVE_SPEED = 4000.0     # px per simulated second. Display only: the real c would cross the screen in ~5 microseconds.
                        # It has to beat the charges' own speeds (~2000 px/s) or a charge outruns its light
FADE_DISTANCE = 1400.0  # px a wavefront travels before it has faded out
WAVE_LIFETIME = FADE_DISTANCE / WAVE_SPEED   # simulated seconds
MAX_WAVES = 500         # oldest wavefronts are dropped beyond this, to keep the frame rate up

def _log_norm(values, decades):
    """Map values onto 0..1 by log10, relative to the largest on screen.
    Logarithmic because Larmor power ~ a^2 ~ 1/r^4 spans many orders of magnitude;
    a linear scale would leave everything but the strongest at the bottom."""
    logs = np.log10(values)
    hi = logs.max()
    lo = max(logs.min(), hi - decades)
    if hi - lo < 1e-12:
        return np.ones_like(logs)       # all equal: they are all "the strongest"
    return np.clip((logs - lo) / (hi - lo), 0.0, 1.0)


class Wavefront:
    """One outgoing arc of light. It stays centred on the point where it was emitted
    (light does not follow its source), and grows and fades as it ages."""
    __slots__ = ("origin", "direction", "r0", "colour", "strength", "age")

    def __init__(self, origin, direction, r0, colour, strength):
        self.origin = np.array(origin, dtype=float)
        self.direction = direction      # angle of the arc's centre (perpendicular to the acceleration)
        self.r0 = r0                    # starting radius: the edge of the particle
        self.colour = colour
        self.strength = strength        # 0..1, relative radiated power
        self.age = 0.0


class RadiationRenderer:
    """
    Draw Larmor radiation as wavefronts leaving each accelerating charge.

    Shape: dP/dOmega ∝ sin^2(theta), theta from the acceleration, so light goes out
    sideways to the net force and none along it. Each emission is a pair of 90-degree
    arcs, one on each side, covering the half-power width of that pattern; brightness
    along an arc follows the pattern, brightest in the middle and fading to the ends.

    Colour: the characteristic frequency of the motion, omega = |a| / |v|
    (exact for circular motion, where a = v*omega). Faster-turning charges are bluer:
    red = slowest on screen, violet = fastest. It is a relative scale, not the true colour.
    The ripples themselves are one to one with the motion: a charge sends out one
    wavefront pair per cycle, T = 2*pi / omega in simulated time, so twice the frequency
    gives twice the ripples and half the wavelength on screen.

    Brightness: relative radiated power (log scale), fading with distance travelled.
    """

    def __init__(self):
        self.waves = []
        self._overlay = None

    def clear(self):
        self.waves.clear()

    def update(self, all_charges, sim_dt):
        """Age the existing wavefronts and emit new ones, in simulated time, so the
        ripples keep step with the motion at any dt / FPS and freeze when paused."""
        for w in self.waves:
            w.age += sim_dt
        self.waves = [w for w in self.waves if w.age < WAVE_LIFETIME]

        radiating = [pc for pc in all_charges
                     if pc.rad_power > 0 and np.linalg.norm(pc.vel) > 0]
        if not radiating:
            return

        power = np.array([pc.rad_power for pc in radiating])
        omega = np.array([np.linalg.norm(pc.rad_accel) / np.linalg.norm(pc.vel) for pc in radiating])
        p_norm = _log_norm(power, POWER_DECADES)
        w_norm = _log_norm(omega, OMEGA_DECADES)
        p_floor = power.max() * 10.0**-POWER_DECADES
        omega_of = {id(pc): w for pc, w in zip(radiating, omega)}

        for pc, p, pn, wn in zip(radiating, power, p_norm, w_norm):
            pc.rad_timer -= sim_dt
            if p < p_floor or pc.rad_timer > 0:
                continue
            # One ripple per period of the motion, T = 2*pi / omega: the frequency on screen is
            # the true frequency, so wavelength on screen = WAVE_SPEED * T, exactly proportional to 1/omega
            period = 2 * np.pi / omega_of[id(pc)] / RIPPLES_PER_CYCLE
            pc.rad_timer = max(pc.rad_timer + period, 0.0)   # += keeps the rhythm exact between frames

            hue = HUE_RED + wn * (HUE_VIOLET - HUE_RED)
            colour = tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hue, 0.9, 1.0))
            strength = 0.35 + 0.65 * pn
            phi_a = np.arctan2(pc.rad_accel[1], pc.rad_accel[0])
            for side in (+1, -1):
                self.waves.append(Wavefront(pc.position, phi_a + side * np.pi / 2,
                                            pc.total_radius, colour, strength))

        if len(self.waves) > MAX_WAVES:
            self.waves = self.waves[-MAX_WAVES:]

    def render(self, screen):
        if not self.waves:
            return
        if self._overlay is None or self._overlay.get_size() != screen.get_size():
            self._overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay = self._overlay
        overlay.fill((0, 0, 0, 0))
        overlay.set_clip(WALL_INNER_RECT)       # light stays inside the walls

        lo = np.array([np.inf, np.inf])       # bounding box of everything drawn
        hi = -lo
        for w in self.waves:
            life = w.age / WAVE_LIFETIME
            fade = w.strength * (1.0 - life) ** 1.5
            if fade < 0.04:
                continue
            radius = w.r0 + WAVE_SPEED * w.age
            half_core = 1.0 + 2.0 * (1.0 - life)    # wavefronts thin out as they spread
            unit = _rotate(_ARC_UNIT, w.direction)
            r, g, b = w.colour
            # whiter core, so the arc reads as light rather than paint
            core = (int(r + 0.45 * (255 - r)), int(g + 0.45 * (255 - g)), int(b + 0.45 * (255 - b)))
            # a soft glow, then the bright core on top
            for half, colour, peak in ((half_core + 4, (r, g, b), 90),
                                       (half_core, core, 255)):
                o = (w.origin + (radius + half) * unit).tolist()
                n = (w.origin + max(radius - half, 0.0) * unit).tolist()
                seg_alpha = (peak * fade * _ARC_TAPER).astype(int).tolist()
                for k in range(ARC_SEGMENTS):
                    if seg_alpha[k] < 4:
                        continue
                    # one curved band per segment; neighbours share edges, so no seams
                    pygame.draw.polygon(overlay, colour + (seg_alpha[k],), (o[k], o[k + 1], n[k + 1], n[k]))
            lo = np.minimum(lo, w.origin - radius - 8)
            hi = np.maximum(hi, w.origin + radius + 8)

        overlay.set_clip(None)
        if hi[0] > lo[0]:
            # blit only the region that has light in it
            drawn = pygame.Rect(int(lo[0]), int(lo[1]), int(hi[0] - lo[0]) + 1, int(hi[1] - lo[1]) + 1)
            drawn = drawn.clip(WALL_INNER_RECT)
            screen.blit(overlay, drawn.topleft, drawn)


def _rotate(points, angle):
    """Rotate an (N, 2) array of points about the origin by angle (radians)."""
    c, s = np.cos(angle), np.sin(angle)
    return points @ np.array([[c, s], [-s, c]])

# A 90-degree arc on the unit circle, centred on +x, split into ARC_SEGMENTS pieces.
# The emitted power at angle delta from the arc's centre is sin^2(90 deg - delta) = cos^2(delta);
# rescaled to be 1 in the middle and 0 at the half-power edges, that is cos(2*delta).
# Each segment is drawn at that brightness, taken at its midpoint.
_ARC_EDGES = np.linspace(-ARC_HALF_ANGLE, ARC_HALF_ANGLE, ARC_SEGMENTS + 1)
_ARC_UNIT = np.column_stack((np.cos(_ARC_EDGES), np.sin(_ARC_EDGES)))
_ARC_TAPER = np.cos(_ARC_EDGES[:-1] + _ARC_EDGES[1:])
