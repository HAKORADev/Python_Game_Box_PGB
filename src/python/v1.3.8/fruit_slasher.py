import pygame
import sys
import random
import math
import numpy as np
from pygame.locals import *

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GRAVITY = 0.35
COMBO_TIMEOUT = 500
MAX_LIVES = 3
TRAIL_LENGTH = 15
PARTICLE_COUNT_FRUIT = 12
PARTICLE_COUNT_BOMB = 25
SPAWN_INTERVAL_BASE = 1500
SPAWN_INTERVAL_MIN = 600

FRUIT_COLORS = {
    "apple": {"main": (229, 57, 53), "secondary": (198, 40, 40), "juice": (255, 82, 82)},
    "orange": {"main": (255, 152, 0), "secondary": (245, 124, 0), "juice": (255, 183, 77)},
    "watermelon": {"main": (76, 175, 80), "secondary": (229, 57, 53), "juice": (255, 138, 128)},
    "banana": {"main": (255, 235, 59), "secondary": (251, 192, 45), "juice": (255, 245, 157)},
    "coconut": {"main": (141, 110, 99), "secondary": (93, 64, 55), "juice": (215, 204, 200)},
    "bomb": {"main": (33, 33, 33), "secondary": (66, 66, 66), "juice": (255, 87, 34)},
}

FRUIT_EMOJIS = {
    "apple": "🍎",
    "orange": "🍊",
    "watermelon": "🍉",
    "banana": "🍌",
    "coconut": "🥥",
    "bomb": "💣",
}

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Fruit Slasher")
clock = pygame.time.Clock()

def generate_tone(freq, duration, volume=0.3, wave_type='sine'):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    if wave_type == 'sine':
        wave = np.sin(2 * np.pi * freq * t)
    elif wave_type == 'square':
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave_type == 'sawtooth':
        wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    else:
        wave = np.sin(2 * np.pi * freq * t)

    envelope = np.ones(n_samples)
    attack = int(0.01 * sample_rate)
    decay = int(0.05 * sample_rate)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-decay:] = np.linspace(1, 0, decay)
    wave *= envelope

    audio = (wave * 32767 * volume).astype(np.int16)
    audio = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio)

slice_sound = generate_tone(880, 0.1, 0.4, 'sine')
bomb_sound = generate_tone(220, 0.3, 0.5, 'square')
combo_sound = generate_tone(1320, 0.15, 0.3, 'sine')
game_over_sound = generate_tone(330, 0.5, 0.5, 'sawtooth')

def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def random_range(min_val, max_val):
    return random.uniform(min_val, max_val)

def generate_id():
    return str(random.getrandbits(32))

def check_slice_collision(p1, p2, fruit):
    fx, fy = fruit["x"], fruit["y"]
    radius = fruit["radius"]
    if distance(((p1[0]+p2[0])/2, (p1[1]+p2[1])/2), (fx, fy)) > radius + 50:
        return False

    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    fx -= p1[0]
    fy -= p1[1]

    a = dx*dx + dy*dy
    b = 2 * (fx*dx + fy*dy)
    c = fx*fx + fy*fy - radius*radius

    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return False

    discriminant = math.sqrt(discriminant)
    t1 = (-b - discriminant) / (2*a)
    t2 = (-b + discriminant) / (2*a)

    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

font_large = pygame.font.Font(None, 72)
font_medium = pygame.font.Font(None, 48)
font_small = pygame.font.Font(None, 36)
font_tiny = pygame.font.Font(None, 24)

class Game:
    def __init__(self):
        self.state = "start"
        self.score = 0
        self.highscore = 0
        self.lives = MAX_LIVES
        self.combo = 0
        self.last_combo_time = 0

        self.fruits = []
        self.fruit_halves = []
        self.particles = []
        self.trail = []
        self.slice_points = []

        self.slicing = False
        self.next_fruit_id = 1
        self.pending_spawns = []
        self.last_spawn_time = 0
        self.spawn_interval = SPAWN_INTERVAL_BASE

        self.combo_display_time = 0
        self.combo_display_text = ""

        self.start_screen = True
        self.game_over_screen = False
        self.game_ui_visible = False

    def start_game(self):
        self.score = 0
        self.lives = MAX_LIVES
        self.combo = 0
        self.fruits.clear()
        self.fruit_halves.clear()
        self.particles.clear()
        self.trail.clear()
        self.slice_points.clear()
        self.pending_spawns.clear()
        self.next_fruit_id = 1
        self.last_spawn_time = pygame.time.get_ticks()
        self.spawn_interval = SPAWN_INTERVAL_BASE

        self.state = "playing"
        self.start_screen = False
        self.game_over_screen = False
        self.game_ui_visible = True

    def end_game(self):
        self.state = "gameover"
        self.game_ui_visible = False
        self.game_over_screen = True
        game_over_sound.play()

        if self.score > self.highscore:
            self.highscore = self.score

    def spawn_fruit(self):
        types = ["apple", "orange", "watermelon", "banana", "coconut"]
        is_bomb = random.random() < 0.1

        fruit_type = "bomb" if is_bomb else random.choice(types)
        radius = random_range(35, 55) if fruit_type == "watermelon" else random_range(30, 45)

        x = random_range(radius + 50, SCREEN_WIDTH - radius - 50)
        y = SCREEN_HEIGHT + radius

        target_x = random_range(SCREEN_WIDTH * 0.2, SCREEN_WIDTH * 0.8)
        target_y = random_range(SCREEN_HEIGHT * 0.15, SCREEN_HEIGHT * 0.35)
        time_to_peak = random_range(1.5, 2.5)
        vx = (target_x - x) / (time_to_peak * FPS)
        vy = (target_y - y) / (time_to_peak * FPS) - (GRAVITY * time_to_peak * FPS) / 2

        self.fruits.append({
            "id": self.next_fruit_id,
            "type": fruit_type,
            "x": x,
            "y": y,
            "vx": vx,
            "vy": vy,
            "radius": radius,
            "rotation": random.uniform(0, math.pi*2),
            "rotation_speed": random_range(-0.1, 0.1),
            "sliced": False,
        })
        self.next_fruit_id += 1

    def create_slice_effect(self, fruit, slice_angle):
        colors = FRUIT_COLORS[fruit["type"]]
        half_speed = 3
        half_id = generate_id()

        self.fruit_halves.append({
            "id": half_id + "_left",
            "type": fruit["type"],
            "x": fruit["x"],
            "y": fruit["y"],
            "vx": fruit["vx"] - math.cos(slice_angle) * half_speed,
            "vy": fruit["vy"] - math.sin(slice_angle) * half_speed,
            "radius": fruit["radius"] * 0.9,
            "rotation": fruit["rotation"],
            "rotation_speed": -0.15,
            "is_left": True,
            "slice_angle": slice_angle,
            "alpha": 1.0,
        })

        self.fruit_halves.append({
            "id": half_id + "_right",
            "type": fruit["type"],
            "x": fruit["x"],
            "y": fruit["y"],
            "vx": fruit["vx"] + math.cos(slice_angle) * half_speed,
            "vy": fruit["vy"] + math.sin(slice_angle) * half_speed,
            "radius": fruit["radius"] * 0.9,
            "rotation": fruit["rotation"],
            "rotation_speed": 0.15,
            "is_left": False,
            "slice_angle": slice_angle,
            "alpha": 1.0,
        })

        if fruit["type"] != "bomb":
            for _ in range(PARTICLE_COUNT_FRUIT):
                angle = random.uniform(0, math.pi*2)
                speed = random_range(2, 8)
                self.particles.append({
                    "id": generate_id(),
                    "x": fruit["x"],
                    "y": fruit["y"],
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - 2,
                    "radius": random_range(3, 8),
                    "color": colors["juice"],
                    "alpha": 1.0,
                    "gravity": 0.2,
                })
        else:
            for _ in range(PARTICLE_COUNT_BOMB):
                angle = random.uniform(0, math.pi*2)
                speed = random_range(5, 15)
                color = (255, 87, 34) if _ % 2 == 0 else (255, 235, 59)
                self.particles.append({
                    "id": generate_id(),
                    "x": fruit["x"],
                    "y": fruit["y"],
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "radius": random_range(5, 12),
                    "color": color,
                    "alpha": 1.0,
                    "gravity": 0.1,
                })

    def handle_slice(self):
        if len(self.slice_points) < 2:
            return

        hit_bomb = False
        fruits_sliced = 0

        for fruit in self.fruits:
            if fruit["sliced"]:
                continue
            for i in range(1, len(self.slice_points)):
                if check_slice_collision(self.slice_points[i-1], self.slice_points[i], fruit):
                    fruit["sliced"] = True
                    slice_angle = math.atan2(
                        self.slice_points[i][1] - self.slice_points[i-1][1],
                        self.slice_points[i][0] - self.slice_points[i-1][0]
                    )
                    self.create_slice_effect(fruit, slice_angle)
                    fruits_sliced += 1
                    if fruit["type"] == "bomb":
                        hit_bomb = True
                    break

        if fruits_sliced > 0:
            if hit_bomb:
                bomb_sound.play()
                self.end_game()
                return

            slice_sound.play()

            now = pygame.time.get_ticks()
            if now - self.last_combo_time < COMBO_TIMEOUT:
                self.combo += fruits_sliced
            else:
                self.combo = fruits_sliced
            self.last_combo_time = now

            if self.combo > 1:
                self.combo_display_text = f"{self.combo}x COMBO!"
                self.combo_display_time = now
                combo_sound.play()

            points_earned = fruits_sliced * (self.combo if self.combo > 1 else 1)
            self.score += points_earned

    def update(self):
        now = pygame.time.get_ticks()

        if self.state == "playing":
            for pending in self.pending_spawns[:]:
                if now >= pending["time"]:
                    self.spawn_fruit()
                    self.pending_spawns.remove(pending)

            if now - self.last_spawn_time > self.spawn_interval:
                count = 2 if random.random() < 0.3 else 1
                for i in range(count):
                    spawn_time = now + i * 150
                    self.pending_spawns.append({"time": spawn_time})
                self.last_spawn_time = now
                self.spawn_interval = max(SPAWN_INTERVAL_MIN, self.spawn_interval - 10)

            if self.slicing and len(self.slice_points) >= 2:
                self.handle_slice()

            self.trail = [p for p in self.trail if p["alpha"] > 0]
            for p in self.trail:
                p["alpha"] -= 0.1
                if p["alpha"] < 0:
                    p["alpha"] = 0

            new_fruits = []
            for fruit in self.fruits:
                if fruit["sliced"]:
                    continue
                fruit["vy"] += GRAVITY
                fruit["x"] += fruit["vx"]
                fruit["y"] += fruit["vy"]
                fruit["rotation"] += fruit["rotation_speed"]

                if fruit["y"] > SCREEN_HEIGHT + fruit["radius"] * 2:
                    if fruit["type"] != "bomb":
                        self.lives -= 1
                        if self.lives <= 0:
                            self.end_game()
                    continue
                new_fruits.append(fruit)
            self.fruits = new_fruits

            new_halves = []
            for half in self.fruit_halves:
                half["vy"] += GRAVITY
                half["x"] += half["vx"]
                half["y"] += half["vy"]
                half["rotation"] += half["rotation_speed"]
                half["alpha"] -= 0.008
                if half["alpha"] > 0 and half["y"] <= SCREEN_HEIGHT + half["radius"] * 2:
                    new_halves.append(half)
            self.fruit_halves = new_halves

            new_particles = []
            for p in self.particles:
                p["vy"] += p["gravity"]
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["alpha"] -= 0.02
                if p["alpha"] > 0:
                    new_particles.append(p)
            self.particles = new_particles

    def draw(self):
        self.draw_static_gradient()

        if self.state == "start":
            self.draw_start_screen()
        elif self.state == "playing":
            self.draw_game_screen()
        elif self.state == "gameover":
            self.draw_gameover_screen()

        pygame.display.flip()

    def draw_static_gradient(self):
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(26 * (1 - ratio) + 15 * ratio)
            g = int(26 * (1 - ratio) + 15 * ratio)
            b = int(46 * (1 - ratio) + 35 * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

    def draw_start_screen(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        title = font_large.render("Fruit Slasher", True, (255, 255, 255))
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
        screen.blit(title, title_rect)

        if self.highscore > 0:
            hs_text = font_small.render(f"High Score: {self.highscore}", True, (250, 204, 21))
            hs_rect = hs_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30))
            screen.blit(hs_text, hs_rect)

        btn_rect = pygame.Rect(0, 0, 300, 80)
        btn_rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50)
        pygame.draw.rect(screen, (34, 197, 94), btn_rect, border_radius=16)
        pygame.draw.rect(screen, (255,255,255), btn_rect, 3, border_radius=16)
        btn_text = font_medium.render("Start Game", True, (255,255,255))
        screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width()//2, btn_rect.centery - btn_text.get_height()//2))

        inst1 = font_tiny.render("Use mouse to slice", True, (200,200,200))
        inst2 = font_tiny.render("Avoid bombs!", True, (200,200,200))
        inst3 = font_tiny.render("Don't miss 3 fruits", True, (200,200,200))
        screen.blit(inst1, (SCREEN_WIDTH//2 - inst1.get_width()//2, SCREEN_HEIGHT//2 + 150))
        screen.blit(inst2, (SCREEN_WIDTH//2 - inst2.get_width()//2, SCREEN_HEIGHT//2 + 180))
        screen.blit(inst3, (SCREEN_WIDTH//2 - inst3.get_width()//2, SCREEN_HEIGHT//2 + 210))

    def draw_gameover_screen(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0,0,0))
        screen.blit(overlay, (0,0))

        box_rect = pygame.Rect(0,0,500,400)
        box_rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        pygame.draw.rect(screen, (30,41,59), box_rect, border_radius=24)
        pygame.draw.rect(screen, (71,85,105), box_rect, 3, border_radius=24)

        go_text = font_large.render("Game Over", True, (239,68,68))
        screen.blit(go_text, (box_rect.centerx - go_text.get_width()//2, box_rect.y + 50))

        score_label = font_small.render("Your Score", True, (255,255,255))
        screen.blit(score_label, (box_rect.centerx - score_label.get_width()//2, box_rect.y + 130))

        score_val = font_large.render(str(self.score), True, (255,255,255))
        screen.blit(score_val, (box_rect.centerx - score_val.get_width()//2, box_rect.y + 170))

        if self.score >= self.highscore and self.score > 0:
            new_hs = font_small.render("New High Score!", True, (250,204,21))
            screen.blit(new_hs, (box_rect.centerx - new_hs.get_width()//2, box_rect.y + 240))

        hs_display = font_small.render(f"High Score: {self.highscore}", True, (250,204,21))
        screen.blit(hs_display, (box_rect.centerx - hs_display.get_width()//2, box_rect.y + 280))

        btn_rect = pygame.Rect(0,0,250,60)
        btn_rect.center = (box_rect.centerx, box_rect.y + 350)
        pygame.draw.rect(screen, (249,115,22), btn_rect, border_radius=12)
        pygame.draw.rect(screen, (255,255,255), btn_rect, 2, border_radius=12)
        btn_text = font_medium.render("Play Again", True, (255,255,255))
        screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width()//2, btn_rect.centery - btn_text.get_height()//2))

    def draw_game_screen(self):
        for fruit in self.fruits:
            if not fruit["sliced"]:
                self.draw_fruit(fruit)

        for half in self.fruit_halves:
            self.draw_fruit_half(half)

        for p in self.particles:
            alpha_surf = pygame.Surface((p["radius"]*2, p["radius"]*2), pygame.SRCALPHA)
            pygame.draw.circle(alpha_surf, (*p["color"], int(p["alpha"]*255)), (p["radius"], p["radius"]), p["radius"])
            screen.blit(alpha_surf, (p["x"]-p["radius"], p["y"]-p["radius"]))

        if len(self.trail) > 1:
            points = [(p["x"], p["y"]) for p in self.trail]
            if len(points) > 1:
                pygame.draw.lines(screen, (100, 200, 255, 100), False, points, 14)
                pygame.draw.lines(screen, (255, 255, 255, 200), False, points, 4)

        score_text = font_large.render(str(self.score), True, (255,255,255))
        screen.blit(score_text, (20, 20))

        self.draw_lives()

        if self.combo_display_time and pygame.time.get_ticks() - self.combo_display_time < 800:
            combo_surf = font_large.render(self.combo_display_text, True, (250,204,21))
            screen.blit(combo_surf, (SCREEN_WIDTH//2 - combo_surf.get_width()//2, SCREEN_HEIGHT//3))

    def draw_lives(self):
        x_start = SCREEN_WIDTH - 120
        y = 40
        radius = 20
        for i in range(MAX_LIVES):
            center = (x_start + i * (radius * 2 + 10), y)
            if i < self.lives:
                for g in range(radius + 8, radius, -1):
                    alpha = 100 - (g - radius) * 20
                    if alpha > 0:
                        glow_surf = pygame.Surface((g*2, g*2), pygame.SRCALPHA)
                        pygame.draw.circle(glow_surf, (255, 80, 80, alpha), (g, g), g)
                        screen.blit(glow_surf, (center[0]-g, center[1]-g))
                pygame.draw.circle(screen, (255, 80, 80), center, radius)
                pygame.draw.circle(screen, (255, 255, 255, 120), (center[0]-5, center[1]-5), radius//3)
            else:
                pygame.draw.circle(screen, (60, 60, 60), center, radius)
                pygame.draw.circle(screen, (30, 30, 30), center, radius, 2)

    def draw_fruit(self, fruit):
        x, y = fruit["x"], fruit["y"]
        r = int(fruit["radius"])
        colors = FRUIT_COLORS[fruit["type"]]

        surf = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
        center = (r+5, r+5)

        if fruit["type"] == "bomb":
            for i in range(r, 0, -1):
                ratio = i / r
                color = (
                    int(colors["main"][0] * ratio + colors["secondary"][0] * (1-ratio)),
                    int(colors["main"][1] * ratio + colors["secondary"][1] * (1-ratio)),
                    int(colors["main"][2] * ratio + colors["secondary"][2] * (1-ratio)),
                )
                pygame.draw.circle(surf, color, center, i)

            highlight_pos = (center[0] - r//4, center[1] - r//4)
            pygame.draw.circle(surf, (180,180,180,80), highlight_pos, r//5)

            fuse_start = (center[0], center[1] - r)
            fuse_end = (center[0], center[1] - r - 10)
            pygame.draw.line(surf, (101, 67, 33), fuse_start, fuse_end, 4)

            flame_center = (center[0], center[1] - r - 14)
            flame_radius = 8
            for j in range(flame_radius, 0, -1):
                ratio = j / flame_radius
                if ratio > 0.6:
                    color = (255, 200, 50)
                elif ratio > 0.3:
                    color = (255, 100, 0)
                else:
                    color = (200, 50, 0)
                pygame.draw.circle(surf, color, flame_center, j)

        else:
            for i in range(r, 0, -1):
                ratio = i / r
                color = (
                    int(colors["main"][0] * ratio + colors["secondary"][0] * (1-ratio)),
                    int(colors["main"][1] * ratio + colors["secondary"][1] * (1-ratio)),
                    int(colors["main"][2] * ratio + colors["secondary"][2] * (1-ratio)),
                )
                pygame.draw.circle(surf, color, center, i)

            pygame.draw.circle(surf, (255,255,255,80), (center[0]-r//3, center[1]-r//3), r//4)

            letter = fruit["type"][0].upper()
            letter_surf = font_medium.render(letter, True, (0,0,0))
            surf.blit(letter_surf, (center[0] - letter_surf.get_width()//2, center[1] - letter_surf.get_height()//2))

        rotated = pygame.transform.rotate(surf, fruit["rotation"] * 180/math.pi)
        screen.blit(rotated, (x - rotated.get_width()//2, y - rotated.get_height()//2))

    def draw_fruit_half(self, half):
        x, y = half["x"], half["y"]
        r = int(half["radius"])
        colors = FRUIT_COLORS[half["type"]]
        slice_angle = half["slice_angle"]
        alpha = half["alpha"]

        surf = pygame.Surface((r*2+10, r*2+10), pygame.SRCALPHA)
        center = (r+5, r+5)

        start_angle = slice_angle + math.pi/2 if half["is_left"] else slice_angle - math.pi/2
        end_angle = slice_angle - math.pi/2 if half["is_left"] else slice_angle + math.pi/2
        if end_angle < start_angle:
            end_angle += 2*math.pi

        points = [center]
        steps = 20
        for i in range(steps+1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            px = center[0] + math.cos(angle) * r
            py = center[1] + math.sin(angle) * r
            points.append((px, py))
        points.append(center)

        color_main = colors["main"]
        color_juice = colors["juice"]

        pygame.draw.polygon(surf, color_main, points)

        inner_points = [center]
        inner_r = r * 0.85
        for i in range(steps+1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            px = center[0] + math.cos(angle) * inner_r
            py = center[1] + math.sin(angle) * inner_r
            inner_points.append((px, py))
        inner_points.append(center)
        pygame.draw.polygon(surf, color_juice, inner_points)

        rotated = pygame.transform.rotate(surf, half["rotation"] * 180/math.pi)
        rotated.set_alpha(int(alpha * 255))
        screen.blit(rotated, (x - rotated.get_width()//2, y - rotated.get_height()//2))

    def handle_event(self, event):
        if event.type == QUIT:
            return False

        if event.type == MOUSEBUTTONDOWN:
            if self.state == "start":
                btn_rect = pygame.Rect(0,0,300,80)
                btn_rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50)
                if btn_rect.collidepoint(event.pos):
                    self.start_game()
            elif self.state == "gameover":
                box_rect = pygame.Rect(0,0,500,400)
                box_rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
                btn_rect = pygame.Rect(0,0,250,60)
                btn_rect.center = (box_rect.centerx, box_rect.y + 350)
                if btn_rect.collidepoint(event.pos):
                    self.start_game()
            elif self.state == "playing":
                self.slicing = True
                self.slice_points = [(event.pos[0], event.pos[1])]
                self.trail.append({"x": event.pos[0], "y": event.pos[1], "alpha": 1.0})

        elif event.type == MOUSEMOTION and self.slicing and self.state == "playing":
            pos = (event.pos[0], event.pos[1])
            self.slice_points.append(pos)
            self.trail.append({"x": pos[0], "y": pos[1], "alpha": 1.0})
            if len(self.trail) > TRAIL_LENGTH:
                self.trail = self.trail[-TRAIL_LENGTH:]
            if len(self.slice_points) > TRAIL_LENGTH:
                self.slice_points = self.slice_points[-TRAIL_LENGTH:]

        elif event.type == MOUSEBUTTONUP:
            self.slicing = False
            self.slice_points.clear()

        return True

def main():
    game = Game()
    running = True

    while running:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if not game.handle_event(event):
                running = False

        game.update()
        game.draw()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
