import pygame
import numpy as np
import sys
import random
import math
import time
import pyganim

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

WIDTH, HEIGHT = 1280, 800
FPS = 60
GRAVITY = 1.0
PLAYER_SPEED = 6
JUMP_SPEED = -18
MAX_FALL_SPEED = 15
COYOTE_TIME = 0.15
JUMP_BUFFER = 0.1
RESPAWN_VERTICAL_OFFSET = 70

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dario (Fixed)")
clock = pygame.time.Clock()

start_time = time.time()
final_time = None

def create_gradient_surface(width, height, start_color, end_color):
    surf = pygame.Surface((width, height))
    for y in range(height):
        ratio = y / height
        color = (
            int(start_color[0] * (1 - ratio) + end_color[0] * ratio),
            int(start_color[1] * (1 - ratio) + end_color[1] * ratio),
            int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        )
        pygame.draw.line(surf, color, (0, y), (width, y))
    return surf

def create_cloud_surface(width, height):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (255, 255, 255, 200), (0, 0, width, height))
    pygame.draw.ellipse(surf, (255, 255, 255, 150), (-10, height // 4, width // 2, height // 2))
    pygame.draw.ellipse(surf, (255, 255, 255, 180), (10, height // 8, width - 20, int(height / 1.5)))
    return surf

def draw_text(surface, text, font, pos, color):
    shadow = font.render(text, True, (0, 0, 0))
    txt = font.render(text, True, color)
    surface.blit(shadow, (pos[0] + 2, pos[1] + 2))
    surface.blit(txt, pos)

def create_circle_surface(diameter, color):
    surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (diameter // 2, diameter // 2), diameter // 2)
    return surf

def generate_sound(freq, duration, volume=0.5, sample_rate=44100):
    """Generate a sound wave of given frequency and duration."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = volume * np.sin(2 * np.pi * freq * t)
    arr = np.int16(wave * 32767)
    stereo_arr = np.column_stack((arr, arr))
    return pygame.sndarray.make_sound(stereo_arr)

jump_sound = generate_sound(600, 0.2, volume=0.5)
coin_sound = generate_sound(800, 0.1, volume=0.5)
stomp_sound = generate_sound(400, 0.15, volume=0.5)
game_over_sound = generate_sound(200, 0.5, volume=0.5)
powerup_sound = generate_sound(1000, 0.1, volume=0.5)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, controls):
        super().__init__()
        frame1 = create_gradient_surface(50, 70, (255, 100, 100), (200, 0, 0))
        frame2 = create_gradient_surface(50, 70, (255, 50, 50), (150, 0, 0))
        self.anim = pyganim.PygAnimation([(frame1, 200), (frame2, 200)])
        self.anim.play()
        self.image = self.anim.getCurrentFrame()
        self.rect = self.image.get_rect(topleft=(x, y))

        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.coyote_counter = 0.0
        self.jump_buffer_counter = 0.0
        self.controls = controls

        self.lives = 3
        self.score = 0
        self.coin_count = 0
        self.kills = 0
        self.active = True

        self.last_safe_x = x
        self.last_safe_y = y

        self.invincible = False
        self.invincible_timer = 0
        self.magnet = False
        self.magnet_timer = 0
        self.slowmo = False
        self.slowmo_timer = 0
        self.score_mul = 1
        self.score_mul_timer = 0
        self.gravity_reversed = False
        self.gravity_timer = 0

    def update(self, platforms, dt):
        if not self.active:
            return

        now = pygame.time.get_ticks()

        if self.invincible and now > self.invincible_timer:
            self.invincible = False
        if self.magnet and now > self.magnet_timer:
            self.magnet = False
        if self.slowmo and now > self.slowmo_timer:
            self.slowmo = False
        if self.score_mul > 1 and now > self.score_mul_timer:
            self.score_mul = 1
        if self.gravity_reversed and now > self.gravity_timer:
            self.gravity_reversed = False

        keys = pygame.key.get_pressed()
        speed_factor = 0.5 if self.slowmo else 1.0
        dx = 0
        if keys[self.controls[0]]:
            dx -= PLAYER_SPEED * speed_factor
        if keys[self.controls[1]]:
            dx += PLAYER_SPEED * speed_factor
        self.vel_x = dx

        if keys[self.controls[2]]:
            self.jump_buffer_counter = JUMP_BUFFER
        else:
            self.jump_buffer_counter -= dt
            if self.jump_buffer_counter < 0:
                self.jump_buffer_counter = 0

        gravity = -GRAVITY if self.gravity_reversed else GRAVITY
        self.vel_y += gravity * speed_factor
        if self.gravity_reversed:
            if self.vel_y < -MAX_FALL_SPEED:
                self.vel_y = -MAX_FALL_SPEED
        else:
            if self.vel_y > MAX_FALL_SPEED:
                self.vel_y = MAX_FALL_SPEED

        self.rect.x += self.vel_x
        self._collide_horizontal(platforms)

        self.rect.y += self.vel_y
        self.on_ground = False
        self._collide_vertical(platforms)

        if self.on_ground:
            self.coyote_counter = COYOTE_TIME
        else:
            self.coyote_counter -= dt
            if self.coyote_counter < 0:
                self.coyote_counter = 0

        if self.jump_buffer_counter > 0:
            can_jump = (self.on_ground or self.coyote_counter > 0)
            if can_jump:
                self.vel_y = JUMP_SPEED * (1 if not self.gravity_reversed else -1)
                jump_sound.play()
                self.jump_buffer_counter = 0
                self.coyote_counter = 0

        if self.on_ground:
            standing_on = None
            self.rect.y += 1
            hits = pygame.sprite.spritecollide(self, platforms, False)
            self.rect.y -= 1
            for p in hits:
                if hasattr(p, "visible") and not p.visible:
                    continue
                standing_on = p
                break
            if standing_on:
                self.last_safe_x = self.rect.centerx
                self.last_safe_y = self.rect.centery

        self.image = self.anim.getCurrentFrame()

    def _collide_horizontal(self, platforms):
        for p in platforms:
            if hasattr(p, "visible") and not p.visible:
                continue
            if self.rect.colliderect(p.rect):
                if self.vel_x > 0:
                    self.rect.right = p.rect.left
                elif self.vel_x < 0:
                    self.rect.left = p.rect.right
                self.vel_x = 0

    def _collide_vertical(self, platforms):
        for p in platforms:
            if hasattr(p, "visible") and not p.visible:
                continue
            if self.rect.colliderect(p.rect):
                if self.vel_y > 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    if isinstance(p, BoostPlatform):
                        self.vel_y = JUMP_SPEED * 1.5
                        jump_sound.play()
                elif self.vel_y < 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0

    def carry_by_moving_platform(self, platforms):
        self.rect.y += 1
        hits = pygame.sprite.spritecollide(self, platforms, False)
        self.rect.y -= 1
        for p in hits:
            if isinstance(p, MovingPlatform):
                self.rect.x += p.speed
                break

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = create_gradient_surface(width, height, (0, 150, 0), (0, 255, 0))
        self.rect = self.image.get_rect(topleft=(x, y))

class MovingPlatform(Platform):
    def __init__(self, x, y, width, height, range_x, speed):
        super().__init__(x, y, width, height)
        self.start_x = x
        self.range_x = range_x
        self.speed = speed

    def update(self):
        self.rect.x += self.speed
        if self.rect.x < self.start_x or self.rect.x > self.start_x + self.range_x:
            self.speed = -self.speed

class DisappearingPlatform(Platform):
    def __init__(self, x, y, width, height, interval):
        super().__init__(x, y, width, height)
        self.interval = interval
        self.last_switch = pygame.time.get_ticks()
        self.visible = True

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_switch > self.interval:
            self.visible = not self.visible
            self.last_switch = now
        if self.visible:
            self.image.set_alpha(255)
        else:
            self.image.set_alpha(0)

class BoostPlatform(Platform):
    def __init__(self, x, y, width, height, boost):
        super().__init__(x, y, width, height)
        self.boost = boost
        self.image = create_gradient_surface(width, height, (255, 140, 0), (255, 215, 0))

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        f1 = create_circle_surface(20, (255, 215, 0))
        f2 = create_circle_surface(20, (255, 255, 0))
        self.anim = pyganim.PygAnimation([(f1, 100), (f2, 100)])
        self.anim.play()
        self.image = self.anim.getCurrentFrame()
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.image = self.anim.getCurrentFrame()

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y, ptype):
        super().__init__()
        self.ptype = ptype
        colors = {
            'invincibility': ((255, 255, 0), (200, 200, 0)),
            'magnet': ((0, 255, 255), (0, 200, 200)),
            'slowmo': ((100, 100, 255), (70, 70, 200)),
            'score': ((255, 0, 255), (200, 0, 200)),
            'gravity': ((0, 255, 0), (0, 200, 0))
        }
        self.image = create_circle_surface(30, colors[ptype][0])
        self.rect = self.image.get_rect(center=(x, y))

class LifeItem(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_circle_surface(25, (255, 0, 0))
        self.rect = self.image.get_rect(center=(x, y))

class Star(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_circle_surface(20, (255, 255, 255))
        self.rect = self.image.get_rect(center=(x, y))

class BackgroundCloud(pygame.sprite.Sprite):
    def __init__(self, x, y, speed):
        super().__init__()
        self.image = create_cloud_surface(100, 60)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = speed

    def update(self):
        self.rect.x -= self.speed
        if self.rect.right < 0:
            self.rect.left = WIDTH

class RollingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y, move_range):
        super().__init__()
        self.base_image = create_gradient_surface(40, 40, (160, 32, 240), (128, 0, 128))
        self.image = self.base_image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.start_x = x
        self.move_range = move_range
        self.speed = 4
        self.angle = 0

    def update(self):
        self.rect.x += self.speed
        self.angle = (self.angle + 10) % 360
        self.image = pygame.transform.rotate(self.base_image, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        if self.rect.x < self.start_x or self.rect.x > self.start_x + self.move_range:
            self.speed = -self.speed

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, move_range):
        super().__init__()
        self.image = create_gradient_surface(40, 40, (0, 0, 255), (0, 0, 200))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.start_x = x
        self.move_range = move_range
        self.speed = 3

    def update(self):
        self.rect.x += self.speed
        if self.rect.x < self.start_x or self.rect.x > self.start_x + self.move_range:
            self.speed = -self.speed

class FlyingEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = create_gradient_surface(40, 40, (255, 0, 255), (200, 0, 200))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.base_y = y
        self.amplitude = 50
        self.freq = random.uniform(0.005, 0.015)
        self.speed = 4

    def update(self):
        self.rect.x -= self.speed
        t = pygame.time.get_ticks() / 1000.0
        self.rect.y = self.base_y + math.sin(t * self.freq) * self.amplitude

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((5, 5), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 255, 255, 255), (2, 2), 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.vel = [random.uniform(-3, 3), random.uniform(-3, 3)]
        self.life = random.randint(20, 40)
        self.initial_life = self.life

    def update(self):
        self.rect.x += self.vel[0]
        self.rect.y += self.vel[1]
        self.life -= 1
        if self.life <= 0:
            self.kill()
        else:
            alpha = int(255 * self.life / self.initial_life)
            self.image.set_alpha(alpha)

all_sprites = pygame.sprite.Group()
platforms = pygame.sprite.Group()
coins = pygame.sprite.Group()
enemies = pygame.sprite.Group()
powerups = pygame.sprite.Group()
lifeitems = pygame.sprite.Group()
stars = pygame.sprite.Group()
background_clouds = pygame.sprite.Group()
particles = pygame.sprite.Group()

players = []
game_mode = 0
game_over = False
font = pygame.font.SysFont("Arial", 30)
big_font = pygame.font.SysFont("Arial", 50)

def create_base_platform():
    base = Platform(WIDTH // 2 - 300, HEIGHT - 150, 600, 20)
    platforms.add(base)
    all_sprites.add(base)

def find_safe_respawn_point():
    return (WIDTH // 2, HEIGHT - 140)

def show_menu():
    global game_mode
    menu = True
    while menu:
        screen.fill((0, 0, 0))
        title = big_font.render("DARIO", True, (255, 255, 255))
        mode1 = font.render("1 - Single Player", True, (255, 255, 255))
        mode2 = font.render("2 - Two Players", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))
        screen.blit(mode1, (WIDTH // 2 - mode1.get_width() // 2, HEIGHT // 2))
        screen.blit(mode2, (WIDTH // 2 - mode2.get_width() // 2, HEIGHT // 2 + 50))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    game_mode = 1
                    menu = False
                if event.key == pygame.K_2:
                    game_mode = 2
                    menu = False

spawn_x = 0
difficulty_factor = 1.0

def spawn_obstacles():
    global spawn_x, difficulty_factor
    active_players = [p for p in players if p.active]
    if not active_players:
        return
    max_x = max(p.rect.x for p in active_players)
    if spawn_x < max_x + 2000:
        gap = random.randint(50, 100) / difficulty_factor
        plat_width = random.randint(200, 400)
        plat_height = 20
        plat_type = random.choices(['normal', 'moving', 'disappearing', 'boost'], weights=(60, 15, 10, 15))[0]
        plat_x = spawn_x + gap
        plat_y = random.randint(HEIGHT - 220, HEIGHT - 100)

        if plat_type == "moving":
            p = MovingPlatform(plat_x, plat_y, plat_width, plat_height,
                               random.randint(50, 150), random.choice([2, 3, 4]))
        elif plat_type == "disappearing":
            p = DisappearingPlatform(plat_x, plat_y, plat_width, plat_height,
                                     random.randint(1500, 2500))
        elif plat_type == "boost":
            p = BoostPlatform(plat_x, plat_y, plat_width, plat_height,
                              random.randint(15, 20))
        else:
            p = Platform(plat_x, plat_y, plat_width, plat_height)

        platforms.add(p)
        all_sprites.add(p)
        spawn_x = plat_x + plat_width

        if random.random() < 0.6:
            coin = Coin(plat_x + plat_width // 2, plat_y - 25)
            coins.add(coin)
            all_sprites.add(coin)

        enemy_prob = random.random()
        if enemy_prob < 0.3:
            e = Enemy(plat_x + random.randint(0, plat_width - 40), plat_y - 40, 80)
            enemies.add(e)
            all_sprites.add(e)
        elif enemy_prob < 0.5:
            fe = FlyingEnemy(plat_x + random.randint(0, plat_width - 40), plat_y - 100)
            enemies.add(fe)
            all_sprites.add(fe)
        elif enemy_prob < 0.6:
            re = RollingEnemy(plat_x + random.randint(0, plat_width - 40), plat_y - 120, 80)
            enemies.add(re)
            all_sprites.add(re)

        if random.random() < 0.1:
            ptype = random.choice(['invincibility', 'magnet', 'slowmo', 'score', 'gravity'])
            pup = PowerUp(plat_x + plat_width // 2, plat_y - 60, ptype)
            powerups.add(pup)
            all_sprites.add(pup)

        if random.random() < 0.05:
            li = LifeItem(plat_x + plat_width // 2, plat_y - 50)
            lifeitems.add(li)
            all_sprites.add(li)

        if random.random() < 0.05:
            st = Star(plat_x + plat_width // 2, plat_y - 50)
            stars.add(st)
            all_sprites.add(st)

        difficulty_factor = 1 + sum(p.score for p in players) / 500.0

def cleanup():
    active_players = [p for p in players if p.active]
    if not active_players:
        return
    min_x = min(p.rect.x for p in active_players)
    for sprite in all_sprites.copy():
        if sprite in players or sprite in background_clouds:
            continue
        if isinstance(sprite, Platform):
            continue
        if sprite.rect.right < min_x - 500:
            sprite.kill()

def reset_game():
    global game_over, final_time, players, spawn_x, start_time
    game_over = False
    final_time = None
    players.clear()
    for sprite in all_sprites.copy():
        if sprite not in background_clouds:
            sprite.kill()
    create_base_platform()

    if game_mode == 1:
        p = Player(WIDTH // 2 - 25, HEIGHT - 250,
                   [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_SPACE])
        players.append(p)
        all_sprites.add(p)
    else:
        p1 = Player(WIDTH // 2 - 100, HEIGHT - 250,
                    [pygame.K_a, pygame.K_d, pygame.K_w])
        p2 = Player(WIDTH // 2 + 50, HEIGHT - 250,
                    [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_SPACE])
        players.extend([p1, p2])
        all_sprites.add(p1, p2)

    for p in players:
        p.rect.topleft = (p.rect.x, HEIGHT - 250)
        p.vel_y = 0
        p.lives = 3
        p.score = 0
        p.coin_count = 0
        p.kills = 0
        p.active = True
        p.invincible = False
        p.magnet = False
        p.slowmo = False
        p.score_mul = 1
        p.gravity_reversed = False
        p.last_safe_x = p.rect.centerx
        p.last_safe_y = p.rect.centery

    spawn_x = max(p.rect.x for p in players) + 200
    start_time = time.time()

for i in range(5):
    cloud = BackgroundCloud(random.randint(0, WIDTH), random.randint(0, HEIGHT // 2),
                            random.uniform(0.5, 1.5))
    background_clouds.add(cloud)
    all_sprites.add(cloud)

show_menu()
reset_game()
running = True

while running:
    dt = clock.tick(FPS) / 1000.0
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and game_over:
                reset_game()
            if event.key == pygame.K_ESCAPE and game_over:
                pygame.quit()
                sys.exit()

    if not game_over:
        spawn_obstacles()

        for sprite in all_sprites:
            if not isinstance(sprite, Player):
                sprite.update()

        for p in players:
            if p.lives <= 0:
                p.active = False
                p.kill()
                continue
            p.update(platforms, dt)

        for p in players:
            if p.active:
                p.carry_by_moving_platform(platforms)

        for p in players:
            if p.active and p.magnet:
                for coin in coins:
                    dx = p.rect.centerx - coin.rect.centerx
                    dy = p.rect.centery - coin.rect.centery
                    coin.rect.x += int(dx * 0.05)
                    coin.rect.y += int(dy * 0.05)

        cleanup()

        active_players = [p for p in players if p.lives > 0]
        if not active_players:
            game_over = True

        for p in players:
            if not p.active:
                continue
            if (not p.gravity_reversed and p.rect.y > HEIGHT + 100) or \
               (p.gravity_reversed and p.rect.bottom < -100):
                if p.invincible:
                    p.vel_y = -JUMP_SPEED if not p.gravity_reversed else JUMP_SPEED
                else:
                    game_over_sound.play()
                    p.lives -= 1
                    if p.lives > 0:
                        p.rect.center = (p.last_safe_x, p.last_safe_y - RESPAWN_VERTICAL_OFFSET)
                        p.vel_y = 0
                        p.invincible = True
                        p.invincible_timer = now + 2000
                    else:
                        p.active = False
                        p.kill()

        for enemy in enemies:
            for p in players:
                if not p.active:
                    continue
                if p.rect.colliderect(enemy.rect):
                    if p.rect.bottom - enemy.rect.top < 20 and p.vel_y > 0:
                        stomp_sound.play()
                        enemy.kill()
                        p.vel_y = JUMP_SPEED // 2
                        p.score += 100 * p.score_mul
                        p.kills += 1
                        if isinstance(enemy, FlyingEnemy):
                            p.score += 50
                    elif not p.invincible:
                        game_over_sound.play()
                        p.lives -= 1
                        if p.lives > 0:
                            p.rect.center = (p.last_safe_x, p.last_safe_y - RESPAWN_VERTICAL_OFFSET)
                            p.vel_y = 0
                            p.invincible = True
                            p.invincible_timer = now + 2000
                        else:
                            p.active = False
                            p.kill()

        for p in players:
            if not p.active:
                continue
            hit_coins = pygame.sprite.spritecollide(p, coins, True)
            for coin in hit_coins:
                coin_sound.play()
                p.coin_count += 1
                p.score += 10 * p.score_mul
                for _ in range(10):
                    part = Particle(p.rect.centerx, p.rect.centery)
                    particles.add(part)
                    all_sprites.add(part)

            hit_powerups = pygame.sprite.spritecollide(p, powerups, True)
            for pup in hit_powerups:
                powerup_sound.play()
                if pup.ptype == "invincibility":
                    p.invincible = True
                    p.invincible_timer = now + 5000
                elif pup.ptype == "magnet":
                    p.magnet = True
                    p.magnet_timer = now + 5000
                elif pup.ptype == "slowmo":
                    p.slowmo = True
                    p.slowmo_timer = now + 5000
                elif pup.ptype == "score":
                    p.score_mul = 2
                    p.score_mul_timer = now + 5000
                elif pup.ptype == "gravity":
                    p.gravity_reversed = not p.gravity_reversed
                    p.gravity_timer = now + 5000

            hit_life = pygame.sprite.spritecollide(p, lifeitems, True)
            for li in hit_life:
                p.lives += 1

            hit_star = pygame.sprite.spritecollide(p, stars, True)
            for st in hit_star:
                p.score += 200 * p.score_mul

            p.score += int(dt * 10 * p.score_mul)

        difficulty_factor = 1 + sum(p.score for p in players) / 500.0

    else:
        if final_time is None:
            final_time = int(time.time() - start_time)

    active_players = [p for p in players if p.active]
    if active_players:
        avg_x = sum(p.rect.centerx for p in active_players) // len(active_players)
        offset_x = avg_x - WIDTH // 2
    else:
        offset_x = 0

    screen.fill((135, 206, 235))

    for cloud in background_clouds:
        screen.blit(cloud.image, (cloud.rect.x - offset_x * 0.5, cloud.rect.y))

    for sprite in all_sprites:
        screen.blit(sprite.image, (sprite.rect.x - offset_x, sprite.rect.y))

    for i, p in enumerate(players):
        if p.lives <= 0 and not p.active:
            continue
        if i == 0:
            draw_text(screen, f"P{i+1} Score: {p.score}", font, (20, 20), (255, 255, 255))
            draw_text(screen, f"Lives: {p.lives}", font, (20, 50), (255, 255, 255))
            draw_text(screen, f"Coins: {p.coin_count}", font, (20, 80), (255, 255, 255))
            draw_text(screen, f"Kills: {p.kills}", font, (20, 110), (255, 255, 255))
        else:
            txt_score = f"P{i+1} Score: {p.score}"
            txt_lives = f"Lives: {p.lives}"
            txt_coins = f"Coins: {p.coin_count}"
            txt_kills = f"Kills: {p.kills}"
            draw_text(screen, txt_score, font, (WIDTH - font.size(txt_score)[0] - 20, 20), (255, 255, 255))
            draw_text(screen, txt_lives, font, (WIDTH - font.size(txt_lives)[0] - 20, 50), (255, 255, 255))
            draw_text(screen, txt_coins, font, (WIDTH - font.size(txt_coins)[0] - 20, 80), (255, 255, 255))
            draw_text(screen, txt_kills, font, (WIDTH - font.size(txt_kills)[0] - 20, 110), (255, 255, 255))

    timer_val = final_time if game_over else int(time.time() - start_time)
    timer_text = font.render(f"Time: {timer_val}", True, (255, 255, 255))
    screen.blit(timer_text, (WIDTH // 2 - timer_text.get_width() // 2, 20))

    if game_over:
        over_text = big_font.render("Game Over! Press R To Restart or ESC To Exit", True, (255, 0, 0))
        screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2))

    pygame.display.flip()
    clock.tick(FPS)
