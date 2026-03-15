import pygame
import random
import numpy as np
import pyganim
import math

pygame.mixer.pre_init(44100, -16, 2)
pygame.init()

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
pygame.display.set_caption("Snowy Tower")
FPS = 60
GRAVITY = 0.5
PLAYER_SPEED = 5
BASE_SCROLL_SPEED = 1.0

MIN_GAP = 70
MAX_GAP = 140
MIN_WIDTH = 30
MAX_WIDTH = 250

TYPE_WEIGHTS = {
    'static': 40,
    'moving': 25,
    'blinking': 15,
    'disappearing': 10,
    'moving_blinking': 10
}
RELIABLE_TYPES = {'static', 'moving'}
UNRELIABLE_TYPES = {'blinking', 'disappearing', 'moving_blinking'}

def generate_sound_wave(freq, duration, vol, waveform):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    if waveform == "sine":
        wave = np.sin(2 * np.pi * freq * t)
    else:
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    wave = (wave * vol * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)

jump_sound = generate_sound_wave(550, 0.1, 0.5, "sine")
move_sound = generate_sound_wave(350, 0.1, 0.5, "square")
fall_sound = generate_sound_wave(200, 0.2, 0.5, "sine")

def draw_gradient(surface, top_color, bottom_color):
    h = surface.get_height()
    w = surface.get_width()
    for i in range(h):
        ratio = i / h
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, i), (w, i))

def create_player_anim(color):
    frames = []
    for scale in (0.8, 1.0, 1.2, 1.0):
        size = 30
        surf = pygame.Surface((size + 6, size + 6), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, color + (50,), (0, 0, size + 6, size + 6))
        inner = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.ellipse(inner, color, (0, 0, size, size))
        surf.blit(inner, (3, 3))
        frames.append((surf, 100))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-5, -1)
        self.life = random.randint(20, 40)
        self.color = (255, 255, 255)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.vy += 0.1

    def draw(self, surface):
        if self.life > 0:
            alpha = max(0, int(255 * (self.life / 40)))
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            s.fill(self.color + (alpha,))
            surface.blit(s, (int(self.x), int(self.y)))

class Cloud:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(50, 200)
        self.speed = random.uniform(0.2, 0.5)
        self.size = random.randint(100, 300)
        self.surf = pygame.Surface((self.size, self.size // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(self.surf, (255, 255, 255, 150), (0, 0, self.size, self.size // 2))

    def update(self):
        self.x -= self.speed
        if self.x + self.size < 0:
            self.x = SCREEN_WIDTH
            self.y = random.randint(50, 200)

    def draw(self, surface):
        surface.blit(self.surf, (self.x, self.y))

class HumanPlayer:
    def __init__(self, x, y, controls):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.vy = 0
        self.controls = controls
        self.score = 0
        self.active = True
        self.is_human = True
        if controls == "arrows":
            self.anim = create_player_anim((255, 215, 0))
        else:
            self.anim = create_player_anim((0, 255, 255))
        self.trail = []

    def update(self, keys):
        if self.controls == "arrows":
            if keys[pygame.K_LEFT]:
                self.rect.x -= PLAYER_SPEED
            elif keys[pygame.K_RIGHT]:
                self.rect.x += PLAYER_SPEED
        elif self.controls == "ad":
            if keys[pygame.K_a]:
                self.rect.x -= PLAYER_SPEED
            elif keys[pygame.K_d]:
                self.rect.x += PLAYER_SPEED

        self.vy += GRAVITY
        self.rect.y += int(self.vy)
        self.rect.left = max(0, min(self.rect.left, SCREEN_WIDTH - 30))

        self.trail.append((self.rect.centerx, self.rect.centery, 30))
        if len(self.trail) > 10:
            self.trail.pop(0)

    def jump(self):
        self.vy = -12
        for _ in range(10):
            particles.append(Particle(self.rect.centerx, self.rect.bottom))

    def draw(self, surface):
        for tx, ty, size in self.trail:
            pygame.draw.circle(surface, (255, 215, 0), (tx, ty), size // 20)
        self.anim.blit(surface, self.rect.topleft)

class AIPlayer:
    def __init__(self, x, y, difficulty):
        self.rect = pygame.Rect(x, y, 30, 30)
        self.vy = 0
        self.score = 0
        self.active = True
        self.is_human = False
        self.jump_delay = 0
        self.difficulty = difficulty
        self.anim = create_player_anim((255, 0, 0))
        if difficulty == 'easy':
            self.speed = 3
        elif difficulty == 'medium':
            self.speed = 5
        else:
            self.speed = 6

    def update(self, platforms):
        if not self.active:
            return

        candidates = [p for p in platforms if p.rect.top > self.rect.bottom]
        if candidates:
            if self.difficulty == 'hard':
                target = min(candidates, key=lambda p: p.rect.top - self.rect.bottom)
            elif self.difficulty == 'medium':
                closest = sorted(candidates, key=lambda p: p.rect.top - self.rect.bottom)[:3]
                target = random.choice(closest) if random.random() < 0.3 else closest[0]
            else:
                target = random.choice(candidates) if random.random() < 0.5 else min(candidates, key=lambda p: p.rect.top - self.rect.bottom)

            target_x = target.rect.centerx - 15
            if target.type == "moving" or target.type == "moving_blinking":
                target_x += target.speed * 8 * target.direction

            if self.difficulty == 'medium':
                target_x += random.randint(-20, 20)
            elif self.difficulty == 'easy':
                target_x += random.randint(-40, 40)

            dx = target_x - self.rect.centerx
            if dx > self.speed:
                self.rect.x += self.speed
            elif dx < -self.speed:
                self.rect.x -= self.speed
            else:
                self.rect.x += dx

        self.vy += GRAVITY
        self.rect.y += int(self.vy)

        if self.rect.top > SCREEN_HEIGHT:
            self.active = False
            fall_sound.play()

        self.rect.left = max(0, min(self.rect.left, SCREEN_WIDTH - 30))

        self.jump_delay = max(0, self.jump_delay - 1)

    def jump(self):
        self.vy = -12
        for _ in range(10):
            particles.append(Particle(self.rect.centerx, self.rect.bottom))

    def draw(self, surface):
        if self.active:
            self.anim.blit(surface, self.rect.topleft)

class Platform:
    def __init__(self, x, y, width, height, ptype):
        self.rect = pygame.Rect(x, y, width, height)
        self.type = ptype
        self.scored = False
        self.visible = True

        if ptype in ("moving", "moving_blinking"):
            self.speed = random.uniform(2, 3)
            self.direction = random.choice([-1, 1])
            self.range_left = x - 80
            self.range_right = x + 80

        if ptype in ("blinking", "moving_blinking"):
            self.blink_timer = 0
            self.blink_interval = 1000

        if ptype == "disappearing":
            self.disappear_timer = 0
            self.disappearing = False

    def update(self):
        if self.type == "moving" or self.type == "moving_blinking":
            self.rect.x += self.speed * self.direction
            if self.rect.x < self.range_left or self.rect.x > self.range_right:
                self.direction *= -1

        if self.type == "blinking" or self.type == "moving_blinking":
            now = pygame.time.get_ticks()
            if now - self.blink_timer > self.blink_interval:
                self.visible = not self.visible
                self.blink_timer = now

        if self.type == "disappearing":
            if self.disappearing:
                self.disappear_timer -= 1
                if self.disappear_timer <= 0:
                    self.visible = True
                    self.disappearing = False
                    self.scored = False

    def draw(self, surface):
        if not self.visible:
            return

        if self.type == "static":
            c = (0, 200, 0)
        elif self.type == "moving":
            c = (200, 0, 0)
        elif self.type == "blinking":
            c = (255, 140, 0)
        elif self.type == "disappearing":
            c = (128, 128, 128)
        elif self.type == "moving_blinking":
            c = (255, 165, 0)

        surf = pygame.Surface((self.rect.width, self.rect.height))
        draw_gradient(surf, c, (max(0, c[0]-50), max(0, c[1]-50), max(0, c[2]-50)))
        surface.blit(surf, (self.rect.x, self.rect.y))

def spawn_snowflake():
    return {
        'x': random.randint(0, SCREEN_WIDTH),
        'y': random.randint(-50, 0),
        'speed': random.uniform(1, 3),
        'radius': random.randint(1, 3)
    }

snowflakes = [spawn_snowflake() for _ in range(100)]

def update_snowflakes():
    for flake in snowflakes:
        flake['y'] += flake['speed']
        if flake['y'] > SCREEN_HEIGHT:
            flake['y'] = random.randint(-50, 0)
            flake['x'] = random.randint(0, SCREEN_WIDTH)

def draw_snowflakes(surface):
    for flake in snowflakes:
        pygame.draw.circle(surface, (255, 255, 255), (flake['x'], int(flake['y'])), flake['radius'])

def choose_platform_type(prev_type):
    prev_unreliable = prev_type in UNRELIABLE_TYPES

    if prev_unreliable:
        total = sum(TYPE_WEIGHTS[t] for t in RELIABLE_TYPES)
        r = random.randint(1, total)
        cumulative = 0
        for t in RELIABLE_TYPES:
            cumulative += TYPE_WEIGHTS[t]
            if r <= cumulative:
                return t
    else:
        total = sum(TYPE_WEIGHTS.values())
        r = random.randint(1, total)
        cumulative = 0
        for t, w in TYPE_WEIGHTS.items():
            cumulative += w
            if r <= cumulative:
                return t

    return "static"

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 40)
particles = []
clouds = [Cloud() for _ in range(5)]

def reset_game(mode):
    global game_mode, players, platforms, game_over
    game_mode = mode
    players = []
    platforms = [Platform(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 20, 200, 10, "static")]

    if mode == "ai_easy":
        players.append(HumanPlayer(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 50, "arrows"))
        players.append(AIPlayer(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 50, "easy"))
    elif mode == "ai_medium":
        players.append(HumanPlayer(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 50, "arrows"))
        players.append(AIPlayer(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 50, "medium"))
    elif mode == "ai_hard":
        players.append(HumanPlayer(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 50, "arrows"))
        players.append(AIPlayer(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 50, "hard"))
    elif mode == "player":
        players.append(HumanPlayer(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 50, "arrows"))
        players.append(HumanPlayer(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT - 50, "ad"))
    else:
        players.append(HumanPlayer(SCREEN_WIDTH // 2 - 15, SCREEN_HEIGHT - 50, "arrows"))

    for _ in range(20):
        prev = platforms[-1]
        gap = random.randint(MIN_GAP, MAX_GAP)
        t = 24 - math.sqrt(576 - 4 * gap)
        max_horiz = PLAYER_SPEED * t

        new_width = random.randint(MIN_WIDTH, MAX_WIDTH)

        reach_left = prev.rect.left - max_horiz
        reach_right = prev.rect.right + max_horiz

        L = reach_left - new_width
        R = reach_right
        min_x = max(0, int(math.floor(L)) + 1)
        max_x = min(SCREEN_WIDTH - new_width, int(math.floor(R - 1e-9)))

        if min_x <= max_x:
            new_x = random.randint(min_x, max_x)
        else:
            new_x = random.randint(0, SCREEN_WIDTH - new_width)

        new_y = prev.rect.top - gap

        ptype = choose_platform_type(prev.type)

        platforms.append(Platform(new_x, new_y, new_width, 10, ptype))

    game_over = False

def ai_difficulty_menu():
    selected = 0
    options = ['Easy', 'Medium', 'Hard', 'Back']
    menu_font = pygame.font.SysFont("Arial", 50)

    while True:
        screen.fill((25, 25, 112))
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif e.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif e.key == pygame.K_RETURN:
                    if selected == 3:
                        return None
                    else:
                        mode = ['ai_easy', 'ai_medium', 'ai_hard'][selected]
                        reset_game(mode)
                        return True

        for i, text in enumerate(options):
            color = (255, 255, 255) if i == selected else (150, 150, 150)
            render = menu_font.render(text, True, color)
            screen.blit(render, (SCREEN_WIDTH // 2 - render.get_width() // 2, 300 + i * 70))

        pygame.display.flip()
        clock.tick(FPS)

def main_menu():
    selected = 0
    menu_font = pygame.font.SysFont("Arial", 50)
    options = ['Single Player', 'VS AI', 'VS Player', 'Exit']

    while True:
        screen.fill((25, 25, 112))
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                elif e.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                elif e.key == pygame.K_RETURN:
                    if selected == 3:
                        pygame.quit()
                        exit()
                    elif selected == 1:
                        result = ai_difficulty_menu()
                        if result is True:
                            return
                    elif selected == 0:
                        reset_game('single')
                        return
                    elif selected == 2:
                        reset_game('player')
                        return

        for i, text in enumerate(options):
            color = (255, 255, 255) if i == selected else (150, 150, 150)
            render = menu_font.render(text, True, color)
            screen.blit(render, (SCREEN_WIDTH // 2 - render.get_width() // 2, 300 + i * 70))

        pygame.display.flip()
        clock.tick(FPS)

main_menu()
game_over = False

while True:
    clock.tick(FPS)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            exit()
        if game_over and e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                main_menu()
            elif e.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()

    if not game_over:
        active_humans = [p for p in players if p.is_human and p.active]
        if not active_humans:
            game_over = True
            continue

        max_score = max(p.score for p in active_humans)
        if max_score < 2:
            scroll_speed = 0
        else:
            scroll_speed = BASE_SCROLL_SPEED * (1.1 ** (max_score // 10))

        for p in players:
            p.rect.y += scroll_speed
        for plat in platforms:
            plat.rect.y += scroll_speed
        for cl in clouds:
            cl.y += scroll_speed
        for part in particles:
            part.y += scroll_speed

        keys = pygame.key.get_pressed()

        for p in players:
            if p.active:
                if isinstance(p, AIPlayer):
                    p.update(platforms)
                else:
                    p.update(keys)

        for plat in platforms[:]:
            plat.update()
            if plat.rect.top > SCREEN_HEIGHT:
                platforms.remove(plat)
                prev = platforms[-1]
                gap = random.randint(MIN_GAP, MAX_GAP)
                t = 24 - math.sqrt(576 - 4 * gap)
                max_horiz = PLAYER_SPEED * t
                new_width = random.randint(MIN_WIDTH, MAX_WIDTH)

                reach_left = prev.rect.left - max_horiz
                reach_right = prev.rect.right + max_horiz
                L = reach_left - new_width
                R = reach_right
                min_x = max(0, int(math.floor(L)) + 1)
                max_x = min(SCREEN_WIDTH - new_width, int(math.floor(R - 1e-9)))

                if min_x <= max_x:
                    new_x = random.randint(min_x, max_x)
                else:
                    new_x = random.randint(0, SCREEN_WIDTH - new_width)

                new_y = prev.rect.top - gap
                ptype = choose_platform_type(prev.type)
                platforms.append(Platform(new_x, new_y, new_width, 10, ptype))

        for p in players:
            if not p.active:
                continue
            for plat in platforms:
                if not plat.visible:
                    continue
                if p.vy > 0 and p.rect.colliderect(plat.rect):
                    p.jump()
                    if p.is_human and not plat.scored:
                        p.score += 1
                        plat.scored = True
                    jump_sound.play()

                    if plat.type == "disappearing" and not plat.disappearing:
                        plat.visible = False
                        plat.disappearing = True
                        plat.disappear_timer = 180

            if p.is_human and p.rect.top > SCREEN_HEIGHT:
                p.active = False
                fall_sound.play()

        for cl in clouds:
            cl.update()

        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        draw_gradient(bg, (135, 206, 250), (25, 25, 112))
        screen.blit(bg, (0, 0))
        for cl in clouds:
            cl.draw(screen)
        update_snowflakes()
        draw_snowflakes(screen)
        for plat in platforms:
            plat.draw(screen)
        for p in players:
            if p.active:
                p.draw(screen)

        for part in particles[:]:
            part.update()
            part.draw(screen)
            if part.life <= 0:
                particles.remove(part)

        y_pos = 20
        for i, p in enumerate([p for p in players if p.is_human]):
            scr = pygame.font.SysFont("Arial", 24).render(f"P{i+1}: {p.score}", True, (0, 0, 0))
            screen.blit(scr, (20, y_pos))
            y_pos += 50

        pygame.display.flip()
    else:
        screen.fill((0, 0, 0))
        h_scores = [f"P{i+1}: {p.score}" for i, p in enumerate(players) if p.is_human]
        text1 = font.render("Scores: " + ", ".join(h_scores), True, (255, 255, 255))
        text2 = font.render("Press R to restart", True, (255, 255, 255))
        screen.blit(text1, (SCREEN_WIDTH // 2 - text1.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(text2, (SCREEN_WIDTH // 2 - text2.get_width() // 2, SCREEN_HEIGHT // 2 + 50))
        pygame.display.flip()
