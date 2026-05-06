import sys
import random
import math
import numpy as np
import pygame
import pyganim
import pymunk
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

pygame.init()
pygame.mixer.init()

WIDTH = 1280
HEIGHT = 720
BOUNDARY = 50
PLAYER_SIZE = 50
PLAYER_X = 200
BASE_SCROLL_SPEED = 7

def generate_tone(freq, duration, volume=0.5):
    sr = 44100
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    tone = np.sin(2 * math.pi * freq * t)
    audio = (tone * 32767 * volume).astype(np.int16)
    audio = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio)

flip_sound = generate_tone(600, 0.1, 0.5)
coin_sound = generate_tone(800, 0.1, 0.5)
game_over_sound = generate_tone(300, 0.3, 0.5)

space = pymunk.Space()
space.gravity = (0, 50)
particles = []

def setup_particles():
    global particles
    space.remove(*space.bodies, *space.shapes)
    particles = []
    for i in range(30):
        body = pymunk.Body(1, float('inf'))
        body.position = (random.randint(0, WIDTH), random.randint(BOUNDARY, HEIGHT))
        body.velocity = (random.uniform(-100, 100), random.uniform(-100, 100))
        shape = pymunk.Circle(body, 3)
        shape.elasticity = 0.9
        space.add(body, shape)
        particles.append(shape)

def update_particles(dt):
    space.step(dt)

def draw_particles(surf):
    for p in particles:
        x, y = int(p.body.position.x), int(p.body.position.y)
        radius = int(p.radius)
        glow_radius = radius + 3
        temp = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(temp, (255, 215, 0, 80), (glow_radius, glow_radius), glow_radius)
        pygame.draw.circle(temp, (255, 215, 0, 255), (glow_radius, glow_radius), radius)
        surf.blit(temp, (x - glow_radius, y - glow_radius))

def create_bg_surface(w, h, top_color, bottom_color):
    bg = pygame.Surface((w, h))
    for i in range(h):
        ratio = i / h
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(bg, (r, g, b), (0, i), (w, i))
    return bg

background = create_bg_surface(WIDTH, HEIGHT, (10, 10, 40), (0, 0, 0))

def create_radial_gradient_surface(size, color):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    cx, cy = w // 2, h // 2
    max_radius = min(cx, cy)
    for r in range(max_radius, 0, -1):
        alpha = int(255 * (r / max_radius))
        pygame.draw.circle(surf, color[:3] + (alpha,), (cx, cy), r)
    return surf

def create_player_anim(cw, ch):
    frames = []
    colors = [(50, 50, 255), (70, 70, 255), (90, 90, 255), (70, 70, 255)]
    for color in colors:
        surf = create_radial_gradient_surface((cw, ch), color)
        frames.append(surf)
    anim = pyganim.PygAnimation([(f, 100) for f in frames])
    anim.play()
    return anim

coin_surface = create_radial_gradient_surface((30, 30), (255, 215, 0))

def draw_coin(surf, x, y):
    surf.blit(coin_surface, (int(x), int(y)))

def draw_glowing_polygon(surface, points, base_color, glow_color):
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            offset_points = [(p[0] + dx, p[1] + dy) for p in points]
            pygame.draw.polygon(surface, glow_color, offset_points)
    pygame.draw.polygon(surface, base_color, points)

def draw_glow_rect(surface, rect, base_color, glow_color):
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            offset_rect = pygame.Rect(rect.x + dx, rect.y + dy, rect.width, rect.height)
            pygame.draw.rect(surface, glow_color, offset_rect)
    pygame.draw.rect(surface, base_color, rect)

class GeometryFlashGame:
    def __init__(self):
        self.menu_active = True
        self.reset()
        self.player_anim = create_player_anim(PLAYER_SIZE, PLAYER_SIZE)
        self.surface = pygame.Surface((WIDTH, HEIGHT))

    def reset(self):
        self.game_over = False
        self.score = 0
        self.obstacles = []
        self.coins = []
        self.enemies = []
        self.pushers = []
        self.last_obstacle_time = pygame.time.get_ticks()
        self.last_coin_time = pygame.time.get_ticks()
        self.last_enemy_time = pygame.time.get_ticks()
        self.last_pusher_time = 0
        self.base_scroll_speed = BASE_SCROLL_SPEED
        self.player_state = "bottom"
        self.player_rect = pygame.Rect(PLAYER_X, HEIGHT - BOUNDARY - PLAYER_SIZE, PLAYER_SIZE, PLAYER_SIZE)
        self.target_y = self.player_rect.y
        self.speed_multiplier = 1.0
        self.last_speed_increase_time = pygame.time.get_ticks()
        self.speed_increase_interval = 20000
        self.attached_pusher = None
        self.pusher_counter = 0
        setup_particles()

    def handle_key(self, key):
        if self.menu_active:
            if key == Qt.Key_Space:
                self.menu_active = False
                self.reset()
            elif key == Qt.Key_Escape:
                QApplication.quit()
        else:
            if not self.game_over:
                if key == Qt.Key_Space:
                    flip_sound.play()
                    if self.player_state == "bottom":
                        self.player_state = "top"
                        self.target_y = BOUNDARY
                    else:
                        self.player_state = "bottom"
                        self.target_y = HEIGHT - BOUNDARY - PLAYER_SIZE
            else:
                if key == Qt.Key_R:
                    self.reset()
                elif key == Qt.Key_Escape:
                    QApplication.quit()

    def update(self, dt):
        update_particles(dt)

        if self.menu_active or self.game_over:
            return

        current_time = pygame.time.get_ticks()

        if current_time - self.last_speed_increase_time >= self.speed_increase_interval:
            self.speed_multiplier += 0.1
            self.last_speed_increase_time = current_time

        effective_scroll = self.base_scroll_speed * self.speed_multiplier

        if abs(self.player_rect.y - self.target_y) > 1:
            self.player_rect.y += (self.target_y - self.player_rect.y) * 0.2
        else:
            self.player_rect.y = self.target_y

        ai_factor = max(0.5, min(self.score / 20.0, 1.0))
        local_obstacle_interval = max(600, int(1200 * (1 / ai_factor)))
        enemy_interval = int(2500 / ai_factor)

        if current_time - self.last_obstacle_time > local_obstacle_interval:
            obs_type = random.choice(["spike", "block"])
            orientation = random.choice(["top", "bottom"])
            self.obstacles.append({"type": obs_type, "orientation": orientation, "x": WIDTH})
            self.last_obstacle_time = current_time

        if current_time - self.last_coin_time > 2000:
            coin_orientation = random.choice(["top", "bottom"])
            candidate = WIDTH
            conflict = True
            while conflict:
                conflict = False
                for obs in self.obstacles:
                    if obs["orientation"] == coin_orientation:
                        if candidate + 40 >= obs["x"] and candidate <= obs["x"] + 60:
                            candidate += 20
                            conflict = True
                            break
            coin_x = candidate
            coin_y = BOUNDARY if coin_orientation == "top" else HEIGHT - BOUNDARY - 50
            self.coins.append({"x": coin_x, "y": coin_y, "orientation": coin_orientation})
            self.last_coin_time = current_time

        if current_time - self.last_enemy_time > enemy_interval:
            enemy_orientation = random.choice(["top", "bottom"])
            enemy_base_speed = random.uniform(12, 16) * ai_factor
            self.enemies.append({"x": WIDTH, "orientation": enemy_orientation, "base_speed": enemy_base_speed})
            self.last_enemy_time = current_time

        if current_time - self.last_pusher_time > 60000:
            orientation = random.choice(["top", "bottom"])
            self.pushers.append({"x": -50, "orientation": orientation, "id": self.pusher_counter})
            self.pusher_counter += 1
            self.last_pusher_time = current_time

        old_pusher_x = {pusher["id"]: pusher["x"] for pusher in self.pushers}

        for obs in self.obstacles:
            obs["x"] -= effective_scroll
        for coin in self.coins:
            coin["x"] -= effective_scroll
        for enemy in self.enemies:
            enemy["x"] -= enemy["base_speed"] * self.speed_multiplier

        pusher_speed = 3 * effective_scroll
        for pusher in self.pushers:
            pusher["x"] += pusher_speed

        if self.attached_pusher is not None:
            attached = None
            for pusher in self.pushers:
                if pusher["id"] == self.attached_pusher:
                    attached = pusher
                    break
            if attached:
                old_x = old_pusher_x.get(self.attached_pusher)
                if old_x is not None:
                    delta = attached["x"] - old_x
                    self.player_rect.x += delta
            else:
                self.attached_pusher = None

        self.obstacles = [obs for obs in self.obstacles if obs["x"] + 50 > 0]
        self.coins = [coin for coin in self.coins if coin["x"] + 30 > 0]
        self.enemies = [enemy for enemy in self.enemies if enemy["x"] + 50 > 0]
        self.pushers = [pusher for pusher in self.pushers if pusher["x"] - 50 < WIDTH]

        for coin in self.coins[:]:
            coin_rect = pygame.Rect(coin["x"], coin["y"], 30, 30)
            if self.player_rect.colliderect(coin_rect):
                coin_sound.play()
                self.score += 1
                self.coins.remove(coin)

        for obs in self.obstacles:
            if obs["type"] == "spike":
                spike_rect = pygame.Rect(obs["x"], BOUNDARY if obs["orientation"] == "top" else HEIGHT - BOUNDARY - 50, 50, 50)
                if self.player_rect.colliderect(spike_rect):
                    self.game_over = True
                    game_over_sound.play()
                    return

        for obs in self.obstacles:
            if obs["type"] == "block":
                rect_y = BOUNDARY if obs["orientation"] == "top" else HEIGHT - BOUNDARY - 50
                block_rect = pygame.Rect(obs["x"], rect_y, 50, 50)
                if self.player_rect.colliderect(block_rect) and self.player_state == obs["orientation"]:
                    self.player_rect.right = block_rect.left

        for enemy in self.enemies:
            rect_y = BOUNDARY if enemy["orientation"] == "top" else HEIGHT - BOUNDARY - 50
            enemy_rect = pygame.Rect(enemy["x"], rect_y, 50, 50)
            if self.player_rect.colliderect(enemy_rect):
                self.game_over = True
                game_over_sound.play()
                return

        new_attached = None
        for pusher in self.pushers:
            rect_y = BOUNDARY if pusher["orientation"] == "top" else HEIGHT - BOUNDARY - 50
            pusher_rect = pygame.Rect(pusher["x"], rect_y, 50, 50)
            if self.player_rect.colliderect(pusher_rect) and self.player_state == pusher["orientation"]:
                new_attached = pusher["id"]
                self.player_rect.x = pusher_rect.x
                break

        self.attached_pusher = new_attached

        if self.player_rect.right < 0 or self.player_rect.left > WIDTH:
            self.game_over = True
            game_over_sound.play()

    def draw(self):
        self.surface.blit(background, (0, 0))
        draw_particles(self.surface)

        if self.menu_active:
            self.draw_menu()
        else:
            pygame.draw.rect(self.surface, (200, 200, 200), (0, 0, WIDTH, BOUNDARY))
            pygame.draw.rect(self.surface, (200, 200, 200), (0, HEIGHT - BOUNDARY, WIDTH, BOUNDARY))

            for obs in self.obstacles:
                if obs["type"] == "spike":
                    if obs["orientation"] == "top":
                        points = [(obs["x"], BOUNDARY), (obs["x"] + 25, BOUNDARY + 50), (obs["x"] + 50, BOUNDARY)]
                    else:
                        points = [(obs["x"], HEIGHT - BOUNDARY), (obs["x"] + 25, HEIGHT - BOUNDARY - 50), (obs["x"] + 50, HEIGHT - BOUNDARY)]
                    draw_glowing_polygon(self.surface, points, (255, 50, 50), (255, 50, 50, 80))
                elif obs["type"] == "block":
                    rect_y = BOUNDARY if obs["orientation"] == "top" else HEIGHT - BOUNDARY - 50
                    block_rect = pygame.Rect(obs["x"], rect_y, 50, 50)
                    draw_glow_rect(self.surface, block_rect, (50, 255, 50), (50, 255, 50, 80))

            for coin in self.coins:
                draw_coin(self.surface, coin["x"], coin["y"])

            for enemy in self.enemies:
                rect_y = BOUNDARY if enemy["orientation"] == "top" else HEIGHT - BOUNDARY - 50
                enemy_rect = pygame.Rect(enemy["x"], rect_y, 50, 50)
                draw_glow_rect(self.surface, enemy_rect, (0, 0, 255), (0, 0, 255, 80))

            for pusher in self.pushers:
                rect_y = BOUNDARY if pusher["orientation"] == "top" else HEIGHT - BOUNDARY - 50
                pusher_rect = pygame.Rect(pusher["x"], rect_y, 50, 50)
                draw_glow_rect(self.surface, pusher_rect, (255, 165, 0), (255, 200, 0, 80))

            self.player_anim.blit(self.surface, (self.player_rect.x, self.player_rect.y))

            font = pygame.font.SysFont("Arial", 36)
            score_text = font.render("Score: " + str(self.score), True, (255, 255, 255))
            self.surface.blit(score_text, (10, 10))

            speed_text = font.render(f"x{self.speed_multiplier:.1f}", True, (255, 255, 255))
            speed_rect = speed_text.get_rect(topright=(WIDTH - 20, 10))
            self.surface.blit(speed_text, speed_rect)

            if self.game_over:
                go_text = font.render("Game Over", True, (255, 0, 0))
                score_go_text = font.render("Score: " + str(self.score), True, (255, 255, 255))
                opt_text = font.render("Press R to restart or ESC to Exit", True, (255, 255, 255))
                self.surface.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 80))
                self.surface.blit(score_go_text, (WIDTH // 2 - score_go_text.get_width() // 2, HEIGHT // 2))
                self.surface.blit(opt_text, (WIDTH // 2 - opt_text.get_width() // 2, HEIGHT // 2 + 80))

    def draw_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.surface.blit(overlay, (0, 0))

        font_large = pygame.font.SysFont("Arial", 72, bold=True)
        font_medium = pygame.font.SysFont("Arial", 48)
        font_small = pygame.font.SysFont("Arial", 36)

        title = font_large.render("GEOMETRY FLASH", True, (255, 215, 0))
        title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        self.surface.blit(title, title_rect)

        start = font_medium.render("Press SPACE to start", True, (255, 255, 255))
        start_rect = start.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.surface.blit(start, start_rect)

        controls = font_small.render("Space to switch lanes", True, (200, 200, 200))
        controls_rect = controls.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.surface.blit(controls, controls_rect)

        esc = font_small.render("ESC to quit", True, (200, 200, 200))
        esc_rect = esc.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 110))
        self.surface.blit(esc, esc_rect)

    def get_qimage(self):
        data = pygame.image.tostring(self.surface, 'RGB')
        return QImage(data, WIDTH, HEIGHT, QImage.Format_RGB888)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geometry Flash")
        self.setGeometry(100, 100, WIDTH, HEIGHT)
        self.setMinimumSize(640, 360)
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.label)
        self.game = GeometryFlashGame()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(16)
        self.last_time = pygame.time.get_ticks()

    def update_frame(self):
        now = pygame.time.get_ticks()
        dt = (now - self.last_time) / 1000.0
        self.last_time = now
        self.game.update(dt)
        self.game.draw()
        qimage = self.game.get_qimage()
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def keyPressEvent(self, event):
        self.game.handle_key(event.key())
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
