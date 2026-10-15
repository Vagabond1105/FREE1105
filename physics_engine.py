# physics_engine.py
import numpy as np

# Keep your existing constants import in your file
from constants_for_all_files import *  # K_COULOMB, WALL_INNER_RECT, etc.

class PhysicsEngine:
    """
    Symplectic/Velocity-Verlet based physics engine for point charges with:
    - softening to avoid singularities
    - pairwise particle collision resolution (positional correction + impulse)
    - wall collisions
    - energy diagnostics (kinetic + Coulomb potential)
    """

    def __init__(self, softening_eps=400.0, debug=False):
        """
        softening_eps: length scale used to soften Coulomb potential (pixels).
                       Must be > 0: it is what removes the r -> 0 singularity.
        debug: if True, print energy diagnostics occasionally
        """
        if softening_eps <= 0:
            raise ValueError("softening_eps must be > 0 (it regularises the r -> 0 singularity)")
        self.softening_eps = float(softening_eps)
        self.softening_eps2 = self.softening_eps * self.softening_eps
        self.debug = debug
        # a(t+dt) from the previous step, reused as a(t) of the next step when
        # nothing (collisions, walls, dragging, new charges) moved the particles in between
        self._cached = None

        # Larmor radiation. None = off; otherwise the speed of light in px/s.
        # Lowering c is how the effect is made visible: with the real c the
        # radiated power of a slow charge is negligibly small.
        self.radiation_c = None
        self.radiated_energy = 0.0   # running total of energy carried away by light (J)

    def reset_radiation(self):
        """Zero the radiated-energy tally (call when the simulation starts)."""
        self.radiated_energy = 0.0

    # ----- Larmor radiation -----
    def apply_radiation(self, dt, velocities, accelerations, charges, masses, static_status):
        """
        Non-relativistic Larmor radiation (valid while v << c):
            P = q^2 a^2 / (6 pi eps0 c^3) = (2/3) k q^2 a^2 / c^3      (k = 1/(4 pi eps0))
        The emission pattern is dP/dOmega ∝ sin^2(theta), theta measured from a:
        symmetric front/back, so the light carries away energy but no net momentum.
        Each charge therefore loses P*dt of kinetic energy with no recoil: its speed
        is scaled down and its direction of travel is unchanged.

        We drain energy at the Larmor rate instead of using the Abraham-Lorentz force
        F = (2/3) k q^2 (da/dt) / c^3, which has runaway (self-accelerating) solutions;
        averaged over the motion the two give the same energy loss.

        Returns (velocities, power). power is the instantaneous Larmor power per charge.
        A charge can't lose more KE than it has, so a charge momentarily at rest
        radiates nothing from its KE that step; only energy actually removed is tallied,
        so KE + PE + radiated stays equal to E0 (up to the integrator's own error).
        """
        a2 = np.einsum("ij,ij->i", accelerations, accelerations)
        power = (2.0 / 3.0) * K_COULOMB * charges**2 * a2 / self.radiation_c**3
        power[static_status] = 0.0

        ke = 0.5 * masses * np.einsum("ij,ij->i", velocities, velocities)
        lost = np.minimum(power * dt, ke)
        scale = np.ones_like(ke)
        moving = ke > 0
        scale[moving] = np.sqrt(1.0 - lost[moving] / ke[moving])

        self.radiated_energy += float(np.sum(lost))
        return velocities * scale[:, None], power

    # ----- Force / Acceleration -----
    def get_accelerations(self, positions, velocities, charges, masses, static_status):
        """
        positions: (N,2) array
        velocities: (N,2) array (not used directly for Coulomb force, but kept for API)
        charges: (N,) array
        masses: (N,) array
        static_status: (N,) boolean array, True if static (immovable)
        returns: accelerations array shape (N,2)

        Softened (Plummer) Coulomb force, all pairs at once with NumPy broadcasting:
            F_i = sum_j k q_i q_j (r_i - r_j) / (|r_i - r_j|^2 + eps^2)^(3/2)
        This is exactly -grad of the potential used in compute_energy,
            U = sum_{i<j} k q_i q_j / sqrt(|r_i - r_j|^2 + eps^2),
        so the force and the energy diagnostic always describe the same physics.
        """
        n = len(positions)
        accelerations = np.zeros((n, 2), dtype=float)
        if n < 2:
            return accelerations

        diff = positions[:, None, :] - positions[None, :, :]        # (N,N,2): r_i - r_j
        r2_soft = np.einsum("ijk,ijk->ij", diff, diff) + self.softening_eps2
        inv_r3 = r2_soft ** -1.5
        np.fill_diagonal(inv_r3, 0.0)                                # no self-force
        coeff = K_COULOMB * charges[:, None] * charges[None, :] * inv_r3
        net_force = np.einsum("ij,ijk->ik", coeff, diff)

        accelerations = net_force / masses[:, None]
        accelerations[static_status] = 0.0                           # static charges never move
        return accelerations

    # ----- Symplectic Integrator: Velocity-Verlet -----
    def update_positions_velocities(self, dt, all_charges):
        """
        Velocity-Verlet update for all particles.
        Steps:
            1) compute a(t)
            2) x(t+dt) = x(t) + v(t)*dt + 0.5*a(t)*dt^2
            3) compute a(t+dt) from new positions
            4) v(t+dt) = v(t) + 0.5*(a(t) + a(t+dt))*dt
        """
        n = len(all_charges)
        if n == 0:
            return

        positions = np.array([p.position for p in all_charges])
        velocities = np.array([p.vel for p in all_charges])
        charges = np.array([p.charge for p in all_charges])
        masses = np.array([p.mass for p in all_charges])
        static_status = np.array([p.static for p in all_charges], dtype=bool)

        # 1. initial accelerations a(t): reuse last step's a(t+dt) if the particles
        #    haven't been moved since (Velocity-Verlet then needs ONE force evaluation per step)
        c = self._cached
        if (c is not None and c[0].shape == positions.shape and np.array_equal(c[0], positions)
                and np.array_equal(c[1], charges) and np.array_equal(c[2], masses)
                and np.array_equal(c[3], static_status)):
            a_t = c[4]
        else:
            a_t = self.get_accelerations(positions, velocities, charges, masses, static_status)

        # 2. update positions
        positions_new = positions + velocities * dt + 0.5 * a_t * (dt * dt)

        # Optional: keep static particles exactly fixed
        for i, s in enumerate(static_status):
            if s:
                positions_new[i] = positions[i]

        # 3. compute accelerations at new positions a(t+dt)
        # Note: velocities passed here are still v(t) — that's fine for force calc
        a_tdt = self.get_accelerations(positions_new, velocities, charges, masses, static_status)

        # 4. update velocities
        a_step = 0.5 * (a_t + a_tdt)          # the acceleration this step actually applied
        velocities_new = velocities + a_step * dt
        self._cached = (positions_new, charges, masses, static_status, a_tdt)

        # 5. Larmor radiation (optional): the net acceleration radiates, not each force
        #    separately, because fields superpose before being squared.
        #    Positions are untouched, so the cached a(t+dt) stays valid.
        if self.radiation_c is not None:
            velocities_new, power = self.apply_radiation(dt, velocities_new, a_step,
                                                         charges, masses, static_status)
        else:
            power = np.zeros(n)

        # 6. write back into objects (skip static)
        for i in range(n):
            pc = all_charges[i]
            # radiation state, read by the renderer
            pc.rad_power = float(power[i])
            pc.rad_accel = a_step[i].copy()
            if not static_status[i]:
                pc.position = positions_new[i]
                pc.vel = velocities_new[i]

    # ----- Pairwise particle collision resolution (internal) -----
    def _resolve_pair_collision(self, p1, p2):
        """
        Robust collision handling between two point-charge objects.
        - Impulse resolution using effective restitution = min(e1, e2)
        - Positional correction (push them apart based on overlap)
        - Handles static flags and infinite mass
        Assumes p1 and p2 expose:
            position (np.array([x,y])), vel (np.array([vx,vy])),
            total_radius (hitbox), mass, static (bool), e (per-object)
        """
        # Quick exit if both static
        if p1.static and p2.static:
            return

        diff = p1.position - p2.position
        dist_sq = np.dot(diff, diff)
        min_dist = p1.total_radius + p2.total_radius

        # If not overlapping, nothing to do
        if dist_sq >= (min_dist * min_dist):
            return

        # compute distance and normal
        if dist_sq == 0:
            # perfect overlap - choose arbitrary normal
            n = np.array([1.0, 0.0], dtype=float)
            dist = 0.0
            overlap = min_dist
        else:
            dist = np.sqrt(dist_sq)
            n = diff / dist
            overlap = min_dist - dist

        # -------- impulse (velocity) resolution FIRST --------
        inv_m1 = 0.0 if p1.static else (1.0 / p1.mass)
        inv_m2 = 0.0 if p2.static else (1.0 / p2.mass)
        inv_mass_sum = inv_m1 + inv_m2

        if inv_mass_sum == 0:
            return  # both infinite mass

        # relative velocity along normal
        v_rel = p1.vel - p2.vel
        vel_along_normal = np.dot(v_rel, n)

        # If separating (positive), nothing to do
        if vel_along_normal > 0:
            return

        # effective restitution: choose minimum (less bouncy dominates)
        e_eff = min(getattr(p1, "e", 1.0), getattr(p2, "e", 1.0))

        # compute impulse scalar
        j = -(1.0 + e_eff) * vel_along_normal
        j /= inv_mass_sum

        impulse = j * n

        if not p1.static:
            p1.vel += impulse * inv_m1
        if not p2.static:
            p2.vel -= impulse * inv_m2

        # -------- positional correction AFTER (with reduced correction to minimize energy injection) --------
        # Use only 80% correction to avoid overshooting and energy gain
        correction_factor = 0.8
        
        if not p1.static and not p2.static:
            p1.position += n * (overlap * correction_factor * (inv_m1 / inv_mass_sum))
            p2.position -= n * (overlap * correction_factor * (inv_m2 / inv_mass_sum))
        elif not p1.static and p2.static:
            p1.position += n * (overlap * correction_factor)
        elif p1.static and not p2.static:
            p2.position -= n * (overlap * correction_factor)

    # ----- Public collision handlers -----
    def handle_particle_collisions(self, all_charges):
        """O(N^2) pairwise collision checks and resolves using internal resolver."""
        n = len(all_charges)
        for i in range(n):
            for j in range(i + 1, n):
                p1 = all_charges[i]
                p2 = all_charges[j]
                # quick skip if both static
                if p1.static and p2.static:
                    continue
                self._resolve_pair_collision(p1, p2)

    def handle_wall_collisions(self, all_charges, wall_cor):
        """
        Boundary collisions — inverts velocity component and multiplies by wall_cor (coefficient).
        Keeps particles inside WALL_INNER_RECT (assumes pygame Rect-like object).
        """
        for pc in all_charges:
            if pc.static:
                continue

            left_bound = WALL_INNER_RECT.left + pc.total_radius
            right_bound = WALL_INNER_RECT.right - pc.total_radius
            if pc.position[0] < left_bound:
                pc.position[0] = left_bound
                pc.vel[0] *= -wall_cor
            elif pc.position[0] > right_bound:
                pc.position[0] = right_bound
                pc.vel[0] *= -wall_cor

            top_bound = WALL_INNER_RECT.top + pc.total_radius
            bottom_bound = WALL_INNER_RECT.bottom - pc.total_radius
            if pc.position[1] < top_bound:
                pc.position[1] = top_bound
                pc.vel[1] *= -wall_cor
            elif pc.position[1] > bottom_bound:
                pc.position[1] = bottom_bound
                pc.vel[1] *= -wall_cor

    # ----- Energy diagnostics -----
    def compute_energy(self, all_charges):
        """
        Returns (kinetic_energy, potential_energy) as floats.
        Potential energy is Coulomb pairwise sum: U = sum_{i<j} k qi qj / r_soft
        with r_soft = sqrt(r^2 + eps^2), the same softening as the force.
        """
        n = len(all_charges)
        positions = np.array([p.position for p in all_charges])
        velocities = np.array([p.vel for p in all_charges])
        charges = np.array([p.charge for p in all_charges])
        masses = np.array([p.mass for p in all_charges])
        static_status = np.array([p.static for p in all_charges], dtype=bool)

        if n == 0:
            return 0.0, 0.0

        # kinetic energy
        ke = float(0.5 * np.sum(masses * np.einsum("ij,ij->i", velocities, velocities)))

        # potential energy: pairwise softened Coulomb, each pair i<j counted once,
        # with exactly the same softening as the force in get_accelerations
        i, j = np.triu_indices(n, k=1)
        diff = positions[i] - positions[j]
        r_soft = np.sqrt(np.einsum("ij,ij->i", diff, diff) + self.softening_eps2)
        pe = float(np.sum(K_COULOMB * charges[i] * charges[j] / r_soft))

        return ke, pe

    # Helper to step full physics tick: integrate, particle collisions, wall collisions, optional energy print
    def step(self, dt, all_charges, wall_cor=1.0, do_collisions=True, do_walls=True, diagnostics=False):
        """
        Convenience function performing:
            - integrate (Velocity-Verlet)
            - handle particle collisions (if do_collisions)
            - handle wall collisions (if do_walls)
            - return energy diagnostics if diagnostics True
        """
        # 1) Integrate
        self.update_positions_velocities(dt, all_charges)

        # 2) Resolve particle collisions (positional + impulses)
        if do_collisions:
            self.handle_particle_collisions(all_charges)

        # 3) Wall collisions
        if do_walls:
            self.handle_wall_collisions(all_charges, wall_cor)

        # 4) Diagnostics
        if diagnostics or self.debug:
            ke, pe = self.compute_energy(all_charges)
            if self.debug:
                print(f"[PhysicsEngine] KE: {ke:.6f}  PE: {pe:.6f}  Total: {ke+pe:.6f}")
            return ke, pe

        return None
