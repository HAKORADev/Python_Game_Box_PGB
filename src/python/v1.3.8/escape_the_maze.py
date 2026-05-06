import sys
import math
import random
from collections import deque

import numpy as np
import pygame
import pyganim
import pymunk
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget

LOGICAL_WIDTH = 1024
LOGICAL_HEIGHT = 768
MAZE_TOP = 50
INITIAL_MAZE_COLS = 16
INITIAL_MAZE_ROWS = 12

pygame.mixer.init()

def generate_tone(freq, duration, volume=0.5):
    sr = 44100
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    tone = np.sin(2 * math.pi * freq * t)
    audio = (tone * 32767 * volume).astype(np.int16)
    audio = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio)

move_sound = generate_tone(700, 0.05, 0.5)
win_sound = generate_tone(900, 0.2, 0.5)
game_over_sound = generate_tone(300, 0.3, 0.5)

def create_bg_surface(w, h, top_color, bottom_color):
    bg = pygame.Surface((w, h))
    for i in range(h):
        ratio = i / h
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(bg, (r, g, b), (0, i), (w, i))
    return bg

background = create_bg_surface(LOGICAL_WIDTH, LOGICAL_HEIGHT, (10, 10, 40), (0, 0, 0))

def generate_maze(cols, rows, openness=0.0):
    maze = [[{'walls': {'top': True, 'right': True, 'bottom': True, 'left': True}, 'visited': False} for _ in range(cols)] for _ in range(rows)]
    stack = []
    current = (0, 0)
    maze[0][0]['visited'] = True

    while True:
        r, c = current
        neighbors = []
        if r > 0 and not maze[r-1][c]['visited']:
            neighbors.append(('top', (r-1, c)))
        if r < rows - 1 and not maze[r+1][c]['visited']:
            neighbors.append(('bottom', (r+1, c)))
        if c > 0 and not maze[r][c-1]['visited']:
            neighbors.append(('left', (r, c-1)))
        if c < cols - 1 and not maze[r][c+1]['visited']:
            neighbors.append(('right', (r, c+1)))

        if neighbors:
            direction, next_cell = random.choice(neighbors)
            nr, nc = next_cell
            if direction == 'top':
                maze[r][c]['walls']['top'] = False
                maze[nr][nc]['walls']['bottom'] = False
            elif direction == 'bottom':
                maze[r][c]['walls']['bottom'] = False
                maze[nr][nc]['walls']['top'] = False
            elif direction == 'left':
                maze[r][c]['walls']['left'] = False
                maze[nr][nc]['walls']['right'] = False
            elif direction == 'right':
                maze[r][c]['walls']['right'] = False
                maze[nr][nc]['walls']['left'] = False

            stack.append(current)
            current = (nr, nc)
            maze[nr][nc]['visited'] = True
        elif stack:
            current = stack.pop()
        else:
            break

    for r in range(rows):
        for c in range(cols):
            if random.random() < openness:
                dirs = []
                if r > 0 and maze[r][c]['walls']['top']:
                    dirs.append(('top', r-1, c))
                if r < rows-1 and maze[r][c]['walls']['bottom']:
                    dirs.append(('bottom', r+1, c))
                if c > 0 and maze[r][c]['walls']['left']:
                    dirs.append(('left', r, c-1))
                if c < cols-1 and maze[r][c]['walls']['right']:
                    dirs.append(('right', r, c+1))
                if dirs:
                    d, nr, nc = random.choice(dirs)
                    if d == 'top':
                        maze[r][c]['walls']['top'] = False
                        maze[nr][nc]['walls']['bottom'] = False
                    elif d == 'bottom':
                        maze[r][c]['walls']['bottom'] = False
                        maze[nr][nc]['walls']['top'] = False
                    elif d == 'left':
                        maze[r][c]['walls']['left'] = False
                        maze[nr][nc]['walls']['right'] = False
                    elif d == 'right':
                        maze[r][c]['walls']['right'] = False
                        maze[nr][nc]['walls']['left'] = False
    return maze

def find_path(maze, start_pos, end_row, end_col, rows, cols):
    start_row, start_col = start_pos[1], start_pos[0]
    queue = deque([(start_row, start_col, [])])
    visited = set()
    while queue:
        row, col, path = queue.popleft()
        if (row, col) == (end_row, end_col):
            return path + [(row, col)]
        if (row, col) in visited:
            continue
        visited.add((row, col))
        current_cell = maze[row][col]
        if not current_cell['walls']['top'] and row > 0:
            queue.append((row - 1, col, path + [(row, col)]))
        if not current_cell['walls']['bottom'] and row < rows - 1:
            queue.append((row + 1, col, path + [(row, col)]))
        if not current_cell['walls']['left'] and col > 0:
            queue.append((row, col - 1, path + [(row, col)]))
        if not current_cell['walls']['right'] and col < cols - 1:
            queue.append((row, col + 1, path + [(row, col)]))
    return []

frame_colors = [(50, 50, 255), (70, 70, 255), (90, 90, 255), (70, 70, 255)]

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
    for color in frame_colors:
        surf = create_radial_gradient_surface((cw // 2, ch // 2), color)
        frames.append(surf)
    anim = pyganim.PygAnimation([(f, 100) for f in frames])
    anim.play()
    return anim

space = pymunk.Space()
space.gravity = (0, 50)
particles = []

def setup_particles():
    global particles
    particles = []
    for i in range(20):
        body = pymunk.Body(1, float('inf'))
        body.position = (random.randint(0, LOGICAL_WIDTH), random.randint(MAZE_TOP, LOGICAL_HEIGHT))
        body.velocity = (random.uniform(-100, 100), random.uniform(-100, 100))
        shape = pymunk.Circle(body, 5)
        shape.elasticity = 0.9
        space.add(body, shape)
        particles.append(shape)

def update_particles(dt):
    space.step(dt)

def draw_particles(surf):
    for p in particles:
        x, y = int(p.body.position.x), int(p.body.position.y)
        radius = int(p.radius)
        glow_radius = radius + 4
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (255, 215, 0, 80), (glow_radius, glow_radius), glow_radius)
        pygame.draw.circle(glow_surface, (255, 215, 0, 255), (glow_radius, glow_radius), radius)
        surf.blit(glow_surface, (x - glow_radius, y - glow_radius))

def draw_maze(surf, maze, cols, rows, cell_w, cell_h):
    glow_layer = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
    for r in range(rows):
        for c in range(cols):
            x = c * cell_w
            y = MAZE_TOP + r * cell_h
            walls = maze[r][c]['walls']
            if walls['top']:
                start, end = (x, y), (x + cell_w, y)
                pygame.draw.line(glow_layer, (255, 255, 255, 80), start, end, 6)
                pygame.draw.line(surf, (255, 255, 255), start, end, 2)
            if walls['right']:
                start, end = (x + cell_w, y), (x + cell_w, y + cell_h)
                pygame.draw.line(glow_layer, (255, 255, 255, 80), start, end, 6)
                pygame.draw.line(surf, (255, 255, 255), start, end, 2)
            if walls['bottom']:
                start, end = (x + cell_w, y + cell_h), (x, y + cell_h)
                pygame.draw.line(glow_layer, (255, 255, 255, 80), start, end, 6)
                pygame.draw.line(surf, (255, 255, 255), start, end, 2)
            if walls['left']:
                start, end = (x, y + cell_h), (x, y)
                pygame.draw.line(glow_layer, (255, 255, 255, 80), start, end, 6)
                pygame.draw.line(surf, (255, 255, 255), start, end, 2)
    surf.blit(glow_layer, (0, 0))

def draw_player(surf, player_pos, cell_w, cell_h, anim):
    col, row = player_pos
    x = col * cell_w + cell_w // 4
    y = MAZE_TOP + row * cell_h + cell_h // 4
    anim.blit(surf, (x, y))

def draw_stats(surf, wins, time_left, available_power_ups, font):
    wins_text = font.render("Wins: " + str(wins), True, (255, 255, 255))
    time_text = font.render("Time: " + str(int(time_left)), True, (255, 255, 255))
    power_text = font.render("Path Finders: " + str(available_power_ups), True, (255, 255, 255))
    surf.blit(wins_text, (10, 10))
    surf.blit(time_text, (LOGICAL_WIDTH - time_text.get_width() - 10, 10))
    surf.blit(power_text, (LOGICAL_WIDTH // 2 - power_text.get_width() // 2, 10))

def draw_game_over(surf, wins):
    surf.blit(background, (0, 0))
    font = pygame.font.SysFont("Arial", 36)
    go_text = font.render("Game Over", True, (255, 0, 0))
    wins_text = font.render("Wins: " + str(wins), True, (255, 255, 255))
    opt_text = font.render("Press R to restart or ESC to Exit", True, (255, 255, 255))
    surf.blit(go_text, (LOGICAL_WIDTH // 2 - go_text.get_width() // 2, LOGICAL_HEIGHT // 2 - 80))
    surf.blit(wins_text, (LOGICAL_WIDTH // 2 - wins_text.get_width() // 2, LOGICAL_HEIGHT // 2))
    surf.blit(opt_text, (LOGICAL_WIDTH // 2 - opt_text.get_width() // 2, LOGICAL_HEIGHT // 2 + 80))

class RedEnemy:
    def __init__(self, r, c):
        self.r = r
        self.c = c
        self.move_timer = 0

    def update(self, maze, player_r, player_c, rows, cols, dt):
        self.move_timer += dt
        if self.move_timer >= 0.4:
            self.move_timer = 0
            if random.random() < 0.1:
                self.move_random(maze, rows, cols)
            else:
                self.move_towards_player(maze, player_r, player_c, rows, cols)

    def move_towards_player(self, maze, player_r, player_c, rows, cols):
        path = find_path(maze, (self.c, self.r), player_r, player_c, rows, cols)
        if path and len(path) > 1:
            next_step = path[1]
            self.r, self.c = next_step

    def move_random(self, maze, rows, cols):
        dirs = []
        if self.r > 0 and not maze[self.r][self.c]['walls']['top']:
            dirs.append((-1, 0))
        if self.r < rows-1 and not maze[self.r][self.c]['walls']['bottom']:
            dirs.append((1, 0))
        if self.c > 0 and not maze[self.r][self.c]['walls']['left']:
            dirs.append((0, -1))
        if self.c < cols-1 and not maze[self.r][self.c]['walls']['right']:
            dirs.append((0, 1))
        if dirs:
            dr, dc = random.choice(dirs)
            self.r += dr
            self.c += dc

class WhiteEnemy:
    def __init__(self, r, c):
        self.r = r
        self.c = c
        self.shoot_timer = 0
        self.shot_count = 0

    def update(self, dt, maze, player_r, player_c):
        self.shoot_timer += dt
        if self.shoot_timer >= 2.0:
            self.shoot_timer = 0
            self.shot_count += 1
            if self.shot_count % 2 == 1:
                return self.get_aimed_direction(player_r, player_c)
            else:
                return self.get_random_open_direction(maze)
        return None

    def get_aimed_direction(self, player_r, player_c):
        dr = player_r - self.r
        dc = player_c - self.c
        if abs(dr) > abs(dc):
            return (1 if dr > 0 else -1, 0)
        else:
            return (0, 1 if dc > 0 else -1)

    def get_random_open_direction(self, maze):
        dirs = []
        if self.r > 0 and not maze[self.r][self.c]['walls']['top']:
            dirs.append((-1, 0))
        if self.r < len(maze)-1 and not maze[self.r][self.c]['walls']['bottom']:
            dirs.append((1, 0))
        if self.c > 0 and not maze[self.r][self.c]['walls']['left']:
            dirs.append((0, -1))
        if self.c < len(maze[0])-1 and not maze[self.r][self.c]['walls']['right']:
            dirs.append((0, 1))
        if dirs:
            return random.choice(dirs)
        return (0, 1)

class Bullet:
    def __init__(self, x, y, dx, dy, speed, lifetime):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.speed = speed
        self.lifetime = lifetime
        self.age = 0

    def update(self, dt):
        self.x += self.dx * self.speed * dt
        self.y += self.dy * self.speed * dt
        self.age += dt

    def is_alive(self):
        return self.age < self.lifetime

class GameWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(800, 600)

        self.wins = 0
        self.maze_cols = INITIAL_MAZE_COLS
        self.maze_rows = INITIAL_MAZE_ROWS
        self.cell_width = LOGICAL_WIDTH // self.maze_cols
        self.cell_height = (LOGICAL_HEIGHT - MAZE_TOP) // self.maze_rows
        self.player_anim = create_player_anim(self.cell_width, self.cell_height)
        openness = min(0.4, 0.1 * (self.wins // 5))
        self.maze = generate_maze(self.maze_cols, self.maze_rows, openness=openness)
        self.player_pos = (0, 0)
        self.start_time = pygame.time.get_ticks()
        self.round_time = 60
        self.used_power_ups = 0
        self.powerup_active = False
        self.powerup_end_time = 0
        self.current_path = []
        self.game_over_flag = False

        self.enemies = []
        self.bullets = []
        self.spawn_enemies()

        self.font = pygame.font.SysFont("Arial", 36)
        self.surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))

        setup_particles()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)

        self.prev_time = pygame.time.get_ticks()

    def spawn_enemies(self):
        self.enemies = []
        self.bullets = []
        if self.wins < 5:
            return
        if self.wins >= 15:
            red_count = 2
            white_count = 2
        elif self.wins >= 10:
            red_count = 1
            white_count = 1
        elif self.wins >= 5:
            red_count = 1
            white_count = 0
        else:
            red_count = 0
            white_count = 0

        all_cells = [(r, c) for r in range(self.maze_rows) for c in range(self.maze_cols)]
        forbidden = [(0, 0), (self.maze_rows-1, self.maze_cols-1)]
        allowed = [cell for cell in all_cells if cell not in forbidden]

        def distance(c1, c2):
            return abs(c1[0]-c2[0]) + abs(c1[1]-c2[1])

        def is_far_from_player(cell, threshold=5):
            return distance(cell, (0, 0)) >= threshold

        def are_far_from_each_other(cells, threshold=4):
            for i in range(len(cells)):
                for j in range(i+1, len(cells)):
                    if distance(cells[i], cells[j]) < threshold:
                        return False
            return True

        selected = []
        attempts = 0
        total_needed = red_count + white_count
        while len(selected) < total_needed and attempts < 1000:
            candidate = random.choice(allowed)
            if not is_far_from_player(candidate, threshold=5):
                continue
            temp = selected + [candidate]
            if are_far_from_each_other(temp, threshold=4):
                selected.append(candidate)
            attempts += 1
        if len(selected) < total_needed:
            selected = random.sample(allowed, min(total_needed, len(allowed)))

        for i in range(red_count):
            if i < len(selected):
                r, c = selected[i]
                self.enemies.append(RedEnemy(r, c))
        for i in range(white_count):
            idx = red_count + i
            if idx < len(selected):
                r, c = selected[idx]
                self.enemies.append(WhiteEnemy(r, c))

    def resize_maze(self):
        factor = 1.3 ** (self.wins // 5)
        self.maze_cols = int(round(INITIAL_MAZE_COLS * factor))
        self.maze_rows = int(round(INITIAL_MAZE_ROWS * factor))
        self.cell_width = LOGICAL_WIDTH // self.maze_cols
        self.cell_height = (LOGICAL_HEIGHT - MAZE_TOP) // self.maze_rows
        self.player_anim = create_player_anim(self.cell_width, self.cell_height)
        openness = min(0.4, 0.1 * (self.wins // 5))
        self.maze = generate_maze(self.maze_cols, self.maze_rows, openness=openness)
        self.player_pos = (0, 0)
        self.start_time = pygame.time.get_ticks()
        self.round_time = 60 + 5 * (self.wins // 5)
        self.used_power_ups = 0
        self.powerup_active = False
        self.current_path = []
        self.spawn_enemies()

    def update_game(self):
        if self.game_over_flag:
            self.update()
            return

        now = pygame.time.get_ticks()
        dt = (now - self.prev_time) / 1000.0
        self.prev_time = now

        time_left = self.round_time - (now - self.start_time) / 1000.0

        if self.player_pos == (self.maze_cols - 1, self.maze_rows - 1):
            win_sound.play()
            self.wins += 1
            self.resize_maze()
            setup_particles()
            time_left = self.round_time

        if time_left <= 0:
            game_over_sound.play()
            self.game_over_flag = True
            self.update()
            return

        if self.powerup_active:
            if now >= self.powerup_end_time:
                self.powerup_active = False
            else:
                end_row, end_col = self.maze_rows - 1, self.maze_cols - 1
                self.current_path = find_path(self.maze, self.player_pos, end_row, end_col, self.maze_rows, self.maze_cols)

        for enemy in self.enemies:
            if isinstance(enemy, RedEnemy):
                enemy.update(self.maze, self.player_pos[1], self.player_pos[0], self.maze_rows, self.maze_cols, dt)
            elif isinstance(enemy, WhiteEnemy):
                direction = enemy.update(dt, self.maze, self.player_pos[1], self.player_pos[0])
                if direction:
                    cx = enemy.c * self.cell_width + self.cell_width // 2
                    cy = MAZE_TOP + enemy.r * self.cell_height + self.cell_height // 2
                    dx, dy = direction
                    self.bullets.append(Bullet(cx, cy, dx, dy, 300, 3.0))

        for enemy in self.enemies:
            if isinstance(enemy, RedEnemy) and (enemy.r, enemy.c) == (self.player_pos[1], self.player_pos[0]):
                self.game_over_flag = True
                game_over_sound.play()
                self.update()
                return

        for bullet in self.bullets[:]:
            bullet.update(dt)
            if not bullet.is_alive():
                self.bullets.remove(bullet)
                continue
            px = self.player_pos[0] * self.cell_width + self.cell_width // 2
            py = MAZE_TOP + self.player_pos[1] * self.cell_height + self.cell_height // 2
            dist = math.hypot(bullet.x - px, bullet.y - py)
            if dist < self.cell_width // 2:
                self.game_over_flag = True
                game_over_sound.play()
                self.update()
                return

        update_particles(dt)
        self.update()

    def paintEvent(self, event):
        self.surface.blit(background, (0, 0))
        draw_particles(self.surface)
        draw_maze(self.surface, self.maze, self.maze_cols, self.maze_rows, self.cell_width, self.cell_height)

        end_col, end_row = self.maze_cols - 1, self.maze_rows - 1
        x = end_col * self.cell_width
        y = MAZE_TOP + end_row * self.cell_height
        pygame.draw.rect(self.surface, (255, 0, 0), (x + 4, y + 4, self.cell_width - 8, self.cell_height - 8), 0)

        for enemy in self.enemies:
            ex = enemy.c * self.cell_width + self.cell_width // 2
            ey = MAZE_TOP + enemy.r * self.cell_height + self.cell_height // 2
            if isinstance(enemy, RedEnemy):
                color = (255, 0, 0)
            else:
                color = (255, 255, 255)
            pygame.draw.circle(self.surface, color, (int(ex), int(ey)), self.cell_width // 4)

        for bullet in self.bullets:
            pygame.draw.circle(self.surface, (255, 255, 0), (int(bullet.x), int(bullet.y)), 5)

        draw_player(self.surface, self.player_pos, self.cell_width, self.cell_height, self.player_anim)

        if self.powerup_active and self.current_path:
            steps_to_show = self.current_path[1:7]
            for step in steps_to_show:
                row, col = step
                x = col * self.cell_width
                y = MAZE_TOP + row * self.cell_height
                pygame.draw.rect(self.surface, (0, 255, 0), (x + self.cell_width // 4, y + self.cell_height // 4, self.cell_width // 2, self.cell_height // 2), 2)

        time_left = self.round_time - (pygame.time.get_ticks() - self.start_time) / 1000.0
        available = (self.wins // 2) - self.used_power_ups
        draw_stats(self.surface, self.wins, time_left, max(available, 0), self.font)

        if self.game_over_flag:
            draw_game_over(self.surface, self.wins)

        data = pygame.image.tostring(self.surface, 'RGB')
        image = QImage(data, LOGICAL_WIDTH, LOGICAL_HEIGHT, QImage.Format_RGB888)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_pixmap = QPixmap.fromImage(image).scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

    def keyPressEvent(self, event):
        if self.game_over_flag:
            if event.key() == Qt.Key_R:
                self.wins = 0
                self.game_over_flag = False
                self.resize_maze()
                setup_particles()
                self.start_time = pygame.time.get_ticks()
                self.prev_time = pygame.time.get_ticks()
            elif event.key() == Qt.Key_Escape:
                QApplication.quit()
            return

        key = event.key()
        if key == Qt.Key_Up:
            if not self.maze[self.player_pos[1]][self.player_pos[0]]['walls']['top'] and self.player_pos[1] > 0:
                self.player_pos = (self.player_pos[0], self.player_pos[1] - 1)
                move_sound.play()
        elif key == Qt.Key_Down:
            if not self.maze[self.player_pos[1]][self.player_pos[0]]['walls']['bottom'] and self.player_pos[1] < self.maze_rows - 1:
                self.player_pos = (self.player_pos[0], self.player_pos[1] + 1)
                move_sound.play()
        elif key == Qt.Key_Left:
            if not self.maze[self.player_pos[1]][self.player_pos[0]]['walls']['left'] and self.player_pos[0] > 0:
                self.player_pos = (self.player_pos[0] - 1, self.player_pos[1])
                move_sound.play()
        elif key == Qt.Key_Right:
            if not self.maze[self.player_pos[1]][self.player_pos[0]]['walls']['right'] and self.player_pos[0] < self.maze_cols - 1:
                self.player_pos = (self.player_pos[0] + 1, self.player_pos[1])
                move_sound.play()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            available = (self.wins // 2) - self.used_power_ups
            if available > 0 and not self.powerup_active:
                self.used_power_ups += 1
                self.powerup_active = True
                self.powerup_end_time = pygame.time.get_ticks() + 10000
        elif key == Qt.Key_F11:
            if self.window().isFullScreen():
                self.window().showNormal()
            else:
                self.window().showFullScreen()
        elif key == Qt.Key_Escape:
            QApplication.quit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Escape The Maze")
        self.resize(1768, 1024)
        self.setCentralWidget(GameWidget(self))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    pygame.init()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
