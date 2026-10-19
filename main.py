import pygame
import sys
import numpy as np

# IMPORTS
from constants_for_all_files import *
from point_charges import *
from electric_field import *
from physics_engine import *
from gui import *
from phase4_visualiser import Phase4Visualiser
phase4 = Phase4Visualiser()
phase4.start()

# --- 1. INITIALIZATION & SETUP ---
pygame.init()
screen = pygame.display.set_mode((SW, SH))
pygame.display.set_caption("FREE1105")
clock = pygame.time.Clock()

# --- 2. SYSTEMS ---
ef_system = ElectricFieldSystem()
reset_btn = ResetButton()
pause_btn = PauseButton()
unpause_btn = UnpauseButton()
start_btn = StartButton()
context_menu = ContextMenu()
create_form = CreationForm()
trails_toggle = TrailsToggle()

# Sliders
wall_cor_slider = WallCORSlider(30, 20, 150, 30, initial_value=BW_coeff)
dt_slider = GenericSlider(1250, 50, 150, 30,min_val=0.00005, max_val=0.02, initial_val=1/1000, 
                          label="Time Step (dt):", fmt="{:.5f}")
fps_slider = GenericSlider(1250, 100, 150, 30, min_val=60, max_val=9000, initial_val=100, 
                           label="Max FPS:", fmt="{:.0f}")
# Larmor radiation, with the real speed of light
radiation_toggle = BinaryToggle(1250, 150, 80, 30, "Radiation:", initial_state=False)
radiation_renderer = RadiationRenderer()

# engine
physics_engine = PhysicsEngine()

# --- 3. STATE MANAGEMENT ---
# 0 = SETUP (Edit Mode), 1 = RUNNING (Physics Mode)
sim_state = 0 

all_point_charges = []
selected_charge = None
p_id_counter = 0
wall_cor = wall_cor_slider.value 
# Double-click tracking for particle duplication
LAST_CLICK_MS = 400  # max ms between clicks to consider a double-click
last_click_time = 0
last_click_pc_id = None

# Set when the integration overflowed (see the physics update); shown in the readout
numerics_blew_up = False

# Energy tracking
total_kinetic_energy = 0.0
total_potential_energy = 0.0
initial_total_energy = None  # Set when simulation starts
energy_font = pygame.font.SysFont('Arial', 16)

# Pause text bouncing (DVD logo style)

import math
pause_text_pos = [SW // 2, SH // 2]
pause_text_vel = [900 * math.cos(math.radians(40)), 900 * math.sin(math.radians(40))]  # 40 degrees
pause_font = pygame.font.SysFont("Roboto", 74)

# core simulation loop

running = True
while running:
    
    dt = dt_slider.value
    fps = int(fps_slider.value)

    # --- A. TIME & MOUSE ---
    mouse_pos = pygame.mouse.get_pos()
    
    # --- B. GLOBAL EVENT HANDLING (THE ONE TRUE LOOP) ---
    for event in pygame.event.get():
        # 1. GLOBAL: Quit
        if event.type == pygame.QUIT:
            running = False
        
        # 2. GLOBAL: Reset Button (Works in ANY state to save you)
        # Back to SETUP: the non-environmental charges are deleted and the rest return to
        # their initial position and velocity, so they can be moved and Started again.
        if reset_btn.handle_event(event):
            sim_state = 0 # Force back to SETUP
            all_point_charges = [pc for pc in all_point_charges if pc.environmental]
            for pc in all_point_charges:
                pc.reset()
            selected_charge = None
            context_menu.active = False
            create_form.active = False
            radiation_renderer.clear()
            numerics_blew_up = False
            print("SIMULATION RESET")
            # This click is used up: passing it on to the SETUP code below could also
            # count it as a click on Start and restart the run straight away
            continue

        # --- C. STATE SPECIFIC EVENTS ---
        
        # === STATE 0: SETUP PHASE (Editing Allowed) ===
        if sim_state == 0:
            
            # 1. Start Button (Only works in Setup) and requires no particles touching walls or other particles and they are existing
            particles_touching = False
            for pc in all_point_charges:
                # Check against the visible black wall (WALL_INNER_RECT), not the window edges
                if (pc.position[0] - pc.total_radius <= WALL_INNER_RECT.left or
                    pc.position[0] + pc.total_radius >= WALL_INNER_RECT.right or
                    pc.position[1] - pc.total_radius <= WALL_INNER_RECT.top or
                    pc.position[1] + pc.total_radius >= WALL_INNER_RECT.bottom):
                    particles_touching = True
                    break
                for other_pc in all_point_charges:
                    if other_pc != pc:
                        dist = np.linalg.norm(pc.position - other_pc.position)
                        if dist < (pc.total_radius + other_pc.total_radius):
                            particles_touching = True
                            break
                if particles_touching:
                    break

            # Evaluate start button once per event to avoid duplicate calls
            start_pressed = start_btn.handle_event(event)
            if start_pressed:
                if particles_touching:
                    print("ERROR: Cannot start simulation while particles are touching walls or each other.")
                elif len(all_point_charges) == 0:
                    print("ERROR: Cannot start simulation without any point charges present.")
                else:
                    sim_state = 1 # LOCK IN! Switch to Running
                    # Clear any active selections
                    selected_charge = None
                    context_menu.active = False
                    create_form.active = False
                    # Capture initial energy
                    ke_init, pe_init = physics_engine.compute_energy(all_point_charges)
                    initial_total_energy = ke_init + pe_init
                    physics_engine.reset_radiation()
                    radiation_renderer.clear()
                    print("SIMULATION STARTED")
                    print(f"Initial Total Energy: {initial_total_energy:.2e} J")
                    # This click is used up: Pause sits exactly where Start is, so passing
                    # it on to the RUNNING code below would pause the run straight away
                    continue

            # 2. Sliders
            wall_cor_slider.handle_event(event)
            dt_slider.handle_event(event)
            fps_slider.handle_event(event)
            radiation_toggle.handle_event(event)

            # 3. Context Menu Logic
            menu_action = context_menu.handle_event(event)
            if menu_action == "open_creator":
                create_form.show(context_menu.pos)

            # 4. Creation Form Logic
            form_data = create_form.handle_event(event)
            if form_data:
                try:
                    # Deletion requested from edit form
                    if form_data.get('delete'):
                        particle = form_data.get('particle')
                        try:
                            all_point_charges = [pc for pc in all_point_charges if pc != particle]
                        except Exception:
                            pass
                        print("Particle deleted")
                        continue
                    if form_data.get('edit'):
                        # Edit existing particle
                        particle = form_data['particle']
                        particle.charge = form_data['charge']
                        particle.mass = form_data['mass']
                        # update coefficient of restitution if provided
                        particle.e = form_data.get('e', getattr(particle, 'e', 1.0))
                        particle.environmental = form_data['environmental']
                        particle.static = form_data['static']
                        # Update color based on charge (handle neutral)
                        if particle.charge > 0:
                            particle.color = (200, 0, 0)
                        elif particle.charge < 0:
                            particle.color = (0, 0, 200)
                        else:
                            particle.color = (80, 80, 80)
                        particle.update_relative_scale(all_point_charges)
                        # update velocity if provided <--- FIX IS HERE
                        particle.vel_0 = form_data['velocity'] 
                        particle.vel = form_data['velocity'].copy()
                    else:
                        # Create new particle
                        new_pc = PointCharge(
                            form_data['position'],
                            form_data['charge'],
                            form_data['mass'],
                            form_data['environmental'],
                            form_data['static'],
                            p_id_counter,
                            form_data.get('e', 1.0),
                            form_data.get('velocity', np.array([0.0, 0.0])) # NEW: Pass vector
                        )
                        all_point_charges.append(new_pc)
                        p_id_counter += 1
                except Exception as e:
                    print(f"Form Error: {e}")

            # 5. Mouse Interactions (Drag & Drop / Right Click)
            # Only allowed if GUI is NOT blocking the mouse
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not context_menu.active and not create_form.active and not wall_cor_slider.dragging:
                    
                    if event.button == 1: # Left Click (Select/Drag / Double-Click Duplicate)
                        clicked_pc = None
                        click_pos = np.array(event.pos)
                        for pc in reversed(all_point_charges):
                            dist = np.linalg.norm(pc.position - click_pos)
                            if dist < pc.total_radius:
                                clicked_pc = pc
                                break

                        if clicked_pc is not None:
                            now = pygame.time.get_ticks()
                            # Double-click detection: same particle clicked twice within LAST_CLICK_MS
                            if last_click_pc_id == getattr(clicked_pc, 'pc_id', None) and (now - last_click_time) <= LAST_CLICK_MS:
                                # Duplicate particle slightly shifted to the right and down
                                try:
                                    shift = np.array([12.0, 12.0])
                                    new_pos = clicked_pc.position + shift
                                    new_pc = PointCharge(
                                        new_pos.copy(),
                                        clicked_pc.charge,
                                        clicked_pc.mass,
                                        clicked_pc.environmental,
                                        clicked_pc.static,
                                        p_id_counter,
                                        getattr(clicked_pc, 'e', 1.0)
                                        ,clicked_pc.vel_0
                                    )
                                    all_point_charges.append(new_pc)
                                    p_id_counter += 1
                                    print(f"Duplicated particle {getattr(clicked_pc,'pc_id','?')} -> {p_id_counter-1}")
                                except Exception as e:
                                    print(f"Duplication error: {e}")
                                # reset click tracker to avoid triple-trigger
                                last_click_time = 0
                                last_click_pc_id = None
                            else:
                                # Single click: prepare for drag
                                selected_charge = clicked_pc
                                clicked_pc.dragging = True
                                # store click info for possible double-click
                                last_click_time = pygame.time.get_ticks()
                                last_click_pc_id = getattr(clicked_pc, 'pc_id', None)
                                
                    elif event.button == 3: # Right Click (Context Menu)
                        clicked_on_charge = False
                        clicked_charge = None
                        for pc in reversed(all_point_charges):
                             dist = np.linalg.norm(pc.position - np.array(event.pos))
                             if dist < pc.total_radius:
                                 clicked_on_charge = True
                                 clicked_charge = pc
                                 break
                        
                        if clicked_on_charge:
                            create_form.show(event.pos, particle=clicked_charge)
                        else:
                            context_menu.show(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and selected_charge:
                    selected_charge.dragging = False
                    # Set new initial position to current position after drag
                    selected_charge.pos_0 = selected_charge.position.copy()
                    selected_charge = None
                    
            elif event.type == pygame.MOUSEMOTION:
                if selected_charge:
                    selected_charge.position = np.array(event.pos, dtype=float)

        # === STATE 1: RUNNING PHASE (Physics Allowed) ===
        if sim_state == 1:
            # No dragging allowed here!
            # Just listening for "Pause" (Future Phase) or "Reset" (Global) and fps / dt sliders

            wall_cor_slider.handle_event(event)
            dt_slider.handle_event(event)
            fps_slider.handle_event(event)
            radiation_toggle.handle_event(event)

            if pause_btn.handle_event(event):
                sim_state = 0.5 # Literally just pauses the sim

            # Trails toggle (only active in running state)
            if trails_toggle.handle_event(event):
                # handle_event already toggles internal state; when turned off, clear existing trails
                if not trails_toggle.state:
                    for pc in all_point_charges:
                        try:
                            pc.history.clear()
                            pc.frame_counter = 0
                        except Exception:
                            pass

        elif sim_state == 0.5:

            # Paused State - Listen for Unpause from same button or Reset
            if unpause_btn.handle_event(event):
                sim_state = 1 # Resume Simulation

    # --- D. LOGIC UPDATES (General) ---
    
    # Update wall coefficient
    wall_cor = wall_cor_slider.value 

    # Radiation on/off, at the real speed of light
    physics_engine.radiation_c = C_LIGHT if radiation_toggle.state else None

    # Update visual scales (Always needed for rendering)
    for pc in all_point_charges:
        pc.update_relative_scale(all_point_charges)

    # --- E. PHYSICS UPDATES (State Dependent) ---

    if sim_state == 1:

        # 1. The Velocity-Verlet integration step (Motion with forces)
        physics_engine.update_positions_velocities(dt, all_point_charges)
        
        # 2. Handle collisions AFTER integration
        physics_engine.handle_wall_collisions(all_point_charges, wall_cor)
        physics_engine.handle_particle_collisions(all_point_charges)

        # Extreme inputs (huge charges, tiny masses, a big dt) can overflow to inf/NaN.
        # Pause instead of crashing in the renderer; Reset restores the initial state.
        if not all(np.all(np.isfinite(pc.position)) and np.all(np.isfinite(pc.vel))
                   for pc in all_point_charges):
            sim_state = 0.5
            numerics_blew_up = True
            print("Simulation paused: the numbers overflowed. Try a smaller dt, or less extreme "
                  "charges and masses, then press Reset.")
            for pc in all_point_charges:
                if not (np.all(np.isfinite(pc.position)) and np.all(np.isfinite(pc.vel))):
                    pc.position = np.nan_to_num(pc.position, nan=SW / 2, posinf=SW / 2, neginf=SW / 2)
                    pc.vel = np.zeros(2)

        # Emit and move the radiation wavefronts (in simulated time, one ripple per cycle of the motion)
        radiation_renderer.update(all_point_charges, dt)

        # No energy "correction" here on purpose: the energy readout must show what the
        # integrator actually does (Verlet: bounded oscillation, no drift), not a value
        # forced back to E0 by rescaling velocities.

        # Record trails for each particle (only if toggle enabled)
        for pc in all_point_charges:
            pc.record_trail(trails_toggle.state)
        
        # Calculate energies using physics engine (ensures consistency with force calculations)
        total_kinetic_energy, total_potential_energy = physics_engine.compute_energy(all_point_charges)

    # Update pause text position (bouncing DVD logo style)
    elif sim_state == 0.5:
        pause_text_pos[0] += pause_text_vel[0] * dt*10
        pause_text_pos[1] += pause_text_vel[1] * dt*19
        
        # Bounce off walls (with margin for text width/height)
        text_bounds = pause_font.render("PAUSED", True, (0, 0, 0)).get_rect()
        text_width = text_bounds.width
        text_height = text_bounds.height
        
        if pause_text_pos[0] - text_width//2 <= 0 or pause_text_pos[0] + text_width//2 >= SW:
            pause_text_vel[0] *= -1
            pause_text_pos[0] = max(text_width//2, min(SW - text_width//2, pause_text_pos[0]))
        
        if pause_text_pos[1] - text_height//2 <= 0 or pause_text_pos[1] + text_height//2 >= SH:
            pause_text_vel[1] *= -1
            pause_text_pos[1] = max(text_height//2, min(SH - text_height//2, pause_text_pos[1]))

    # --- F. RENDERING (The Layers) ---
    
    # Layer 0: Background (E-Field)
    ef_system.render(screen, all_point_charges)
    
    # Layer 1: Environment (Walls)
    pygame.draw.rect(screen, WC, WALL_RECT, WBT) 
    
    # Layer 2: Particles (render trails behind particles)
    
    for pc in all_point_charges:
        pc.render_trails(screen)

    # Layer 2.2: Larmor radiation wavefronts (behind the particles)
    if sim_state != 0:
        radiation_renderer.render(screen)

    for pc in all_point_charges:
        # Only show arrows in setup mode (sim_state == 0)
        if sim_state == 0:
            pc.update_arrow(all_point_charges)
            pc.arrow_display = True
        else:
            pc.arrow_display = False
        pc.render(screen)

    # Layer 2.5: Energy readout (measured, never corrected)
    if sim_state != 0 and initial_total_energy is not None:
        # Radiated energy is counted in the total: light carries it away, it isn't destroyed,
        # so KE + PE + radiated should stay at E0 (walls/collisions with restitution < 1 still lose energy)
        radiated = physics_engine.radiated_energy
        total_energy = total_kinetic_energy + total_potential_energy + radiated
        drift = (total_energy - initial_total_energy) / abs(initial_total_energy) if initial_total_energy else 0.0
        energy_lines = [
            (f"KE        {total_kinetic_energy: .4e} J", text_c),
            (f"PE        {total_potential_energy: .4e} J", text_c),
            (f"Radiated  {radiated: .4e} J", text_c),
            (f"Total     {total_energy: .4e} J", text_c),
            (f"(E - E0)/|E0|  {drift: .2e}", text_c),
        ]
        if physics_engine.radiation_c is not None and all_point_charges:
            # The Larmor formula used is the non-relativistic one: it needs v << c
            v_over_c = max(np.linalg.norm(pc.vel) for pc in all_point_charges) / physics_engine.radiation_c
            energy_lines.append((f"max v/c  {v_over_c:.3f}" + ("  (Larmor needs v << c)" if v_over_c > 0.3 else ""),
                                 (180, 0, 0) if v_over_c > 0.3 else text_c))
        if numerics_blew_up:
            energy_lines.append(("Numbers overflowed: paused. Press Reset.", (180, 0, 0)))
        top = SH - 70 - 20 * len(energy_lines)     # stacked above the Reset button
        for line_no, (line, colour) in enumerate(energy_lines):
            screen.blit(energy_font.render(line, True, colour), (WBT + 10, top + 20 * line_no))

    # Layer 3: GUI (State Dependent)

    # Always show Reset
    reset_btn.render(screen)
    
    if sim_state == 0:
        # Only show Setup GUI in Setup Mode
        start_btn.render(screen)
        wall_cor_slider.render(screen)
        context_menu.render(screen)
        create_form.render(screen)
        dt_slider.render(screen)
        fps_slider.render(screen)
        radiation_toggle.render(screen)

    elif sim_state == 1:
        pause_btn.render(screen)
        trails_toggle.render(screen)
        dt_slider.render(screen)
        fps_slider.render(screen)
        radiation_toggle.render(screen)

    elif sim_state == 0.5:
        unpause_btn.render(screen)
        
        # Render PAUSED text with bouncing and letter borders
        pause_text = "PAUSED"
        letter_color = (250, 190, 200)  # Pink
        border_color = (60, 200, 60)  # Light Green
        border_width = 3
        
        # Render each letter individually with border
        letter_spacing = 10
        total_width = sum(pause_font.render(char, True, letter_color).get_width() for char in pause_text) + (len(pause_text) - 1) * letter_spacing
        start_x = pause_text_pos[0] - total_width // 2
        
        for i, char in enumerate(pause_text):
            char_surf = pause_font.render(char, True, letter_color)
            char_width = char_surf.get_width()
            
            # Draw border around letter (by rendering text 4 times around it)
            for dx, dy in [(-border_width, 0), (border_width, 0), (0, -border_width), (0, border_width)]:
                border_surf = pause_font.render(char, True, border_color)
                screen.blit(border_surf, (start_x + dx, pause_text_pos[1] - char_surf.get_height()//2 + dy))
            
            # Draw actual letter on top
            screen.blit(char_surf, (start_x, pause_text_pos[1] - char_surf.get_height()//2))
            start_x += char_width + letter_spacing

    phase4.update(all_point_charges)

    pygame.display.flip()
    clock.tick(fps)


pygame.quit()
phase4.stop()
sys.exit()