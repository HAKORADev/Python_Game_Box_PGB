import pygame
import sys
import random
import math
import numpy as np
import pyganim

pygame.init()

screen_width = 805
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Hen Invaders")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)

def create_sound(frequency, duration, volume=0.5):
    sample_rate = 44100
    n_samples = int(round(duration * sample_rate))
    t = np.linspace(0, duration, n_samples, endpoint=False)
    waveform = np.sin(2 * math.pi * frequency * t)
    waveform = waveform * 32767 * volume
    waveform = waveform.astype(np.int16)
    waveform = np.column_stack((waveform, waveform))
    return pygame.sndarray.make_sound(waveform)

shoot_sound = create_sound(800, 0.1)
explosion_sound = create_sound(300, 0.15)
rocket_sound = create_sound(500, 0.2)
hit_sound = create_sound(150, 0.2)
enhancement_sound = create_sound(700, 0.1)

def get_weapon_params(enh):
    if enh < 20:
        return (enh // 5 + 1, 0)
    elif enh < 40:
        return (5, (enh - 20) // 5)
    else:
        return (5, 4)

def get_enemy_color(level):
    hues = [(255, 0, 0), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255), (128, 128, 0), (128, 0, 128), (0, 128, 128), (255, 165, 0)]
    return hues[(level - 1) % len(hues)]

def create_radial_gradient(size, color):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    cx, cy = w // 2, h // 2
    r = min(cx, cy)
    for i in range(r, 0, -1):
        a = int(255 * (i / r))
        pygame.draw.circle(surf, (color[0], color[1], color[2], a), (cx, cy), i)
    return surf

def create_explosion_anim():
    frames = []
    for i in range(1, 6):
        size = 20 + i * 10
        surf = create_radial_gradient((size, size), (255, max(0, 255 - i * 40), 0))
        frames.append((surf, 100))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

class Explosion:
    def __init__(self, x, y):
        self.anim = create_explosion_anim()
        self.x = x
        self.y = y
        self.start_time = pygame.time.get_ticks()
        self.duration = 500

    def finished(self):
        return pygame.time.get_ticks() - self.start_time > self.duration

    def draw(self, surface):
        self.anim.blit(surface, (self.x, self.y))

def create_enhancement_anim(color, radius):
    frames = []
    for scale in (0.8, 1.0, 1.2, 1.0):
        size = int(radius * 2 * scale)
        surf = create_radial_gradient((size, size), color)
        frames.append((surf, 100))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

def create_bg_surface(w, h, top_color, bottom_color):
    bg = pygame.Surface((w, h))
    for i in range(h):
        ratio = i / h
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(bg, (r, g, b), (0, i), (w, i))
    return bg

def draw_glow_polygon(surface, points, base_color, glow_color):
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

class Player:
    def __init__(self, x, color):
        self.width = 40
        self.height = 20
        self.x = x
        self.y = screen_height - self.height - 10
        self.speed = 5
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, self.width, self.height)
        self.enhancement_points = 0
        self.weapon_stage, self.rocket_count = get_weapon_params(self.enhancement_points)
        self.bullet_cooldown = 0
        self.rocket_cooldown = 0
        self.lives = 3
        self.color = color

    def move(self, dx):
        if self.lives > 0:
            self.rect.x += dx * self.speed
            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > screen_width: self.rect.right = screen_width

    def draw(self, surface):
        if self.lives > 0:
            pts = [(self.rect.centerx, self.rect.top), (self.rect.left, self.rect.bottom), (self.rect.right, self.rect.bottom)]
            draw_glow_polygon(surface, pts, self.color, (self.color[0], self.color[1], self.color[2], 80))

class AIShip:
    def __init__(self):
        self.width = 40
        self.height = 20
        self.speed = 4
        self.rect = pygame.Rect(screen_width // 2 - self.width // 2,
                                screen_height - self.height - 30,
                                self.width, self.height)
        self.color = (135, 206, 235)
        self.bullet_cooldown = 0
        self.bullet_delay = 12

    def move(self, dx):
        self.rect.x += dx * self.speed
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > screen_width:
            self.rect.right = screen_width

    def update(self, enemies, eggs):
        target_x = None
        if enemies:
            closest = min(enemies, key=lambda e: e.rect.bottom)
            target_x = closest.rect.centerx
        else:
            target_x = screen_width // 2

        dx = 0
        if self.rect.centerx < target_x - 5:
            dx = 1
        elif self.rect.centerx > target_x + 5:
            dx = -1

        avoid = 0
        for egg in eggs:
            if (egg.rect.bottom > self.rect.top - 50 and
                egg.rect.top < self.rect.bottom + 50):
                if egg.rect.centerx < self.rect.centerx:
                    avoid += 1
                else:
                    avoid -= 1

        if avoid != 0:
            dx = 1 if avoid > 0 else -1

        self.move(dx)

        if self.bullet_cooldown <= 0 and enemies:
            offsets = [-10, 0, 10]
            for off in offsets:
                bullets.append(Bullet(self.rect.centerx, self.rect.top, off))
            shoot_sound.play()
            self.bullet_cooldown = self.bullet_delay

        if self.bullet_cooldown > 0:
            self.bullet_cooldown -= 1

    def draw(self, surface):
        pts = [(self.rect.centerx, self.rect.top),
               (self.rect.left, self.rect.bottom),
               (self.rect.right, self.rect.bottom)]
        draw_glow_polygon(surface, pts, self.color, (self.color[0], self.color[1], self.color[2], 80))

class Bullet:
    def __init__(self, x, y, offset):
        self.speed = 8
        self.rect = pygame.Rect(x + offset - 2, y - 10, 4, 10)

    def update(self):
        self.rect.y -= self.speed

    def draw(self, surface):
        draw_glow_rect(surface, self.rect, (255, 255, 0), (255, 255, 0, 80))

class Egg:
    def __init__(self, x, y):
        self.speed = 5
        self.rect = pygame.Rect(x - 3, y - 3, 6, 6)

    def update(self):
        self.rect.y += self.speed

    def draw(self, surface):
        temp = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(temp, (255, 255, 255, 200), temp.get_rect())
        surface.blit(temp, self.rect)

class Enemy:
    def __init__(self, x, y, speed, health, level):
        self.rect = pygame.Rect(x, y, 40, 30)
        self.speed = speed
        self.health = health
        self.level = level

    def update(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def draw(self, surface):
        color = get_enemy_color(self.level)
        draw_glow_rect(surface, self.rect, color, (min(color[0]+50, 255), min(color[1]+50, 255), min(color[2]+50, 255), 80))
        pygame.draw.circle(surface, (min(color[0]+50, 255), min(color[1]+50, 255), min(color[2]+50, 255)), (self.rect.centerx, self.rect.top + 10), 10)

class Enhancement:
    def __init__(self):
        self.radius = 8
        self.x = random.randrange(self.radius, screen_width - self.radius)
        self.y = -self.radius
        self.speed = 6
        self.color = random.choice([(0, 0, 255), (0, 255, 0), (255, 255, 0)])
        self.rect = pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)
        self.anim = create_enhancement_anim(self.color, self.radius)

    def update(self):
        self.y += self.speed
        self.rect.y = int(self.y)

    def draw(self, surface):
        self.anim.blit(surface, (self.x - self.radius, int(self.y) - self.radius))

def generate_wave(level, wave):
    rows = min(wave, 6)
    columns = 8 + level
    enemy_speed = 1 + level * 0.2 + random.random() * 0.5
    formation = []
    enemy_width = 40
    enemy_height = 30
    spacing_x = 10
    spacing_y = 10
    total_width = columns * enemy_width + (columns - 1) * spacing_x
    start_x = (screen_width - total_width) // 2
    start_y = 50
    for row in range(rows):
        for col in range(columns):
            x = start_x + col * (enemy_width + spacing_x)
            y = start_y + row * (enemy_height + spacing_y)
            formation.append(Enemy(x, y, enemy_speed, level, level))
    return formation

def main_menu():
    menu = True
    game_mode = 1
    menu_bg = create_bg_surface(screen_width, screen_height, (10, 10, 40), (0, 0, 0))
    while menu:
        screen.blit(menu_bg, (0, 0))
        title = font.render("HEN INVADERS", True, (0, 255, 0))
        mode1 = font.render("1 - SINGLE PLAYER", True, (255, 255, 255) if game_mode == 1 else (100, 100, 100))
        mode2 = font.render("2 - TWO PLAYERS", True, (255, 255, 255) if game_mode == 2 else (100, 100, 100))
        start = font.render("PRESS ENTER TO START", True, (200, 200, 200))

        screen.blit(title, (screen_width // 2 - title.get_width() // 2, 100))
        screen.blit(mode1, (screen_width // 2 - mode1.get_width() // 2, 250))
        screen.blit(mode2, (screen_width // 2 - mode2.get_width() // 2, 300))
        screen.blit(start, (screen_width // 2 - start.get_width() // 2, 400))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: game_mode = 1
                elif event.key == pygame.K_2: game_mode = 2
                elif event.key == pygame.K_RETURN: return game_mode
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

while True:
    game_mode = main_menu()
    player1 = Player(screen_width // 2 - 50 if game_mode == 2 else screen_width // 2, (0, 255, 0))
    player2 = Player(screen_width // 2 + 50, (255, 165, 0)) if game_mode == 2 else None

    bullets = []
    enemies = []
    eggs = []
    enhancements = []
    explosions = []

    level = 1
    wave = 1
    score = 0
    extra_life_threshold = 100
    ai_charges = 0
    next_ai_threshold = 1000
    ai_ship = None
    ai_waves_remaining = 0

    max_enhancements_in_level = random.randint(2, 10)
    spawned_enhancements_this_level = 0
    enemies = generate_wave(level, wave)
    formation_direction = 1
    game_over = False

    running = True
    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not game_over:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and player1.lives > 0 and player1.bullet_cooldown <= 0:
                        shoot_sound.play()
                        num = player1.weapon_stage
                        offsets = []
                        if num % 2:
                            offsets.append(0)
                            for i in range(1, num // 2 + 1):
                                offsets.append(-i * 10)
                                offsets.append(i * 10)
                        else:
                            for i in range(1, num // 2 + 1):
                                offsets.append(-i * 10 + 5)
                                offsets.append(i * 10 - 5)
                        for off in offsets:
                            bullets.append(Bullet(player1.rect.centerx, player1.rect.top, off))
                        player1.bullet_cooldown = 15

                    if event.key == pygame.K_RETURN and player1.lives > 0 and player1.rocket_count > 0 and player1.rocket_cooldown <= 0:
                        rocket_sound.play()
                        score += len(enemies)
                        for e in enemies:
                            explosions.append(Explosion(e.rect.x, e.rect.y))
                        enemies = []
                        player1.rocket_count -= 1
                        player1.rocket_cooldown = 30

                    if player2 and player2.lives > 0:
                        if event.key == pygame.K_w and player2.bullet_cooldown <= 0:
                            shoot_sound.play()
                            num = player2.weapon_stage
                            offsets = []
                            if num % 2:
                                offsets.append(0)
                                for i in range(1, num // 2 + 1):
                                    offsets.append(-i * 10)
                                    offsets.append(i * 10)
                            else:
                                for i in range(1, num // 2 + 1):
                                    offsets.append(-i * 10 + 5)
                                    offsets.append(i * 10 - 5)
                            for off in offsets:
                                bullets.append(Bullet(player2.rect.centerx, player2.rect.top, off))
                            player2.bullet_cooldown = 15
                        if event.key == pygame.K_e and player2.rocket_count > 0 and player2.rocket_cooldown <= 0:
                            rocket_sound.play()
                            score += len(enemies)
                            for e in enemies:
                                explosions.append(Explosion(e.rect.x, e.rect.y))
                            enemies = []
                            player2.rocket_count -= 1
                            player2.rocket_cooldown = 30

                    if event.key == pygame.K_c and ai_charges > 0 and ai_ship is None:
                        ai_ship = AIShip()
                        ai_waves_remaining = 3
                        ai_charges -= 1
            else:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        running = False
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

        if not game_over:
            keys = pygame.key.get_pressed()
            if player1.lives > 0:
                if keys[pygame.K_LEFT]: player1.move(-1)
                if keys[pygame.K_RIGHT]: player1.move(1)
            if player2 and player2.lives > 0:
                if keys[pygame.K_a]: player2.move(-1)
                if keys[pygame.K_d]: player2.move(1)

            if player1.bullet_cooldown > 0: player1.bullet_cooldown -= 1
            if player1.rocket_cooldown > 0: player1.rocket_cooldown -= 1
            if player2:
                if player2.bullet_cooldown > 0: player2.bullet_cooldown -= 1
                if player2.rocket_cooldown > 0: player2.rocket_cooldown -= 1

            for b in bullets:
                b.update()
            bullets = [b for b in bullets if b.rect.bottom > 0]

            for e in eggs:
                e.update()
            eggs = [e for e in eggs if e.rect.top <= screen_height]

            for enh in enhancements:
                enh.update()
            enhancements = [enh for enh in enhancements if enh.rect.top <= screen_height]

            if enemies:
                lefts = [e.rect.left for e in enemies]
                rights = [e.rect.right for e in enemies]
                dx = enemies[0].speed * formation_direction
                if min(lefts) + dx < 0 or max(rights) + dx > screen_width:
                    formation_direction *= -1
                    for e in enemies:
                        e.update(0, 10)
                else:
                    for e in enemies:
                        e.update(dx, 0)

                for e in enemies:
                    if random.random() < 0.001 + level * 0.0005:
                        eggs.append(Egg(e.rect.centerx, e.rect.bottom))
            else:
                wave += 1
                if ai_ship:
                    ai_waves_remaining -= 1
                    if ai_waves_remaining <= 0:
                        ai_ship = None
                if wave > 10:
                    level = min(level + 1, 10)
                    wave = 1
                    max_enhancements_in_level = random.randint(2, 10)
                    spawned_enhancements_this_level = 0
                enemies = generate_wave(level, wave)
                formation_direction = 1
                for e in enemies:
                    explosions.append(Explosion(e.rect.x, e.rect.y))

            if random.random() < 0.002 and spawned_enhancements_this_level < max_enhancements_in_level:
                enhancements.append(Enhancement())
                spawned_enhancements_this_level += 1

            if ai_ship:
                ai_ship.update(enemies, eggs)
                for egg in eggs[:]:
                    if egg.rect.colliderect(ai_ship.rect):
                        hit_sound.play()
                        eggs.remove(egg)
                        explosions.append(Explosion(ai_ship.rect.x, ai_ship.rect.y))
                        ai_ship = None
                        break

            if score >= next_ai_threshold:
                ai_charges += 1
                next_ai_threshold += 1000

            for b in bullets[:]:
                for e in enemies[:]:
                    if b.rect.colliderect(e.rect):
                        explosion_sound.play()
                        bullets.remove(b)
                        e.health -= 1
                        if e.health <= 0:
                            score += 1
                            explosions.append(Explosion(e.rect.x, e.rect.y))
                            enemies.remove(e)
                            if score >= extra_life_threshold:
                                player1.lives += 1
                                if player2:
                                    player2.lives += 1
                                extra_life_threshold += 100
                        break

            active_players = [p for p in [player1, player2] if p and p.lives > 0]
            if not active_players and ai_ship is None:
                game_over = True

            for e in eggs[:]:
                for p in active_players:
                    if e.rect.colliderect(p.rect):
                        hit_sound.play()
                        eggs.remove(e)
                        p.lives -= 1
                        p.enhancement_points = max(0, p.enhancement_points - 5)
                        break

            for enh in enhancements[:]:
                for p in active_players:
                    if enh.rect.colliderect(p.rect):
                        enhancement_sound.play()
                        enhancements.remove(enh)
                        p.enhancement_points += 1
                        break

            for p in [player1, player2]:
                if p:
                    p.weapon_stage, p.rocket_count = get_weapon_params(p.enhancement_points)

            explosions = [exp for exp in explosions if not exp.finished()]

        bg = create_bg_surface(screen_width, screen_height, (10, 10, 40), (0, 0, 0))
        screen.blit(bg, (0, 0))

        if not game_over:
            if player1.lives > 0:
                player1.draw(screen)
            if player2 and player2.lives > 0:
                player2.draw(screen)
            if ai_ship:
                ai_ship.draw(screen)
            for b in bullets:
                b.draw(screen)
            for e in enemies:
                e.draw(screen)
            for egg in eggs:
                egg.draw(screen)
            for enh in enhancements:
                enh.draw(screen)
            for exp in explosions:
                exp.draw(screen)

            if ai_ship:
                ai_status = f"AI: active ({ai_waves_remaining} waves left)"
            else:
                ai_status = f"AI: {ai_charges} charges"

            t1 = font.render(f"Score: {score}    Level: {level} Wave: {wave}    {ai_status}", True, (255, 255, 255))
            t2 = font.render(f"P1: Lives: {player1.lives}  Weapon: {player1.weapon_stage}  Rockets: {player1.rocket_count}", True, (255, 255, 255))
            screen.blit(t1, (10, 10))
            screen.blit(t2, (10, 40))
            if player2:
                t3 = font.render(f"P2: Lives: {player2.lives}  Weapon: {player2.weapon_stage}  Rockets: {player2.rocket_count}", True, (255, 255, 255))
                screen.blit(t3, (10, 70))
        else:
            ot = font.render("Game Over", True, (255, 0, 0))
            st = font.render(f"Final Score: {score}", True, (255, 255, 255))
            rt = font.render("Press R to Restart or ESC to Exit", True, (255, 255, 255))
            screen.blit(ot, (screen_width // 2 - ot.get_width() // 2, screen_height // 2 - 60))
            screen.blit(st, (screen_width // 2 - st.get_width() // 2, screen_height // 2))
            screen.blit(rt, (screen_width // 2 - rt.get_width() // 2, screen_height // 2 + 60))

        pygame.display.flip()
