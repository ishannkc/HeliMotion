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
HELI_BODY_COLOR = (80, 80, 90)
HELI_ACCENT_COLOR = (30, 30, 35)
ROTOR_COLOR = (20, 20, 20)
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
MAX_ROTOR_SPEED = 6.0  # rad/s (main rotor)
SPIN_ACCEL = 3.0       # rad/s^2 (spin up)
SPIN_DECEL = 2.0       # rad/s^2 (spin down)
TAKEOFF_VS = 150.0     # px/s vertical speed (up)
LANDING_VS = 140.0     # px/s vertical speed (down)
FLIGHT_SCROLL_SPEED = 180.0  # px/s background scroll to simulate forward motion

# -----------------------------
# State Machine
# -----------------------------
class FlightState:
    GROUND_IDLE = 0
    SPIN_UP = 1
    TAKE_OFF = 2
    FLY = 3
    LANDING = 4
    SPIN_DOWN = 5
    DONE = 6


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

    def update_scroll(self, dt, active: bool):
        if active:
            self.offset_x += FLIGHT_SCROLL_SPEED * dt

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
        self.x = x
        self.y = ground_y  # starts on ground
        self.ground_y = ground_y
        # rotor dynamics
        self.rotor_angle = 0.0
        self.rotor_speed = 0.0  # rad/s
        # geometry
        self.body_w = 140
        self.body_h = 36
        self.tail_w = 90
        self.tail_h = 12
        self.skid_w = 120
        self.skid_h = 6
        self.rotor_len = 70
        self.rotor_post_h = 18

    def update_rotor(self, dt, target_speed=None, decel=False):
        if target_speed is not None and not decel:
            # spin up capped at MAX_ROTOR_SPEED
            self.rotor_speed = min(MAX_ROTOR_SPEED, self.rotor_speed + SPIN_ACCEL * dt)
            # clamp to target
            self.rotor_speed = min(self.rotor_speed, target_speed)
        elif decel:
            # spin down to zero
            self.rotor_speed = max(0.0, self.rotor_speed - SPIN_DECEL * dt)
        self.rotor_angle = (self.rotor_angle + self.rotor_speed * dt) % (2 * math.pi)

    def move_vertical(self, dt, up=True):
        if up:
            self.y = max(self.ground_y - 220, self.y - TAKEOFF_VS * dt)
        else:
            self.y = min(self.ground_y, self.y + LANDING_VS * dt)

    def on_ground(self):
        return abs(self.y - self.ground_y) < 0.5

    def at_altitude(self):
        return abs(self.y - (self.ground_y - 220)) < 1.0

    def draw(self, screen):
        # body center
        cx, cy = int(self.x), int(self.y - self.body_h // 2)
        # fuselage
        body_rect = pygame.Rect(cx - self.body_w // 2, cy - self.body_h // 2, self.body_w, self.body_h)
        pygame.draw.rect(screen, HELI_BODY_COLOR, body_rect, border_radius=6)
        # cockpit accent
        pygame.draw.rect(screen, HELI_ACCENT_COLOR, (body_rect.x + 8, body_rect.y + 6, 40, self.body_h - 12), border_radius=4)
        # tail boom
        tail_rect = pygame.Rect(body_rect.right - 12, cy - self.tail_h // 2, self.tail_w, self.tail_h)
        pygame.draw.rect(screen, HELI_BODY_COLOR, tail_rect)
        # skids
        skid_y = self.y + 12
        pygame.draw.rect(screen, HELI_BODY_COLOR, (cx - self.skid_w // 2, skid_y, self.skid_w, self.skid_h), border_radius=3)
        pygame.draw.line(screen, HELI_BODY_COLOR, (cx - 40, skid_y), (cx - 40, cy + 14), 3)
        pygame.draw.line(screen, HELI_BODY_COLOR, (cx + 40, skid_y), (cx + 40, cy + 14), 3)
        # main rotor: hub above body
        hub_x, hub_y = cx, cy - self.body_h // 2 - self.rotor_post_h
        pygame.draw.line(screen, HELI_BODY_COLOR, (hub_x, cy - self.body_h // 2), (hub_x, hub_y), 4)
        # two opposite blades using rotation
        bx1 = hub_x + int(math.cos(self.rotor_angle) * self.rotor_len)
        by1 = hub_y + int(math.sin(self.rotor_angle) * self.rotor_len)
        bx2 = hub_x + int(math.cos(self.rotor_angle + math.pi) * self.rotor_len)
        by2 = hub_y + int(math.sin(self.rotor_angle + math.pi) * self.rotor_len)
        pygame.draw.line(screen, ROTOR_COLOR, (hub_x, hub_y), (bx1, by1), 5)
        pygame.draw.line(screen, ROTOR_COLOR, (hub_x, hub_y), (bx2, by2), 5)
        # tiny tail rotor imitation (simple rotating line)
        tail_center = (tail_rect.right - 6, tail_rect.y + tail_rect.h // 2)
        rx1 = tail_center[0] + int(math.cos(self.rotor_angle * 2) * 10)
        ry1 = tail_center[1] + int(math.sin(self.rotor_angle * 2) * 10)
        rx2 = tail_center[0] + int(math.cos(self.rotor_angle * 2 + math.pi) * 10)
        ry2 = tail_center[1] + int(math.sin(self.rotor_angle * 2 + math.pi) * 10)
        pygame.draw.line(screen, ROTOR_COLOR, tail_center, (rx1, ry1), 3)
        pygame.draw.line(screen, ROTOR_COLOR, tail_center, (rx2, ry2), 3)


# -----------------------------
# Main loop with state transitions
# -----------------------------
class Simulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("HeliMotion")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 16)
        # actors
        self.bg = Background()
        self.heli = Helicopter(x=int(WIDTH * 0.35), ground_y=GROUND_Y - 10)
        # state
        self.state = FlightState.GROUND_IDLE
        self.time_in_state = 0.0

    def change_state(self, new_state):
        self.state = new_state
        self.time_in_state = 0.0

    def update(self, dt):
        self.time_in_state += dt
        # state machine logic
        if self.state == FlightState.GROUND_IDLE:
            self.heli.update_rotor(dt, target_speed=0.0)
            # brief pause before spinning up
            if self.time_in_state > 0.6:
                self.change_state(FlightState.SPIN_UP)

        elif self.state == FlightState.SPIN_UP:
            self.heli.update_rotor(dt, target_speed=MAX_ROTOR_SPEED)
            if self.heli.rotor_speed >= MAX_ROTOR_SPEED * 0.98:
                self.change_state(FlightState.TAKE_OFF)

        elif self.state == FlightState.TAKE_OFF:
            self.heli.update_rotor(dt, target_speed=MAX_ROTOR_SPEED)
            self.heli.move_vertical(dt, up=True)
            if self.heli.at_altitude():
                self.change_state(FlightState.FLY)

        elif self.state == FlightState.FLY:
            # keep rotor at max speed while flying
            self.heli.update_rotor(dt, target_speed=MAX_ROTOR_SPEED)
            # scroll background to simulate horizontal motion
            self.bg.update_scroll(dt, active=True)
            # once pad B is aligned beneath helicopter, start landing
            if self.bg.pad_b_alignment(self.heli.x):
                self.change_state(FlightState.LANDING)

        elif self.state == FlightState.LANDING:
            # stop horizontal scroll; descend
            self.heli.update_rotor(dt, target_speed=MAX_ROTOR_SPEED)
            self.bg.update_scroll(dt, active=False)
            self.heli.move_vertical(dt, up=False)
            if self.heli.on_ground():
                self.change_state(FlightState.SPIN_DOWN)

        elif self.state == FlightState.SPIN_DOWN:
            self.heli.update_rotor(dt, decel=True)
            if self.heli.rotor_speed <= 0.02:
                self.change_state(FlightState.DONE)

        elif self.state == FlightState.DONE:
            # stay idle with rotor stopped
            self.heli.update_rotor(dt, target_speed=0.0)

    def draw(self):
        self.bg.draw(self.screen)
        self.heli.draw(self.screen)
        # HUD text
        self._draw_hud()
        pygame.display.flip()

    def _draw_hud(self):
        labels = [
            f"State: {self._state_name(self.state)}",
            f"Rotor speed (rad/s): {self.heli.rotor_speed:.2f}",
            f"dt (ms): {self.clock.get_time()} | FPS target: {FPS}",
            "Motion illusion: background scroll (helicopter fixed X)",
        ]
        for i, text in enumerate(labels):
            surf = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(surf, (12, 10 + i * 18))

    def _state_name(self, s):
        return {
            FlightState.GROUND_IDLE: "GROUND_IDLE",
            FlightState.SPIN_UP: "SPIN_UP",
            FlightState.TAKE_OFF: "TAKE_OFF",
            FlightState.FLY: "FLY",
            FlightState.LANDING: "LANDING",
            FlightState.SPIN_DOWN: "SPIN_DOWN",
            FlightState.DONE: "DONE",
        }[s]

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # seconds per frame
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            self.update(dt)
            self.draw()
        pygame.quit()
        return 0


if __name__ == "__main__":
    sim = Simulation()
    sys.exit(sim.run())
