# FREE1105 — Funky Radical Electrodynamics Engine

> **About this README:** it was written by an LLM (Claude), summarising this codebase, its git history and my development notes (the notebook `FREE1105 Primary Notebook.ipynb`). The project itself, its design and the physics choices are mine; see [Authorship](#authorship) for exactly which parts were AI-assisted.

A 2D classical electrodynamics sandbox written from scratch in Python. You place point charges, give them masses, velocities and restitution coefficients, press **Start**, and watch them move under their mutual Coulomb forces. The simulation features:

- a symplectic Velocity-Verlet integrator, with energy shown live and never corrected;
- impulse-based collisions with particles and walls;
- a live electric-potential heatmap;
- a 3D potential-surface window;
- **Larmor radiation**: accelerating charges emit light, lose energy and spiral inward, as in the classical atom-collapse problem.

![FREE1105 running](https://github.com/user-attachments/assets/f406baf8-15f7-4318-8896-94861fcc9ada)

## Contents

- [Run it](#run-it) · [Controls](#controls)
- [Development history](#development-history-in-stages): how it was built, phase by phase
- [Physics overview](#physics-overview): what the engine actually computes
- [Shortcomings vs real life](#shortcomings-vs-real-life): what's simplified or wrong, and why
- [Verification](#verification): measured numbers
- [Architecture](#architecture) · [Authorship](#authorship) · [Review fixes](#review-fixes-october-2026) · [Roadmap](#roadmap)

---

## Run it

```bash
pip install -r requirements.txt     # pygame, numpy, matplotlib
python main.py
```

The 3D potential window opens alongside the main window.

## Controls

| Where | Control | What it does |
|---|---|---|
| Setup | Right-click empty space | Menu → create a charge (charge, mass, velocity via angle wheel, restitution, *environmental*, *static*) |
| Setup | Right-click a charge | Edit or delete it |
| Setup | Left-drag / double-click | Move a charge / duplicate it |
| Setup | Arrows on charges | Show the initial velocity (relative length) |
| Any | **Start / Pause / Reset** | Run the simulation; Reset deletes non-environmental charges and returns the rest to their initial state |
| Top-left | Wall restitution slider | 1 = elastic walls, below 1 = energy lost per bounce |
| Top-right | Time step, max FPS | Simulation speed and accuracy |
| Top-right | **Speed of light c**, **Radiation ON/OFF** | Larmor radiation; c is on a log scale from 10² px/s to the real 3×10⁸ |
| Running | TRAILS | Fading trails |
| Bottom-left | Energy readout | KE, PE, radiated energy, total, relative change since Start, and max v/c when radiation is on |

Charge sizes scale with |q| and the border thickness with mass, both relative to the other charges on screen.

---

## Development history (in stages)

The original plan, from the first cell of the notebook, had five phases:

1. Set up electric fields in a 2D coordinate system
2. Simulate the motion of point charges
3. Simulate the motion of charged rigid bodies
4. Visualise the field via geometrical curvature
5. Implement Maxwell's 4th law for magnetic fields and light

Each phase in the notebook has the same structure: a checklist of aims, a planned architecture, then a frank "How it actually went". Its `%%writefile` cells regenerate the code as it stood at the end of each phase (`*_jypter1.py`, `*_jupyter2.py`), so you can run any intermediate stage.

### Phase 1: fields and the sandbox (November 2025)

**Aims:** a window with walls; placing point charges with *static* (pinned) and *environmental* (survives a reset) flags; superposing their fields; showing the field as a background heatmap; a reset button; a right-click menu for creating and dragging charges.

**Design:** five modules (main loop, shared constants, `PointCharge` class, field renderer, GUI). Charge size encodes |q| and border thickness encodes mass, each scaled relative to the other charges. To keep the per-pixel field sum affordable, the heatmap is computed on a ¼-resolution virtual screen and scaled up, which does 16× less work.

**How it went:** the physics and maths were the easy part. The GUI widgets (text boxes, toggles, the form layout) were mostly AI-generated after several attempts that I scrapped and restarted. The notes say plainly that micromanaging pixel layouts was the least enjoyable part of the project.

### Phase 2: motion, integrators and collisions (late November 2025)

**Aims:**
- a Start button that locks editing;
- a three-state machine (SETUP / RUNNING / PAUSED), so dragging a charge can never race with the force calculation;
- reset back to initial conditions;
- particle–particle and particle–wall collisions with adjustable restitution;
- fading trails;
- initial velocities set with an angle wheel and a mantissa/exponent input, shown as scaled arrows before the run;
- time-step and FPS sliders so the motion is watchable.

**The integrator journey:** this was the core of the phase.

1. **Explicit Euler.** Energy grew steadily and orbits spiralled outward.
2. **RK2.** Smoother, but it still drifted.
3. **RK4.** Accurate over short runs, but not symplectic, so energy still drifted over long runs.
4. **Velocity-Verlet.** Adopted on someone's suggestion to use a symplectic integrator, because it respects energy conservation. The energy now oscillated in a bounded band instead of drifting. That observation is the project's central numerical result. See [Physics](#3-time-integration-velocity-verlet).

**How it went:** exhausting. The GUI and the first draft of the physics engine were AI-generated. The integration, debugging and tuning were mine, and it took a lot of cycles of breaking something, debugging, then re-learning my own code. I tuned the softening and collision handling until the energy behaved.

### Phase 3: charged rigid bodies (planned, not built)

The plan was triangle and rectangle bodies that could be dragged, rotated and scaled, with charge spread along an axis through an editable distribution, plus strings between particles. It was set aside for lack of time and is still on the [roadmap](#roadmap).

### Phase 4: the potential as geometry (February 2026)

The potential V(x, y) is drawn as a 3D surface. Positive charges raise it and negative charges dent it, much like the rubber-sheet picture of spacetime curvature. I built this before phases 3 and 5 because it was the most self-contained piece (mostly matplotlib) at a time when other commitments left little time.

### October 2026: review and fixes

An AI-assisted code review found several real problems:
- an energy "correction" that made the conservation check true by construction;
- a heatmap that wasn't the potential;
- forces computed three times per step in Python loops;
- an inconsistent force/potential clamp;
- matplotlib running in a non-main thread.

All of these were fixed. See [Review fixes](#review-fixes-october-2026).

### Phase 5a: Larmor radiation (October 2026)

This is the first step of the original phase 5 ("magnetic fields and light"). Accelerating charges now radiate, lose kinetic energy, and show their emission pattern on screen. My design was:
- light is emitted perpendicular to the acceleration;
- the energy comes out of KE;
- the colour runs from red to violet, scaled relative to the other charges on screen;
- the strength is adjustable through a scaled c.

I chose to colour by the characteristic frequency of the motion rather than by power, because that is what actually sets the colour of the emitted light. The implementation was AI-written to this design. See [Physics § 5](#5-larmor-radiation-phase-5a).

---

## Physics overview

### 1. Coulomb force with Plummer softening

Every pair of charges interacts through a softened Coulomb force:

$$\vec F_{ij} = k_e\, q_i q_j \, \frac{\vec r_i - \vec r_j}{\left(|\vec r_i - \vec r_j|^2 + \varepsilon^2\right)^{3/2}}, \qquad \varepsilon = 400\ \text{px}.$$

This force is exactly $-\nabla$ of the softened potential energy

$$U = \sum_{i<j} \frac{k_e\, q_i q_j}{\sqrt{r_{ij}^2 + \varepsilon^2}},$$

so the force and the energy readout always describe the same physics. Softening removes the $r \to 0$ singularity: without it, a close pass between opposite charges produces arbitrarily large accelerations that no fixed time step can resolve. The technique comes from gravitational N-body codes. The value 400 px was chosen empirically by watching the energy in close encounters.

All pairs are evaluated in one NumPy broadcast. The cost is O(N²), which is fine for tens of charges.

### 2. Units

The code uses SI constants ($k_e$, $e$, $m_e$, $m_p$, $c$) with **1 px treated as 1 m**. The creation form defaults to 1 C and 1 kg. These magnitudes are wildly unphysical (1 C is an enormous charge), but they give motion on a human timescale.

### 3. Time integration: Velocity-Verlet

$$x_{n+1} = x_n + v_n \Delta t + \tfrac{1}{2} a_n \Delta t^2, \qquad v_{n+1} = v_n + \tfrac{1}{2}(a_n + a_{n+1}) \Delta t$$

Velocity-Verlet is **symplectic**: it preserves the phase-space structure of Hamiltonian mechanics. It exactly conserves a "shadow Hamiltonian" that differs from the true energy by $O(\Delta t^2)$. As a result, the energy error **oscillates within a bounded band and does not drift**, even over very long runs. RK4 has a higher order but lacks this property, which is why molecular dynamics codes (GROMACS, LAMMPS) and N-body codes use Verlet-type schemes.

The engine evaluates forces once per step: $a_{n+1}$ is cached and reused as the next step's $a_n$, unless collisions, walls or dragging moved a particle in between.

### 4. Collisions

- **Particle–particle:** an impulse along the contact normal, with the reduced mass and an effective restitution $e = \min(e_1, e_2)$. A positional correction of 80% of the overlap then separates the pair without overshooting.
- **Walls:** the normal velocity is reflected and multiplied by the wall restitution (slider).
- With restitution below 1, energy is lost, as it should be.

### 5. Larmor radiation (Phase 5a)

**Power.** A non-relativistic accelerating charge radiates

$$P = \frac{q^2 a^2}{6\pi\varepsilon_0 c^3} = \frac{2}{3}\,\frac{k_e\, q^2 a^2}{c^3}.$$

Here $a$ is the **net** acceleration. Fields superpose before they are squared, so a charge pulled equally in two opposite directions doesn't radiate. Neutral and static charges never radiate.

**Direction.** The angular distribution is

$$\frac{dP}{d\Omega} \propto \sin^2\theta,$$

with θ measured from the acceleration. No light goes along the force; the maximum is perpendicular to it. In 3D this is a doughnut around the acceleration axis. On screen it is drawn as its cross-section: **two lobes perpendicular to the net force**, with the exact $\sin^2$ shape.

**Energy loss.** The pattern is front–back symmetric, so the light carries away energy but **no net momentum**. Each step, a radiating charge loses $P\,\Delta t$ of kinetic energy. Its speed is scaled down and its direction is unchanged. This energy-drain method is used instead of the Abraham–Lorentz self-force $\frac{2}{3}k_e q^2 \dot{\vec a}/c^3$, which has unphysical runaway solutions. Averaged over the motion, both give the same energy loss. The radiated energy is tallied and the readout shows

$$KE + PE + E_{\text{rad}} = E_0,$$

so energy bookkeeping still provides a consistency check.

**Colour.** Real emitted light has the frequency of the motion that produces it. For circular motion that frequency is $\omega = a/v$ exactly, and this ratio is a good estimate in general. Each lobe is coloured by $\omega$ on a log scale relative to the other charges on screen: the slowest-turning charge is **red** and the fastest is **violet**, following the visible spectrum. Lobe size and opacity show the relative radiated **power**, also on a log scale. Log scales are needed because $P \propto a^2 \propto 1/r^4$ spans many orders of magnitude, and a linear scale would leave everything except the strongest emitter at the bottom.

**Strength.** With the real $c = 3\times10^8$, radiation from charges moving at a few thousand px/s is negligible: about $10^{-15}$ of the orbital energy per orbit. The **speed of light slider** lowers c so the effect becomes visible. This is a "slow light" universe. The readout shows the largest $v/c$ and turns red above 0.3, because the formula assumes $v \ll c$. The default $c = 3\times10^4$ px/s gives $v/c \approx 0.08$ for a typical orbit, and the orbit visibly spirals inward.

### 6. Potential heatmap and 3D surface

Both show the scalar potential $V(x,y) = \sum_i k_e q_i / r_i$, with $r_i$ held at the particle's radius inside its disc.

- **2D heatmap:** computed on a ¼-resolution grid. Positive potential is darker, negative is lighter, and zero is mid-grey.
- **3D surface:** height and grey level encode the normalised V, with a blue wireframe and the charges marked (red +, blue −).
- **Process model:** the 3D window runs in **its own process**, because matplotlib's GUI must own its process's main thread. The simulation sends it a JSON snapshot of the charges at 5 Hz over a pipe.

---

## Shortcomings vs real life

This is a teaching-grade classical model. The list below is deliberately thorough, and several entries are interesting physics in their own right.

### Electrodynamics that's missing

| Simplification | Real physics | Consequence here |
|---|---|---|
| **Electrostatic forces only.** No magnetic force between moving charges | Moving charges make magnetic fields, and the force is the full Lorentz force $q(\vec E + \vec v\times\vec B)$. The magnetic interaction is smaller by about $(v/c)^2$ | With real c the error is negligible. With radiation on and c lowered to make it visible, $v/c \sim 0.1$, so the missing magnetic forces are about 1%. The lowered c is applied to radiation only, not consistently. Fixing this is phase 5b |
| **Instantaneous action at a distance** | Fields propagate at c. Each charge feels the others where they were at the *retarded* time (Liénard–Wiechert potentials) | Same order as above: fine for $v \ll c$ |
| **3D Coulomb law in a 2D world** | Genuine 2D electrostatics has a logarithmic potential and a 1/r force | These are really 3D charges confined to a plane. The radiation lobes are a slice of the 3D doughnut |
| **Softening, ε = 400 px** | Point charges obey $1/r^2$ down to (at least) nuclear scales | ε is comparable to the screen size, so it is a big modification. At 300 px the force is only **22%** of the true Coulomb value, and at short range it flattens out instead of diverging. Motion is qualitatively Coulomb-like, but quantitatively softer |
| **Conducting walls aren't modelled** | A real conducting wall induces image charges and attracts nearby charges | Walls only reflect particles mechanically |

### Radiation (Phase 5a)

| Simplification | Real physics | Consequence here |
|---|---|---|
| **Non-relativistic Larmor** | Liénard's relativistic formula grows as $\gamma^6$, and at high speed the emission is beamed forward along $\vec v$ (synchrotron "headlight") | Valid only while $v \ll c$. The readout warns above $v/c = 0.3$ |
| **Energy drain instead of a self-force** | Radiation reaction is a subtle, still-debated problem (Abraham–Lorentz–Dirac, Landau–Lifshitz) | Correct energy loss rate, but the instantaneous force direction isn't modelled. A charge momentarily at rest can't lose KE in that step, so that step's emission isn't tallied |
| **Collisions don't radiate** | A sudden stop radiates strongly (bremsstrahlung: the X-rays in an X-ray tube) | Collision and wall impulses are instantaneous, so $a$ would be infinite. They are excluded |
| **Emitted light doesn't interact with anything** | Radiation carries fields that push on other charges (absorption, scattering) | Energy simply leaves the system |
| **Colour is relative** | A charge circling at ω = 20 rad/s emits ~3 Hz radio waves, nowhere near visible light | Red→violet ranks the charges by frequency; it is not the true colour |
| **Classical radiation, no photons** | Light comes in quanta, and atoms have stable ground states | See the next table |

### Things that only quantum mechanics fixes

- **The classical atom collapses.** A classical electron orbiting a proton at the Bohr radius radiates its energy away and spirals into the nucleus in about **1.6×10⁻¹¹ s**. Turn radiation on with an orbiting ± pair and you watch exactly this failure of classical physics. Historically it was one of the main motivations for the Bohr model and quantum mechanics.
- **Opposite charges should collapse even without radiation.** Point charges with a pure $1/r^2$ attraction meet in finite time. Here two artificial things stop it: softening, and treating charges as hard discs that bounce. In reality, quantum mechanics (the uncertainty principle) and the Pauli exclusion principle keep atoms from collapsing.

### Mechanics and numerics

| Simplification | Note |
|---|---|
| Charges are hard discs with restitution | Real charges don't have contact collisions; this is a sandbox mechanic. The positional correction can create or remove small amounts of energy |
| Collisions are applied after the Verlet step | This slightly breaks symplecticity: energy is bounded between collisions, not through them |
| Fixed time step | No adaptive stepping. Close encounters need a smaller dt (slider) |
| Static charges are pinned with infinite mass | An idealisation; real "fixed" charges are held by forces |
| O(N²) forces | Fine for tens of charges; thousands would need Barnes–Hut or GPU |
| Heatmap at ¼ resolution; V held constant inside each disc | Visual approximations |

---

## Verification

All numbers below come from headless tests of `physics_engine.py`. In each test a charge orbits a fixed opposite charge (q = ±1 C, m = 1 kg, r = 300 px, ε = 400 px, 400 steps per orbit, no walls or collisions), and the orbit speed is set so the orbit is circular in the softened potential.

| Test | Result |
|---|---|
| Energy conservation, radiation off, 50 orbits | $\lvert E - E_0\rvert / \lvert E_0\rvert < 7.2\times10^{-6}$. Mean error $-3.1\times10^{-6}$ over the first orbit and $-2.9\times10^{-6}$ over the last: **no drift** |
| Radiated energy vs analytic Larmor, c = 10⁵ px/s, 20 orbits | Simulated $4.135\times10^4$ J vs analytic $P \cdot 20T = 4.134\times10^4$ J (**0.02%**) |
| Energy bookkeeping with radiation, c = 3×10⁴, 20 orbits | Orbit decays 300 → 253 px; $\lvert KE + PE + E_{\text{rad}} - E_0\rvert / \lvert E_0\rvert < 4.6\times10^{-6}$ |
| Radiation off vs real c (3×10⁸) | Indistinguishable |
| Neutral charge | Never radiates |
| Vectorised forces vs the original loop code | Identical, apart from one pair inside the old 20 px clamp. About 33× faster at N = 20 |

---

## Architecture

```
FREE1105/
├── main.py                  # loop, state machine (SETUP / RUNNING / PAUSED), rendering, energy readout
├── physics_engine.py        # softened Coulomb, Velocity-Verlet, Larmor radiation, collisions, energy
├── point_charges.py         # PointCharge (state, trails, arrows, drawing) and radiation-lobe rendering
├── electric_field.py        # 2D potential heatmap (¼-resolution grid, scaled up)
├── phase4_visualiser.py     # 3D potential surface, run as a separate process
├── gui.py                   # buttons, sliders (incl. log-scale), toggles, creation form
├── constants_for_all_files.py
├── FREE1105 Primary Notebook.ipynb   # development log, phase by phase
└── requirements.txt
```

**Physics step (each frame while running):**

1. **Verlet position update**, using the cached $a_n$.
2. **New forces**, giving $a_{n+1}$.
3. **Verlet velocity update.**
4. **Larmor energy drain**, if radiation is on.
5. **Wall collisions.**
6. **Particle collisions.**
7. **Energy diagnostics**, including the radiated energy.

---

## Authorship

- **Phase 1 (Nov 2025):** physics, field calculation and architecture are mine. The GUI widgets were largely AI-generated.
- **Phase 2 (Nov 2025):** I designed and debugged it, including the state machine, collision handling and the Euler → RK2 → RK4 → Verlet progression and its tuning. The GUI and the first draft of the physics engine were AI-generated, then integrated and reworked by me.
- **Phase 4 (Feb 2026):** lightly AI-assisted.
- **October 2026 review:** an AI-assisted code review found the issues in the table below, and the fixes and repo clean-up were AI-implemented.
- **Phase 5a, radiation (Oct 2026):** the design is mine (direction, energy drain from KE, red→violet relative colour scale, scaled c). The implementation and tests were AI-written.
- **This README:** written by Claude from the code, the git history and my notebook notes.

## Review fixes (October 2026)

| Issue found | Fix |
|---|---|
| In fully elastic mode, velocities were rescaled every step to force the total energy back to $E_0$, so the conservation check was true by construction | Rescaling removed; the energy is displayed live, as measured |
| The 2D heatmap summed signed $kq/r^2$, which is neither the potential nor the field strength | The heatmap now shows the potential $kq/r$, the same quantity as Phase 4 |
| Forces were evaluated 3× per step (one result discarded) in pure-Python double loops | One evaluation per step, vectorised: ~33× faster at 20 charges |
| A 20 px minimum-distance clamp made the force and the potential disagree at close range | Clamp removed; softening alone regularises the force, consistently |
| Matplotlib ran in a background thread, which isn't thread-safe and can crash | The visualiser runs as a separate process |
| A per-frame debug print of every particle flooded the terminal and slowed the loop | Removed |
| Repo clutter: generated stage files, `__pycache__`, editor settings, a 1 MB notebook (10k lines of debug output) | Removed or git-ignored; notebook outputs cleared (160 KB); `requirements.txt` added |

## Roadmap

- **Phase 5b, magnetism:** velocity-dependent (Darwin) forces and $\vec v \times \vec B$, using the same scaled c as radiation, so the slow-light universe is consistent.
- **Phase 5c, retardation:** fields propagating at c (Liénard–Wiechert), visible as expanding wavefronts.
- **Phase 3, rigid bodies:** charged triangles and rectangles with torque from non-uniform charge distributions; strings.
- Bremsstrahlung on collisions, given finite-duration contacts.
- Barnes–Hut $O(N\log N)$ forces, or GPU, for large N.

---

*Built as a self-directed computational physics project alongside a Theoretical Physics degree, 2025–26.*

<img width="1906" height="996" alt="FREE1105 screenshot" src="https://github.com/user-attachments/assets/8a589cc4-d17c-4821-9932-99e83a15ee4d" />
<img width="1919" height="959" alt="FREE1105 screenshot" src="https://github.com/user-attachments/assets/423fbba2-0143-4b61-a73f-7ea3235bb881" />
<img width="1769" height="1026" alt="Phase 4 potential surface" src="https://github.com/user-attachments/assets/78eb871b-89b7-4b4e-9c50-55479ca131f8" />
