import math
import sys
import pygame

# -----------------------------
# Config / Constants
# -----------------------------
WIDTH, HEIGHT = 900, 520
FPS = 60
SKY_COLOR = (135, 206, 235)
GROUND_COLOR = (60, 120, 60)
PAD_A_COLOR = (200, 200, 60)
PAD_B_COLOR = (200, 100, 50)
HELI_BODY_COLOR = (220, 40, 45)  # red fuselage
HELI_WINDOW_COLOR = (180, 220, 230)  # light cyan windows
HELI_OUTLINE_COLOR = (50, 50, 50)  # dark outline
ROTOR_COLOR = (90, 90, 95)  # gray rotors
SKID_COLOR = (70, 75, 80)  # gray landing skids
CLOUD_COLOR = (255, 255, 255)
BUILDING_COLOR = (100, 100, 130)
WINDOW_LIT_COLOR = (240, 240, 190)
WINDOW_DARK_COLOR = (65, 75, 95)
TEXT_COLOR = (15, 25, 35)
TREE_TRUNK_COLOR = (94, 64, 44)
TREE_LEAF_COLOR = (50, 130, 70)
GROUND_Y = HEIGHT - 120

# World layout for illusion of horizontal movement (background scroll)
PAD_A_X = 50
PAD_B_X = 1500  # Point B far to the right in world coordinates

# Motion tuning (time-based)
MAX_ROTOR_SPEED = 18.0  # rad/s (main rotor) - faster for visual effect
SPIN_ACCEL = 8.0        # rad/s^2 (spin up) - responsive acceleration
SPIN_DECEL = 4.0        # rad/s^2 (spin down) - gradual deceleration
TAKEOFF_VS = 150.0      # px/s vertical speed (up)
LANDING_VS = 100.0      # px/s vertical speed (down) - slower for smooth landing
FLIGHT_SCROLL_SPEED = 180.0  # px/s background scroll to simulate forward motion
MANUAL_HORI_SPEED = 220.0    # px/s horizontal speed for keyboard control
MANUAL_VERT_SPEED = 150.0    # px/s vertical speed for keyboard control
GRAVITY = 80.0               # px/s gravity pull when not pressing W
MIN_FLIGHT_ROTOR_SPEED = 12.0  # minimum rotor speed needed for lift

# -----------------------------
# State Machine
# -----------------------------
class FlightState:
    IDLE = 0           # On ground, rotors stopped
    SPINNING_UP = 1    # W pressed, rotors accelerating
    FLYING = 2         # Airborne with controls
    LANDING = 3        # S pressed, descending
    SPIN_DOWN = 4      # Landed, rotors decelerating


# -----------------------------
# Background (world) rendering and scrolling
# -----------------------------
class Background:
    def __init__(self):
        self.offset_x = 0.0  # world-to-screen transform: screen_x = world_x - offset_x
        # simple parallax layers: buildings (far), trees/stripes (near), clouds (farther)
        self.clouds = [(200, 80), (500, 110), (900, 70), (1200, 130), (1600, 90)]
        # Buildings defined as (x, width, height); all rest on ground (GROUND_Y)
        self.buildings = [
            (300, 90, 210),
            (620, 120, 180),
            (960, 100, 200),
            (1320, 140, 230),
            (1680, 110, 190),
        ]
        self.stripes = [i * 120 for i in range(0, 40)]
        # Procedural tree placement along the world; deterministic variety
        self.trees = []  # each item: (x, size)
        for i in range(0, 38):
            tx = 140 + i * 160 + int(40 * math.sin(i * 0.8))
            size = 52 + (i % 5) * 10  # varied foliage size
            self.trees.append((tx, size))
        # Grass patches for more realistic ground
        self.grass_patches = []  # each item: (x, y_offset, blade_heights)
        for i in range(0, 200):
            gx = i * 30 + int(15 * math.sin(i * 1.3))
            gy_offset = 5 + (i % 4) * 8  # varied y position on ground
            # Generate varied blade heights for each patch
            blade_heights = [8 + (j * 3 + i) % 12 for j in range(5)]
            self.grass_patches.append((gx, gy_offset, blade_heights))

    def update_scroll(self, dt, direction=0):
        """Update background scroll based on movement direction (-1=left, 0=none, 1=right)"""
        if direction != 0:
            self.offset_x += direction * FLIGHT_SCROLL_SPEED * dt
            # Clamp offset to reasonable bounds
            self.offset_x = max(-200, min(2000, self.offset_x))

    def draw(self, screen):
        # Sky
        screen.fill(SKY_COLOR)
        # Clouds (farther layer: move slightly slower for parallax)
        for cx, cy in self.clouds:
            sx = int(cx - self.offset_x * 0.5)
            self._draw_cloud(screen, sx, cy)
        # Buildings (far layer)
        for bx, bw, bh in self.buildings:
            sx = int(bx - self.offset_x * 0.8)
            # draw building grounded: top at GROUND_Y - height
            self._draw_building(screen, sx, bw, bh)
        # Ground
        pygame.draw.rect(screen, GROUND_COLOR, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        # Grass patches (draw on ground for realistic texture)
        for gx, gy_offset, blade_heights in self.grass_patches:
            sx = int(gx - self.offset_x)
            if -20 < sx < WIDTH + 20:
                self._draw_grass_patch(screen, sx, GROUND_Y + gy_offset, blade_heights)
        # Ground stripes (near layer: fastest parallax)
        for x in self.stripes:
            sx = int(x - self.offset_x)
            pygame.draw.rect(screen, (70, 140, 70), (sx, GROUND_Y + 20, 40, 10))
        # Trees (near layer): draw after ground so they sit on it
        for tx, size in self.trees:
            sx = int(tx - self.offset_x)
            # small cull to avoid overdraw off-screen
            if -80 < sx < WIDTH + 80:
                self._draw_tree(screen, sx, GROUND_Y, size)
        # Pads
        pad_a_screen_x = int(PAD_A_X - self.offset_x)
        pad_b_screen_x = int(PAD_B_X - self.offset_x)
        pygame.draw.rect(screen, PAD_A_COLOR, (pad_a_screen_x - 40, GROUND_Y - 4, 80, 8))
        pygame.draw.rect(screen, PAD_B_COLOR, (pad_b_screen_x - 40, GROUND_Y - 4, 80, 8))

    def _draw_cloud(self, screen, x, y):
        pygame.draw.circle(screen, CLOUD_COLOR, (x, y), 18)
        pygame.draw.circle(screen, CLOUD_COLOR, (x + 20, y + 5), 22)
        pygame.draw.circle(screen, CLOUD_COLOR, (x - 18, y + 8), 16)

    def _draw_building(self, screen, x, w, h):
        # main block
        top_y = GROUND_Y - h
        rect = pygame.Rect(x, top_y, w, h)
        pygame.draw.rect(screen, BUILDING_COLOR, rect)
        # simple roofline
        pygame.draw.rect(screen, (85, 85, 110), (x, top_y - 4, w, 4))
        # windows grid inside with padding
        pad_x, pad_y = 8, 12
        win_w, win_h = 12, 14
        gap_x, gap_y = 6, 6
        usable_w = w - 2 * pad_x
        usable_h = h - pad_y - 22  # leave a little footer area
        if usable_w <= 0 or usable_h <= 0:
            return
        # compute number of columns/rows that fit
        cols = max(1, (usable_w + gap_x) // (win_w + gap_x))
        rows = max(1, (usable_h + gap_y) // (win_h + gap_y))
        # center the grid horizontally
        grid_w = cols * win_w + (cols - 1) * gap_x
        start_x = x + pad_x + max(0, (usable_w - grid_w) // 2)
        start_y = top_y + pad_y
        for r in range(int(rows)):
            for c in range(int(cols)):
                wx = start_x + c * (win_w + gap_x)
                wy = start_y + r * (win_h + gap_y)
                # alternating lit/unlit pattern for visual interest
                lit = ((r + c) % 2 == 0)
                color = WINDOW_LIT_COLOR if lit else WINDOW_DARK_COLOR
                pygame.draw.rect(screen, color, (wx, wy, win_w, win_h), border_radius=2)

    def _draw_tree(self, screen, x, base_y, size):
        # trunk
        trunk_w = max(8, size // 6)
        trunk_h = max(28, size // 2)
        pygame.draw.rect(screen, TREE_TRUNK_COLOR, (x - trunk_w // 2, base_y - trunk_h, trunk_w, trunk_h))
        # foliage (clustered circles)
        crown_y = base_y - trunk_h - 4
        r1 = max(14, size // 3)
        r2 = max(12, size // 4)
        pygame.draw.circle(screen, TREE_LEAF_COLOR, (x, crown_y), r1)
        pygame.draw.circle(screen, TREE_LEAF_COLOR, (x - r1 + 6, crown_y + 6), r2 + 4)
        pygame.draw.circle(screen, TREE_LEAF_COLOR, (x + r1 - 6, crown_y + 8), r2 + 2)

    def _draw_grass_patch(self, screen, x, y, blade_heights):
        # Draw individual grass blades as small lines/triangles
        grass_colors = [
            (45, 110, 55),   # darker green
            (55, 130, 60),   # medium green
            (65, 145, 70),   # lighter green
            (50, 120, 55),   # another shade
            (40, 100, 50),   # dark accent
        ]
        blade_spacing = 4
        for i, height in enumerate(blade_heights):
            bx = x + i * blade_spacing - 8
            # Draw grass blade as a thin triangle
            color = grass_colors[i % len(grass_colors)]
            # Slight sway variation based on position
            sway = int(2 * math.sin(x * 0.1 + i))
            points = [
                (bx, y),                          # base left
                (bx + 2, y),                      # base right
                (bx + 1 + sway, y - height),     # tip
            ]
            pygame.draw.polygon(screen, color, points)

    def pad_b_alignment(self, heli_screen_x: int) -> bool:
        """
        Returns True when the B pad is horizontally aligned under the helicopter,
        meaning the helicopter can begin a landing.
        """
        pad_b_screen_x = PAD_B_X - self.offset_x
        return abs(pad_b_screen_x - heli_screen_x) < 6


# -----------------------------
# Helicopter drawing and kinematics
# -----------------------------
class Helicopter:
    def __init__(self, x, ground_y):
        self.x = float(x)
        self.y = float(ground_y)  # starts on ground
        self.ground_y = ground_y
        # rotor dynamics
        self.rotor_angle = 0.0
        self.rotor_speed = 0.0  # rad/s
        # velocity for smooth physics
        self.vel_y = 0.0
        # geometry
        self.body_h = 42
        self.rotor_len = 100

    def update_rotor(self, dt, spinning_up=False):
        """Update rotor speed based on input state"""
        if spinning_up:
            # Accelerate rotor towards max speed
            self.rotor_speed = min(MAX_ROTOR_SPEED, self.rotor_speed + SPIN_ACCEL * dt)
        else:
            # Decelerate rotor towards zero
            self.rotor_speed = max(0.0, self.rotor_speed - SPIN_DECEL * dt)
        
        # Update rotor visual angle
        self.rotor_angle = (self.rotor_angle + self.rotor_speed * dt) % (2 * math.pi)

    def can_fly(self):
        """Check if rotor speed is sufficient for flight"""
        return self.rotor_speed >= MIN_FLIGHT_ROTOR_SPEED

    def apply_lift(self, dt):
        """Apply upward force when W is held and rotor is fast enough"""
        if self.can_fly():
            self.vel_y = -MANUAL_VERT_SPEED
        else:
            # Rotor not fast enough, reduced lift
            lift_factor = self.rotor_speed / MIN_FLIGHT_ROTOR_SPEED
            self.vel_y = -MANUAL_VERT_SPEED * lift_factor * 0.3

    def apply_gravity(self, dt):
        """Apply gravity when not pressing W"""
        if not self.on_ground():
            # Rotor provides some resistance to falling based on speed
            rotor_lift = (self.rotor_speed / MAX_ROTOR_SPEED) * GRAVITY * 0.8
            effective_gravity = GRAVITY - rotor_lift
            self.vel_y = min(LANDING_VS, self.vel_y + effective_gravity * dt)
        else:
            self.vel_y = 0.0

    def update_position(self, dt):
        """Update vertical position based on velocity"""
        self.y += self.vel_y * dt
        # Clamp to boundaries
        min_altitude = self.ground_y - 350  # Max height
        self.y = max(min_altitude, min(self.ground_y, self.y))
        # Stop at ground
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vel_y = 0.0

    def move_horizontal(self, dt, direction):
        """Move left (-1) or right (+1)"""
        self.x += direction * MANUAL_HORI_SPEED * dt
        # Clamp to screen boundaries with padding
        self.x = max(100, min(WIDTH - 100, self.x))

    def descend_landing(self, dt):
        """Controlled descent for landing"""
        self.vel_y = LANDING_VS
        self.y += self.vel_y * dt
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vel_y = 0.0

    def on_ground(self):
        return self.y >= self.ground_y - 1.0

    def at_altitude(self):
        return self.y <= self.ground_y - 50  # At least 50px off ground

    def draw(self, screen):
        # center reference for fuselage
        cx, cy = int(self.x), int(self.y - self.body_h // 2)

        # === MAIN ROTOR (draw first so it appears behind body) ===
        hub_x = cx + 10
        hub_y = cy - 38
        # Rotor mast/post
        pygame.draw.line(screen, HELI_OUTLINE_COLOR, (hub_x, cy - 18), (hub_x, hub_y), 4)
        # Rotating main rotor blades (long horizontal bar)
        bx1 = hub_x + int(math.cos(self.rotor_angle) * self.rotor_len)
        by1 = hub_y + int(math.sin(self.rotor_angle) * 8)  # flatten for top-down look
        bx2 = hub_x + int(math.cos(self.rotor_angle + math.pi) * self.rotor_len)
        by2 = hub_y + int(math.sin(self.rotor_angle + math.pi) * 8)
        pygame.draw.line(screen, ROTOR_COLOR, (bx1, by1), (bx2, by2), 6)
        # Hub circle
        pygame.draw.circle(screen, ROTOR_COLOR, (hub_x, hub_y), 5)

        # === TAIL SECTION ===
        # Tail boom (tapers towards the back)
        tail_points = [
            (cx - 40, cy - 8),    # start at body
            (cx - 120, cy - 4),   # top of tail end
            (cx - 120, cy + 6),   # bottom of tail end  
            (cx - 40, cy + 12),   # back to body
        ]
        pygame.draw.polygon(screen, HELI_BODY_COLOR, tail_points)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, tail_points, 2)

        # Tail fin (vertical stabilizer)
        tail_fin = [
            (cx - 115, cy - 4),
            (cx - 130, cy - 20),
            (cx - 140, cy - 20),
            (cx - 125, cy + 2),
        ]
        pygame.draw.polygon(screen, HELI_BODY_COLOR, tail_fin)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, tail_fin, 2)

        # Tail rotor (small rotating blade on tail)
        tail_rotor_x = cx - 138
        tail_rotor_y = cy - 12
        tr_angle = self.rotor_angle * 3.0
        tr_len = 14
        trx1 = tail_rotor_x
        try1 = tail_rotor_y + int(math.sin(tr_angle) * tr_len)
        trx2 = tail_rotor_x
        try2 = tail_rotor_y + int(math.sin(tr_angle + math.pi) * tr_len)
        pygame.draw.line(screen, ROTOR_COLOR, (trx1, try1), (trx2, try2), 4)

        # === MAIN BODY (fuselage) ===
        # Rounded rectangular body shape like in the image
        body_points = [
            (cx - 40, cy - 18),   # top left
            (cx + 50, cy - 18),   # top right before nose
            (cx + 75, cy - 10),   # nose top curve
            (cx + 85, cy + 2),    # nose tip
            (cx + 75, cy + 14),   # nose bottom curve
            (cx + 50, cy + 22),   # bottom right
            (cx - 40, cy + 22),   # bottom left
        ]
        pygame.draw.polygon(screen, HELI_BODY_COLOR, body_points)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, body_points, 2)

        # === COCKPIT WINDOWS (light cyan like in image) ===
        win_top = cy - 12
        win_bot = cy + 14
        
        # Three rectangular windows with slight slant
        # Window 1 (leftmost)
        w1 = [
            (cx - 25, win_top),
            (cx - 8, win_top),
            (cx - 10, win_bot),
            (cx - 27, win_bot),
        ]
        pygame.draw.polygon(screen, HELI_WINDOW_COLOR, w1)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, w1, 2)
        
        # Window 2 (middle)
        w2 = [
            (cx - 3, win_top),
            (cx + 16, win_top),
            (cx + 14, win_bot),
            (cx - 5, win_bot),
        ]
        pygame.draw.polygon(screen, HELI_WINDOW_COLOR, w2)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, w2, 2)
        
        # Window 3 (front, more slanted)
        w3 = [
            (cx + 21, win_top),
            (cx + 42, win_top + 4),
            (cx + 38, win_bot - 2),
            (cx + 19, win_bot),
        ]
        pygame.draw.polygon(screen, HELI_WINDOW_COLOR, w3)
        pygame.draw.polygon(screen, HELI_OUTLINE_COLOR, w3, 2)

        # === LANDING SKIDS (gray like in image) ===
        skid_y = cy + 38
        
        # Left skid (long horizontal bar with curved front)
        skid_left = cx - 60
        skid_right = cx + 70
        # Main skid bar
        pygame.draw.line(screen, SKID_COLOR, (skid_left, skid_y), (skid_right - 15, skid_y), 5)
        # Front curve up
        skid_curve = [
            (skid_right - 15, skid_y),
            (skid_right - 5, skid_y - 4),
            (skid_right, skid_y - 10),
        ]
        pygame.draw.lines(screen, SKID_COLOR, False, skid_curve, 5)
        
        # Rear curve up (slight)
        rear_curve = [
            (skid_left, skid_y),
            (skid_left - 8, skid_y - 6),
        ]
        pygame.draw.lines(screen, SKID_COLOR, False, rear_curve, 5)
        
        # Struts connecting body to skids
        strut_top = cy + 22
        # Front strut
        pygame.draw.line(screen, SKID_COLOR, (cx + 30, strut_top), (cx + 35, skid_y), 4)
        # Rear strut  
        pygame.draw.line(screen, SKID_COLOR, (cx - 25, strut_top), (cx - 30, skid_y), 4)


# -----------------------------
# Main loop with state transitions
# -----------------------------
class Simulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("HeliMotion - Keyboard Controls")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 16)
        self.font_large = pygame.font.SysFont("consolas", 20, bold=True)
        # actors
        self.bg = Background()
        self.heli = Helicopter(x=int(WIDTH * 0.35), ground_y=GROUND_Y - 10)
        # state
        self.state = FlightState.IDLE
        self.time_in_state = 0.0

    def change_state(self, new_state):
        self.state = new_state
        self.time_in_state = 0.0

    def handle_input(self):
        """Get current keyboard state using pygame's efficient key polling"""
        keys = pygame.key.get_pressed()
        return {
            'w': keys[pygame.K_w],
            'a': keys[pygame.K_a],
            's': keys[pygame.K_s],
            'd': keys[pygame.K_d],
        }

    def update(self, dt):
        self.time_in_state += dt
        
        # Get current input state
        inputs = self.handle_input()
        w_held = inputs['w']
        a_held = inputs['a']
        s_held = inputs['s']
        d_held = inputs['d']
        
        # State machine logic
        if self.state == FlightState.IDLE:
            # On ground, waiting for input
            self.heli.update_rotor(dt, spinning_up=False)
            
            # W key starts spinning up rotors
            if w_held:
                self.change_state(FlightState.SPINNING_UP)
        
        elif self.state == FlightState.SPINNING_UP:
            # W is held, rotors are spinning up
            if w_held:
                self.heli.update_rotor(dt, spinning_up=True)
                
                # Once rotor is fast enough and W is still held, apply lift
                if self.heli.can_fly():
                    self.heli.apply_lift(dt)
                    self.heli.update_position(dt)
                    
                    # Transition to flying once airborne
                    if self.heli.at_altitude():
                        self.change_state(FlightState.FLYING)
                elif self.heli.rotor_speed > MIN_FLIGHT_ROTOR_SPEED * 0.5:
                    # Partial lift as rotors spin up
                    self.heli.apply_lift(dt)
                    self.heli.update_position(dt)
            else:
                # W released - start spinning down
                self.heli.update_rotor(dt, spinning_up=False)
                self.heli.apply_gravity(dt)
                self.heli.update_position(dt)
                
                # Return to idle if on ground and rotors stopped
                if self.heli.on_ground() and self.heli.rotor_speed < 0.5:
                    self.change_state(FlightState.IDLE)
        
        elif self.state == FlightState.FLYING:
            # Full flight control mode
            
            # S key initiates landing
            if s_held:
                self.change_state(FlightState.LANDING)
                return
            
            # W key for lift / altitude
            if w_held:
                self.heli.update_rotor(dt, spinning_up=True)
                self.heli.apply_lift(dt)
            else:
                # Maintain rotor speed but apply gravity
                self.heli.update_rotor(dt, spinning_up=True)  # Keep rotors spinning in flight
                self.heli.apply_gravity(dt)
            
            # A/D for horizontal movement with background parallax
            if a_held and not d_held:
                self.bg.update_scroll(dt, direction=-1)  # Scroll background right (moving left)
            elif d_held and not a_held:
                self.bg.update_scroll(dt, direction=1)   # Scroll background left (moving right)
            
            # Update position
            self.heli.update_position(dt)
            
            # Check if helicopter touched ground (emergency landing)
            if self.heli.on_ground():
                self.change_state(FlightState.SPIN_DOWN)
        
        elif self.state == FlightState.LANDING:
            # Controlled descent
            self.heli.update_rotor(dt, spinning_up=True)  # Keep rotors at speed
            self.heli.descend_landing(dt)
            
            # A/D still work during landing for positioning
            if a_held and not d_held:
                self.bg.update_scroll(dt, direction=-1)
            elif d_held and not a_held:
                self.bg.update_scroll(dt, direction=1)
            
            # Cancel landing with W
            if w_held and not self.heli.on_ground():
                self.change_state(FlightState.FLYING)
                return
            
            # Landed successfully
            if self.heli.on_ground():
                self.change_state(FlightState.SPIN_DOWN)
        
        elif self.state == FlightState.SPIN_DOWN:
            # On ground, rotors spinning down
            self.heli.update_rotor(dt, spinning_up=False)
            
            # Can restart by pressing W
            if w_held:
                self.change_state(FlightState.SPINNING_UP)
                return
            
            # Fully stopped
            if self.heli.rotor_speed < 0.1:
                self.change_state(FlightState.IDLE)

    def draw(self):
        self.bg.draw(self.screen)
        self.heli.draw(self.screen)
        self._draw_hud()
        pygame.display.flip()

    def _draw_hud(self):
        # State display
        state_text = f"State: {self._state_name(self.state)}"
        state_surf = self.font.render(state_text, True, TEXT_COLOR)
        self.screen.blit(state_surf, (12, 10))
        
        # Rotor speed indicator with proper spacing
        rotor_pct = int((self.heli.rotor_speed / MAX_ROTOR_SPEED) * 100)
        rotor_text = f"Rotor:"
        rotor_surf = self.font.render(rotor_text, True, TEXT_COLOR)
        self.screen.blit(rotor_surf, (12, 30))
        
        # Rotor power bar (positioned after label)
        bar_x, bar_y = 70, 32
        bar_w, bar_h = 80, 14
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(bar_w * (self.heli.rotor_speed / MAX_ROTOR_SPEED))
        bar_color = (50, 200, 50) if self.heli.can_fly() else (200, 200, 50)
        pygame.draw.rect(self.screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(self.screen, TEXT_COLOR, (bar_x, bar_y, bar_w, bar_h), 1)
        
        # Percentage text after bar
        pct_text = f"{rotor_pct}%"
        pct_surf = self.font.render(pct_text, True, TEXT_COLOR)
        self.screen.blit(pct_surf, (bar_x + bar_w + 8, 30))
        
        # Altitude indicator
        altitude = int(self.heli.ground_y - self.heli.y)
        alt_text = f"Altitude: {altitude}px"
        alt_surf = self.font.render(alt_text, True, TEXT_COLOR)
        self.screen.blit(alt_surf, (12, 52))
        
        # Controls help (always visible)
        controls = [
            "W - Ascend",
            "A - Left",
            "D - Right", 
            "S - Land",
        ]
        
        # Draw controls panel
        panel_x = WIDTH - 140
        panel_y = 10
        panel_w = 130
        panel_h = 95
        pygame.draw.rect(self.screen, (30, 30, 40), (panel_x - 8, panel_y - 5, panel_w, panel_h), border_radius=6)
        pygame.draw.rect(self.screen, (100, 100, 120), (panel_x - 8, panel_y - 5, panel_w, panel_h), 2, border_radius=6)
        
        title_surf = self.font_large.render("CONTROLS", True, (255, 255, 255))
        self.screen.blit(title_surf, (panel_x, panel_y))
        
        for i, ctrl in enumerate(controls):
            ctrl_surf = self.font.render(ctrl, True, (220, 220, 220))
            self.screen.blit(ctrl_surf, (panel_x, panel_y + 22 + i * 17))

    def _state_name(self, s):
        return {
            FlightState.IDLE: "IDLE",
            FlightState.SPINNING_UP: "SPINNING UP",
            FlightState.FLYING: "FLYING",
            FlightState.LANDING: "LANDING",
            FlightState.SPIN_DOWN: "SPIN DOWN",
        }.get(s, "UNKNOWN")

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds per frame
            
            # Event handling (only for quit)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            self.update(dt)
            self.draw()
        
        pygame.quit()
        return 0


if __name__ == "__main__":
    sim = Simulation()
    sys.exit(sim.run())
