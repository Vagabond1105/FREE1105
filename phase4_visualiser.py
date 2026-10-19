"""
FREE1105 - Phase 4: Geometrical Curvature Visualiser
=====================================================
Renders the electric potential V(x,y) = sum(kq/r) as a 3D surface
in a separate matplotlib window.

- Positive potential regions: warped UPWARD, coloured darker (same greyscale as the 2D heatmap)
- Negative potential regions: warped DOWNWARD, coloured lighter
- Blue wireframe overlaid on coloured surface
- Updates 5 times per second

The window runs in its own Python *process* (this file, launched with
`python phase4_visualiser.py`), not in a thread of the pygame process:
matplotlib's GUI backends (here Tk) must run on their process's main
thread, so drawing from a background thread can crash on some systems.
The pygame process sends a small JSON snapshot of the charges down the
child's stdin at most 5 times per second; inside the child, a reader
thread only does I/O and the main thread does all the drawing.

USAGE (as in main.py):
    from phase4_visualiser import Phase4Visualiser
    phase4 = Phase4Visualiser()
    phase4.start()                   <- once, after imports
    phase4.update(all_point_charges) <- every frame (rate-limited internally)
    phase4.stop()                    <- on exit
"""

import json
import os
import subprocess
import sys
import threading
import time

import numpy as np

# ── constants (mirrored from constants_for_all_files.py) ──────────────────────
K_COULOMB = 8.99e9
SW = 1500
SH = 900

# Grid resolution for the 3D surface (higher = prettier but slower)
GRID_RES = 60          # NxN grid points
UPDATE_INTERVAL = 0.2  # seconds between redraws (= 5 Hz)


def _compute_potential(charges, grid_x, grid_y):
    """
    Vectorised V(x,y) = sum_i  k * q_i / r_i  for snapshot dicts
    {'px', 'py', 'charge', 'radius'}. Returns an array shaped like grid_x.
    """
    V = np.zeros_like(grid_x, dtype=float)
    for c in charges:
        r = np.sqrt((grid_x - c['px'])**2 + (grid_y - c['py'])**2)
        r = np.maximum(r, c['radius'])   # inside a charge's disc, hold V at its surface value
        V += K_COULOMB * c['charge'] / r
    return V


def _make_surface_colors(V_norm):
    """
    Map normalised potential [-1, 1] to RGBA colours, mirroring the 2D heatmap
    in electric_field.py (pixel = 127.5 - 0.7 * normalised * 127.5) but over the
    full [-1, 1] range: positive -> darker, negative -> lighter, 0 -> mid-grey.

    V_norm: array in [-1, 1]
    Returns RGBA array shape (*V_norm.shape, 4)
    """
    pixel_vals = 0.5 - (0.5 * V_norm)   # in [0, 1], 0=dark, 1=bright
    a = np.ones_like(pixel_vals) * 0.85  # slight transparency so wireframe pops
    return np.stack([pixel_vals, pixel_vals, pixel_vals, a], axis=-1)


class Phase4Visualiser:
    """
    Pygame-side handle for the potential-surface window (a child process).
    """

    def __init__(self, grid_res=GRID_RES, update_interval=UPDATE_INTERVAL):
        self.grid_res = grid_res
        self.update_interval = update_interval
        self._proc = None
        self._last_sent = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Launch the visualiser window as a separate process."""
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), str(self.grid_res), str(self.update_interval)],
            stdin=subprocess.PIPE, text=True)

    def stop(self):
        """Close the pipe (the child exits on end-of-input) and make sure it is gone."""
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self._proc.terminate()
        self._proc = None

    def update(self, all_point_charges):
        """
        Call this every frame from your main loop. Sends a snapshot of the
        charges at most once per update_interval; if the window was closed,
        this quietly does nothing.
        """
        if self._proc is None or self._proc.poll() is not None:
            return
        now = time.time()
        if now - self._last_sent < self.update_interval:
            return
        self._last_sent = now
        snapshot = [{
            'px': float(pc.position[0]),
            'py': float(pc.position[1]),
            'charge': float(pc.charge),
            'radius': float(getattr(pc, 'total_radius', 20.0)),
        } for pc in all_point_charges]
        try:
            self._proc.stdin.write(json.dumps(snapshot) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self._proc = None   # window closed by the user


# ── Child process: the matplotlib window ─────────────────────────────────────

def _use_matching_mpl_toolkits():
    """
    Make sure the 3D toolkit (mpl_toolkits.mplot3d) is the one that ships with the
    matplotlib actually being imported.

    On Ubuntu/Debian, the apt package python3-matplotlib installs a .pth hook that
    claims the mpl_toolkits namespace for its own (older) copy. If a newer matplotlib
    is also pip-installed, 3D plotting then fails with "Unknown projection '3d'" and
    this window never opens. Putting the matching folder first fixes it.
    """
    import matplotlib
    import mpl_toolkits
    own = os.path.join(os.path.dirname(os.path.dirname(matplotlib.__file__)), 'mpl_toolkits')
    paths = list(mpl_toolkits.__path__)
    if os.path.isdir(own) and (not paths or os.path.realpath(paths[0]) != os.path.realpath(own)):
        mpl_toolkits.__path__ = [own] + [p for p in paths if os.path.realpath(p) != os.path.realpath(own)]


def _run_window(grid_res, update_interval):
    import matplotlib
    matplotlib.use('TkAgg')  # Must be set before importing pyplot
    _use_matching_mpl_toolkits()
    import matplotlib.pyplot as plt

    lock = threading.Lock()
    state = {'charges': [], 'eof': False}

    def read_stdin():
        # I/O only - all matplotlib calls stay on the main thread
        for line in sys.stdin:
            try:
                charges = json.loads(line)
            except ValueError:
                continue
            with lock:
                state['charges'] = charges
        with lock:
            state['eof'] = True

    threading.Thread(target=read_stdin, daemon=True).start()

    xs = np.linspace(0, SW, grid_res)
    ys = np.linspace(0, SH, grid_res)
    grid_x, grid_y = np.meshgrid(xs, ys)
    gx_norm, gy_norm = grid_x / SW, grid_y / SH   # normalised grid in [0,1] for axis display

    plt.ion()
    fig = plt.figure(figsize=(8, 6), facecolor='#1a1a2e')
    fig.canvas.manager.set_window_title("FREE1105 — Phase 4: Potential Surface")
    ax = fig.add_subplot(111, projection='3d')
    _style_axes(ax)

    last_update = 0.0
    while plt.fignum_exists(fig.number):
        with lock:
            charges = list(state['charges'])
            eof = state['eof']
        if eof:
            break

        now = time.time()
        if now - last_update < update_interval:
            plt.pause(0.02)
            continue
        last_update = now

        ax.cla()
        _style_axes(ax)

        if not charges:
            ax.set_title("No charges present", color='white', fontsize=12, pad=15)
            plt.pause(0.02)
            continue

        # ── Potential, normalised for colour and z-height ─────────────────
        V = _compute_potential(charges, grid_x, grid_y)
        v_abs_max = np.max(np.abs(V)) or 1.0
        V_norm = np.clip(V / v_abs_max, -1.0, 1.0)   # [-1, 1]
        Z = V_norm * 0.4   # positive up, negative down, [-0.4, 0.4] in normalised coords

        ax.plot_surface(gx_norm, gy_norm, Z, facecolors=_make_surface_colors(V_norm),
                        shade=False, antialiased=False, zorder=1)
        ax.plot_wireframe(gx_norm, gy_norm, Z, color='#00aaff', linewidth=0.5, alpha=0.55, zorder=2)

        # ── Mark charge positions (z from the nearest grid point) ─────────
        for c in charges:
            cx_n, cy_n = c['px'] / SW, c['py'] / SH
            ix = int(np.clip(cx_n * (grid_res - 1), 0, grid_res - 1))
            iy = int(np.clip(cy_n * (grid_res - 1), 0, grid_res - 1))
            colour = '#ff3333' if c['charge'] > 0 else '#3333ff' if c['charge'] < 0 else '#888888'
            ax.scatter([cx_n], [cy_n], [Z[iy, ix] + 0.03], color=colour, s=80, zorder=5, depthshade=False)

        n_pos = sum(1 for c in charges if c['charge'] > 0)
        n_neg = sum(1 for c in charges if c['charge'] < 0)
        ax.set_title(f"Electric Potential  |  +{n_pos} positive   −{n_neg} negative",
                     color='white', fontsize=11, pad=12)
        plt.pause(0.02)

    plt.close('all')


def _style_axes(ax):
    ax.set_facecolor('#1a1a2e')
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.fill = False
        axis.pane.set_edgecolor('#333355')
    ax.tick_params(colors='#aaaacc', labelsize=7)
    ax.set_xlabel("X", color='#aaaacc', fontsize=8, labelpad=4)
    ax.set_ylabel("Y", color='#aaaacc', fontsize=8, labelpad=4)
    ax.set_zlabel("V (norm)", color='#aaaacc', fontsize=8, labelpad=4)
    ax.set_zlim(-0.5, 0.5)
    ax.grid(False)


if __name__ == "__main__":
    _run_window(int(sys.argv[1]) if len(sys.argv) > 1 else GRID_RES,
                float(sys.argv[2]) if len(sys.argv) > 2 else UPDATE_INTERVAL)
