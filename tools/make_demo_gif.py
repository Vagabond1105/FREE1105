"""
Render the README demo GIF headless, using the app's own physics and drawing code.

    python tools/make_demo_gif.py            # writes assets/demo.gif (needs ffmpeg)

Scene: a fixed positive charge with six light negative charges on circular orbits
at different radii, radiation on (real c), trails on. Each orbit turns at a different
frequency, so each one radiates in its own colour, once per orbit.
"""

import os
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import numpy as np
import pygame

from constants_for_all_files import SW, SH, WC, WALL_RECT, WBT, C_LIGHT
from electric_field import ElectricFieldSystem
from physics_engine import PhysicsEngine
from point_charges import PointCharge, RadiationRenderer

FPS = 25                 # GIF frame rate
SECONDS = 8
STEPS_PER_FRAME = 12     # physics steps per GIF frame (like raising the FPS slider)
DT = 1e-3                # the app's default time step
OUT_WIDTH = 1050         # GIF width in px (height keeps the 5:3 window ratio)


def build_scene(engine):
    centre = np.array([SW / 2, SH / 2])
    charges = [PointCharge(centre, 1.0, 1.0, True, True, 0, 1.0, (0.0, 0.0))]
    # Light satellites (q/m the same as a -1 C, 1 kg charge, so the orbits match the
    # README tests) whose charges are small enough that they barely disturb each other.
    q, m = -0.02, 0.02
    orbits = [(90, 0.0), (150, 2.6), (205, 5.1), (260, 1.4), (315, 3.9), (370, 0.5)]
    for i, (r, start_angle) in enumerate(orbits):
        a = 8.99e9 * 1.0 * abs(q) * r / (r * r + engine.softening_eps2) ** 1.5 / m
        v = np.sqrt(a * r)
        radial = np.array([np.cos(start_angle), np.sin(start_angle)])
        tangent = np.array([radial[1], -radial[0]])
        charges.append(PointCharge(centre + r * radial, q, m, True, False, i + 1, 1.0, v * tangent))
    return charges


def main():
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg is needed to encode the GIF")
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    engine = PhysicsEngine()
    engine.radiation_c = C_LIGHT
    field = ElectricFieldSystem()
    radiation = RadiationRenderer()
    charges = build_scene(engine)
    out_size = (OUT_WIDTH, OUT_WIDTH * SH // SW)

    frames_dir = tempfile.mkdtemp(prefix="free1105_frames_")
    try:
        for frame in range(FPS * SECONDS):
            for _ in range(STEPS_PER_FRAME):
                engine.update_positions_velocities(DT, charges)
                engine.handle_wall_collisions(charges, 1.0)
                engine.handle_particle_collisions(charges)
                radiation.update(charges, DT)
                for pc in charges:
                    pc.record_trail(True)
            for pc in charges:
                pc.update_relative_scale(charges)

            # the same layers, in the same order, as main.py
            field.render(screen, charges)
            pygame.draw.rect(screen, WC, WALL_RECT, WBT)
            for pc in charges:
                pc.render_trails(screen)
            radiation.render(screen)
            for pc in charges:
                pc.arrow_display = False
                pc.render(screen)

            small = pygame.transform.smoothscale(screen, out_size)
            pygame.image.save(small, os.path.join(frames_dir, f"f{frame:04d}.png"))

        out = os.path.join(ROOT, "assets", "demo.gif")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pattern = os.path.join(frames_dir, "f%04d.png")
        palette = os.path.join(frames_dir, "palette.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern,
                        "-vf", "palettegen=max_colors=128:stats_mode=diff", palette], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern,
                        "-i", palette, "-lavfi", "paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                        "-loop", "0", out], check=True)
        print(f"wrote {out} ({os.path.getsize(out) / 1e6:.1f} MB)")
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)
        pygame.quit()


if __name__ == "__main__":
    main()
