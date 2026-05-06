import pygame
import sys
import random
import math
import numpy as np
import pymunk
from pygame.locals import *

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("XO Battle Arena")
clock = pygame.time.Clock()

def generate_wave(freq=440, waveform='sine', dur=0.5, fm=0):
    sample_rate = 44100
    t = np.linspace(0, dur, int(sample_rate * dur), endpoint=False)
    if waveform == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t + fm * np.sin(2 * np.pi * 2 * t)))
    elif waveform == "saw":
        wave = (t * freq % 1) * 2 - 1
    else:
        wave = np.sin(2 * np.pi * freq * t)
    mono_wave = np.int16(wave * 32767 * 0.3)
    stereo_wave = np.column_stack([mono_wave, mono_wave])
    return pygame.sndarray.make_sound(stereo_wave)

snd_place = generate_wave(880, "square", 0.2)
snd_win = generate_wave(660, "saw", 1.0)
snd_tie = generate_wave(600, "square", 0.7)
snd_hover = generate_wave(1200, "sine", 0.05)
snd_click = generate_wave(1000, "sine", 0.05)
music = generate_wave(130, "sine", 4.0, fm=5)

WINNING_COMBINATIONS = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],
    [0, 3, 6], [1, 4, 7], [2, 5, 8],
    [0, 4, 8], [2, 4, 6]
]

DIFFICULTY_DESC = {
    "Easy": "Perfect for beginners! The AI makes lots of mistakes.",
    "Medium": "A balanced challenge. The AI plays decently but not perfectly.",
    "Hard": "Quite challenging! The AI rarely makes mistakes.",
    "Overkill": "IMPOSSIBLE TO BEAT! The AI plays perfectly every time."
}

WIN_TAUNTS = {
    "Easy": ["Oh no! You got me!", "Good game!", "You win this time!"],
    "Medium": ["Nice play!", "Well done!", "I'll get you next time!"],
    "Hard": ["Impressive! You beat me!", "Great strategy!", "You got lucky this time!"],
    "Overkill": ["IMPOSSIBLE! You must be cheating!", "How did you...?!", "This can't be!"]
}

LOSS_TAUNTS = {
    "Easy": ["Oops, I won!", "Hehe, gotcha!", "Better luck next time!"],
    "Medium": ["I win!", "Got you!", "Victory is mine!"],
    "Hard": ["Checkmate!", "You never stood a chance!", "Too easy!"],
    "Overkill": ["DID YOU REALLY THINK YOU COULD WIN?", "PATHETIC!", "I AM UNBEATABLE!", "BOW BEFORE ME!"]
}

def draw_text_with_outline(surface, text, font, color, outline_color, pos, outline_width=2):
    x, y = pos
    for dx in (-outline_width, outline_width):
        for dy in (-outline_width, outline_width):
            if dx != 0 or dy != 0:
                surf = font.render(text, True, outline_color)
                surface.blit(surf, (x + dx, y + dy))
    surf = font.render(text, True, color)
    surface.blit(surf, (x, y))

def draw_paper_texture(surface):
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 4):
        for x in range(0, WIDTH, 4):
            alpha = random.randint(0, 10)
            s.set_at((x, y), (0, 0, 0, alpha))
    surface.blit(s, (0, 0))

class TicTacToeGame:
    def __init__(self):
        self.board = [None] * 9
        self.current_player = "X"
        self.game_mode = "menu"
        self.difficulty = "Medium"
        self.status = "playing"
        self.winning_line = None
        self.scores = {"X": 0, "O": 0, "Draws": 0}

        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        self.font_tiny = pygame.font.Font(None, 24)
        self.font_huge = pygame.font.Font(None, 96)
        self.font_score = pygame.font.Font(None, 30)

        self.space = pymunk.Space()
        self.space.gravity = (0, 200)
        self.particles = []

        self.cell_animations = {}

        self.ai_message = None
        self.ai_message_time = 0

        self.game_over_modal = False
        self.modal_result = None
        self.modal_delay_until = 0

        self.last_hover = None
        self.hover_difficulty = None

        self.sound_enabled = True
        music.play(-1)

        self.anim_cache = {'X': {}, 'O': {}}
        self._precompute_animations()

    def _precompute_animations(self):
        base_size = self.font_large.size('X')
        base_width, base_height = base_size
        for symbol in ['X', 'O']:
            color = (239, 68, 68) if symbol == 'X' else (59, 130, 246)
            base_surf = self.font_large.render(symbol, True, color)
            scales = [round(i * 0.05, 2) for i in range(1, 21)]
            for scale in scales:
                size = max(1, int(base_width * scale))
                scaled = pygame.transform.smoothscale(base_surf, (size, size))
                angle = 360 * (1 - scale)
                rotated = pygame.transform.rotate(scaled, angle)
                self.anim_cache[symbol][scale] = rotated

    def minimax(self, board, depth, is_max, alpha=-math.inf, beta=math.inf):
        winner = self.check_winner(board)
        if winner == "O":
            return {"score": 10 - depth, "move": None}
        if winner == "X":
            return {"score": depth - 10, "move": None}
        if all(board):
            return {"score": 0, "move": None}

        moves = [i for i, v in enumerate(board) if v is None]
        if is_max:
            best = -math.inf
            best_move = None
            for move in moves:
                board[move] = "O"
                score = self.minimax(board, depth + 1, False, alpha, beta)["score"]
                board[move] = None
                if score > best:
                    best = score
                    best_move = move
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return {"score": best, "move": best_move}
        else:
            best = math.inf
            best_move = None
            for move in moves:
                board[move] = "X"
                score = self.minimax(board, depth + 1, True, alpha, beta)["score"]
                board[move] = None
                if score < best:
                    best = score
                    best_move = move
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return {"score": best, "move": best_move}

    def get_ai_move(self, board):
        moves = [i for i, v in enumerate(board) if v is None]
        if not moves:
            return None

        if self.difficulty == "Easy":
            r = random.random()
            if r < 0.1:
                for combo in WINNING_COMBINATIONS:
                    a, b, c = combo
                    if board[a] == "O" and board[b] == "O" and board[c] is None:
                        return c
                    if board[a] == "O" and board[c] == "O" and board[b] is None:
                        return b
                    if board[b] == "O" and board[c] == "O" and board[a] is None:
                        return a
            if r < 0.3:
                for combo in WINNING_COMBINATIONS:
                    a, b, c = combo
                    if board[a] == "X" and board[b] == "X" and board[c] is None:
                        return c
                    if board[a] == "X" and board[c] == "X" and board[b] is None:
                        return b
                    if board[b] == "X" and board[c] == "X" and board[a] is None:
                        return a
            return random.choice(moves)

        elif self.difficulty == "Medium":
            if random.random() < 0.5:
                for combo in WINNING_COMBINATIONS:
                    a, b, c = combo
                    if board[a] == "O" and board[b] == "O" and board[c] is None:
                        return c
                    if board[a] == "O" and board[c] == "O" and board[b] is None:
                        return b
                    if board[b] == "O" and board[c] == "O" and board[a] is None:
                        return a
                for combo in WINNING_COMBINATIONS:
                    a, b, c = combo
                    if board[a] == "X" and board[b] == "X" and board[c] is None:
                        return c
                    if board[a] == "X" and board[c] == "X" and board[b] is None:
                        return b
                    if board[b] == "X" and board[c] == "X" and board[a] is None:
                        return a
                if board[4] is None:
                    return 4
                corners = [i for i in [0, 2, 6, 8] if board[i] is None]
                if corners:
                    return random.choice(corners)
            return random.choice(moves)

        elif self.difficulty == "Hard":
            if random.random() < 0.8:
                result = self.minimax(board[:], 0, True)
                return result["move"] if result["move"] is not None else random.choice(moves)
            for combo in WINNING_COMBINATIONS:
                a, b, c = combo
                if board[a] == "O" and board[b] == "O" and board[c] is None:
                    return c
                if board[a] == "O" and board[c] == "O" and board[b] is None:
                    return b
                if board[b] == "O" and board[c] == "O" and board[a] is None:
                    return a
            for combo in WINNING_COMBINATIONS:
                a, b, c = combo
                if board[a] == "X" and board[b] == "X" and board[c] is None:
                    return c
                if board[a] == "X" and board[c] == "X" and board[b] is None:
                    return b
                if board[b] == "X" and board[c] == "X" and board[a] is None:
                    return a
            return random.choice(moves)

        else:
            result = self.minimax(board[:], 0, True)
            return result["move"] if result["move"] is not None else random.choice(moves)

    def check_winner(self, board):
        for combo in WINNING_COMBINATIONS:
            a, b, c = combo
            if board[a] and board[a] == board[b] == board[c]:
                return board[a]
        return None

    def get_winning_line(self, board):
        for combo in WINNING_COMBINATIONS:
            a, b, c = combo
            if board[a] and board[a] == board[b] == board[c]:
                return combo
        return None

    def make_move(self, index):
        if self.board[index] or self.status != "playing":
            return False

        self.board[index] = self.current_player
        self.cell_animations[index] = pygame.time.get_ticks()
        if self.sound_enabled:
            snd_place.play()

        winner = self.check_winner(self.board)
        if winner:
            self.status = "won" if winner == "X" else "lost"
            self.winning_line = self.get_winning_line(self.board)
            self.scores[winner] += 1
            if self.sound_enabled:
                snd_win.play()
            if self.game_mode == "ai":
                if winner == "X":
                    taunt = random.choice(WIN_TAUNTS[self.difficulty])
                else:
                    taunt = random.choice(LOSS_TAUNTS[self.difficulty])
                self.show_ai_message(taunt)
            self.spawn_particles((WIDTH//2, HEIGHT//2))
            self.modal_delay_until = pygame.time.get_ticks() + 1500
            return True

        if all(self.board):
            self.status = "draw"
            self.scores["Draws"] += 1
            if self.sound_enabled:
                snd_tie.play()
            if self.game_mode == "ai":
                self.show_ai_message("It's a draw! Well played!")
            self.spawn_particles((WIDTH//2, HEIGHT//2))
            self.modal_delay_until = pygame.time.get_ticks() + 1500
            return True

        self.current_player = "O" if self.current_player == "X" else "X"
        return True

    def reset_board(self, keep_scores=False):
        self.board = [None] * 9
        self.current_player = "X"
        self.status = "playing"
        self.winning_line = None
        self.cell_animations = {}
        self.ai_message = None
        self.game_over_modal = False
        if not keep_scores:
            self.scores = {"X": 0, "O": 0, "Draws": 0}

    def show_ai_message(self, text):
        self.ai_message = text
        self.ai_message_time = pygame.time.get_ticks()

    def spawn_particles(self, pos):
        for _ in range(20):
            radius = random.randint(3, 7)
            mass = 1
            moment = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, moment)
            body.position = pos
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            body.velocity = (speed * math.cos(angle), speed * math.sin(angle))
            shape = pymunk.Circle(body, radius)
            self.space.add(body, shape)
            self.particles.append({'body': body, 'shape': shape, 'time': pygame.time.get_ticks(), 'lifetime': 1000})

    def update_particles(self):
        dt = clock.get_time() / 1000
        self.space.step(dt)
        current = pygame.time.get_ticks()
        survived = []
        for p in self.particles:
            if current - p['time'] < p['lifetime']:
                survived.append(p)
            else:
                self.space.remove(p['body'], p['shape'])
        self.particles = survived

    def draw_particles(self):
        current = pygame.time.get_ticks()
        for p in self.particles:
            pos = (int(p['body'].position.x), int(p['body'].position.y))
            life_ratio = (current - p['time']) / p['lifetime']
            alpha = max(0, 255 - int(255 * life_ratio))
            s = pygame.Surface((p['shape'].radius * 2, p['shape'].radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 0, alpha), (p['shape'].radius, p['shape'].radius), int(p['shape'].radius))
            screen.blit(s, (pos[0] - p['shape'].radius, pos[1] - p['shape'].radius))

    def draw_menu(self):
        screen.fill((250, 250, 240))
        draw_paper_texture(screen)

        font_title = pygame.font.Font(None, 180)
        x_color = (239, 68, 68)
        o_color = (31, 41, 55)
        for offset in range(5, 0, -1):
            text_surf = font_title.render("XO", True, (30, 30, 30))
            screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2 + offset, 100 + offset))
        text_surf = font_title.render("XO", True, (0, 0, 0))
        screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 100))
        x_surf = font_title.render("X", True, x_color)
        o_surf = font_title.render("O", True, o_color)
        screen.blit(x_surf, (WIDTH//2 - x_surf.get_width() - 10, 100))
        screen.blit(o_surf, (WIDTH//2 + 10, 100))

        subtitle = "Battle Arena"
        draw_text_with_outline(screen, subtitle, pygame.font.Font(None, 48), (100,100,100), (0,0,0), (WIDTH//2 - self.font_medium.size(subtitle)[0]//2, 220), 1)

        btn_2p = pygame.Rect(WIDTH//2 - 150, 300, 300, 60)
        btn_ai = pygame.Rect(WIDTH//2 - 150, 380, 300, 60)
        btn_quit = pygame.Rect(WIDTH//2 - 150, 460, 300, 60)

        mouse_pos = pygame.mouse.get_pos()
        for rect, text, color in [(btn_2p, "2 Players", (34, 197, 94)), (btn_ai, "vs CPU", (59, 130, 246)), (btn_quit, "Quit", (100, 100, 100))]:
            hover = rect.collidepoint(mouse_pos)
            if hover:
                pygame.draw.rect(screen, color, rect, border_radius=10)
                pygame.draw.rect(screen, (0,0,0), rect, 3, border_radius=10)
                if self.last_hover != text and self.sound_enabled:
                    snd_hover.play()
                    self.last_hover = text
            else:
                pygame.draw.rect(screen, (255,255,255), rect, border_radius=10)
                pygame.draw.rect(screen, (0,0,0), rect, 3, border_radius=10)
            draw_text_with_outline(screen, text, self.font_medium, (0,0,0) if not hover else (255,255,255), (50,50,50), (rect.x + 20, rect.y + 15), 1)

        sound_rect = pygame.Rect(WIDTH-60, 20, 40, 40)
        pygame.draw.circle(screen, (200,200,200), sound_rect.center, 20)
        if self.sound_enabled:
            pygame.draw.polygon(screen, (0,0,0), [(sound_rect.x+10, sound_rect.y+10), (sound_rect.x+20, sound_rect.y+5), (sound_rect.x+20, sound_rect.y+35), (sound_rect.x+10, sound_rect.y+30)])
            pygame.draw.circle(screen, (0,0,0), (sound_rect.x+30, sound_rect.y+20), 5, 2)
        else:
            pygame.draw.line(screen, (255,0,0), (sound_rect.x+10, sound_rect.y+10), (sound_rect.x+30, sound_rect.y+30), 3)
            pygame.draw.line(screen, (255,0,0), (sound_rect.x+30, sound_rect.y+10), (sound_rect.x+10, sound_rect.y+30), 3)

    def draw_difficulty_menu(self):
        screen.fill((250, 250, 240))
        draw_paper_texture(screen)

        title = "Select Difficulty"
        draw_text_with_outline(screen, title, self.font_large, (0,0,0), (50,50,50), (WIDTH//2 - self.font_large.size(title)[0]//2, 80), 2)

        difficulties = ["Easy", "Medium", "Hard", "Overkill"]
        colors = [(34, 197, 94), (234, 179, 8), (249, 115, 22), (220, 38, 38)]
        y_start = 200
        mouse_pos = pygame.mouse.get_pos()
        self.hover_difficulty = None

        for i, (diff, col) in enumerate(zip(difficulties, colors)):
            rect = pygame.Rect(WIDTH//2 - 200, y_start + i*80, 400, 60)
            hover = rect.collidepoint(mouse_pos)
            if hover:
                self.hover_difficulty = diff
                pygame.draw.rect(screen, col, rect, border_radius=10)
                pygame.draw.rect(screen, (0,0,0), rect, 3, border_radius=10)
                if self.last_hover != diff and self.sound_enabled:
                    snd_hover.play()
                    self.last_hover = diff
            else:
                pygame.draw.rect(screen, (255,255,255), rect, border_radius=10)
                pygame.draw.rect(screen, (0,0,0), rect, 3, border_radius=10)
            draw_text_with_outline(screen, diff, self.font_medium, (0,0,0) if not hover else (255,255,255), (50,50,50), (rect.x + 20, rect.y + 15), 1)

        desc_diff = self.hover_difficulty if self.hover_difficulty else self.difficulty
        desc = DIFFICULTY_DESC.get(desc_diff, "")
        desc_font = pygame.font.Font(None, 28)
        draw_text_with_outline(screen, desc, desc_font, (80,80,80), (0,0,0), (WIDTH//2 - desc_font.size(desc)[0]//2, 520), 1)

        back_rect = pygame.Rect(20, 20, 100, 40)
        pygame.draw.rect(screen, (200,200,200), back_rect, border_radius=5)
        pygame.draw.rect(screen, (0,0,0), back_rect, 2, border_radius=5)
        draw_text_with_outline(screen, "Back", self.font_small, (0,0,0), (50,50,50), (back_rect.x+10, back_rect.y+8), 1)

    def draw_game_screen(self):
        screen.fill((250, 250, 240))
        draw_paper_texture(screen)

        home_rect = pygame.Rect(20, 20, 40, 40)
        pygame.draw.rect(screen, (200,200,200), home_rect, border_radius=5)
        for i in range(3):
            y = home_rect.y + 10 + i*8
            pygame.draw.line(screen, (0,0,0), (home_rect.x+10, y), (home_rect.x+30, y), 3)

        mode_text = "2 Players" if self.game_mode == "2p" else f"vs CPU ({self.difficulty})"
        draw_text_with_outline(screen, mode_text, self.font_medium, (0,0,0), (50,50,50), (WIDTH//2 - self.font_medium.size(mode_text)[0]//2, 25), 1)

        sound_rect = pygame.Rect(WIDTH-60, 20, 40, 40)
        pygame.draw.circle(screen, (200,200,200), sound_rect.center, 20)
        if self.sound_enabled:
            pygame.draw.polygon(screen, (0,0,0), [(sound_rect.x+10, sound_rect.y+10), (sound_rect.x+20, sound_rect.y+5), (sound_rect.x+20, sound_rect.y+35), (sound_rect.x+10, sound_rect.y+30)])
            pygame.draw.circle(screen, (0,0,0), (sound_rect.x+30, sound_rect.y+20), 5, 2)
        else:
            pygame.draw.line(screen, (255,0,0), (sound_rect.x+10, sound_rect.y+10), (sound_rect.x+30, sound_rect.y+30), 3)
            pygame.draw.line(screen, (255,0,0), (sound_rect.x+30, sound_rect.y+10), (sound_rect.x+10, sound_rect.y+30), 3)

        box_width, box_height = 80, 60
        gap = 20
        total_width = 3 * box_width + 2 * gap
        start_x = (WIDTH - total_width) // 2
        score_y = HEIGHT - 80

        x_rect = pygame.Rect(start_x, score_y, box_width, box_height)
        pygame.draw.rect(screen, (239, 68, 68), x_rect, border_radius=5)
        pygame.draw.rect(screen, (0,0,0), x_rect, 2, border_radius=5)
        x_text = "X"
        x_surf = self.font_small.render(x_text, True, (255,255,255))
        draw_text_with_outline(screen, x_text, self.font_small, (255,255,255), (0,0,0), (x_rect.centerx - x_surf.get_width()//2, x_rect.y + 5), 1)
        x_score_surf = self.font_score.render(str(self.scores["X"]), True, (255,255,255))
        draw_text_with_outline(screen, str(self.scores["X"]), self.font_score, (255,255,255), (0,0,0), (x_rect.centerx - x_score_surf.get_width()//2, x_rect.y + 30), 1)

        d_rect = pygame.Rect(start_x + box_width + gap, score_y, box_width, box_height)
        pygame.draw.rect(screen, (107, 114, 128), d_rect, border_radius=5)
        pygame.draw.rect(screen, (0,0,0), d_rect, 2, border_radius=5)
        draws_text = "Draws"
        draws_surf = self.font_tiny.render(draws_text, True, (255,255,255))
        draw_text_with_outline(screen, draws_text, self.font_tiny, (255,255,255), (0,0,0), (d_rect.centerx - draws_surf.get_width()//2, d_rect.y + 5), 1)
        draws_score_surf = self.font_score.render(str(self.scores["Draws"]), True, (255,255,255))
        draw_text_with_outline(screen, str(self.scores["Draws"]), self.font_score, (255,255,255), (0,0,0), (d_rect.centerx - draws_score_surf.get_width()//2, d_rect.y + 30), 1)

        o_rect = pygame.Rect(start_x + 2*(box_width + gap), score_y, box_width, box_height)
        pygame.draw.rect(screen, (59, 130, 246), o_rect, border_radius=5)
        pygame.draw.rect(screen, (0,0,0), o_rect, 2, border_radius=5)
        o_text = "O"
        o_surf = self.font_small.render(o_text, True, (255,255,255))
        draw_text_with_outline(screen, o_text, self.font_small, (255,255,255), (0,0,0), (o_rect.centerx - o_surf.get_width()//2, o_rect.y + 5), 1)
        o_score_surf = self.font_score.render(str(self.scores["O"]), True, (255,255,255))
        draw_text_with_outline(screen, str(self.scores["O"]), self.font_score, (255,255,255), (0,0,0), (o_rect.centerx - o_score_surf.get_width()//2, o_rect.y + 30), 1)

        turn_y = 120
        turn_text = f"Turn: {self.current_player}"
        if self.game_mode == "ai" and self.current_player == "O" and self.status == "playing":
            turn_text += " (thinking...)"
        draw_text_with_outline(screen, turn_text, self.font_small, (0,0,0), (50,50,50), (WIDTH//2 - self.font_small.size(turn_text)[0]//2, turn_y), 1)

        board_size = 360
        board_x = (WIDTH - board_size) // 2
        board_y = 150
        cell_size = board_size // 3

        current_time = pygame.time.get_ticks()
        for i in range(9):
            row = i // 3
            col = i % 3
            rect = pygame.Rect(board_x + col * cell_size, board_y + row * cell_size, cell_size, cell_size)

            if self.winning_line and i in self.winning_line:
                pulse = int(20 * math.sin(current_time * 0.005) + 20)
                color = (255, 240, 200 - pulse//2)
            else:
                color = (255, 255, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)

            if self.board[i]:
                symbol = self.board[i]
                if i in self.cell_animations:
                    elapsed = current_time - self.cell_animations[i]
                    if elapsed < 300:
                        scale = min(1.0, elapsed / 200)
                        rounded_scale = round(scale * 20) / 20
                        if rounded_scale < 0.05:
                            rounded_scale = 0.05
                        elif rounded_scale > 1.0:
                            rounded_scale = 1.0
                        surf = self.anim_cache[symbol][rounded_scale]
                    else:
                        surf = self.anim_cache[symbol][1.0]
                else:
                    surf = self.anim_cache[symbol][1.0]
                rect_center = rect.center
                screen.blit(surf, (rect_center[0] - surf.get_width()//2,
                                   rect_center[1] - surf.get_height()//2))
            else:
                if rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.draw.rect(screen, (230, 230, 230), rect, 2)

        self.draw_ai_message()

    def draw_ai_message(self):
        if not self.ai_message:
            return
        elapsed = pygame.time.get_ticks() - self.ai_message_time
        if elapsed > 3000:
            self.ai_message = None
            return

        bubble = pygame.Surface((300, 80), pygame.SRCALPHA)
        bubble.fill((255, 255, 255, 230))
        pygame.draw.rect(bubble, (59, 130, 246), bubble.get_rect(), 3, border_radius=10)
        pygame.draw.polygon(bubble, (59, 130, 246), [(145, 80), (155, 80), (150, 90)])
        lines = self.ai_message.split('\n')
        y_offset = 10
        for line in lines:
            text = self.font_tiny.render(line, True, (0, 0, 0))
            bubble.blit(text, (10, y_offset))
            y_offset += 20

        screen.blit(bubble, (WIDTH//2 - 150, 20))

    def draw_game_over_modal(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        modal_w, modal_h = 400, 300
        modal_x = (WIDTH - modal_w) // 2
        modal_y = (HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
        pygame.draw.rect(screen, (250, 250, 240), modal_rect, border_radius=15)
        pygame.draw.rect(screen, (0,0,0), modal_rect, 3, border_radius=15)

        if self.status == "won":
            result_text = "You Win!"
            color = (34, 197, 94)
            icon = ""
        elif self.status == "lost":
            result_text = "You Lose!"
            color = (239, 68, 68)
            icon = ""
        else:
            result_text = "It's a Draw!"
            color = (107, 114, 128)
            icon = ""

        icon_font = pygame.font.Font(None, 80)
        icon_surf = icon_font.render(icon, True, color)
        screen.blit(icon_surf, (modal_x + modal_w//2 - icon_surf.get_width()//2, modal_y + 30))

        draw_text_with_outline(screen, result_text, self.font_large, color, (50,50,50), (modal_x + modal_w//2 - self.font_large.size(result_text)[0]//2, modal_y + 120), 2)

        btn_again = pygame.Rect(modal_x + 50, modal_y + 200, 140, 50)
        btn_menu = pygame.Rect(modal_x + 210, modal_y + 200, 140, 50)
        mouse_pos = pygame.mouse.get_pos()

        for rect, text in [(btn_again, "Play Again"), (btn_menu, "Main Menu")]:
            hover = rect.collidepoint(mouse_pos)
            if hover:
                pygame.draw.rect(screen, (100,100,100), rect, border_radius=5)
                if self.last_hover != text and self.sound_enabled:
                    snd_hover.play()
                    self.last_hover = text
            else:
                pygame.draw.rect(screen, (255,255,255), rect, border_radius=5)
            pygame.draw.rect(screen, (0,0,0), rect, 2, border_radius=5)
            draw_text_with_outline(screen, text, self.font_small, (0,0,0), (50,50,50), (rect.x+10, rect.y+12), 1)

    def run(self):
        while True:
            current_time = pygame.time.get_ticks()
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == MOUSEBUTTONDOWN:
                    if self.sound_enabled:
                        snd_click.play()
                    if self.game_mode == "menu":
                        if 300 < mouse_pos[0] < 600:
                            if 300 < mouse_pos[1] < 360:
                                self.game_mode = "2p"
                                self.reset_board(keep_scores=True)
                            elif 380 < mouse_pos[1] < 440:
                                self.game_mode = "difficulty"
                            elif 460 < mouse_pos[1] < 520:
                                pygame.quit()
                                sys.exit()
                        if (WIDTH-60) < mouse_pos[0] < (WIDTH-20) and 20 < mouse_pos[1] < 60:
                            self.sound_enabled = not self.sound_enabled

                    elif self.game_mode == "difficulty":
                        if 20 < mouse_pos[0] < 120 and 20 < mouse_pos[1] < 60:
                            self.game_mode = "menu"
                        else:
                            for i, diff in enumerate(["Easy", "Medium", "Hard", "Overkill"]):
                                rect = pygame.Rect(WIDTH//2 - 200, 200 + i*80, 400, 60)
                                if rect.collidepoint(mouse_pos):
                                    self.difficulty = diff
                                    self.game_mode = "ai"
                                    self.reset_board(keep_scores=True)
                                    break
                        if (WIDTH-60) < mouse_pos[0] < (WIDTH-20) and 20 < mouse_pos[1] < 60:
                            self.sound_enabled = not self.sound_enabled

                    else:
                        if 20 < mouse_pos[0] < 60 and 20 < mouse_pos[1] < 60:
                            self.game_mode = "menu"
                            self.reset_board(keep_scores=False)
                        if (WIDTH-60) < mouse_pos[0] < (WIDTH-20) and 20 < mouse_pos[1] < 60:
                            self.sound_enabled = not self.sound_enabled

                        if not self.game_over_modal and current_time >= self.modal_delay_until:
                            board_size = 360
                            board_x = (WIDTH - board_size) // 2
                            board_y = 150
                            cell_size = board_size // 3
                            for i in range(9):
                                row = i // 3
                                col = i % 3
                                rect = pygame.Rect(board_x + col * cell_size, board_y + row * cell_size, cell_size, cell_size)
                                if rect.collidepoint(mouse_pos):
                                    if self.game_mode == "ai" and self.current_player != "X":
                                        break
                                    if self.make_move(i):
                                        if (self.game_mode == "ai" and self.current_player == "O"
                                                and self.status == "playing"):
                                            pygame.time.set_timer(pygame.USEREVENT, 500)
                                    break

                        if self.game_over_modal:
                            modal_x = (WIDTH - 400) // 2
                            modal_y = (HEIGHT - 300) // 2
                            btn_again = pygame.Rect(modal_x + 50, modal_y + 200, 140, 50)
                            btn_menu = pygame.Rect(modal_x + 210, modal_y + 200, 140, 50)
                            if btn_again.collidepoint(mouse_pos):
                                self.game_over_modal = False
                                self.reset_board(keep_scores=True)
                            elif btn_menu.collidepoint(mouse_pos):
                                self.game_over_modal = False
                                self.game_mode = "menu"
                                self.reset_board(keep_scores=False)

                if event.type == pygame.USEREVENT:
                    pygame.time.set_timer(pygame.USEREVENT, 0)
                    if (self.game_mode == "ai" and self.current_player == "O"
                            and self.status == "playing"):
                        move = self.get_ai_move(self.board)
                        if move is not None:
                            self.make_move(move)

            if self.modal_delay_until and current_time >= self.modal_delay_until and self.status != "playing":
                self.game_over_modal = True
                self.modal_delay_until = 0

            if self.game_mode == "menu":
                self.draw_menu()
            elif self.game_mode == "difficulty":
                self.draw_difficulty_menu()
            else:
                self.draw_game_screen()
                if self.game_over_modal:
                    self.draw_game_over_modal()

            self.update_particles()
            self.draw_particles()

            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    game = TicTacToeGame()
    game.run()
