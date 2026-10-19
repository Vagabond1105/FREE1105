"""
Drive the real main.py with scripted mouse events, headless, and check the
Start / Pause / Reset flow:

    Start -> run -> Reset   back in SETUP, non-environmental charges deleted,
                            the rest at their initial position
    drag a charge           it moves, and its new spot becomes its initial position
    Start again             runs from the dragged position
    Pause -> Reset          back in SETUP as well

Run from the repository root:
    python -m unittest discover -s tests -v
"""

import os
import runpy
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, REPO)

import numpy as np
import pygame

import phase4_visualiser

E = pygame.event.Event


def click(pos):
    """What a real click looks like: the mouse moves there, then the button goes down and up."""
    return [E(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)),
            E(pygame.MOUSEBUTTONDOWN, pos=pos, button=1),
            E(pygame.MOUSEBUTTONUP, pos=pos, button=1)]


def run_app(make_script, checkpoints):
    """
    Run main.py, feeding it events frame by frame. make_script(g) is called on the first
    frame with main.py's globals and returns {frame: [events]}; it can also add charges.
    At each frame in checkpoints, a snapshot of (sim_state, charges) is recorded.
    """
    snapshots, script, frame = {}, {}, [0]
    cursor = [(0, 0)]       # headless there is no real mouse: follow the scripted events

    def fake_get(*args, **kwargs):
        g = sys._getframe(1).f_globals          # main.py's module globals
        f = frame[0]
        frame[0] += 1
        if f == 0:
            script.update(make_script(g))
        if f in checkpoints:
            snapshots[f] = (g['sim_state'],
                            [(pc.pc_id, pc.position.copy(), pc.pos_0.copy()) for pc in g['all_point_charges']])
        events = script.get(f, [])
        for ev in events:
            if hasattr(ev, 'pos'):
                cursor[0] = ev.pos
        return events

    real_get, real_start = pygame.event.get, phase4_visualiser.Phase4Visualiser.start
    real_mouse = pygame.mouse.get_pos
    pygame.event.get = fake_get
    pygame.mouse.get_pos = lambda: cursor[0]      # dragging follows the mouse position
    phase4_visualiser.Phase4Visualiser.start = lambda self: None     # no 3D window in tests
    try:
        runpy.run_path(os.path.join(REPO, "main.py"), run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.event.get = real_get
        pygame.mouse.get_pos = real_mouse
        phase4_visualiser.Phase4Visualiser.start = real_start
    return snapshots


def add_charges(g):
    from point_charges import PointCharge
    g['all_point_charges'] += [
        PointCharge((600.0, 450.0), 1.0, 1.0, True, True, 0, 1.0, (0.0, 0.0)),        # environmental, static
        PointCharge((900.0, 450.0), -1.0, 1.0, True, False, 1, 1.0, (0.0, -1500.0)),  # environmental, moving
        PointCharge((300.0, 700.0), 1.0, 1.0, False, False, 2, 1.0, (0.0, 0.0)),      # not environmental
    ]


def positions(snapshot):
    return {pc_id: pos for pc_id, pos, _ in snapshot[1]}


class TestStartResetFlow(unittest.TestCase):

    def test_reset_then_drag_then_start_again(self):
        def script(g):
            add_charges(g)
            start, reset = g['start_btn'].rect.center, g['reset_btn'].rect.center
            return {
                1: click(start),
                40: click(reset),
                42: [E(pygame.MOUSEMOTION, pos=(900, 450), rel=(0, 0), buttons=(0, 0, 0)),
                     E(pygame.MOUSEBUTTONDOWN, pos=(900, 450), button=1)],
                43: [E(pygame.MOUSEMOTION, pos=(1000, 300), rel=(100, -150), buttons=(1, 0, 0))],
                44: [E(pygame.MOUSEBUTTONUP, pos=(1000, 300), button=1)],
                46: click(start),
                70: [E(pygame.QUIT)],
            }

        snaps = run_app(script, {39, 41, 45, 47, 69})

        self.assertEqual(snaps[39][0], 1, "should be running before Reset")
        self.assertFalse(np.allclose(positions(snaps[39])[1], (900, 450)), "the charge should have moved")

        state, charges = snaps[41]
        self.assertEqual(state, 0, "Reset must go back to SETUP, not keep running")
        self.assertEqual(sorted(positions(snaps[41])), [0, 1], "the non-environmental charge is deleted")
        np.testing.assert_allclose(positions(snaps[41])[1], (900, 450))

        self.assertEqual(snaps[45][0], 0, "still in SETUP while dragging")
        np.testing.assert_allclose(positions(snaps[45])[1], (1000, 300))
        pos_0 = {pc_id: p0 for pc_id, _, p0 in snaps[45][1]}
        np.testing.assert_allclose(pos_0[1], (1000, 300), err_msg="the drop spot becomes the new start")

        self.assertEqual(snaps[47][0], 1, "Start works again after Reset")
        self.assertEqual(snaps[69][0], 1)
        self.assertFalse(np.allclose(positions(snaps[69])[1], (1000, 300)), "and it runs from there")

    def test_pause_then_reset(self):
        def script(g):
            add_charges(g)
            start, reset = g['start_btn'].rect.center, g['reset_btn'].rect.center
            pause = g['pause_btn'].rect.center
            return {1: click(start), 20: click(pause), 25: click(reset), 30: [E(pygame.QUIT)]}

        snaps = run_app(script, {22, 27})
        self.assertEqual(snaps[22][0], 0.5, "paused")
        self.assertEqual(snaps[27][0], 0, "Reset from pause goes back to SETUP")
        np.testing.assert_allclose(positions(snaps[27])[1], (900, 450))

    def test_reset_in_setup_stays_in_setup(self):
        def script(g):
            add_charges(g)
            return {3: click(g['reset_btn'].rect.center), 8: [E(pygame.QUIT)]}

        snaps = run_app(script, {5})
        self.assertEqual(snaps[5][0], 0)


if __name__ == "__main__":
    unittest.main()
