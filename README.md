# FREE1105 — Funky Radical Electrodynamics Engine

A 2D electrodynamics simulator built from scratch in Python: real-time charge dynamics under mutual Coulomb forces, a symplectic (Velocity-Verlet) integrator, impulse-based collisions, a live electric-potential heatmap, and a separate 3D potential-surface visualiser. Developed independently alongside the second year of a Theoretical Physics degree.

![FREE1105 running](https://github.com/user-attachments/assets/f406baf8-15f7-4318-8896-94861fcc9ada)

## Run

```bash
pip install -r requirements.txt     # pygame, numpy, matplotlib
python main.py
```

The 3D potential window opens alongside the main window. In setup mode, right-click opens the menu for creating and editing charges, left-drag moves a charge and double-click duplicates it. Then press **Start**.

The notebook `FREE1105 Primary Notebook.ipynb` documents the iterative development, with the thinking at each stage. Its `%%writefile` cells regenerate the intermediate stage files (`*_jypter1.py`, `*_jupyter2.py`); those files are generated, so they are not kept in the repo.

## Authorship

- **Phases 1–2** (charges, Coulomb dynamics, integrators, collisions, GUI): hand-coded in 2nd year.
- **Phase 4** (3D potential visualiser): lightly AI-assisted.
- **October 2026 review**: an AI-assisted code review found the issues listed under [Review fixes](#review-fixes-october-2026); the fixes and the repo clean-up were AI-assisted.
- This README was written with Claude's help.

---

## Physics

### Coulomb force with softening

Pairwise electrostatic forces use Coulomb's law with **Plummer softening** $\varepsilon$, which removes the $r \to 0$ singularity:

$$\vec F_{ij} = k_e\, q_i q_j \, \frac{\vec r_i - \vec r_j}{\left(|\vec r_i - \vec r_j|^2 + \varepsilon^2\right)^{3/2}}$$

This force is exactly $-\nabla$ of the softened potential energy used in the energy diagnostic,

$$U = \sum_{i<j} \frac{k_e\, q_i q_j}{\sqrt{r_{ij}^2 + \varepsilon^2}},$$

so the forces and the energy readout always describe the same physics. Softening is standard in N-body simulation (cf. cosmological particle codes). The default $\varepsilon = 400$ px (`PhysicsEngine(softening_eps=...)`) was chosen empirically: too small gives energy spikes in close encounters, too large distorts the physics.

**Units:** SI constants ($k_e$, $e$, $m_e$, $m_p$) are used with positions in pixels, i.e. 1 px is treated as 1 m.

### Electric potential (2D heatmap and Phase 4 surface)

Both views show the scalar potential

$$V(x, y) = \sum_i \frac{k_e q_i}{r_i(x,y)}$$

with $r_i$ held at the particle's radius inside its disc. In the 2D heatmap, positive potential is darker, negative is lighter, and zero is mid-grey. In 3D, positive potential warps the surface upward and negative downward, a geometric picture analogous to spacetime-curvature diagrams.

---

## Numerical methods: the integrator progression

The central goal was **long-term energy conservation**. The integrator went through four stages:

1. **Explicit Euler.** $x_{n+1} = x_n + v_n \Delta t,\ v_{n+1} = v_n + a_n \Delta t$. Energy grows steadily and orbits spiral outward. Rejected.
2. **RK2 (midpoint).** Much smoother, but energy still drifts over long runs. Rejected.
3. **RK4.** Fourth-order accurate and good over short runs, but **not symplectic**: it doesn't preserve the phase-space structure of a Hamiltonian system, so energy drifts over long times.
4. **Velocity-Verlet (symplectic).** The final choice:

$$x_{n+1} = x_n + v_n \Delta t + \tfrac{1}{2} a_n \Delta t^2, \qquad v_{n+1} = v_n + \tfrac{1}{2}(a_n + a_{n+1}) \Delta t$$

Velocity-Verlet conserves a *shadow Hamiltonian* close to the true one, so the total energy **oscillates within a bounded band instead of drifting**. This is why molecular-dynamics (GROMACS, LAMMPS) and N-body codes use it.

**Measured:** a charge orbiting a fixed opposite charge for 50 orbits (400 steps per orbit, no walls or collisions) keeps $|E - E_0|/|E_0| < 7.2\times10^{-6}$. The mean error is $-3.1\times10^{-6}$ over the first orbit and $-2.9\times10^{-6}$ over the last, so there is no secular drift.

The engine evaluates forces **once per step**: the $a_{n+1}$ of one step is reused as the $a_n$ of the next, unless collisions, walls or dragging moved a particle in between. All pairs are computed at once with NumPy broadcasting.

## Collisions

- **Particle–particle:** impulse resolution along the collision normal, using the reduced mass and an effective restitution $e = \min(e_1, e_2)$. A positional correction of 80 % of the overlap then separates the particles without overshooting.
- **Walls:** reflection with a wall coefficient of restitution, adjustable at runtime with a slider.

With any restitution below 1, energy is (correctly) lost in collisions.

## Energy diagnostics

The bottom-left readout shows the kinetic, potential and total energy, plus the relative change $(E - E_0)/|E_0|$ since **Start**. The energy is **measured, never corrected**: nothing rescales velocities to hold it at $E_0$. What you see is what the integrator and the collisions actually do.

## Phase 4: 3D potential visualiser

The surface is drawn by matplotlib in **its own process** (`phase4_visualiser.py`, launched by `main.py`). Matplotlib's GUI must run on its process's main thread, so a separate process keeps both the pygame loop and the plot window safe. The simulation sends a small JSON snapshot of the charges over a pipe at 5 Hz. In the child process, a reader thread handles only that input and the main thread does all the drawing, so the plot never slows the simulation down.

- Surface height and greyscale colour encode the normalised $V(x,y)$
- Blue wireframe overlay; charges marked on the surface (red = positive, blue = negative)

## Architecture

```
FREE1105/
├── main.py                  # simulation loop, state machine (SETUP / RUNNING / PAUSED), rendering, energy readout
├── physics_engine.py        # softened Coulomb forces, Velocity-Verlet, collisions, energy diagnostics
├── point_charges.py         # PointCharge class: state, trails, arrows, drawing
├── electric_field.py        # 2D potential heatmap (computed on a 1/4-resolution grid, scaled up)
├── phase4_visualiser.py     # 3D potential surface, run as a separate process
├── gui.py                   # buttons, sliders, context menu, creation form
├── constants_for_all_files.py
├── FREE1105 Primary Notebook.ipynb   # development log
└── requirements.txt
```

The **state machine** (SETUP / RUNNING / PAUSED) separates editing from physics updates, so dragging a charge can never race with the force calculation.

## Review fixes (October 2026)

| Issue found | Fix |
|---|---|
| In fully elastic mode, velocities were rescaled every step to force the total energy back to $E_0$, which made the conservation check true by construction | Rescaling removed; the energy is now displayed live, as measured |
| The 2D heatmap summed signed $kq/r^2$, which is neither the potential nor the field strength | The heatmap now shows the potential $kq/r$, the same quantity as Phase 4 |
| Forces were evaluated 3× per step (one result discarded) in pure-Python double loops | One evaluation per step, vectorised: ~33× faster at 20 charges |
| A 20 px minimum-distance clamp made the force and the potential disagree at close range | Clamp removed; softening alone regularises the force, consistently |
| Matplotlib ran in a background thread, which is not thread-safe and can crash | The visualiser now runs as a separate process |
| A per-frame debug print of every particle flooded the terminal and slowed the loop | Removed |
| Repo clutter: generated stage files, `__pycache__`, editor settings, a 1 MB notebook (10k lines of debug output) | Removed or git-ignored; notebook outputs cleared (160 KB); `requirements.txt` added |

## Possible extensions

- **Radiation:** accelerating charges radiate (Larmor formula) and lose energy
- Charged rigid-body dynamics (torque from non-uniform charge distributions)
- Magnetic fields and electromagnetic wave propagation (full Maxwell)
- Barnes–Hut tree for $O(N \log N)$ forces; GPU acceleration for large $N$

The phases are numbered out of order because the geometric visualisation was originally planned as a later phase. With limited time I built it before phases 3 and 5, since it was the most self-contained piece.

---

*Built independently as a self-directed computational physics project, 2025–26.*

<img width="1906" height="996" alt="FREE1105 screenshot" src="https://github.com/user-attachments/assets/8a589cc4-d17c-4821-9932-99e83a15ee4d" />
<img width="1919" height="959" alt="FREE1105 screenshot" src="https://github.com/user-attachments/assets/423fbba2-0143-4b61-a73f-7ea3235bb881" />
<img width="1769" height="1026" alt="Phase 4 potential surface" src="https://github.com/user-attachments/assets/78eb871b-89b7-4b4e-9c50-55479ca131f8" />
