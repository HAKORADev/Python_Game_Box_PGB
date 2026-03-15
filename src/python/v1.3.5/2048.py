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

space = pymunk.Space()
space.gravity = (0, 200)

WIDTH = 1280
HEIGHT = 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2048")
clock = pygame.time.Clock()

font = pygame.font.SysFont("Arial", 25)
font_medium = pygame.font.SysFont("Arial", 22)
font_large = pygame.font.SysFont("Arial", 45)
font_small = pygame.font.SysFont("Arial", 20)
arrow_font = pygame.font.SysFont("Arial", 20)

board_rows, board_cols = (4, 4)
board_size = 500
board_x = (WIDTH - board_size) // 2
board_y = 50
tile_size = board_size // board_cols

particles = []

def generate_tone(freq, duration, volume=0.5):
    sr = 44100
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    tone = np.sin(2 * math.pi * freq * t)
    audio = (tone * 32767 * volume).astype(np.int16)
    audio = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio)

move_sound = generate_tone(600, 0.05, 0.5)
merge_sound = generate_tone(800, 0.1, 0.5)
spawn_sound = generate_tone(700, 0.05, 0.5)
game_over_sound = generate_tone(300, 0.3, 0.5)

def get_bg_color():
    t = pygame.time.get_ticks() / 1000.0
    hue = (t * 0.07) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.2, 0.9)
    return (int(r * 255), int(g * 255), int(b * 255))

tile_colors = {
    0: (205, 193, 180),
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46)
}

def get_text_color(v):
    if v <= 4:
        return (119, 110, 101)
    return (249, 246, 242)

def spawn_particles(x, y, color):
    for i in range(8):
        m = 0.1
        r = 3
        moment = pymunk.moment_for_circle(m, 0, r, (0, 0))
        body = pymunk.Body(m, moment)
        body.position = (x, y)
        vx = random.uniform(-100, 100)
        vy = random.uniform(-150, -50)
        body.velocity = (vx, vy)
        shape = pymunk.Circle(body, r)
        shape.color = color
        shape.elasticity = 0.5
        space.add(body, shape)
        particles.append((body, shape, pygame.time.get_ticks()))

def update_particles():
    current = pygame.time.get_ticks()
    new_particles = []
    for body, shape, birth in particles:
        if current - birth < 1000:
            new_particles.append((body, shape, birth))
        else:
            space.remove(body, shape)
    particles[:] = new_particles

def draw_particles():
    for body, shape, birth in particles:
        pos = (int(body.position.x), int(body.position.y))
        age = pygame.time.get_ticks() - birth
        alpha = max(0, 255 - int(255 * age / 1000))
        surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(surf, shape.color + (alpha,), (3, 3), 3)
        screen.blit(surf, (pos[0] - 3, pos[1] - 3))

frames = []
for i in range(10):
    surf = pygame.Surface((board_size + 20, board_size + 20), pygame.SRCALPHA)
    col = (255, 215, 0, max(0, 255 - i * 25))
    pygame.draw.rect(surf, col, (0, 0, board_size + 20, board_size + 20), border_radius=18)
    frames.append((surf, 100))

board_glow_ani = pyganim.PygAnimation(frames)
board_glow_ani.play()

arrow_buttons = {}
btn_size = 60
arrow_buttons["up"] = pygame.Rect(WIDTH // 2 - btn_size // 2, board_y + board_size + 20, btn_size, btn_size)
arrow_buttons["down"] = pygame.Rect(WIDTH // 2 - btn_size // 2, board_y + board_size + 20 + btn_size + 10, btn_size, btn_size)
arrow_buttons["left"] = pygame.Rect(WIDTH // 2 - btn_size - 10, board_y + board_size + 20 + btn_size // 2 + 5, btn_size, btn_size)
arrow_buttons["right"] = pygame.Rect(WIDTH // 2 + 10, board_y + board_size + 20 + btn_size // 2 + 5, btn_size, btn_size)

def draw_arrows():
    for direction, rect in arrow_buttons.items():
        pygame.draw.rect(screen, (50, 50, 50), rect, border_radius=8)
        if direction == "up":
            arrow_text = "↑"
        elif direction == "down":
            arrow_text = "↓"
        elif direction == "left":
            arrow_text = "←"
        elif direction == "right":
            arrow_text = "→"
        txt = arrow_font.render(arrow_text, True, (255, 255, 255))
        screen.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

def init_board():
    board = [[0 for _ in range(board_cols)] for __ in range(board_rows)]
    animations = {}
    spawn_tile(board, animations)
    spawn_tile(board, animations)
    return board, animations

def spawn_tile(board, animations):
    empties = [(r, c) for r in range(board_rows) for c in range(board_cols) if board[r][c] == 0]
    if not empties:
        return
    r, c = random.choice(empties)
    board[r][c] = 4 if random.random() < 0.1 else 2
    animations[(r, c)] = 20
    spawn_sound.play()
    cx = board_x + c * tile_size + tile_size // 2 + 10
    cy = board_y + r * tile_size + tile_size // 2 + 10
    spawn_particles(cx, cy, tile_colors[board[r][c]])

def can_move(board):
    for r in range(board_rows):
        for c in range(board_cols):
            if board[r][c] == 0:
                return True
            if c < board_cols - 1 and board[r][c] == board[r][c+1]:
                return True
            if r < board_rows - 1 and board[r][c] == board[r+1][c]:
                return True
    return False

def process_row_left(old_row, row_index):
    tiles = [(col, old_row[col]) for col in range(len(old_row)) if old_row[col] != 0]
    new_row = [0] * len(old_row)
    moves = []
    new_col = 0
    i = 0
    while i < len(tiles):
        col, val = tiles[i]
        if i + 1 < len(tiles) and tiles[i+1][1] == val:
            new_val = val * 2
            new_row[new_col] = new_val
            moves.append((row_index, col, row_index, new_col, new_val))
            moves.append((row_index, tiles[i+1][0], row_index, new_col, new_val))
            merge_sound.play()
            i += 2
        else:
            new_row[new_col] = val
            if col != new_col:
                moves.append((row_index, col, row_index, new_col, val))
            i += 1
        new_col += 1
    return new_row, moves

def move_left_animated(board):
    new_board = []
    all_moves = []
    changed = False
    for r in range(board_rows):
        new_row, moves = process_row_left(board[r], r)
        if new_row != board[r]:
            changed = True
        new_board.append(new_row)
        all_moves.extend(moves)
    return new_board, changed, all_moves

def reverse(board):
    return [list(reversed(r)) for r in board]

def transpose(board):
    return [list(r) for r in zip(*board)]

def move_animated(board, direction):
    if direction == "left":
        return move_left_animated(board)
    elif direction == "right":
        rev = reverse(board)
        new_rev, changed, moves = move_left_animated(rev)
        new_board = reverse(new_rev)
        transformed_moves = []
        for r, old_c, r2, new_c, val in moves:
            transformed_moves.append((r, board_cols-1-old_c, r, board_cols-1-new_c, val))
        return new_board, changed, transformed_moves
    elif direction == "up":
        trans = transpose(board)
        new_trans, changed, moves = move_left_animated(trans)
        new_board = transpose(new_trans)
        transformed_moves = []
        for old_r, old_c, new_r, new_c, val in moves:
            transformed_moves.append((old_c, old_r, new_c, new_r, val))
        return new_board, changed, transformed_moves
    elif direction == "down":
        trans = transpose(board)
        rev = reverse(trans)
        new_rev, changed, moves = move_left_animated(rev)
        new_board = transpose(reverse(new_rev))
        transformed_moves = []
        for old_r, old_c, new_r, new_c, val in moves:
            old_B_r = board_cols-1 - old_c
            old_B_c = old_r
            new_B_r = board_cols-1 - new_c
            new_B_c = new_r
            transformed_moves.append((old_B_r, old_B_c, new_B_r, new_B_c, val))
        return new_board, changed, transformed_moves
    return board, False, []

class MovingTile:
    def __init__(self, start_r, start_c, end_r, end_c, value, board_x, board_y, tile_size):
        self.start_r = start_r
        self.start_c = start_c
        self.end_r = end_r
        self.end_c = end_c
        self.value = value
        self.progress = 0.0
        self.speed = 0.02
        self.board_x = board_x
        self.board_y = board_y
        self.tile_size = tile_size

    def update(self):
        self.progress += self.speed
        if self.progress > 1.0:
            self.progress = 1.0

    def done(self):
        return self.progress >= 1.0

    def get_pos(self):
        start_x = self.board_x + self.start_c * self.tile_size + self.tile_size // 2 + 10
        start_y = self.board_y + self.start_r * self.tile_size + self.tile_size // 2 + 10
        end_x = self.board_x + self.end_c * self.tile_size + self.tile_size // 2 + 10
        end_y = self.board_y + self.end_r * self.tile_size + self.tile_size // 2 + 10
        x = start_x + (end_x - start_x) * self.progress
        y = start_y + (end_y - start_y) * self.progress
        return int(x), int(y)

    def draw(self, screen):
        x, y = self.get_pos()
        w = self.tile_size - 20
        h = self.tile_size - 20
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (x, y)
        col = tile_colors.get(self.value, (60, 58, 50))
        pygame.draw.rect(screen, col, rect, border_radius=8)
        if self.value:
            s = str(self.value)
            txt = font.render(s, True, get_text_color(self.value))
            txt_rect = txt.get_rect(center=rect.center)
            screen.blit(txt, txt_rect)

def draw_board_glow(x, y):
    board_glow_ani.blit(screen, (x - 10, y - 10))

def draw_board_static(board, x, y, skip_cells=None):
    pygame.draw.rect(screen, (187, 173, 160), (x, y, board_size, board_size), border_radius=10)
    for r in range(board_rows):
        for c in range(board_cols):
            if skip_cells and (r, c) in skip_cells:
                continue
            v = board[r][c]
            if v == 0:
                continue
            tile_x = x + c * tile_size + 10
            tile_y = y + r * tile_size + 10
            w = tile_size - 20
            h = tile_size - 20
            rect = pygame.Rect(tile_x, tile_y, w, h)
            col = tile_colors.get(v, (60, 58, 50))
            pygame.draw.rect(screen, col, rect, border_radius=8)
            if v:
                s = str(v)
                txt = font.render(s, True, get_text_color(v))
                txt_rect = txt.get_rect(center=rect.center)
                screen.blit(txt, txt_rect)

def update_animations(animations):
    rem = []
    for k in animations:
        animations[k] -= 1
        if animations[k] <= 0:
            rem.append(k)
    for k in rem:
        del animations[k]

def board_has_changed(old, new):
    for r in range(board_rows):
        for c in range(board_cols):
            if old[r][c] != new[r][c]:
                return True
    return False

def game_over_screen_2048(score):
    game_over_sound.play()
    restart_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)
    menu_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 120, 200, 50)
    while True:
        clock.tick(60)
        bg = get_bg_color()
        screen.fill(bg)
        go_txt = font_large.render("Game Over!", True, (255, 0, 0))
        score_txt = font_medium.render(f"Score: {score}", True, (255, 255, 255))
        opt_txt = font_small.render("Click Restart or Menu", True, (255, 255, 255))
        pygame.draw.rect(screen, (50, 50, 50), restart_btn, border_radius=8)
        pygame.draw.rect(screen, (50, 50, 50), menu_btn, border_radius=8)
        restart_txt = font_medium.render("Restart", True, (255, 255, 255))
        menu_txt = font_medium.render("Menu", True, (255, 255, 255))
        screen.blit(go_txt, (WIDTH // 2 - go_txt.get_width() // 2, HEIGHT // 2 - 120))
        screen.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, HEIGHT // 2 - 60))
        screen.blit(opt_txt, (WIDTH // 2 - opt_txt.get_width() // 2, HEIGHT // 2 - 10))
        screen.blit(restart_txt, (restart_btn.centerx - restart_txt.get_width() // 2, restart_btn.centery - restart_txt.get_height() // 2))
        screen.blit(menu_txt, (menu_btn.centerx - menu_txt.get_width() // 2, menu_btn.centery - menu_txt.get_height() // 2))
        update_particles()
        draw_particles()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if restart_btn.collidepoint(mx, my):
                    game_loop_2048()
                    return
                if menu_btn.collidepoint(mx, my):
                    main_menu_2048()
                    return

def game_over_screen_vs(score1, score2, winner):
    restart_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 50, 200, 50)
    menu_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 120, 200, 50)
    while True:
        clock.tick(60)
        bg = get_bg_color()
        screen.fill(bg)
        go_txt = font_large.render("Game Over!", True, (255, 0, 0))
        if winner == "tie":
            winner_txt = font_medium.render("Tie!", True, (255, 255, 255))
        else:
            winner_txt = font_medium.render(f"{winner} Wins!", True, (255, 255, 255))
        score1_txt = font_small.render(f"P1 Score: {score1}", True, (255, 255, 255))
        score2_txt = font_small.render(f"P2 Score: {score2}", True, (255, 255, 255))
        opt_txt = font_small.render("Click Restart or Menu", True, (255, 255, 255))
        pygame.draw.rect(screen, (50, 50, 50), restart_btn, border_radius=8)
        pygame.draw.rect(screen, (50, 50, 50), menu_btn, border_radius=8)
        restart_txt = font_medium.render("Restart", True, (255, 255, 255))
        menu_txt = font_medium.render("Menu", True, (255, 255, 255))
        screen.blit(go_txt, (WIDTH // 2 - go_txt.get_width() // 2, HEIGHT // 2 - 120))
        screen.blit(winner_txt, (WIDTH // 2 - winner_txt.get_width() // 2, HEIGHT // 2 - 80))
        screen.blit(score1_txt, (WIDTH // 2 - score1_txt.get_width() // 2, HEIGHT // 2 - 40))
        screen.blit(score2_txt, (WIDTH // 2 - score2_txt.get_width() // 2, HEIGHT // 2))
        screen.blit(opt_txt, (WIDTH // 2 - opt_txt.get_width() // 2, HEIGHT // 2 + 40))
        screen.blit(restart_txt, (restart_btn.centerx - restart_txt.get_width() // 2, restart_btn.centery - restart_txt.get_height() // 2))
        screen.blit(menu_txt, (menu_btn.centerx - menu_txt.get_width() // 2, menu_btn.centery - menu_txt.get_height() // 2))
        update_particles()
        draw_particles()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if restart_btn.collidepoint(mx, my):
                    game_loop_vs()
                    return
                if menu_btn.collidepoint(mx, my):
                    main_menu_2048()
                    return

def main_menu_2048():
    single_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 60, 200, 50)
    vs_btn = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 50)
    while True:
        clock.tick(60)
        bg = get_bg_color()
        screen.fill(bg)
        title = font_large.render("2048 Game", True, (255, 215, 0))
        single_txt = font_medium.render("Single Player", True, (255, 255, 255))
        vs_txt = font_medium.render("VS Mode", True, (255, 255, 255))
        pygame.draw.rect(screen, (50, 50, 50), single_btn, border_radius=8)
        pygame.draw.rect(screen, (50, 50, 50), vs_btn, border_radius=8)
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 150))
        screen.blit(single_txt, (single_btn.centerx - single_txt.get_width() // 2, single_btn.centery - single_txt.get_height() // 2))
        screen.blit(vs_txt, (vs_btn.centerx - vs_txt.get_width() // 2, vs_btn.centery - vs_txt.get_height() // 2))
        update_particles()
        draw_particles()
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if single_btn.collidepoint(mx, my):
                    game_loop_2048()
                    return
                if vs_btn.collidepoint(mx, my):
                    game_loop_vs()
                    return

def game_loop_2048():
    board, animations = init_board()
    score = 0
    moving_tiles = []
    pending_board = None
    animating = False

    while True:
        clock.tick(60)
        bg = get_bg_color()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not animating and event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for direction, btn in arrow_buttons.items():
                    if btn.collidepoint(mx, my):
                        old_board = [row[:] for row in board]
                        new_board, changed, moves = move_animated(board, direction)
                        if changed and board_has_changed(old_board, new_board):
                            move_sound.play()
                            animating = True
                            pending_board = new_board
                            moving_tiles = []
                            for (r1, c1, r2, c2, val) in moves:
                                mt = MovingTile(r1, c1, r2, c2, val, board_x, board_y, tile_size)
                                moving_tiles.append(mt)
                            break

        if animating:
            all_done = True
            for mt in moving_tiles:
                mt.update()
                if not mt.done():
                    all_done = False
            if all_done:
                board = pending_board
                spawn_tile(board, animations)
                moving_tiles = []
                animating = False
                pending_board = None

        space.step(0.016666666666666666)

        screen.fill(bg)
        draw_board_glow(board_x, board_y)

        if animating:
            source_cells = {(mt.start_r, mt.start_c) for mt in moving_tiles}
            draw_board_static(board, board_x, board_y, skip_cells=source_cells)
            for mt in moving_tiles:
                mt.draw(screen)
        else:
            draw_board_static(board, board_x, board_y, skip_cells=None)
            for (r, c), t in animations.items():
                v = board[r][c]
                if v == 0:
                    continue
                tile_x = board_x + c * tile_size + 10
                tile_y = board_y + r * tile_size + 10
                w = tile_size - 20
                h = tile_size - 20
                scale = 1 + 0.3 * (t / 20)
                tw = int(w * scale)
                th = int(h * scale)
                rect = pygame.Rect(0, 0, tw, th)
                rect.center = (tile_x + w / 2, tile_y + h / 2)
                col = tile_colors.get(v, (60, 58, 50))
                pygame.draw.rect(screen, col, rect, border_radius=8)
                if v:
                    s = str(v)
                    txt = font.render(s, True, get_text_color(v))
                    txt_rect = txt.get_rect(center=rect.center)
                    screen.blit(txt, txt_rect)

        draw_arrows()
        score = sum(sum(row) for row in board)
        score_disp = font_medium.render(f"Score: {score}", True, (255, 255, 255))
        screen.blit(score_disp, (board_x + board_size + 10, board_y))

        update_animations(animations)
        update_particles()
        draw_particles()
        pygame.display.flip()

        if not can_move(board):
            game_over_screen_2048(score)
            return

def game_loop_vs():
    board1, anim1 = init_board()
    board2, anim2 = init_board()
    moving_tiles1 = []
    moving_tiles2 = []
    pending_board1 = None
    pending_board2 = None
    animating1 = False
    animating2 = False

    while True:
        clock.tick(60)
        bg = get_bg_color()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                direction = None
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    direction = ["left", "right", "up", "down"][
                        [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN].index(event.key)
                    ]
                    if not animating2:
                        old_board = [row[:] for row in board2]
                        new_board, changed, moves = move_animated(board2, direction)
                        if changed and board_has_changed(old_board, new_board):
                            move_sound.play()
                            animating2 = True
                            pending_board2 = new_board
                            moving_tiles2 = []
                            for (r1, c1, r2, c2, val) in moves:
                                mt = MovingTile(r1, c1, r2, c2, val,
                                                board_x + 300, board_y, tile_size)
                                moving_tiles2.append(mt)
                elif event.key in (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s):
                    direction = ["left", "right", "up", "down"][
                        [pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s].index(event.key)
                    ]
                    if not animating1:
                        old_board = [row[:] for row in board1]
                        new_board, changed, moves = move_animated(board1, direction)
                        if changed and board_has_changed(old_board, new_board):
                            move_sound.play()
                            animating1 = True
                            pending_board1 = new_board
                            moving_tiles1 = []
                            for (r1, c1, r2, c2, val) in moves:
                                mt = MovingTile(r1, c1, r2, c2, val,
                                                board_x - 300, board_y, tile_size)
                                moving_tiles1.append(mt)

        if animating1:
            all_done = True
            for mt in moving_tiles1:
                mt.update()
                if not mt.done():
                    all_done = False
            if all_done:
                board1 = pending_board1
                spawn_tile(board1, anim1)
                moving_tiles1 = []
                animating1 = False
                pending_board1 = None

        if animating2:
            all_done = True
            for mt in moving_tiles2:
                mt.update()
                if not mt.done():
                    all_done = False
            if all_done:
                board2 = pending_board2
                spawn_tile(board2, anim2)
                moving_tiles2 = []
                animating2 = False
                pending_board2 = None

        space.step(0.016666666666666666)

        screen.fill(bg)

        draw_board_glow(board_x - 300, board_y)
        if animating1:
            source_cells = {(mt.start_r, mt.start_c) for mt in moving_tiles1}
            draw_board_static(board1, board_x - 300, board_y, skip_cells=source_cells)
            for mt in moving_tiles1:
                mt.draw(screen)
        else:
            draw_board_static(board1, board_x - 300, board_y, skip_cells=None)
            for (r, c), t in anim1.items():
                v = board1[r][c]
                if v == 0:
                    continue
                tile_x = board_x - 300 + c * tile_size + 10
                tile_y = board_y + r * tile_size + 10
                w = tile_size - 20
                h = tile_size - 20
                scale = 1 + 0.3 * (t / 20)
                tw = int(w * scale)
                th = int(h * scale)
                rect = pygame.Rect(0, 0, tw, th)
                rect.center = (tile_x + w / 2, tile_y + h / 2)
                col = tile_colors.get(v, (60, 58, 50))
                pygame.draw.rect(screen, col, rect, border_radius=8)
                if v:
                    s = str(v)
                    txt = font.render(s, True, get_text_color(v))
                    txt_rect = txt.get_rect(center=rect.center)
                    screen.blit(txt, txt_rect)

        draw_board_glow(board_x + 300, board_y)
        if animating2:
            source_cells = {(mt.start_r, mt.start_c) for mt in moving_tiles2}
            draw_board_static(board2, board_x + 300, board_y, skip_cells=source_cells)
            for mt in moving_tiles2:
                mt.draw(screen)
        else:
            draw_board_static(board2, board_x + 300, board_y, skip_cells=None)
            for (r, c), t in anim2.items():
                v = board2[r][c]
                if v == 0:
                    continue
                tile_x = board_x + 300 + c * tile_size + 10
                tile_y = board_y + r * tile_size + 10
                w = tile_size - 20
                h = tile_size - 20
                scale = 1 + 0.3 * (t / 20)
                tw = int(w * scale)
                th = int(h * scale)
                rect = pygame.Rect(0, 0, tw, th)
                rect.center = (tile_x + w / 2, tile_y + h / 2)
                col = tile_colors.get(v, (60, 58, 50))
                pygame.draw.rect(screen, col, rect, border_radius=8)
                if v:
                    s = str(v)
                    txt = font.render(s, True, get_text_color(v))
                    txt_rect = txt.get_rect(center=rect.center)
                    screen.blit(txt, txt_rect)

        score1 = sum(sum(row) for row in board1)
        score2 = sum(sum(row) for row in board2)
        score1_txt = font_medium.render(f"P1: {score1}", True, (255, 255, 255))
        score2_txt = font_medium.render(f"P2: {score2}", True, (255, 255, 255))
        screen.blit(score1_txt, (board_x - 300, board_y + board_size + 10))
        screen.blit(score2_txt, (board_x + 300, board_y + board_size + 10))

        update_animations(anim1)
        update_animations(anim2)
        update_particles()
        draw_particles()
        pygame.display.flip()

        p1_alive = can_move(board1)
        p2_alive = can_move(board2)
        if not p1_alive or not p2_alive:
            if score1 > score2:
                winner = "player1"
            elif score2 > score1:
                winner = "player2"
            else:
                winner = "tie"
            game_over_screen_vs(score1, score2, winner)
            return

if __name__ == "__main__":
    main_menu_2048()
