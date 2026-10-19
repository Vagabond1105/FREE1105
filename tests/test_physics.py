"""
Headless tests for the FREE1105 physics engine and radiation renderer.

Run from the repository root:
    python -m unittest discover -s tests -v

Most tests use the setup quoted in the README's Verification section: one charge
orbiting a fixed opposite charge, q = +-1 C, m = 1 kg, r = 300 px, softening
eps = 400 px, 400 steps per orbit, no walls or collisions, with the speed set so
the orbit is circular in the softened potential.
"""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")     # no window needed
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
import pygame

from constants_for_all_files import K_COULOMB, C_LIGHT, WALL_INNER_RECT
from physics_engine import PhysicsEngine
from point_charges import PointCharge, RadiationRenderer, RIPPLES_PER_CYCLE
from phase4_visualiser import _compute_potential

EPS = 400.0
R_ORBIT = 300.0
STEPS_PER_ORBIT = 400


def make_orbit(engine, r=R_ORBIT, q=1.0, m=1.0):
    """A fixed +q at the centre and a -q of mass m on a circular orbit of radius r.
    Returns (charges, period)."""
    centre = np.array([750.0, 450.0])
    nucleus = PointCharge(centre, q, 1.0, True, True, 0, 1.0, (0.0, 0.0))
    # softened attraction k q^2 r / (r^2 + eps^2)^(3/2) supplies m v^2 / r
    a = K_COULOMB * q * q * r / (r * r + engine.softening_eps2) ** 1.5 / m
    v = np.sqrt(a * r)
    electron = PointCharge(centre + (r, 0.0), -q, m, True, False, 1, 1.0, (0.0, v))
    return [nucleus, electron], 2 * np.pi * r / v


def total_energy(engine, charges):
    ke, pe = engine.compute_energy(charges)
    return ke + pe + engine.radiated_energy


class TestIntegrator(unittest.TestCase):

    def test_energy_conserved_without_radiation(self):
        """Velocity-Verlet: energy error stays small and bounded over 50 orbits (no drift)."""
        eng = PhysicsEngine(softening_eps=EPS)
        charges, period = make_orbit(eng)
        dt = period / STEPS_PER_ORBIT
        e0 = total_energy(eng, charges)
        errors = []
        for _ in range(50 * STEPS_PER_ORBIT):
            eng.update_positions_velocities(dt, charges)
            errors.append((total_energy(eng, charges) - e0) / abs(e0))
        errors = np.array(errors)
        self.assertLess(np.max(np.abs(errors)), 1e-7)
        first, last = errors[:STEPS_PER_ORBIT].mean(), errors[-STEPS_PER_ORBIT:].mean()
        self.assertLess(abs(last - first), 1e-8, "mean error drifted between first and last orbit")

    def test_circular_orbit_stays_circular(self):
        eng = PhysicsEngine(softening_eps=EPS)
        charges, period = make_orbit(eng)
        dt = period / STEPS_PER_ORBIT
        radii = []
        for _ in range(10 * STEPS_PER_ORBIT):
            eng.update_positions_velocities(dt, charges)
            radii.append(np.linalg.norm(charges[1].position - charges[0].position))
        self.assertLess(np.ptp(radii) / R_ORBIT, 1e-3)

    def test_force_is_minus_gradient_of_potential(self):
        """The force and the energy diagnostic must describe the same (softened) physics."""
        eng = PhysicsEngine(softening_eps=EPS)
        rng = np.random.default_rng(1)
        charges = [PointCharge(rng.uniform(100, 1400, 2), q, 1.0, True, False, i, 1.0, (0, 0))
                   for i, q in enumerate([1.0, -2.0, 0.5, 1.5])]
        pos = np.array([c.position for c in charges])
        q = np.array([c.charge for c in charges])
        m = np.ones(len(charges))
        acc = eng.get_accelerations(pos, np.zeros_like(pos), q, m, np.zeros(len(charges), bool))
        h = 1e-3
        for k in range(2):
            charges[0].position = pos[0].copy(); charges[0].position[k] += h
            _, pe_plus = eng.compute_energy(charges)
            charges[0].position = pos[0].copy(); charges[0].position[k] -= h
            _, pe_minus = eng.compute_energy(charges)
            force = -(pe_plus - pe_minus) / (2 * h)
            self.assertAlmostEqual(force / acc[0, k], 1.0, places=6)

    def test_static_charge_never_moves(self):
        eng = PhysicsEngine(softening_eps=EPS)
        charges, period = make_orbit(eng)
        start = charges[0].position.copy()
        for _ in range(500):
            eng.update_positions_velocities(period / STEPS_PER_ORBIT, charges)
        np.testing.assert_array_equal(charges[0].position, start)

    def test_momentum_conserved_for_free_pair(self):
        eng = PhysicsEngine(softening_eps=EPS)
        a = PointCharge((500.0, 450.0), 1.0, 1.0, True, False, 0, 1.0, (30.0, 10.0))
        b = PointCharge((900.0, 400.0), -1.0, 3.0, True, False, 1, 1.0, (-5.0, 0.0))
        p0 = a.mass * a.vel + b.mass * b.vel
        for _ in range(2000):
            eng.update_positions_velocities(1e-3, [a, b])
        np.testing.assert_allclose(a.mass * a.vel + b.mass * b.vel, p0, atol=1e-6)

    def test_invalid_softening_rejected(self):
        with self.assertRaises(ValueError):
            PhysicsEngine(softening_eps=0.0)


class TestRadiation(unittest.TestCase):

    def run_orbits(self, c, n_orbits):
        eng = PhysicsEngine(softening_eps=EPS)
        eng.radiation_c = c
        charges, period = make_orbit(eng)
        dt = period / STEPS_PER_ORBIT
        e0 = total_energy(eng, charges)
        worst = 0.0
        for _ in range(n_orbits * STEPS_PER_ORBIT):
            eng.update_positions_velocities(dt, charges)
            worst = max(worst, abs(total_energy(eng, charges) - e0) / abs(e0))
        return eng, charges, period, worst

    def test_radiated_energy_matches_larmor(self):
        """P = (2/3) k q^2 a^2 / c^3, integrated over 20 orbits, against the simulation's tally."""
        c = 1e5
        eng, charges, period, _ = self.run_orbits(c, 20)
        a = K_COULOMB * R_ORBIT / (R_ORBIT ** 2 + EPS ** 2) ** 1.5
        analytic = (2.0 / 3.0) * K_COULOMB * a ** 2 / c ** 3 * 20 * period
        self.assertAlmostEqual(eng.radiated_energy / analytic, 1.0, delta=1e-3)

    def test_energy_bookkeeping_with_radiation(self):
        """With a strong drain (c = 3e4) the orbit decays, but KE + PE + radiated stays at E0."""
        eng, charges, _, worst = self.run_orbits(3e4, 20)
        r_final = np.linalg.norm(charges[1].position - charges[0].position)
        self.assertLess(r_final, 0.9 * R_ORBIT, "the orbit should visibly decay")
        self.assertLess(worst, 1e-5)

    def test_real_c_is_indistinguishable_from_off(self):
        with_rad = self.run_orbits(C_LIGHT, 5)[1]
        without = self.run_orbits(None, 5)[1]
        np.testing.assert_allclose(with_rad[1].position, without[1].position, atol=1e-6)

    def test_neutral_and_static_charges_never_radiate(self):
        eng = PhysicsEngine(softening_eps=EPS)
        eng.radiation_c = 3e4
        nucleus = PointCharge((750.0, 450.0), 1.0, 1.0, True, True, 0, 1.0, (0, 0))
        neutral = PointCharge((1000.0, 450.0), 0.0, 1.0, True, False, 1, 1.0, (0, 500.0))
        pushed = PointCharge((500.0, 450.0), 1.0, 1.0, True, True, 2, 1.0, (0, 0))   # static, feels a force
        for _ in range(1000):
            eng.update_positions_velocities(1e-3, [nucleus, neutral, pushed])
        self.assertEqual(eng.radiated_energy, 0.0)
        self.assertEqual(neutral.rad_power, 0.0)
        self.assertEqual(pushed.rad_power, 0.0)


class TestCollisions(unittest.TestCase):

    def test_elastic_collision_conserves_momentum_and_energy(self):
        eng = PhysicsEngine(softening_eps=EPS)
        a = PointCharge((700.0, 450.0), 0.0, 1.0, True, False, 0, 1.0, (100.0, 0.0))
        b = PointCharge((735.0, 455.0), 0.0, 2.0, True, False, 1, 1.0, (-20.0, 0.0))
        p0 = a.mass * a.vel + b.mass * b.vel
        ke0 = 0.5 * a.mass * a.vel @ a.vel + 0.5 * b.mass * b.vel @ b.vel
        eng.handle_particle_collisions([a, b])
        np.testing.assert_allclose(a.mass * a.vel + b.mass * b.vel, p0, atol=1e-9)
        ke1 = 0.5 * a.mass * a.vel @ a.vel + 0.5 * b.mass * b.vel @ b.vel
        self.assertAlmostEqual(ke1, ke0, places=6)

    def test_inelastic_collision_loses_energy(self):
        eng = PhysicsEngine(softening_eps=EPS)
        a = PointCharge((700.0, 450.0), 0.0, 1.0, True, False, 0, 0.5, (100.0, 0.0))
        b = PointCharge((735.0, 450.0), 0.0, 1.0, True, False, 1, 0.5, (-100.0, 0.0))
        eng.handle_particle_collisions([a, b])
        # head-on, equal masses, e = 0.5: each rebounds at half speed
        np.testing.assert_allclose(a.vel, [-50.0, 0.0], atol=1e-9)
        np.testing.assert_allclose(b.vel, [50.0, 0.0], atol=1e-9)

    def test_wall_bounce_applies_restitution(self):
        eng = PhysicsEngine(softening_eps=EPS)
        pc = PointCharge((WALL_INNER_RECT.left + 5.0, 450.0), 1.0, 1.0, True, False, 0, 1.0, (-200.0, 30.0))
        eng.handle_wall_collisions([pc], 0.9)
        self.assertAlmostEqual(pc.vel[0], 180.0)
        self.assertAlmostEqual(pc.vel[1], 30.0)
        self.assertGreaterEqual(pc.position[0], WALL_INNER_RECT.left + pc.total_radius)


class TestRadiationRenderer(unittest.TestCase):

    def test_one_ripple_per_cycle(self):
        """Ripple rate is one to one with the motion: one arc pair per period 2*pi/omega."""
        eng = PhysicsEngine(softening_eps=EPS)
        eng.radiation_c = C_LIGHT
        charges, period = make_orbit(eng)
        renderer = RadiationRenderer()
        dt = period / STEPS_PER_ORBIT
        emitted = 0
        for _ in range(3 * STEPS_PER_ORBIT):
            eng.update_positions_velocities(dt, charges)
            old = {id(w) for w in renderer.waves}       # old waves also age out, so count new ones
            renderer.update(charges, dt)
            emitted += sum(1 for w in renderer.waves if id(w) not in old)
        # 3 orbits: one emission at t = 0, then one per period (the last may land on either
        # side of the final step); each emission is a pair of arcs
        self.assertIn(emitted, (2 * 3 * RIPPLES_PER_CYCLE, 2 * (3 * RIPPLES_PER_CYCLE + 1)))

    def test_render_smoke(self):
        pygame.init()
        screen = pygame.Surface((1500, 900))
        eng = PhysicsEngine(softening_eps=EPS)
        eng.radiation_c = C_LIGHT
        charges, period = make_orbit(eng)
        renderer = RadiationRenderer()
        for _ in range(100):      # a quarter orbit: the first wavefront is still in flight
            eng.update_positions_velocities(period / STEPS_PER_ORBIT, charges)
            renderer.update(charges, period / STEPS_PER_ORBIT)
            renderer.render(screen)
        self.assertGreater(len(renderer.waves), 0)


class TestPotentialSurface(unittest.TestCase):

    def test_potential_matches_coulomb(self):
        xs, ys = np.meshgrid(np.linspace(0, 1500, 7), np.linspace(0, 900, 5))
        charges = [{'px': 300.0, 'py': 200.0, 'charge': 2.0, 'radius': 21.0},
                   {'px': 1100.0, 'py': 700.0, 'charge': -1.0, 'radius': 21.0}]
        V = _compute_potential(charges, xs, ys)
        expected = sum(K_COULOMB * c['charge'] / np.maximum(np.hypot(xs - c['px'], ys - c['py']), c['radius'])
                       for c in charges)
        np.testing.assert_allclose(V, expected)


if __name__ == "__main__":
    unittest.main()
