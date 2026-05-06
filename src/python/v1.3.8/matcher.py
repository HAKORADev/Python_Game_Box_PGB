import sys
import random
import time
import pygame
import pymunk
import pyganim
import numpy as np
import math

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT, FPS = 640, 800, 60
GEM_SIZE, GRID_COLS, GRID_ROWS = 64, 8, 8
GRID_TOP = 100
GRID_LEFT = (WIDTH - GRID_COLS * GEM_SIZE) // 2

COLORS = [
    (200, 50, 50),
    (50, 200, 50),
    (50, 50, 200),
    (200, 200, 50),
    (150, 100, 200)
]

SPECIAL_THRESHOLDS = {
    'matcher': 2500,
    'cleaner': 5000,
    'bomber': 7500,
    'vanisher': 10000
}

clock = pygame.time.Clock()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Matcher")

def generate_tone(freq, duration, volume=0.5):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = np.sin(2 * np.pi * freq * t)
    tone = (tone * 32767 * volume).astype(np.int16)
    tone = np.c_[tone, tone]
    return pygame.sndarray.make_sound(tone)

def draw_gradient_circle(surface, center, radius, inner_color, outer_color):
    for r in range(radius, 0, -1):
        ratio = r / radius
        col = (
            int(inner_color[0] * ratio + outer_color[0] * (1 - ratio)),
            int(inner_color[1] * ratio + outer_color[1] * (1 - ratio)),
            int(inner_color[2] * ratio + outer_color[2] * (1 - ratio))
        )
        pygame.draw.circle(surface, col, center, r)

def draw_gradient_rect(surface, rect, inner_color, outer_color):
    x, y, w, h = rect
    for i in range(h):
        ratio = i / h
        col = (
            int(inner_color[0] * (1 - ratio) + outer_color[0] * ratio),
            int(inner_color[1] * (1 - ratio) + outer_color[1] * ratio),
            int(inner_color[2] * (1 - ratio) + outer_color[2] * ratio)
        )
        pygame.draw.line(surface, col, (x, y + i), (x + w, y + i))

def draw_gradient_triangle(surface, points, inner_color, outer_color):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    miny = min(ys)
    maxy = max(ys)
    edges = [(points[i], points[(i+1)%3]) for i in range(3)]
    for y in range(miny, maxy+1):
        x_vals = []
        for (p1, p2) in edges:
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                t = (y - p1[1]) / (p2[1] - p1[1])
                x = p1[0] + t * (p2[0] - p1[0])
                x_vals.append(x)
        if len(x_vals) >= 2:
            x1 = min(x_vals)
            x2 = max(x_vals)
            ratio = (y - miny) / (maxy - miny)
            col = (
                int(inner_color[0] * (1 - ratio) + outer_color[0] * ratio),
                int(inner_color[1] * (1 - ratio) + outer_color[1] * ratio),
                int(inner_color[2] * (1 - ratio) + outer_color[2] * ratio)
            )
            pygame.draw.line(surface, col, (x1, y), (x2, y))

def init_stars(n):
    s = []
    for _ in range(n):
        pos = (random.randint(0, WIDTH), random.randint(0, HEIGHT))
        phase = random.uniform(0, 2 * math.pi)
        s.append({'pos': pos, 'phase': phase})
    return s

stars = init_stars(100)

def draw_background(surface):
    t = time.time()
    top_color = (20 + int(10 * math.sin(t)), 20, 40 + int(10 * math.cos(t)))
    bottom_color = (0, 0, int(30 + 10 * math.sin(t)))
    for i in range(HEIGHT):
        ratio = i / HEIGHT
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, i), (WIDTH, i))
    for star in stars:
        brightness = 128 + 127 * math.sin(t + star['phase'])
        c = (int(brightness), int(brightness), int(brightness))
        pygame.draw.circle(surface, c, star['pos'], 1)

def apply_shader(surface):
    scaled = pygame.transform.smoothscale(surface, (WIDTH // 2, HEIGHT // 2))
    scaled = pygame.transform.smoothscale(scaled, (WIDTH, HEIGHT))
    alpha = 60 + int(20 * math.sin(time.time() * 0.5))
    scaled.set_alpha(alpha)
    surface.blit(scaled, (0, 0), special_flags=pygame.BLEND_ADD)

def draw_gem(surface, pos, color):
    x, y = pos
    radius = GEM_SIZE // 2 - 4
    s = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    pygame.draw.circle(s, (0, 0, 0, 120), (radius * 2 + 3, radius * 2 + 3), radius + 3)
    pygame.draw.circle(s, color, (radius * 2, radius * 2), radius)
    highlight_center = (int(radius * 1.4), int(radius * 1.4))
    pygame.draw.circle(s, (255, 255, 255, 200), highlight_center, radius // 3)
    surface.blit(s, (x - radius * 2, y - radius * 2))

def draw_text_outline(surface, text, font, color, outline_color, pos):
    x, y = pos
    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
        surface.blit(font.render(text, True, outline_color), (x + dx, y + dy))
    surface.blit(font.render(text, True, color), pos)

class Particle:
    def __init__(self, pos, color):
        self.pos = list(pos)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(50, 150)
        self.vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.gravity = 200
        self.life = random.uniform(0.5, 1.0)
        self.size = random.randint(2, 4)
        self.color = color

    def update(self, dt):
        self.life -= dt
        self.vel[1] += self.gravity * dt
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = max(0, int(255 * (self.life / 1.0)))
        s = pygame.Surface((self.size * 6, self.size * 6), pygame.SRCALPHA)
        center = (self.size * 3, self.size * 3)
        for i in range(self.size * 3, 0, -1):
            a = max(0, int(alpha * (i / (self.size * 3))))
            pygame.draw.circle(s, self.color + (a,), center, i)
        surface.blit(s, (int(self.pos[0]) - self.size * 3, int(self.pos[1]) - self.size * 3))

class Gem:
    def __init__(self, color):
        self.color = color
        self.pos = None
        self.target_pos = None

class Board:
    def __init__(self):
        self.grid = []
        for r in range(GRID_ROWS):
            row = []
            for c in range(GRID_COLS):
                gem = self.random_gem()
                target = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                          GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                gem.pos = target
                gem.target_pos = target
                row.append(gem)
            self.grid.append(row)

    def random_gem(self):
        return Gem(random.choice(COLORS))

    def draw(self, surface):
        pygame.draw.rect(surface, (30, 30, 50),
                         (GRID_LEFT, GRID_TOP, GRID_COLS * GEM_SIZE, GRID_ROWS * GEM_SIZE))
        for r in range(GRID_ROWS + 1):
            y = GRID_TOP + r * GEM_SIZE
            pygame.draw.line(surface, (80, 80, 100),
                             (GRID_LEFT, y), (GRID_LEFT + GRID_COLS * GEM_SIZE, y))
        for c in range(GRID_COLS + 1):
            x = GRID_LEFT + c * GEM_SIZE
            pygame.draw.line(surface, (80, 80, 100),
                             (x, GRID_TOP), (x, GRID_TOP + GRID_ROWS * GEM_SIZE))
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                gem = self.grid[r][c]
                if gem:
                    draw_gem(surface, gem.pos, gem.color)

    def swap(self, pos1, pos2):
        r1, c1 = pos1
        r2, c2 = pos2
        self.grid[r1][c1], self.grid[r2][c2] = self.grid[r2][c2], self.grid[r1][c1]

    def find_matches(self):
        matched = set()
        for r in range(GRID_ROWS):
            c = 0
            while c < GRID_COLS:
                if self.grid[r][c] is None:
                    c += 1
                    continue
                run = [(r, c)]
                while c + 1 < GRID_COLS and self.grid[r][c + 1] is not None \
                        and self.grid[r][c].color == self.grid[r][c + 1].color:
                    run.append((r, c + 1))
                    c += 1
                if len(run) >= 3:
                    matched.update(run)
                c += 1
        for c in range(GRID_COLS):
            r = 0
            while r < GRID_ROWS:
                if self.grid[r][c] is None:
                    r += 1
                    continue
                run = [(r, c)]
                while r + 1 < GRID_ROWS and self.grid[r + 1][c] is not None \
                        and self.grid[r][c].color == self.grid[r + 1][c].color:
                    run.append((r + 1, c))
                    r += 1
                if len(run) >= 3:
                    matched.update(run)
                r += 1
        return list(matched)

    def remove_matches(self, matches):
        score_gain = 0
        explosions = []
        for r, c in matches:
            if self.grid[r][c]:
                score_gain += 10
                explosions.append((GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                                   GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2,
                                   self.grid[r][c].color))
                self.grid[r][c] = None
        return score_gain, explosions

    def collapse(self):
        animations = []
        for c in range(GRID_COLS):
            column = [self.grid[r][c] for r in range(GRID_ROWS)]
            remain = [g for g in column if g is not None]
            missing = GRID_ROWS - len(remain)
            new_column = []
            for i in range(missing):
                gem = self.random_gem()
                start_y = GRID_TOP - (missing - i) * GEM_SIZE
                gem.pos = [GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2, start_y]
                new_column.append(gem)
            new_column.extend(remain)
            for r in range(GRID_ROWS):
                gem = new_column[r]
                target = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                          GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                if gem.pos != target:
                    animations.append(FallAnimation(gem, gem.pos, target))
                gem.target_pos = target
                self.grid[r][c] = gem
        return animations

    def process_matches_once(self):
        matches = self.find_matches()
        if not matches:
            return 0, [], []
        score, explosions = self.remove_matches(matches)
        animations = self.collapse()
        return score, explosions, animations

class FallAnimation:
    def __init__(self, gem, start_pos, end_pos, duration=0.3):
        self.gem = gem
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.duration = duration
        self.elapsed = 0

    def update(self, dt):
        self.elapsed += dt
        t = min(self.elapsed / self.duration, 1)
        new_x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        new_y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
        self.gem.pos = (new_x, new_y)
        return self.elapsed >= self.duration

    def draw(self, surface):
        draw_gem(surface, self.gem.pos, self.gem.color)

class SwapAnimation:
    def __init__(self, gem, start_pos, end_pos, duration=0.2):
        self.gem = gem
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.duration = duration
        self.elapsed = 0

    def update(self, dt):
        self.elapsed += dt
        t = min(self.elapsed / self.duration, 1)
        new_x = self.start_pos[0] + (self.end_pos[0] - self.start_pos[0]) * t
        new_y = self.start_pos[1] + (self.end_pos[1] - self.start_pos[1]) * t
        self.gem.pos = (new_x, new_y)
        return self.elapsed >= self.duration

    def draw(self, surface):
        draw_gem(surface, self.gem.pos, self.gem.color)

class Explosion:
    def __init__(self, pos, color):
        self.pos = pos
        self.duration = 0.5
        self.elapsed = 0
        self.max_radius = 40
        self.color = color
        self.spawned = False

    def update(self, dt):
        self.elapsed += dt
        return self.elapsed >= self.duration

    def draw(self, surface):
        progress = self.elapsed / self.duration
        radius = int(progress * self.max_radius)
        r = radius if radius > 0 else 1
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for i in range(r, 0, -2):
            a = max(0, 255 - int(255 * (i / r)))
            pygame.draw.circle(s, self.color + (a,), (r, r), i)
        surface.blit(s, (self.pos[0] - r, self.pos[1] - r))

class SpecialPowers:
    def __init__(self):
        self.counts = {'matcher': 0, 'cleaner': 0, 'bomber': 0, 'vanisher': 0}
        self.progress = {'matcher': 0, 'cleaner': 0, 'bomber': 0, 'vanisher': 0}

    def update(self, score):
        for key in self.progress:
            self.progress[key] += score
            while self.progress[key] >= SPECIAL_THRESHOLDS[key] and self.counts[key] < 3:
                self.counts[key] += 1
                self.progress[key] -= SPECIAL_THRESHOLDS[key]

    def use(self, key, board):
        if self.counts[key] <= 0:
            return 0, [], []
        self.counts[key] -= 1

        if key == 'matcher':
            swap_anims = []
            for _ in range(2):
                r = random.randint(0, GRID_ROWS - 1)
                c = random.randint(0, GRID_COLS - 1)
                neighbors = []
                if r > 0:
                    neighbors.append((r - 1, c))
                if r < GRID_ROWS - 1:
                    neighbors.append((r + 1, c))
                if c > 0:
                    neighbors.append((r, c - 1))
                if c < GRID_COLS - 1:
                    neighbors.append((r, c + 1))
                if neighbors:
                    r2, c2 = random.choice(neighbors)
                    board.grid[r][c], board.grid[r2][c2] = board.grid[r2][c2], board.grid[r][c]
                    gem1 = board.grid[r][c]
                    gem2 = board.grid[r2][c2]
                    gem1.target_pos = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                                       GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                    gem2.target_pos = (GRID_LEFT + c2 * GEM_SIZE + GEM_SIZE // 2,
                                       GRID_TOP + r2 * GEM_SIZE + GEM_SIZE // 2)
                    swap_anims.append(SwapAnimation(gem1, gem1.pos, gem1.target_pos))
                    swap_anims.append(SwapAnimation(gem2, gem2.pos, gem2.target_pos))
            raw_score, raw_explosions, raw_anims = board.process_matches_once()
            explosions = [Explosion((x, y), color) for x, y, color in raw_explosions]
            booster_sound.play()
            return raw_score, explosions, swap_anims + raw_anims

        elif key == 'cleaner':
            explosions = []
            if random.choice([True, False]):
                row = random.randint(0, GRID_ROWS - 1)
                for c in range(GRID_COLS):
                    gem = board.grid[row][c]
                    if gem:
                        pos = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + row * GEM_SIZE + GEM_SIZE // 2)
                        explosions.append(Explosion(pos, gem.color))
                        board.grid[row][c] = None
            else:
                col = random.randint(0, GRID_COLS - 1)
                for r in range(GRID_ROWS):
                    gem = board.grid[r][col]
                    if gem:
                        pos = (GRID_LEFT + col * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                        explosions.append(Explosion(pos, gem.color))
                        board.grid[r][col] = None
            fall_anims = board.collapse()
            raw_score, raw_explosions, match_anims = board.process_matches_once()
            explosions.extend([Explosion((x, y), color) for x, y, color in raw_explosions])
            booster_sound.play()
            return raw_score, explosions, fall_anims + match_anims

        elif key == 'bomber':
            explosions = []
            r = random.randint(0, GRID_ROWS - 4)
            c = random.randint(0, GRID_COLS - 4)
            for i in range(4):
                for j in range(4):
                    if r + i < GRID_ROWS and c + j < GRID_COLS:
                        gem = board.grid[r + i][c + j]
                        if gem:
                            pos = (GRID_LEFT + (c + j) * GEM_SIZE + GEM_SIZE // 2,
                                   GRID_TOP + (r + i) * GEM_SIZE + GEM_SIZE // 2)
                            explosions.append(Explosion(pos, gem.color))
                            board.grid[r + i][c + j] = None
            fall_anims = board.collapse()
            raw_score, raw_explosions, match_anims = board.process_matches_once()
            explosions.extend([Explosion((x, y), color) for x, y, color in raw_explosions])
            booster_sound.play()
            return raw_score, explosions, fall_anims + match_anims

        elif key == 'vanisher':
            explosions = []
            clr = random.choice(COLORS)
            for r in range(GRID_ROWS):
                for c in range(GRID_COLS):
                    gem = board.grid[r][c]
                    if gem and gem.color == clr:
                        pos = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                        explosions.append(Explosion(pos, gem.color))
                        board.grid[r][c] = None
            fall_anims = board.collapse()
            raw_score, raw_explosions, match_anims = board.process_matches_once()
            explosions.extend([Explosion((x, y), color) for x, y, color in raw_explosions])
            booster_sound.play()
            return raw_score, explosions, fall_anims + match_anims

        return 0, [], []

    def draw(self, surface):
        font = pygame.font.SysFont("Comic Sans MS", 20)
        seg_width = WIDTH / 4
        y_icon = HEIGHT - 80
        y_text = y_icon + 40
        keys = ['matcher', 'cleaner', 'bomber', 'vanisher']
        for i, key in enumerate(keys):
            center = (int(seg_width * i + seg_width / 2), int(y_icon))
            txt = font.render(key.capitalize(), True, (255, 255, 255))
            rect = txt.get_rect(center=(center[0], y_icon - 60))
            surface.blit(txt, rect)
            temp = pygame.Surface((60, 60), pygame.SRCALPHA)
            if key == 'matcher':
                draw_gradient_circle(temp, (30, 30), 30, (0, 122, 204), (0, 0, 50))
            elif key == 'cleaner':
                draw_gradient_rect(temp, (0, 0, 60, 60), (0, 200, 0), (0, 50, 0))
            elif key == 'bomber':
                draw_gradient_circle(temp, (30, 30), 30, (200, 0, 0), (100, 0, 0))
                pygame.draw.line(temp, (0, 0, 0), (30, 0), (30, 20), 3)
                pygame.draw.circle(temp, (255, 255, 0), (30, 0), 5)
            elif key == 'vanisher':
                points = [(30, 0), (0, 60), (60, 60)]
                draw_gradient_triangle(temp, points, (150, 0, 150), (50, 0, 50))
            surface.blit(temp, (center[0] - 30, center[1] - 30))
            ct_val = self.counts[key]
            ct_str = str(ct_val) if ct_val < 3 else "Full"
            ct = font.render(ct_str, True, (255, 255, 255))
            rt = ct.get_rect(center=(center[0], y_text))
            surface.blit(ct, rt)
            prog = font.render(str(self.progress[key]) + "/" + str(SPECIAL_THRESHOLDS[key]),
                               True, (255, 255, 255))
            rt2 = prog.get_rect(center=(center[0], y_text + 20))
            surface.blit(prog, rt2)

    def get_icon_positions(self):
        positions = {}
        seg_width = WIDTH / 4
        y_icon = HEIGHT - 80
        keys = ['matcher', 'cleaner', 'bomber', 'vanisher']
        for i, key in enumerate(keys):
            center = (int(seg_width * i + seg_width / 2), int(y_icon))
            positions[key] = (center, 30)
        return positions

class Game:
    def __init__(self):
        self.state = 'menu'
        self.board = Board()
        self.special = SpecialPowers()
        self.total_score = 0
        self.round_score = 0
        self.moves = 20
        self.round_count = 0
        self.target = 700 + self.round_count * 100
        self.timer_total = 40 + (self.round_count // 2) * 5
        self.time_left = self.timer_total
        self.win_count = 0
        self.loss_count = 0
        self.selected = None
        self.animations = []
        self.explosions = []
        self.game_over_played = False
        self.cascade_level = 0
        self.user_move = False
        self.last_swap = None
        self.particles = []

    def reset_round(self):
        self.round_count += 1
        bonus = (self.win_count // 10) * 5
        self.board = Board()
        self.round_score = 0
        self.moves = 20 + bonus
        self.target = 700 + self.round_count * 100
        self.timer_total = 40 + (self.round_count // 2) * 5
        self.time_left = self.timer_total
        self.selected = None
        self.cascade_level = 0
        self.user_move = False
        self.last_swap = None

    def spawn_particles(self, pos, color, count):
        for _ in range(count):
            self.particles.append(Particle(pos, color))

    def update(self, dt):
        if self.animations:
            for anim in self.animations[:]:
                if anim.update(dt):
                    self.animations.remove(anim)

        if self.explosions:
            for exp in self.explosions[:]:
                if not exp.spawned:
                    self.spawn_particles(exp.pos, exp.color, 20)
                    exp.spawned = True
                if exp.update(dt):
                    self.explosions.remove(exp)

        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

        if not self.animations and not self.explosions:
            score_gain, exps, new_anims = self.board.process_matches_once()
            if score_gain > 0:
                if self.user_move:
                    match_sound.play()
                    self.cascade_level = 0
                    self.user_move = False
                else:
                    cascade_freq = 880 + self.cascade_level * 50
                    generate_tone(cascade_freq, 0.1).play()
                    self.cascade_level += 1
                self.round_score += score_gain
                self.special.update(score_gain)
                for e in exps:
                    self.explosions.append(Explosion((e[0], e[1]), e[2]))
                self.animations.extend(new_anims)
                return
            elif self.user_move:
                if self.last_swap:
                    pos1, pos2 = self.last_swap
                    self.board.swap(pos1, pos2)
                    gemA = self.board.grid[pos1[0]][pos1[1]]
                    gemB = self.board.grid[pos2[0]][pos2[1]]
                    targetA = (GRID_LEFT + pos1[1] * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + pos1[0] * GEM_SIZE + GEM_SIZE // 2)
                    targetB = (GRID_LEFT + pos2[1] * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + pos2[0] * GEM_SIZE + GEM_SIZE // 2)
                    self.animations.append(SwapAnimation(gemA, gemA.pos, targetA))
                    self.animations.append(SwapAnimation(gemB, gemB.pos, targetB))
                generate_tone(300, 0.15).play()
                self.user_move = False
                return

        self.time_left -= dt
        if self.time_left <= 0:
            self.state = 'game_over'

        if self.moves <= 0 and self.round_score < self.target:
            self.loss_count += 1
            if self.loss_count >= 10:
                self.state = 'game_over'
            else:
                lose_sound.play()
                self.total_score += self.round_score
                self.reset_round()

        if self.round_score >= self.target:
            self.win_count += 1
            win_sound.play()
            self.total_score += self.round_score
            self.reset_round()

        if self.state == 'game_over' and not self.game_over_played:
            game_over_sound.play()
            self.game_over_played = True

    def draw_ui(self, surface):
        font = pygame.font.SysFont("Comic Sans MS", 24)
        draw_text_outline(surface, "Score: " + str(self.round_score), font,
                          (255, 255, 0), (0, 0, 0), (10, 10))
        draw_text_outline(surface, "Moves: " + str(self.moves), font,
                          (255, 255, 0), (0, 0, 0), (10, 40))
        draw_text_outline(surface, "Target: " + str(self.target), font,
                          (255, 255, 0), (0, 0, 0), (WIDTH - 150, 10))
        draw_text_outline(surface, "Time: " + str(int(self.time_left)), font,
                          (255, 255, 0), (0, 0, 0), (WIDTH - 150, 40))
        draw_text_outline(surface, "Losses: 10/" + str(self.loss_count), font,
                          (255, 255, 0), (0, 0, 0), (WIDTH - 150, 70))
        draw_text_outline(surface, "Wins: " + str(self.win_count), font,
                          (255, 255, 0), (0, 0, 0), (WIDTH // 2 - 100, 10))
        self.special.draw(surface)

    def handle_mouse(self, pos):
        for key, (center, rad) in self.special.get_icon_positions().items():
            dx = pos[0] - center[0]
            dy = pos[1] - center[1]
            if dx * dx + dy * dy <= rad * rad:
                if self.animations:
                    return
                score, exps, anims = self.special.use(key, self.board)
                if score > 0 or exps or anims:
                    self.round_score += score
                    self.special.update(score)
                    self.explosions.extend(exps)
                    self.animations.extend(anims)
                return

        x, y = pos
        if (GRID_TOP <= y < GRID_TOP + GRID_ROWS * GEM_SIZE and
                GRID_LEFT <= x < GRID_LEFT + GRID_COLS * GEM_SIZE):
            if self.animations:
                return
            col = (x - GRID_LEFT) // GEM_SIZE
            row = (y - GRID_TOP) // GEM_SIZE
            if self.selected is None:
                self.selected = (row, col)
                return
            r, c = self.selected
            if abs(r - row) + abs(c - col) == 1:
                gem1 = self.board.grid[r][c]
                gem2 = self.board.grid[row][col]
                if gem1 and gem2:
                    pos1, pos2 = gem1.pos, gem2.pos
                    self.board.swap((r, c), (row, col))
                    self.last_swap = ((r, c), (row, col))
                    target1 = (GRID_LEFT + col * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + row * GEM_SIZE + GEM_SIZE // 2)
                    target2 = (GRID_LEFT + c * GEM_SIZE + GEM_SIZE // 2,
                               GRID_TOP + r * GEM_SIZE + GEM_SIZE // 2)
                    self.animations.append(SwapAnimation(gem1, pos1, target1))
                    self.animations.append(SwapAnimation(gem2, pos2, target2))
                    self.moves -= 1
                    self.user_move = True
                self.selected = None
            else:
                self.selected = (row, col)

    def handle_key(self, key):
        if self.state == 'menu' and key == pygame.K_SPACE:
            self.state = 'playing'
        elif self.state == 'game_over':
            if key == pygame.K_r:
                self.__init__()
                self.state = 'playing'
            elif key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    def draw_menu(self, surface):
        surface.fill((0, 0, 0))
        font = pygame.font.SysFont("Comic Sans MS", 36)
        text = font.render("Press SPACE to Start", True, (255, 255, 0))
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        surface.blit(text, rect)

    def draw_game_over(self, surface):
        surface.fill((0, 0, 0))
        font = pygame.font.SysFont("Comic Sans MS", 36)
        text = font.render("Game Over", True, (255, 0, 0))
        rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
        surface.blit(text, rect)
        stats = "Wins: " + str(self.win_count) + " Losses: " + str(self.loss_count) + \
                " Total Score: " + str(self.total_score)
        stats_text = font.render(stats, True, (255, 255, 255))
        rect2 = stats_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        surface.blit(stats_text, rect2)
        prompt = font.render("Press R to Restart or ESC to Exit", True, (255, 255, 255))
        rect3 = prompt.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        surface.blit(prompt, rect3)

    def draw_particles(self, surface):
        for p in self.particles:
            p.draw(surface)

swap_sound = generate_tone(440, 0.1)
match_sound = generate_tone(880, 0.1)
booster_sound = generate_tone(660, 0.1)
win_sound = generate_tone(523, 0.5)
lose_sound = generate_tone(196, 0.5)
game_over_sound = generate_tone(130, 0.75)

def main():
    game = Game()
    running = True
    last_time = time.time()
    while running:
        dt = time.time() - last_time
        last_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and game.state == 'playing':
                game.handle_mouse(pygame.mouse.get_pos())
            if event.type == pygame.KEYDOWN:
                game.handle_key(event.key)

        draw_background(screen)

        if game.state == 'playing':
            game.update(dt)
            game.board.draw(screen)
            if game.selected:
                r, c = game.selected
                pygame.draw.rect(screen, (255, 255, 255),
                                 (GRID_LEFT + c * GEM_SIZE, GRID_TOP + r * GEM_SIZE,
                                  GEM_SIZE, GEM_SIZE), 3)
            for anim in game.animations:
                if hasattr(anim, "draw"):
                    anim.draw(screen)
            for exp in game.explosions:
                exp.draw(screen)
            game.draw_particles(screen)
            game.draw_ui(screen)
        elif game.state == 'menu':
            game.draw_menu(screen)
        elif game.state == 'game_over':
            game.draw_game_over(screen)

        apply_shader(screen)
        pygame.display.update()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
