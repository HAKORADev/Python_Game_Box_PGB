import pygame
import sys
import random
import numpy as np
import math
import pymunk
import pyganim
from pygame.math import Vector2

pygame.init()
pygame.mixer.init()

WIDTH = 800
HEIGHT = 600
cell_size = 20
cols = WIDTH // cell_size
rows = HEIGHT // cell_size
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Snake Game")
clock = pygame.time.Clock()

space = pymunk.Space()
space.gravity = (0, 0)

base_speed = 150
glow_radius = 6

def create_sound(freq=440, waveform='sine', dur=0.1):
    sample_rate = 44100
    t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False)
    if waveform == 'square':
        wave = np.sign(np.sin(2 * np.pi * freq * t))
    elif waveform == 'sawtooth':
        wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    else:
        wave = np.sin(2 * np.pi * freq * t)
    sound_array = np.int16(wave * 32767 * 0.3)
    sound_array = np.reshape(sound_array, (-1, 1))
    channels = pygame.mixer.get_init()[2]
    final_array = np.repeat(sound_array, channels, axis=1) if channels > 1 else sound_array
    return pygame.sndarray.make_sound(final_array)

eat_sound = create_sound(880, 'square', 0.08)
gameover_sound = create_sound(220, 'sine', 0.5)
collision_sound = create_sound(110, 'sine', 0.5)
death_sound = create_sound(180, 'sine', 0.3)

def create_food_anim():
    frames = []
    for scale in (0.9, 1.0, 1.1, 1.0):
        size = int(cell_size * scale)
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255, 100, 100), (0, 0, size, size))
        frames.append((surf, 100))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

def reset_game(mode, ai_level=1):
    if mode == 1:
        snake1 = [Vector2(cols // 2, rows // 2),
                  Vector2(cols // 2 - 1, rows // 2),
                  Vector2(cols // 2 - 2, rows // 2)]
        direction1 = Vector2(1, 0)
        snake2 = []
        direction2 = Vector2(0, 0)
        snake_ai = []
        direction_ai = Vector2(0, 0)
    elif mode == 2:
        snake1 = [Vector2(cols // 3, rows // 2),
                  Vector2(cols // 3 - 1, rows // 2),
                  Vector2(cols // 3 - 2, rows // 2)]
        direction1 = Vector2(1, 0)
        snake2 = [Vector2(2 * cols // 3, rows // 2),
                  Vector2(2 * cols // 3 - 1, rows // 2),
                  Vector2(2 * cols // 3 - 2, rows // 2)]
        direction2 = Vector2(1, 0)
        snake_ai = []
        direction_ai = Vector2(0, 0)
    else:
        snake1 = [Vector2(cols // 4, rows // 2),
                  Vector2(cols // 4 - 1, rows // 2),
                  Vector2(cols // 4 - 2, rows // 2)]
        direction1 = Vector2(1, 0)
        snake2 = []
        direction2 = Vector2(0, 0)
        snake_ai = [Vector2(3 * cols // 4, rows // 2),
                    Vector2(3 * cols // 4 + 1, rows // 2),
                    Vector2(3 * cols // 4 + 2, rows // 2)]
        direction_ai = Vector2(-1, 0)

    food = spawn_food(snake1 + snake2 + snake_ai)
    obstacles = []
    score1, score2, score_ai = 0, 0, 0
    return snake1, direction1, snake2, direction2, snake_ai, direction_ai, food, obstacles, score1, score2, score_ai, ai_level

def spawn_food(snakes):
    while True:
        pos = Vector2(random.randint(0, cols - 1), random.randint(0, rows - 1))
        if (pos.x, pos.y) not in [(s.x, s.y) for s in snakes]:
            return pos

def spawn_obstacles(snakes):
    obstacles = []
    count = random.randint(1, 5)
    for _ in range(count):
        while True:
            pos = Vector2(random.randint(0, cols - 1), random.randint(0, rows - 1))
            if ((pos.x, pos.y) not in ((s.x, s.y) for s in snakes) and
                all(pos != o['pos'] for o in obstacles)):
                obstacles.append({
                    'pos': pos,
                    'spawn_time': pygame.time.get_ticks(),
                    'duration': random.randint(2000, 4000)
                })
                break
    return obstacles

def game_over_screen(score1, score2, score_ai, mode):
    font = pygame.font.SysFont("Arial", 36)
    if mode == 3:
        msg_text = f"Game Over! Scores: Player {score1} - AI {score_ai}"
    elif mode == 2:
        msg_text = f"Game Over! Scores: {score1} & {score2}"
    else:
        msg_text = f"Game Over! Score: {score1}"

    msg = font.render(msg_text, True, (255, 0, 0))
    sub = font.render("Press any key to restart", True, (255, 255, 255))

    while True:
        screen.fill((0, 0, 0))
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - msg.get_height()))
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 20))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                return

particles = []
def spawn_particles(pos, color, count, lifetime):
    for _ in range(count):
        particles.append({
            'pos': Vector2(pos),
            'vel': Vector2(random.uniform(-3, 3), random.uniform(-3, 3)),
            'lifetime': lifetime,
            'age': 0,
            'color': color
        })

def update_particles(dt):
    for p in particles[:]:
        p['age'] += dt
        p['pos'] += p['vel']
        if p['age'] >= p['lifetime']:
            particles.remove(p)

def draw_particles(surface):
    for p in particles:
        alpha = 255 * (1 - p['age'] / p['lifetime'])
        surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        surf.fill(list(p['color']) + [int(alpha)])
        surface.blit(surf, (p['pos'].x, p['pos'].y))

ripples = []
def spawn_ripple(pos, max_radius, lifetime):
    ripples.append({'pos': Vector2(pos), 'radius': 0, 'max': max_radius, 'lifetime': lifetime, 'age': 0})

def update_ripples(dt):
    for r in ripples[:]:
        r['age'] += dt
        r['radius'] = r['max'] * (r['age'] / r['lifetime'])
        if r['age'] >= r['lifetime']:
            ripples.remove(r)

def draw_ripples(surface):
    for r in ripples:
        alpha = int(255 * (1 - r['age'] / r['lifetime']))
        s = pygame.Surface((r['max'] * 2, r['max'] * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 255, 255, alpha), (r['max'], r['max']), int(r['radius']), 3)
        surface.blit(s, (r['pos'].x - r['max'], r['pos'].y - r['max']))

def draw_grid():
    for x in range(0, WIDTH, cell_size):
        pygame.draw.line(screen, (50, 50, 50), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, cell_size):
        pygame.draw.line(screen, (50, 50, 50), (0, y), (WIDTH, y))

def draw_background(surface):
    t = pygame.time.get_ticks() / 1000
    for y in range(HEIGHT):
        factor = y / HEIGHT
        r = int(20 + 10 * (1 + math.sin(t + factor * math.pi)))
        g = int(20 + 10 * (1 + math.sin(t + factor * math.pi + 2)))
        b = int(20 + 10 * (1 + math.sin(t + factor * math.pi + 4)))
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

def create_glowing_rect(size, color, glow):
    surf = pygame.Surface((size + 2 * glow, size + 2 * glow), pygame.SRCALPHA)
    for i in range(glow, 0, -1):
        alpha = int(255 * (1 - i / glow) * 0.5)
        pygame.draw.rect(surf, list(color) + [alpha],
                         (glow - i, glow - i, size + 2 * i, size + 2 * i), border_radius=8)
    pygame.draw.rect(surf, color, (glow, glow, size, size), border_radius=8)
    return surf

def ai_menu():
    font = pygame.font.SysFont("Arial", 48)
    title = font.render("SELECT AI LEVEL", True, (0, 100, 255))
    easy = font.render("1 - Easy", True, (255, 255, 255))
    medium = font.render("2 - Medium", True, (255, 255, 255))
    hard = font.render("3 - Hard", True, (255, 255, 255))

    while True:
        draw_background(screen)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        screen.blit(easy, (WIDTH // 2 - easy.get_width() // 2, 200))
        screen.blit(medium, (WIDTH // 2 - medium.get_width() // 2, 300))
        screen.blit(hard, (WIDTH // 2 - hard.get_width() // 2, 400))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: return 1
                if event.key == pygame.K_2: return 2
                if event.key == pygame.K_3: return 3

def main_menu():
    font = pygame.font.SysFont("Arial", 48)
    title = font.render("SNAKE GAME", True, (0, 255, 0))
    single = font.render("1 - Single Player", True, (255, 255, 255))
    multi = font.render("2 - Two Players", True, (255, 255, 255))
    ai = font.render("3 - VS AI", True, (0, 100, 255))

    while True:
        draw_background(screen)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        screen.blit(single, (WIDTH // 2 - single.get_width() // 2, 200))
        screen.blit(multi, (WIDTH // 2 - multi.get_width() // 2, 300))
        screen.blit(ai, (WIDTH // 2 - ai.get_width() // 2, 400))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1: return 1
                if event.key == pygame.K_2: return 2
                if event.key == pygame.K_3:
                    ai_level = ai_menu()
                    return (3, ai_level)

def a_star(start, end, snake, obstacles, advanced=False):
    open_set = [start]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, end)}

    while open_set:
        current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
        if current == end:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            return path[::-1]

        open_set.remove(current)
        for neighbor in get_neighbors(current):
            if neighbor[0] < 0 or neighbor[0] >= cols or neighbor[1] < 0 or neighbor[1] >= rows:
                continue
            if neighbor in snake or neighbor in obstacles:
                continue

            tentative_g = g_score[current] + 1
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, end) * (0.3 if advanced else 1)
                if neighbor not in open_set:
                    open_set.append(neighbor)
    return None

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def get_neighbors(pos):
    return [(pos[0]+1, pos[1]), (pos[0]-1, pos[1]), (pos[0], pos[1]+1), (pos[0], pos[1]-1)]

def ai_move(snake, food, obstacles, level, direction):
    current_pos = (int(snake[0].x), int(snake[0].y))
    food_pos = (int(food.x), int(food.y))
    snake_positions = [(int(s.x), int(s.y)) for s in snake]
    obstacle_positions = [tuple(o['pos']) for o in obstacles]

    possible_directions = [Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1)]
    valid_directions = []
    for d in possible_directions:
        new_head = snake[0] + d
        new_head_tuple = (int(new_head.x), int(new_head.y))
        if 0 <= new_head.x < cols and 0 <= new_head.y < rows:
            if new_head_tuple not in snake_positions and new_head_tuple not in obstacle_positions:
                if new_head_tuple not in [(int(s.x), int(s.y)) for s in snake1]:
                    valid_directions.append(d)

    if not valid_directions:
        return direction

    if level == 1:
        return random.choice(valid_directions)

    path = a_star(current_pos, food_pos, snake_positions, obstacle_positions, level == 3)
    if path and len(path) > 1:
        next_step = Vector2(path[1][0] - current_pos[0], path[1][1] - current_pos[1])
        if next_step in valid_directions:
            return next_step

    return min(valid_directions, key=lambda d: (snake[0] + d - food).length())

mode_data = main_menu()
if isinstance(mode_data, tuple):
    mode, ai_level = mode_data
else:
    mode, ai_level = mode_data, 1

snake1, direction1, snake2, direction2, snake_ai, direction_ai, food, obstacles, score1, score2, score_ai, ai_level = reset_game(mode, ai_level)

snake1_old = [s.copy() for s in snake1]
snake2_old = [s.copy() for s in snake2] if snake2 else []
snake_ai_old = [s.copy() for s in snake_ai] if snake_ai else []

game_over1, game_over2, game_over_ai = False, False, False
move_delay1, move_delay2, move_delay_ai = base_speed, base_speed, base_speed
last_move_time1 = pygame.time.get_ticks()
last_move_time2 = pygame.time.get_ticks()
last_move_time_ai = pygame.time.get_ticks()
obstacle_timer = pygame.time.get_ticks()

snake1_img = create_glowing_rect(cell_size, (0, 255, 0), glow_radius)
snake2_img = create_glowing_rect(cell_size, (255, 255, 0), glow_radius)
snake_ai_img = create_glowing_rect(cell_size, (0, 100, 255), glow_radius)
food_anim = create_food_anim()

while True:
    dt = clock.tick(60)
    current_time = pygame.time.get_ticks()

    space.step(dt / 1000.0)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and direction1.y != 1:
                direction1 = Vector2(0, -1)
            if event.key == pygame.K_DOWN and direction1.y != -1:
                direction1 = Vector2(0, 1)
            if event.key == pygame.K_LEFT and direction1.x != 1:
                direction1 = Vector2(-1, 0)
            if event.key == pygame.K_RIGHT and direction1.x != -1:
                direction1 = Vector2(1, 0)

            if mode == 2:
                if event.key == pygame.K_w and direction2.y != 1:
                    direction2 = Vector2(0, -1)
                if event.key == pygame.K_s and direction2.y != -1:
                    direction2 = Vector2(0, 1)
                if event.key == pygame.K_a and direction2.x != 1:
                    direction2 = Vector2(-1, 0)
                if event.key == pygame.K_d and direction2.x != -1:
                    direction2 = Vector2(1, 0)

    obstacles = [o for o in obstacles if current_time - o['spawn_time'] < o['duration']]

    if current_time - obstacle_timer > 5000:
        obstacles.extend(spawn_obstacles(snake1 + snake2 + snake_ai))
        obstacle_timer = current_time

    if not game_over1 and current_time - last_move_time1 > move_delay1:
        snake1_old = [s.copy() for s in snake1]
        new_head = snake1[0] + direction1

        collision = (new_head.x < 0 or new_head.x >= cols or
                     new_head.y < 0 or new_head.y >= rows or
                     (new_head.x, new_head.y) in [(s.x, s.y) for s in snake1] or
                     any(new_head == o['pos'] for o in obstacles) or
                     (mode == 2 and (new_head.x, new_head.y) in [(s.x, s.y) for s in snake2]) or
                     (mode == 3 and (new_head.x, new_head.y) in [(s.x, s.y) for s in snake_ai]))

        if collision:
            game_over1 = True
            death_sound.play()
            spawn_particles(snake1[0] * cell_size + Vector2(cell_size/2, cell_size/2),
                            (255, 0, 0), 50, 1.0)
        else:
            snake1.insert(0, new_head)
            if new_head == food:
                score1 += 1
                eat_sound.play()
                spawn_particles(food * cell_size + Vector2(cell_size/2, cell_size/2),
                                (255, 255, 0), 30, 0.5)
                spawn_ripple(food * cell_size + Vector2(cell_size/2, cell_size/2),
                             cell_size * 3, 0.5)
                food = spawn_food(snake1 + snake2 + snake_ai)
                obstacles.extend(spawn_obstacles(snake1 + snake2 + snake_ai))
                if score1 % 10 == 0:
                    move_delay1 = max(50, int(move_delay1 * 0.9))
            else:
                snake1.pop()
        last_move_time1 = current_time

    if mode == 2 and not game_over2 and current_time - last_move_time2 > move_delay2:
        snake2_old = [s.copy() for s in snake2]
        new_head = snake2[0] + direction2

        collision = (new_head.x < 0 or new_head.x >= cols or
                     new_head.y < 0 or new_head.y >= rows or
                     (new_head.x, new_head.y) in [(s.x, s.y) for s in snake2] or
                     any(new_head == o['pos'] for o in obstacles) or
                     (new_head.x, new_head.y) in [(s.x, s.y) for s in snake1])

        if collision:
            game_over2 = True
            death_sound.play()
            spawn_particles(snake2[0] * cell_size + Vector2(cell_size/2, cell_size/2),
                            (255, 0, 0), 50, 1.0)
        else:
            snake2.insert(0, new_head)
            if new_head == food:
                score2 += 1
                eat_sound.play()
                spawn_particles(food * cell_size + Vector2(cell_size/2, cell_size/2),
                                (255, 255, 0), 30, 0.5)
                spawn_ripple(food * cell_size + Vector2(cell_size/2, cell_size/2),
                             cell_size * 3, 0.5)
                food = spawn_food(snake1 + snake2 + snake_ai)
                obstacles.extend(spawn_obstacles(snake1 + snake2 + snake_ai))
                if score2 % 10 == 0:
                    move_delay2 = max(50, int(move_delay2 * 0.9))
            else:
                snake2.pop()
        last_move_time2 = current_time

    if mode == 3 and not game_over_ai and current_time - last_move_time_ai > move_delay_ai:
        snake_ai_old = [s.copy() for s in snake_ai]
        direction_ai = ai_move(snake_ai, food, obstacles, ai_level, direction_ai)
        new_head = snake_ai[0] + direction_ai

        collision = (new_head.x < 0 or new_head.x >= cols or
                     new_head.y < 0 or new_head.y >= rows or
                     (new_head.x, new_head.y) in [(s.x, s.y) for s in snake_ai] or
                     any(new_head == o['pos'] for o in obstacles) or
                     (new_head.x, new_head.y) in [(s.x, s.y) for s in snake1])

        if collision:
            game_over_ai = True
            death_sound.play()
            spawn_particles(snake_ai[0] * cell_size + Vector2(cell_size/2, cell_size/2),
                            (255, 0, 0), 50, 1.0)
        else:
            snake_ai.insert(0, new_head)
            if new_head == food:
                score_ai += 1
                eat_sound.play()
                spawn_particles(food * cell_size + Vector2(cell_size/2, cell_size/2),
                                (255, 255, 0), 30, 0.5)
                spawn_ripple(food * cell_size + Vector2(cell_size/2, cell_size/2),
                             cell_size * 3, 0.5)
                food = spawn_food(snake1 + snake2 + snake_ai)
                obstacles.extend(spawn_obstacles(snake1 + snake2 + snake_ai))
                if score_ai % 10 == 0:
                    move_delay_ai = max(50, int(move_delay_ai * 0.9))
            else:
                snake_ai.pop()
        last_move_time_ai = current_time

    draw_background(screen)
    draw_grid()

    for i, pos in enumerate(snake1):
        target_pos = pos * cell_size
        if i < len(snake1_old):
            start_pos = snake1_old[i] * cell_size
            interp = min((current_time - last_move_time1) / move_delay1, 1)
            interp_pos = start_pos.lerp(target_pos, interp)
        else:
            interp_pos = target_pos
        screen.blit(snake1_img, (interp_pos.x - glow_radius, interp_pos.y - glow_radius))

    if mode == 2:
        for i, pos in enumerate(snake2):
            target_pos = pos * cell_size
            if i < len(snake2_old):
                start_pos = snake2_old[i] * cell_size
                interp = min((current_time - last_move_time2) / move_delay2, 1)
                interp_pos = start_pos.lerp(target_pos, interp)
            else:
                interp_pos = target_pos
            screen.blit(snake2_img, (interp_pos.x - glow_radius, interp_pos.y - glow_radius))

    if mode == 3:
        for i, pos in enumerate(snake_ai):
            target_pos = pos * cell_size
            if i < len(snake_ai_old):
                start_pos = snake_ai_old[i] * cell_size
                interp = min((current_time - last_move_time_ai) / move_delay_ai, 1)
                interp_pos = start_pos.lerp(target_pos, interp)
            else:
                interp_pos = target_pos
            screen.blit(snake_ai_img, (interp_pos.x - glow_radius, interp_pos.y - glow_radius))

    food_rect = pygame.Rect(food.x * cell_size, food.y * cell_size, cell_size, cell_size)
    food_anim.blit(screen, food_rect.topleft)

    for obstacle in obstacles:
        scale = 0.8 + 0.2 * math.sin(current_time / 200 + (obstacle['spawn_time'] % 100))
        size = int(cell_size * scale)
        offset = (cell_size - size) // 2
        pygame.draw.rect(screen, (100, 100, 100),
                         (int(obstacle['pos'].x * cell_size) + offset,
                          int(obstacle['pos'].y * cell_size) + offset,
                          size, size))

    font_small = pygame.font.SysFont("Arial", 24)
    screen.blit(font_small.render(f"P1: {score1}", True, (0, 255, 0)), (10, 10))
    if mode == 2:
        screen.blit(font_small.render(f"P2: {score2}", True, (255, 255, 0)), (10, 40))
    if mode == 3:
        screen.blit(font_small.render(f"AI: {score_ai}", True, (0, 100, 255)), (10, 40))

    update_particles(dt / 1000)
    update_ripples(dt / 1000)
    draw_particles(screen)
    draw_ripples(screen)

    pygame.display.flip()

    if mode == 1:
        game_over_cond = game_over1
    elif mode == 2:
        game_over_cond = game_over1 and game_over2
    else:
        game_over_cond = game_over1 or game_over_ai

    if game_over_cond:
        gameover_sound.play()
        game_over_screen(score1, score2, score_ai, mode)

        mode_data = main_menu()
        if isinstance(mode_data, tuple):
            mode, ai_level = mode_data
        else:
            mode, ai_level = mode_data, 1
        snake1, direction1, snake2, direction2, snake_ai, direction_ai, food, obstacles, score1, score2, score_ai, ai_level = reset_game(mode, ai_level)
        snake1_old = [s.copy() for s in snake1]
        snake2_old = [s.copy() for s in snake2] if snake2 else []
        snake_ai_old = [s.copy() for s in snake_ai] if snake_ai else []
        game_over1 = game_over2 = game_over_ai = False
        move_delay1 = move_delay2 = move_delay_ai = base_speed
        last_move_time1 = last_move_time2 = last_move_time_ai = pygame.time.get_ticks()
        obstacle_timer = pygame.time.get_ticks()
