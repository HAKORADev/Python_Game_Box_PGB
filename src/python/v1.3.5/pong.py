import pygame
import sys
import random
import math
import numpy as np
import colorsys
import pymunk
import pyganim

pygame.init()
pygame.mixer.init()

WIDTH = 1280
HEIGHT = 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong")
clock = pygame.time.Clock()

fontLarge = pygame.font.SysFont("Arial", 72)
fontMedium = pygame.font.SysFont("Arial", 36)
fontSmall = pygame.font.SysFont("Arial", 24)

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
bounce_sound = generate_tone(600, 0.05, 0.5)
score_sound = generate_tone(800, 0.1, 0.5)

def get_bg_color():
    t = pygame.time.get_ticks() / 1000.0
    hue = (t * 0.1) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.8, 0.3)
    return (int(r * 255), int(g * 255), int(b * 255))

def create_ball_anim(size):
    frames = []
    for scale in (0.9, 1.0, 1.1, 1.0):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        s = size * scale
        off = (size - s) / 2
        pygame.draw.ellipse(surf, (255, 255, 0), (off, off, s, s))
        frames.append((surf, 100))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return anim

class ParticleBackground:
    def __init__(self, num):
        self.particles = []
        for i in range(num):
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            r = random.uniform(1, 3)
            dx = random.uniform(-0.5, 0.5)
            dy = random.uniform(-0.5, 0.5)
            self.particles.append([x, y, r, dx, dy])

    def update(self, dt):
        for p in self.particles:
            p[0] += p[3] * dt * 60
            p[1] += p[4] * dt * 60
            if p[0] < 0: p[0] = WIDTH
            if p[0] > WIDTH: p[0] = 0
            if p[1] < 0: p[1] = HEIGHT
            if p[1] > HEIGHT: p[1] = 0

    def draw(self, surface):
        for p in self.particles:
            s = pygame.Surface((int(p[2] * 2), int(p[2] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, 50), (int(p[2]), int(p[2])), int(p[2]))
            surface.blit(s, (p[0] - p[2], p[1] - p[2]))

def main_menu():
    while True:
        clock.tick(60)
        bg_color = get_bg_color()
        screen.fill(bg_color)
        title = fontLarge.render("Pong Game", True, (255, 255, 0))
        vs_ai_text = fontMedium.render("1. VS AI", True, (0, 255, 255))
        vs_player_text = fontMedium.render("2. VS PLAYER", True, (255, 105, 180))
        instruct = fontSmall.render("Press 1 or 2 to select mode. ESC to quit.", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
        screen.blit(vs_ai_text, (WIDTH // 2 - vs_ai_text.get_width() // 2, 250))
        screen.blit(vs_player_text, (WIDTH // 2 - vs_player_text.get_width() // 2, 320))
        screen.blit(instruct, (WIDTH // 2 - instruct.get_width() // 2, 400))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_1:
                    ai_difficulty_menu()
                if event.key == pygame.K_2:
                    vs_player_mode()

def ai_difficulty_menu():
    while True:
        clock.tick(60)
        bg_color = get_bg_color()
        screen.fill(bg_color)
        title = fontLarge.render("Select AI Difficulty", True, (255, 255, 0))
        easy_text = fontMedium.render("1. Easy", True, (0, 255, 255))
        medium_text = fontMedium.render("2. Medium", True, (0, 255, 0))
        hard_text = fontMedium.render("3. Hard", True, (255, 0, 0))
        instruct = fontSmall.render("Press 1, 2, or 3. ESC to return.", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
        screen.blit(easy_text, (WIDTH // 2 - easy_text.get_width() // 2, 250))
        screen.blit(medium_text, (WIDTH // 2 - medium_text.get_width() // 2, 320))
        screen.blit(hard_text, (WIDTH // 2 - hard_text.get_width() // 2, 390))
        screen.blit(instruct, (WIDTH // 2 - instruct.get_width() // 2, 460))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_1:
                    vs_ai_mode("easy")
                if event.key == pygame.K_2:
                    vs_ai_mode("medium")
                if event.key == pygame.K_3:
                    vs_ai_mode("hard")

def vs_ai_mode(difficulty):
    paddle_width, paddle_height = 20, 100
    ball_size = 20
    left_score, right_score = 0, 0
    space = pymunk.Space()
    space.gravity = (0, 0)
    static_lines = [
        pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 1),
        pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 1)
    ]
    for line in static_lines:
        line.elasticity = 1.0
        line.friction = 0
        line.collision_type = 0
    space.add(*static_lines)

    left_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    left_body.position = (50, HEIGHT // 2)
    left_poly = pymunk.Poly(left_body, [(-paddle_width/2, -paddle_height/2), (-paddle_width/2, paddle_height/2), (paddle_width/2, paddle_height/2), (paddle_width/2, -paddle_height/2)])
    left_poly.elasticity = 1.0
    left_poly.collision_type = 2
    space.add(left_body, left_poly)

    right_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    right_body.position = (WIDTH - 50, HEIGHT // 2)
    right_poly = pymunk.Poly(right_body, [(-paddle_width/2, -paddle_height/2), (-paddle_width/2, paddle_height/2), (paddle_width/2, paddle_height/2), (paddle_width/2, -paddle_height/2)])
    right_poly.elasticity = 1.0
    right_poly.collision_type = 3
    space.add(right_body, right_poly)

    ball_radius = ball_size / 2
    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, ball_radius)
    ball_body = pymunk.Body(mass, moment)
    ball_body.position = (WIDTH // 2, HEIGHT // 2)
    ball_shape = pymunk.Circle(ball_body, ball_radius)
    ball_shape.elasticity = 1.0
    ball_shape.friction = 0
    ball_shape.collision_type = 1
    space.add(ball_body, ball_shape)

    vx = 400 if random.choice([True, False]) else -400
    vy = 400 if random.choice([True, False]) else -400
    ball_body.velocity = (vx, vy)

    flash_timer = 0
    flash_pos = pygame.math.Vector2(0, 0)
    ball_trail = []
    ball_anim = create_ball_anim(ball_size)
    paddle_speed = 400
    ai_speed = 4 if difficulty == "easy" else (6 if difficulty == "medium" else 8)
    pb = ParticleBackground(50)

    def ball_paddle_collision(arbiter, space, data):
        nonlocal flash_timer, flash_pos
        bounce_sound.play()
        flash_timer = 5
        flash_pos = ball_body.position
        return True

    handler1 = space.add_collision_handler(1, 2)
    handler1.begin = ball_paddle_collision
    handler2 = space.add_collision_handler(1, 3)
    handler2.begin = ball_paddle_collision

    def ball_wall_collision(arbiter, space, data):
        bounce_sound.play()
        return True

    handler_wall = space.add_collision_handler(1, 0)
    handler_wall.begin = ball_wall_collision

    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] and left_body.position.y - paddle_height / 2 > 0:
            left_body.position = (left_body.position.x, left_body.position.y - paddle_speed * dt)
        if keys[pygame.K_s] and left_body.position.y + paddle_height / 2 < HEIGHT:
            left_body.position = (left_body.position.x, left_body.position.y + paddle_speed * dt)

        if ball_body.position.y < right_body.position.y and right_body.position.y - paddle_height / 2 > 0:
            right_body.position = (right_body.position.x, right_body.position.y - ai_speed)
        elif ball_body.position.y > right_body.position.y and right_body.position.y + paddle_height / 2 < HEIGHT:
            right_body.position = (right_body.position.x, right_body.position.y + ai_speed)

        space.step(dt)

        if ball_body.position.x < 0:
            right_score += 1
            score_sound.play()
            ball_body.position = (WIDTH // 2, HEIGHT // 2)
            vx = 400 if random.choice([True, False]) else -400
            vy = 400 if random.choice([True, False]) else -400
            ball_body.velocity = (vx, vy)
            ball_trail = []
        elif ball_body.position.x > WIDTH:
            left_score += 1
            score_sound.play()
            ball_body.position = (WIDTH // 2, HEIGHT // 2)
            vx = 400 if random.choice([True, False]) else -400
            vy = 400 if random.choice([True, False]) else -400
            ball_body.velocity = (vx, vy)
            ball_trail = []

        ball_trail.append([ball_body.position.x, ball_body.position.y, 30])
        for titem in ball_trail:
            titem[2] -= 1
        ball_trail = [t for t in ball_trail if t[2] > 0]

        bg_color = get_bg_color()
        screen.fill(bg_color)
        pb.update(dt)
        pb.draw(screen)

        for titem in ball_trail:
            alpha = int(titem[2] / 30 * 255)
            trail_surf = pygame.Surface((ball_size, ball_size), pygame.SRCALPHA)
            pygame.draw.ellipse(trail_surf, (255, 255, 255, alpha), (0, 0, ball_size, ball_size))
            screen.blit(trail_surf, (titem[0] - ball_size // 2, titem[1] - ball_size // 2))

        left_rect = pygame.Rect(0, 0, paddle_width, paddle_height)
        left_rect.center = (left_body.position.x, left_body.position.y)
        right_rect = pygame.Rect(0, 0, paddle_width, paddle_height)
        right_rect.center = (right_body.position.x, right_body.position.y)
        pygame.draw.rect(screen, (50, 255, 255), left_rect)
        pygame.draw.rect(screen, (255, 105, 180), right_rect)

        ball_pos = (int(ball_body.position.x - ball_size / 2), int(ball_body.position.y - ball_size / 2))
        ball_anim.blit(screen, ball_pos)
        pygame.draw.aaline(screen, (255, 255, 255), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))
        score_text = fontMedium.render(f"{left_score}   {right_score}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 20))

        if flash_timer > 0:
            flash_surf = pygame.Surface((ball_size * 2, ball_size * 2), pygame.SRCALPHA)
            alpha = int(flash_timer / 5 * 255)
            pygame.draw.ellipse(flash_surf, (255, 255, 255, alpha), (0, 0, ball_size * 2, ball_size * 2))
            screen.blit(flash_surf, (int(flash_pos.x) - ball_size, int(flash_pos.y) - ball_size))
            flash_timer -= 1

        pygame.display.flip()

def vs_player_mode():
    paddle_width, paddle_height = 20, 100
    ball_size = 20
    p1_score, p2_score = 0, 0
    space = pymunk.Space()
    space.gravity = (0, 0)
    static_lines = [
        pymunk.Segment(space.static_body, (0, 0), (WIDTH, 0), 1),
        pymunk.Segment(space.static_body, (0, HEIGHT), (WIDTH, HEIGHT), 1)
    ]
    for line in static_lines:
        line.elasticity = 1.0
        line.friction = 0
        line.collision_type = 0
    space.add(*static_lines)

    left_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    left_body.position = (50, HEIGHT // 2)
    left_poly = pymunk.Poly(left_body, [(-paddle_width/2, -paddle_height/2), (-paddle_width/2, paddle_height/2), (paddle_width/2, paddle_height/2), (paddle_width/2, -paddle_height/2)])
    left_poly.elasticity = 1.0
    left_poly.collision_type = 2
    space.add(left_body, left_poly)

    right_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
    right_body.position = (WIDTH - 50, HEIGHT // 2)
    right_poly = pymunk.Poly(right_body, [(-paddle_width/2, -paddle_height/2), (-paddle_width/2, paddle_height/2), (paddle_width/2, paddle_height/2), (paddle_width/2, -paddle_height/2)])
    right_poly.elasticity = 1.0
    right_poly.collision_type = 3
    space.add(right_body, right_poly)

    ball_radius = ball_size / 2
    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, ball_radius)
    ball_body = pymunk.Body(mass, moment)
    ball_body.position = (WIDTH // 2, HEIGHT // 2)
    ball_shape = pymunk.Circle(ball_body, ball_radius)
    ball_shape.elasticity = 1.0
    ball_shape.friction = 0
    ball_shape.collision_type = 1
    space.add(ball_body, ball_shape)

    vx = 400 if random.choice([True, False]) else -400
    vy = 400 if random.choice([True, False]) else -400
    ball_body.velocity = (vx, vy)

    flash_timer = 0
    flash_pos = pygame.math.Vector2(0, 0)
    ball_trail = []
    ball_anim = create_ball_anim(ball_size)
    paddle_speed = 400
    pb = ParticleBackground(50)

    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] and left_body.position.y - paddle_height / 2 > 0:
            left_body.position = (left_body.position.x, left_body.position.y - paddle_speed * dt)
        if keys[pygame.K_s] and left_body.position.y + paddle_height / 2 < HEIGHT:
            left_body.position = (left_body.position.x, left_body.position.y + paddle_speed * dt)
        if keys[pygame.K_UP] and right_body.position.y - paddle_height / 2 > 0:
            right_body.position = (right_body.position.x, right_body.position.y - paddle_speed * dt)
        if keys[pygame.K_DOWN] and right_body.position.y + paddle_height / 2 < HEIGHT:
            right_body.position = (right_body.position.x, right_body.position.y + paddle_speed * dt)

        space.step(dt)

        if ball_body.position.x < 0:
            p2_score += 1
            score_sound.play()
            ball_body.position = (WIDTH // 2, HEIGHT // 2)
            vx = 400 if random.choice([True, False]) else -400
            vy = 400 if random.choice([True, False]) else -400
            ball_body.velocity = (vx, vy)
            ball_trail = []
        elif ball_body.position.x > WIDTH:
            p1_score += 1
            score_sound.play()
            ball_body.position = (WIDTH // 2, HEIGHT // 2)
            vx = 400 if random.choice([True, False]) else -400
            vy = 400 if random.choice([True, False]) else -400
            ball_body.velocity = (vx, vy)
            ball_trail = []

        ball_trail.append([ball_body.position.x, ball_body.position.y, 30])
        for titem in ball_trail:
            titem[2] -= 1
        ball_trail = [t for t in ball_trail if t[2] > 0]

        bg_color = get_bg_color()
        screen.fill(bg_color)
        pb.update(dt)
        pb.draw(screen)

        for titem in ball_trail:
            alpha = int(titem[2] / 30 * 255)
            trail_surf = pygame.Surface((ball_size, ball_size), pygame.SRCALPHA)
            pygame.draw.ellipse(trail_surf, (255, 255, 255, alpha), (0, 0, ball_size, ball_size))
            screen.blit(trail_surf, (titem[0] - ball_size // 2, titem[1] - ball_size // 2))

        left_rect = pygame.Rect(0, 0, paddle_width, paddle_height)
        left_rect.center = (left_body.position.x, left_body.position.y)
        right_rect = pygame.Rect(0, 0, paddle_width, paddle_height)
        right_rect.center = (right_body.position.x, right_body.position.y)
        pygame.draw.rect(screen, (50, 255, 255), left_rect)
        pygame.draw.rect(screen, (255, 105, 180), right_rect)

        ball_pos = (int(ball_body.position.x - ball_size / 2), int(ball_body.position.y - ball_size / 2))
        ball_anim.blit(screen, ball_pos)
        pygame.draw.aaline(screen, (255, 255, 255), (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))
        score_text = fontMedium.render(f"{p1_score}   {p2_score}", True, (255, 255, 255))
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 20))

        if flash_timer > 0:
            flash_surf = pygame.Surface((ball_size * 2, ball_size * 2), pygame.SRCALPHA)
            alpha = int(flash_timer / 5 * 255)
            pygame.draw.ellipse(flash_surf, (255, 255, 255, alpha), (0, 0, ball_size * 2, ball_size * 2))
            screen.blit(flash_surf, (int(flash_pos.x) - ball_size, int(flash_pos.y) - ball_size))
            flash_timer -= 1

        pygame.display.flip()

if __name__ == "__main__":
    main_menu()
