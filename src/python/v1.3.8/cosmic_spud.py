import pygame
import sys
import random
import math
import numpy as np

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)

WIDTH, HEIGHT = 1280, 720
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 50, 255)
YELLOW = (255, 255, 0)
CYAN = (50, 255, 255)
PURPLE = (150, 50, 255)
ORANGE = (255, 150, 0)
BROWN = (212, 175, 55)
DARK_GREY = (30, 30, 40)
LIGHT_GREY = (200, 200, 200)
AURA_PURPLE = (180, 100, 255)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cosmic Spud")
clock = pygame.time.Clock()
font_small = pygame.font.SysFont("Courier New", 16, bold=True)
font_medium = pygame.font.SysFont("Courier New", 24, bold=True)
font_large = pygame.font.SysFont("Courier New", 48, bold=True)

def generate_sound(freq, duration, volume=0.5, wave_type='sine'):
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
    wave = (wave * volume * 32767).astype(np.int16)
    stereo = np.column_stack((wave, wave))
    return pygame.sndarray.make_sound(stereo)

shoot_sound = generate_sound(880, 0.1, 0.3, 'square')
hit_sound = generate_sound(440, 0.08, 0.2, 'sine')
kill_sound = generate_sound(660, 0.15, 0.3, 'sine')
game_over_sound = generate_sound(220, 0.5, 0.5, 'sawtooth')
wave_win_sound = generate_sound(523, 0.3, 0.4, 'sine')
level_up_sound = generate_sound(1046, 0.2, 0.4, 'square')

def rand(min_val, max_val):
    return random.uniform(min_val, max_val)

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)

def normalize_angle(a):
    return a % (2 * math.pi)

UPGRADES = [
    {"name": "Power Potato", "desc": "Damage +20%", "type": "dmg", "val": 0.2, "rare": "common"},
    {"name": "Swift Spud", "desc": "Move Speed +10%", "type": "spd", "val": 0.1, "rare": "common"},
    {"name": "Rapid Fire", "desc": "Attack Speed +15%", "type": "atk", "val": 0.15, "rare": "common"},
    {"name": "Long Barrel", "desc": "Range +25%", "type": "rng", "val": 0.25, "rare": "common"},
    {"name": "Iron Skin", "desc": "Armor +2", "type": "arm", "val": 2, "rare": "common"},
    {"name": "Vitality", "desc": "Max HP +20", "type": "hp", "val": 20, "rare": "common"},
    {"name": "Regeneration", "desc": "HP Regen +1/s", "type": "reg", "val": 1, "rare": "rare"},
    {"name": "Critical Mash", "desc": "Crit Chance +10%", "type": "crit", "val": 0.1, "rare": "rare"},
    {"name": "Multi-Shot", "desc": "+1 Projectile", "type": "mult", "val": 1, "rare": "epic"},
    {"name": "Laser Eyes", "desc": "Piercing Shots", "type": "pierce", "val": 1, "rare": "epic"},
]

class Particle:
    def __init__(self, x, y, color, speed, size, life):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size *= 0.95

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        if len(self.color) == 3:
            color = self.color + (alpha,)
        else:
            color = self.color
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (int(self.size), int(self.size)), int(self.size))
        surface.blit(s, (self.x - self.size, self.y - self.size))

class Pickup:
    def __init__(self, x, y, ptype, amount=0):
        self.x = x
        self.y = y
        self.type = ptype
        self.amount = amount
        self.size = 15 if ptype == 'health' else 10
        self.life = 600
        self.bob = random.uniform(0, math.pi * 2)

    def update(self, player):
        self.bob += 0.05
        self.y += math.sin(self.bob) * 0.5

        d = distance(self.x, self.y, player.x, player.y)
        if d < 150:
            ang = angle_to(self.x, self.y, player.x, player.y)
            self.x += math.cos(ang) * 5
            self.y += math.sin(ang) * 5

        if d < player.size + self.size:
            self.collect(player)
            return True
        return False

    def collect(self, player):
        if self.type == 'xp':
            player.gain_xp(self.amount)
        elif self.type == 'coin':
            player.coins += 1
        elif self.type == 'health':
            player.heal(20)

    def draw(self, surface):
        if self.type == 'xp':
            color = CYAN
            points = [
                (self.x, self.y - self.size),
                (self.x + self.size, self.y),
                (self.x, self.y + self.size),
                (self.x - self.size, self.y)
            ]
            pygame.draw.polygon(surface, color, points)
        elif self.type == 'coin':
            color = YELLOW
            pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size // 2)
            text = font_small.render("$", True, BLACK)
            surface.blit(text, (self.x - 5, self.y - 8))
        else:
            color = RED
            pygame.draw.rect(surface, color, (self.x - self.size // 2, self.y - 2, self.size, 4))
            pygame.draw.rect(surface, color, (self.x - 2, self.y - self.size // 2, 4, self.size))

class Projectile:
    def __init__(self, x, y, angle, damage, speed, range_max, pierce=False):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.range = range_max
        self.traveled = 0
        self.size = 6
        self.pierce = pierce
        self.pierced = []
        self.dead = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.traveled += math.hypot(self.vx, self.vy)
        if self.traveled > self.range:
            self.dead = True
        if self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT:
            self.dead = True

    def draw(self, surface):
        color = ORANGE if self.pierce else YELLOW
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)

class EnemyProjectile:
    def __init__(self, x, y, angle, damage, speed):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.size = 5
        self.color = RED
        self.dead = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.dead = True

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.size)

class Enemy:
    def __init__(self, x, y, etype, wave):
        self.x = x
        self.y = y
        self.type = etype
        self.flash = 0
        self.died_from_damage = False

        base_stats = {
            'basic': {'hp': 30, 'spd': 2, 'dmg': 10, 'size': 20, 'color': RED, 'xp': 10},
            'fast':  {'hp': 15, 'spd': 4, 'dmg': 8,  'size': 15, 'color': ORANGE, 'xp': 20},
            'tank':  {'hp': 80, 'spd': 1, 'dmg': 20, 'size': 30, 'color': PURPLE, 'xp': 30},
            'ranged':{'hp': 25, 'spd': 1.5,'dmg':15, 'size': 18, 'color': GREEN, 'xp': 20},
            'shooter':{'hp': 20, 'spd': 1.0, 'dmg': 15, 'size': 18, 'color': GREEN, 'xp': 25},
            'aura':  {'hp': 100, 'spd': 0.5, 'dmg': 10, 'size': 30, 'color': AURA_PURPLE, 'xp': 50},
            'spawner':{'hp': 50, 'spd': 1.0, 'dmg': 10, 'size': 22, 'color': YELLOW, 'xp': 30},
            'minion': {'hp': 15, 'spd': 3.0, 'dmg': 8,  'size': 12, 'color': BLUE, 'xp': 5},
            'shielded':{'hp': 300, 'spd': 1.2, 'dmg': 20, 'size': 30, 'color': BLUE, 'xp': 100},
            'healer': {'hp': 1000, 'spd': 0.8, 'dmg': 10, 'size': 30, 'color': GREEN, 'xp': 150}
        }
        stats = base_stats.get(etype, base_stats['basic'])
        self.max_hp = stats['hp'] * (1 + wave * 0.1)
        self.hp = self.max_hp
        self.speed = stats['spd']
        self.damage = stats['dmg']
        self.size = stats['size']
        self.color = stats['color']
        self.xp_value = stats['xp']

        if self.type in ('shooter', 'minion'):
            self.shoot_cooldown = random.randint(0, 15 if self.type == 'minion' else 30)
            self.shoot_interval = 30 if self.type == 'minion' else 60
        else:
            self.shoot_cooldown = None

        if self.type == 'aura':
            self.aura_radius = 250
            self.aura_damage = 15
            self.aura_cooldown = 1000
            self.last_aura_hit = 0
        else:
            self.aura_radius = 0

        if self.type == 'healer':
            self.heal_radius = 500
            self.heal_amount = 10
            self.heal_cooldown = 0
            self.heal_interval = 30
        else:
            self.heal_radius = 0

        if self.type == 'shielded':
            self.shield_radii = [90, 70, 50]
            self.shield_thickness = 8
            self.shield_angles = [random.uniform(0, 2*math.pi) for _ in range(3)]
            self.shield_speeds = [0.05, 0.03, 0.01]
            self.shield_destroyed = [[] for _ in range(3)]
        else:
            self.shield_radii = []
            self.shield_thickness = 0
            self.shield_angles = []
            self.shield_speeds = []
            self.shield_destroyed = []

    def add_crack(self, shield_index, impact_angle, crack_width_px):
        local_angle = normalize_angle(impact_angle - self.shield_angles[shield_index])
        radius = self.shield_radii[shield_index]
        half_angle = (crack_width_px / 2) / radius
        start = normalize_angle(local_angle - half_angle)
        end = normalize_angle(local_angle + half_angle)
        destroyed = self.shield_destroyed[shield_index]
        destroyed.append((start, end))

    def check_shield_collision(self, bullet_x, bullet_y, bullet_size):
        dist = distance(self.x, self.y, bullet_x, bullet_y)
        impact_angle_world = normalize_angle(math.atan2(bullet_y - self.y, bullet_x - self.x))
        for i, radius in enumerate(self.shield_radii):
            if abs(dist - radius) <= self.shield_thickness / 2 + bullet_size / 2:
                local_angle = normalize_angle(impact_angle_world - self.shield_angles[i])
                destroyed = False
                for start, end in self.shield_destroyed[i]:
                    if start <= end:
                        if start <= local_angle <= end:
                            destroyed = True
                            break
                    else:
                        if local_angle >= start or local_angle <= end:
                            destroyed = True
                            break
                if not destroyed:
                    return False, i, impact_angle_world
                else:
                    continue
            elif dist < radius - self.shield_thickness/2:
                continue
        if len(self.shield_radii) > 0 and dist < self.shield_radii[-1] - self.shield_thickness/2:
            return True, None, None
        elif len(self.shield_radii) == 0:
            return True, None, None
        else:
            return False, None, None

    def update(self, player, current_time):
        ang = angle_to(self.x, self.y, player.x, player.y)
        self.x += math.cos(ang) * self.speed
        self.y += math.sin(ang) * self.speed

        if self.flash > 0:
            self.flash -= 1

        if self.type == 'aura':
            dist_to_player = distance(self.x, self.y, player.x, player.y)
            if dist_to_player < self.aura_radius:
                if current_time - self.last_aura_hit >= self.aura_cooldown:
                    player.take_damage(self.aura_damage)
                    self.last_aura_hit = current_time

        if self.type == 'shielded':
            for i in range(3):
                self.shield_angles[i] += self.shield_speeds[i]
                self.shield_angles[i] %= 2 * math.pi

    def heal_nearby(self, enemies, frame_count):
        if self.type != 'healer' or self.hp <= 0:
            return
        self.heal_cooldown += 1
        if self.heal_cooldown >= self.heal_interval:
            self.heal_cooldown = 0
            for other in enemies:
                if other is self or other.hp <= 0:
                    continue
                if distance(self.x, self.y, other.x, other.y) < self.heal_radius:
                    other.hp = min(other.max_hp, other.hp + self.heal_amount)

    def take_damage(self, dmg):
        self.hp -= dmg
        self.flash = 5
        hit_sound.play()
        if self.hp <= 0:
            self.died_from_damage = True

    def draw(self, surface):
        if self.type == 'aura':
            aura_surf = pygame.Surface((self.aura_radius*2, self.aura_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*self.color, 80), (self.aura_radius, self.aura_radius), self.aura_radius)
            surface.blit(aura_surf, (self.x - self.aura_radius, self.y - self.aura_radius))

        if self.type == 'healer':
            aura_surf = pygame.Surface((self.heal_radius*2, self.heal_radius*2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (*GREEN, 40), (self.heal_radius, self.heal_radius), self.heal_radius, 2)
            surface.blit(aura_surf, (self.x - self.heal_radius, self.y - self.heal_radius))

        if self.type == 'shielded':
            for i, radius in enumerate(self.shield_radii):
                destroyed = self.shield_destroyed[i]
                full = [(0, 2*math.pi)]
                remaining_local = self._subtract_intervals(full, destroyed)
                for start_local, end_local in remaining_local:
                    start_world = normalize_angle(start_local + self.shield_angles[i])
                    end_world = normalize_angle(end_local + self.shield_angles[i])
                    if start_world <= end_world:
                        pygame.draw.arc(surface, CYAN,
                                       (self.x - radius, self.y - radius, radius*2, radius*2),
                                       start_world, end_world, self.shield_thickness)
                    else:
                        pygame.draw.arc(surface, CYAN,
                                       (self.x - radius, self.y - radius, radius*2, radius*2),
                                       start_world, 2*math.pi, self.shield_thickness)
                        pygame.draw.arc(surface, CYAN,
                                       (self.x - radius, self.y - radius, radius*2, radius*2),
                                       0, end_world, self.shield_thickness)

        if self.flash > 0:
            draw_color = WHITE
        else:
            draw_color = self.color

        if self.type == 'tank':
            rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size*2, self.size*2)
            pygame.draw.rect(surface, draw_color, rect)
        elif self.type in ('fast', 'shooter', 'minion'):
            points = [
                (self.x + self.size, self.y),
                (self.x - self.size//2, self.y - self.size//2),
                (self.x - self.size//2, self.y + self.size//2)
            ]
            pygame.draw.polygon(surface, draw_color, points)
        elif self.type in ('shielded', 'healer'):
            rect = pygame.Rect(self.x - self.size, self.y - self.size, self.size*2, self.size*2)
            pygame.draw.rect(surface, draw_color, rect)
        else:
            pygame.draw.circle(surface, draw_color, (int(self.x), int(self.y)), self.size)

        if self.hp < self.max_hp:
            bar_width = 30
            bar_height = 4
            bar_x = self.x - bar_width // 2
            bar_y = self.y - self.size - 10
            pygame.draw.rect(surface, (50,0,0), (bar_x, bar_y, bar_width, bar_height))
            health_width = bar_width * (self.hp / self.max_hp)
            pygame.draw.rect(surface, RED, (bar_x, bar_y, health_width, bar_height))

    def _subtract_intervals(self, base, remove):
        base_nw = []
        for s, e in base:
            if s <= e:
                base_nw.append((s, e))
            else:
                base_nw.append((s, 2*math.pi))
                base_nw.append((0, e))
        remove_nw = []
        for s, e in remove:
            if s <= e:
                remove_nw.append((s, e))
            else:
                remove_nw.append((s, 2*math.pi))
                remove_nw.append((0, e))
        remove_nw.sort()
        result = []
        for start, end in base_nw:
            cur_start = start
            for r_start, r_end in remove_nw:
                if r_end <= cur_start:
                    continue
                if r_start >= end:
                    break
                if r_start > cur_start:
                    result.append((cur_start, r_start))
                cur_start = max(cur_start, r_end)
            if cur_start < end:
                result.append((cur_start, end))
        return result

class DamageText:
    def __init__(self, x, y, text, color=WHITE):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 60
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = -1.5

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / 60)
        surf = font_small.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, (self.x, self.y))

class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.size = 25
        self.angle = 0

        self.max_hp = 100
        self.hp = 100
        self.damage = 10
        self.speed = 5
        self.attack_speed = 1.0
        self.range = 200
        self.armor = 0
        self.crit_chance = 0
        self.projectiles = 1
        self.pierce = False
        self.regen = 0

        self.xp = 0
        self.level = 1
        self.xp_to_next = 100
        self.coins = 0

        self.last_shot = 0
        self.regen_timer = 0.0

        self.base_image = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.ellipse(self.base_image, BROWN, (5, 10, 40, 30))
        pygame.draw.circle(self.base_image, BLACK, (40, 20), 4)
        pygame.draw.circle(self.base_image, BLACK, (40, 40), 4)
        pygame.draw.rect(self.base_image, (100,100,100), (45, 23, 20, 6))
        pygame.draw.rect(self.base_image, (150,150,150), (60, 25, 6, 4))

    def move(self, keys_pressed):
        dx = 0
        dy = 0
        if keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP]:
            dy = -1
        if keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]:
            dy = 1
        if keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]:
            dx = -1
        if keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]:
            dx = 1

        if dx != 0 or dy != 0:
            mag = math.hypot(dx, dy)
            dx /= mag
            dy /= mag
            self.x += dx * self.speed
            self.y += dy * self.speed

        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.y = max(self.size, min(HEIGHT - self.size, self.y))

    def aim(self, mouse_x, mouse_y):
        self.angle = angle_to(self.x, self.y, mouse_x, mouse_y)

    def shoot(self, current_time):
        if current_time - self.last_shot < self.attack_speed * 1000:
            return []
        self.last_shot = current_time
        projs = []
        for i in range(self.projectiles):
            ang = self.angle
            if self.projectiles > 1:
                ang += (i - (self.projectiles - 1) / 2) * 0.2
            crit = random.random() < self.crit_chance
            dmg = self.damage * (2 if crit else 1)
            proj = Projectile(
                self.x + math.cos(ang) * 30,
                self.y + math.sin(ang) * 30,
                ang,
                dmg,
                10,
                self.range,
                self.pierce
            )
            projs.append(proj)
        shoot_sound.play()
        return projs

    def take_damage(self, dmg):
        actual = max(1, dmg - self.armor)
        self.hp -= actual
        if self.hp < 0:
            self.hp = 0

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)

    def gain_xp(self, amount):
        self.xp += amount

    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next
        self.xp_to_next = int(self.xp_to_next * 1.2)
        level_up_sound.play()

    def update_regen(self, dt):
        self.regen_timer += dt
        if self.regen_timer >= 1.0:
            self.regen_timer = 0
            self.hp = min(self.max_hp, self.hp + self.regen)

    def apply_upgrade(self, upgrade):
        typ = upgrade["type"]
        val = upgrade["val"]
        if typ == "dmg":
            self.damage *= (1 + val)
        elif typ == "spd":
            self.speed *= (1 + val)
        elif typ == "atk":
            self.attack_speed *= (1 - val)
        elif typ == "rng":
            self.range *= (1 + val)
        elif typ == "arm":
            self.armor += val
        elif typ == "hp":
            self.max_hp += val
            self.hp += val
        elif typ == "reg":
            self.regen += val
        elif typ == "crit":
            self.crit_chance += val
        elif typ == "mult":
            self.projectiles += val
        elif typ == "pierce":
            self.pierce = True

    def draw(self, surface):
        rotated = pygame.transform.rotate(self.base_image, -math.degrees(self.angle))
        rect = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect.topleft)

class CosmicSpud:
    def __init__(self):
        self.player = Player()
        self.enemies = []
        self.projectiles = []
        self.enemy_projectiles = []
        self.particles = []
        self.pickups = []
        self.damage_texts = []
        self.wave = 1
        self.kills = 0
        self.shake = 0
        self.state = "start"
        self.paused = False
        self.wave_timer = 0
        self.wave_duration = 1800
        self.spawn_timer = 0
        self.upgrade_choices = []
        self.mouse_pos = (WIDTH//2, HEIGHT//2)
        self.keys_pressed = pygame.key.get_pressed()
        self.frame_count = 0

    def start(self):
        self.state = "playing"

    def spawn_enemy(self):
        side = random.choice(['left','right','top','bottom'])
        if side == 'left':
            x = -50
            y = random.uniform(0, HEIGHT)
        elif side == 'right':
            x = WIDTH + 50
            y = random.uniform(0, HEIGHT)
        elif side == 'top':
            x = random.uniform(0, WIDTH)
            y = -50
        else:
            x = random.uniform(0, WIDTH)
            y = HEIGHT + 50

        types = ['basic', 'basic', 'fast']
        if self.wave > 2:
            types.append('tank')
        if self.wave > 3:
            types.append('shooter')
        if self.wave > 4:
            types.append('ranged')
        if self.wave > 5:
            types.append('aura')
        if self.wave > 6:
            types.append('spawner')
        if self.wave > 7:
            types.append('shielded')
        if self.wave > 8:
            types.append('healer')
        etype = random.choice(types)
        self.enemies.append(Enemy(x, y, etype, self.wave))

    def spawn_particles(self, x, y, color, count, size=4, life=30):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, rand(2,5), rand(2,size), life))

    def spawn_damage_text(self, x, y, text, color=WHITE):
        self.damage_texts.append(DamageText(x, y, text, color))

    def kill_enemy(self, enemy):
        self.kills += 1
        self.pickups.append(Pickup(enemy.x, enemy.y, 'xp', amount=enemy.xp_value))
        if random.random() < 0.1:
            self.pickups.append(Pickup(enemy.x, enemy.y, random.choice(['health','coin'])))
        self.spawn_particles(enemy.x, enemy.y, enemy.color, 8, 4, 30)
        kill_sound.play()

        if enemy.type == 'spawner':
            for offset in [-20, 20]:
                minion = Enemy(enemy.x + offset, enemy.y + offset, 'minion', self.wave)
                self.enemies.append(minion)

    def enter_level_up(self):
        self.paused = True
        self.state = "level_up"
        self.upgrade_choices = random.sample(UPGRADES, 4)

    def apply_separation(self):
        separation_distance = 100
        strength = 0.5
        for i, e1 in enumerate(self.enemies):
            dx_total = 0
            dy_total = 0
            count = 0
            for j, e2 in enumerate(self.enemies):
                if i == j:
                    continue
                dx = e1.x - e2.x
                dy = e1.y - e2.y
                dist = math.hypot(dx, dy)
                if 0 < dist < separation_distance:
                    force = (separation_distance - dist) / separation_distance
                    dx_total += (dx / dist) * force
                    dy_total += (dy / dist) * force
                    count += 1
            if count > 0:
                e1.x += dx_total * strength
                e1.y += dy_total * strength
                e1.x = max(e1.size, min(WIDTH - e1.size, e1.x))
                e1.y = max(e1.size, min(HEIGHT - e1.size, e1.y))

        for e in self.enemies:
            e.x += random.uniform(-0.3, 0.3)
            e.y += random.uniform(-0.3, 0.3)
            e.x = max(e.size, min(WIDTH - e.size, e.x))
            e.y = max(e.size, min(HEIGHT - e.size, e.y))

    def update(self):
        if self.state == "playing" and not self.paused:
            dt = clock.get_time() / 1000.0
            current_time = pygame.time.get_ticks()
            self.frame_count += 1

            self.player.move(self.keys_pressed)
            self.player.aim(*self.mouse_pos)
            self.player.update_regen(dt)

            new_projs = self.player.shoot(current_time)
            self.projectiles.extend(new_projs)

            self.wave_timer += 1
            self.spawn_timer += 1
            spawn_rate = max(30, 120 - self.wave * 10)
            if self.spawn_timer > spawn_rate and self.wave_timer < self.wave_duration:
                self.spawn_enemy()
                self.spawn_timer = 0

            if self.wave_timer > self.wave_duration + 300 and len(self.enemies) == 0:
                self.wave += 1
                self.wave_timer = 0
                self.player.heal(20)
                wave_win_sound.play()

            for enemy in self.enemies:
                enemy.update(self.player, current_time)

            for enemy in self.enemies:
                if enemy.type == 'healer':
                    enemy.heal_nearby(self.enemies, self.frame_count)

            self.apply_separation()

            for proj in self.projectiles[:]:
                proj.update()
                if proj.dead:
                    self.projectiles.remove(proj)
                    continue

                for enemy in self.enemies:
                    if enemy.type == 'shielded' and not proj.dead:
                        hit_enemy, shield_idx, impact_angle = enemy.check_shield_collision(proj.x, proj.y, proj.size)
                        if shield_idx is not None:
                            enemy.add_crack(shield_idx, impact_angle, proj.size)
                            proj.dead = True
                            self.spawn_particles(proj.x, proj.y, CYAN, 5, 3, 15)
                            break
                        elif hit_enemy:
                            pass

                if not proj.dead:
                    for enemy in self.enemies[:]:
                        if proj.dead or enemy in proj.pierced:
                            continue
                        if distance(proj.x, proj.y, enemy.x, enemy.y) < enemy.size + proj.size:
                            enemy.take_damage(proj.damage)
                            self.spawn_damage_text(enemy.x, enemy.y - 20, str(int(proj.damage)), YELLOW)
                            if proj.damage > self.player.damage:
                                self.spawn_damage_text(enemy.x, enemy.y - 40, "CRIT!", ORANGE)
                            if proj.pierce:
                                proj.pierced.append(enemy)
                            else:
                                proj.dead = True
                                self.spawn_particles(proj.x, proj.y, YELLOW, 3, 3, 20)
                                break

            for enemy in self.enemies:
                if hasattr(enemy, 'shoot_cooldown') and enemy.shoot_cooldown is not None:
                    enemy.shoot_cooldown += 1
                    if enemy.shoot_cooldown >= enemy.shoot_interval:
                        enemy.shoot_cooldown = 0
                        ang = angle_to(enemy.x, enemy.y, self.player.x, self.player.y)
                        e_proj = EnemyProjectile(enemy.x, enemy.y, ang, enemy.damage, 5)
                        self.enemy_projectiles.append(e_proj)

            for e_proj in self.enemy_projectiles[:]:
                e_proj.update()
                if e_proj.dead:
                    self.enemy_projectiles.remove(e_proj)
                    continue
                if distance(e_proj.x, e_proj.y, self.player.x, self.player.y) < self.player.size + e_proj.size:
                    self.player.take_damage(e_proj.damage)
                    self.spawn_damage_text(self.player.x, self.player.y - 30, str(e_proj.damage), RED)
                    self.spawn_particles(e_proj.x, e_proj.y, RED, 5, 3, 15)
                    self.enemy_projectiles.remove(e_proj)

            dead_enemies = [e for e in self.enemies if e.hp <= 0 and e.died_from_damage]
            for enemy in dead_enemies:
                self.kill_enemy(enemy)
                self.enemies.remove(enemy)

            for enemy in self.enemies:
                if enemy.type == 'shielded':
                    for radius in enemy.shield_radii:
                        dist = distance(self.player.x, self.player.y, enemy.x, enemy.y)
                        if dist < radius + self.player.size:
                            ang = angle_to(enemy.x, enemy.y, self.player.x, self.player.y)
                            push_dist = radius + self.player.size - dist
                            self.player.x += math.cos(ang) * push_dist
                            self.player.y += math.sin(ang) * push_dist
                            self.player.x = max(self.player.size, min(WIDTH - self.player.size, self.player.x))
                            self.player.y = max(self.player.size, min(HEIGHT - self.player.size, self.player.y))

                if distance(self.player.x, self.player.y, enemy.x, enemy.y) < self.player.size + enemy.size:
                    self.player.take_damage(enemy.hp)
                    self.spawn_damage_text(self.player.x, self.player.y - 30, str(int(enemy.hp)), RED)
                    enemy.hp = 0
                    enemy.died_from_damage = True

            for pickup in self.pickups[:]:
                if pickup.update(self.player):
                    self.pickups.remove(pickup)

            for p in self.particles[:]:
                p.update()
                if p.life <= 0:
                    self.particles.remove(p)

            for dtxt in self.damage_texts[:]:
                dtxt.update()
                if dtxt.life <= 0:
                    self.damage_texts.remove(dtxt)

            if self.shake > 0:
                self.shake *= 0.9
                if self.shake < 0.5:
                    self.shake = 0

            if self.player.xp >= self.player.xp_to_next:
                self.player.level_up()
                self.enter_level_up()

            if self.player.hp <= 0:
                self.state = "game_over"
                game_over_sound.play()

    def draw(self):
        if self.shake > 0:
            offset_x = random.uniform(-self.shake, self.shake)
            offset_y = random.uniform(-self.shake, self.shake)
            view = screen.get_rect().move(offset_x, offset_y)
            screen.set_clip(view)
        else:
            screen.set_clip(None)

        screen.fill(DARK_GREY)
        for x in range(0, WIDTH, 50):
            pygame.draw.line(screen, (50,50,70), (x,0), (x,HEIGHT), 1)
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(screen, (50,50,70), (0,y), (WIDTH,y), 1)

        for pickup in self.pickups:
            pickup.draw(screen)
        for p in self.particles:
            p.draw(screen)
        for proj in self.projectiles:
            proj.draw(screen)
        for e_proj in self.enemy_projectiles:
            e_proj.draw(screen)
        for enemy in self.enemies:
            enemy.draw(screen)
        self.player.draw(screen)
        for dtxt in self.damage_texts:
            dtxt.draw(screen)

        screen.set_clip(None)
        self.draw_ui()

    def draw_ui(self):
        bar_x, bar_y = 20, 20
        bar_width, bar_height = 200, 20
        pygame.draw.rect(screen, (50,0,0), (bar_x, bar_y, bar_width, bar_height))
        health_ratio = self.player.hp / self.player.max_hp
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width * health_ratio, bar_height))

        xp_y = bar_y + bar_height + 5
        pygame.draw.rect(screen, (0,20,40), (bar_x, xp_y, bar_width, 10))
        xp_ratio = self.player.xp / self.player.xp_to_next
        pygame.draw.rect(screen, CYAN, (bar_x, xp_y, bar_width * xp_ratio, 10))

        xp_text = font_small.render(f"XP: {int(self.player.xp)}/{self.player.xp_to_next}", True, WHITE)
        screen.blit(xp_text, (bar_x + bar_width + 10, xp_y - 2))

        level_text = font_small.render(f"Level {self.player.level}", True, WHITE)
        screen.blit(level_text, (bar_x + bar_width + 10, bar_y))

        stats_x = WIDTH - 220
        stats_y = 20
        stats_width = 200
        stats_height = 160
        pygame.draw.rect(screen, (0,0,0,128), (stats_x, stats_y, stats_width, stats_height))
        pygame.draw.rect(screen, WHITE, (stats_x, stats_y, stats_width, stats_height), 2)

        hp_text = font_small.render(f"HP: {self.player.hp:.0f}/{self.player.max_hp:.0f}", True, WHITE)
        dmg = font_small.render(f"DMG: {self.player.damage:.1f}", True, WHITE)
        spd = font_small.render(f"SPD: {self.player.speed:.1f}", True, WHITE)
        atk = font_small.render(f"ATK: {self.player.attack_speed:.2f}s", True, WHITE)
        rng = font_small.render(f"RNG: {self.player.range:.0f}", True, WHITE)
        crit = font_small.render(f"CRIT: {self.player.crit_chance*100:.0f}%", True, WHITE)

        screen.blit(hp_text, (stats_x+10, stats_y+10))
        screen.blit(dmg, (stats_x+10, stats_y+30))
        screen.blit(spd, (stats_x+10, stats_y+50))
        screen.blit(atk, (stats_x+10, stats_y+70))
        screen.blit(rng, (stats_x+10, stats_y+90))
        screen.blit(crit, (stats_x+10, stats_y+110))

        wave_text = font_large.render(f"WAVE {self.wave}", True, YELLOW)
        wave_rect = wave_text.get_rect(center=(WIDTH//2, 50))
        screen.blit(wave_text, wave_rect)
        enemy_count = font_medium.render(f"Enemies: {len(self.enemies)}", True, WHITE)
        screen.blit(enemy_count, (WIDTH//2 - 50, 90))

        if self.wave_timer < 60:
            warn = font_large.render("WAVE INCOMING!", True, RED)
            warn_rect = warn.get_rect(center=(WIDTH//2, HEIGHT//2))
            screen.blit(warn, warn_rect)

    def draw_start_screen(self):
        screen.fill(DARK_GREY)
        title = font_large.render("COSMIC SPUD", True, YELLOW)
        title_rect = title.get_rect(center=(WIDTH//2, HEIGHT//2 - 100))
        screen.blit(title, title_rect)
        subtitle = font_medium.render("Click to Start", True, WHITE)
        subtitle_rect = subtitle.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(subtitle, subtitle_rect)
        controls = font_small.render("WASD/Arrows: Move | Mouse: Aim | Auto-shoot", True, LIGHT_GREY)
        controls_rect = controls.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
        screen.blit(controls, controls_rect)

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        screen.blit(overlay, (0,0))
        go = font_large.render("GAME OVER", True, RED)
        go_rect = go.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
        screen.blit(go, go_rect)
        wave_t = font_medium.render(f"Wave Reached: {self.wave}", True, WHITE)
        wave_rect = wave_t.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen.blit(wave_t, wave_rect)
        kills_t = font_medium.render(f"Enemies Defeated: {self.kills}", True, WHITE)
        kills_rect = kills_t.get_rect(center=(WIDTH//2, HEIGHT//2 + 30))
        screen.blit(kills_t, kills_rect)
        restart = font_medium.render("Press R to Restart", True, CYAN)
        restart_rect = restart.get_rect(center=(WIDTH//2, HEIGHT//2 + 80))
        screen.blit(restart, restart_rect)

    def draw_level_up(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,200))
        screen.blit(overlay, (0,0))

        modal_w, modal_h = 600, 400
        modal_x = (WIDTH - modal_w) // 2
        modal_y = (HEIGHT - modal_h) // 2
        pygame.draw.rect(screen, (30,30,40), (modal_x, modal_y, modal_w, modal_h))
        pygame.draw.rect(screen, WHITE, (modal_x, modal_y, modal_w, modal_h), 3)

        title = font_large.render("LEVEL UP!", True, YELLOW)
        title_rect = title.get_rect(center=(WIDTH//2, modal_y + 50))
        screen.blit(title, title_rect)

        card_w, card_h = 250, 100
        for i, upg in enumerate(self.upgrade_choices):
            col = i % 2
            row = i // 2
            card_x = modal_x + 50 + col * (card_w + 20)
            card_y = modal_y + 120 + row * (card_h + 20)
            if upg['rare'] == 'common':
                bg = (50,50,70)
            elif upg['rare'] == 'rare':
                bg = (80,50,100)
            else:
                bg = (100,50,30)
            pygame.draw.rect(screen, bg, (card_x, card_y, card_w, card_h))
            pygame.draw.rect(screen, WHITE, (card_x, card_y, card_w, card_h), 2)
            name = font_medium.render(upg['name'], True, YELLOW)
            desc = font_small.render(upg['desc'], True, WHITE)
            screen.blit(name, (card_x + 10, card_y + 10))
            screen.blit(desc, (card_x + 10, card_y + 40))
            upg['rect'] = pygame.Rect(card_x, card_y, card_w, card_h)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if self.state == "game_over" and event.key == pygame.K_r:
                    self.__init__()
                    self.state = "playing"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "start":
                    self.start()
                elif self.state == "level_up":
                    mouse = pygame.mouse.get_pos()
                    for upg in self.upgrade_choices:
                        if upg.get('rect') and upg['rect'].collidepoint(mouse):
                            self.player.apply_upgrade(upg)
                            self.state = "playing"
                            self.paused = False
                            break
        return True

    def run(self):
        running = True
        while running:
            self.keys_pressed = pygame.key.get_pressed()
            self.mouse_pos = pygame.mouse.get_pos()
            running = self.handle_events()

            if self.state == "playing":
                self.update()
                self.draw()
            elif self.state == "start":
                self.draw_start_screen()
            elif self.state == "level_up":
                self.draw()
                self.draw_level_up()
            elif self.state == "game_over":
                self.draw()
                self.draw_game_over()

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = CosmicSpud()
    game.run()
