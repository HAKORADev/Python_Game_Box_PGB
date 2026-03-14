import pygame
import sys
import random
import time
import numpy as np
import pyganim
from scipy import signal

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 1280, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Keyboard Singer")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)
big_font = pygame.font.Font(None, 72)
small_font = pygame.font.Font(None, 20)

RED = (200, 0, 0)
GREEN = (0, 200, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

def generate_tone(frequency, duration=0.3, sample_rate=44100, waveform='sine', weight=1.0):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    if waveform == 'sine':
        tone = np.sin(2 * np.pi * frequency * t)
    elif waveform == 'square':
        tone = signal.square(2 * np.pi * frequency * t)
    elif waveform == 'sawtooth':
        tone = signal.sawtooth(2 * np.pi * frequency * t)
    elif waveform == 'noise':
        tone = np.random.uniform(-1, 1, t.shape)
    else:
        tone = np.sin(2 * np.pi * frequency * t)

    envelope = np.linspace(1, 0, int(sample_rate * duration))
    tone = tone * envelope * weight
    tone = (tone * 32767).astype(np.int16)
    stereo = np.column_stack((tone, tone))
    return pygame.sndarray.make_sound(stereo)

key_freq = {chr(i): 200 + (i - 65) * 30 for i in range(65, 91)}

bank_sounds = {
    1: {'name': "Piano", 'mult': 1.0, 'wave': "sine"},
    2: {'name': "Electric Guitar", 'mult': 1.2, 'wave': "square"},
    3: {'name': "BeatBox", 'mult': 1.0, 'wave': "noise"},
    4: {'name': "Organ", 'mult': 1.5, 'wave': "sine"},
    5: {'name': "Flute", 'mult': 1.1, 'wave': "sine"},
    6: {'name': "Violin", 'mult': 0.9, 'wave': "sawtooth"},
    7: {'name': "Trumpet", 'mult': 1.3, 'wave': "square"},
    8: {'name': "Bass", 'mult': 0.7, 'wave': "sine"},
    9: {'name': "Synth", 'mult': 1.4, 'wave': "sawtooth"},
    0: {'name': "Xylophone", 'mult': 1.0, 'wave': "square"}
}

class BackgroundEffect:
    def __init__(self, num=50):
        self.particles = []
        for i in range(num):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            r = random.randint(5, 15)
            dx = random.uniform(-1, 1)
            dy = random.uniform(-1, 1)
            color = (random.randint(50, 100), random.randint(0, 50), random.randint(100, 255))
            self.particles.append([x, y, dx, dy, r, color])

    def update(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            if p[0] < 0: p[0] = WIDTH
            if p[0] > WIDTH: p[0] = 0
            if p[1] < 0: p[1] = HEIGHT
            if p[1] > HEIGHT: p[1] = 0

    def draw(self, surface):
        for p in self.particles:
            pygame.draw.circle(surface, p[5], (int(p[0]), int(p[1])), p[4])

class Button:
    def __init__(self, char, x, y, width, height):
        self.char = char
        self.rect = pygame.Rect(x, y, width, height)
        self.active = False
        self.correct = None

    def draw(self, surface):
        if self.active:
            col = GREEN
        else:
            col = RED

        if self.correct is True:
            col = GREEN
        elif self.correct is False:
            col = (255, 50, 50)

        pygame.draw.rect(surface, col, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)
        txt = small_font.render(self.char, True, WHITE)
        r = txt.get_rect(center=self.rect.center)
        surface.blit(txt, r)

    def reset(self):
        self.active = False
        self.correct = None

class KeyboardPanel:
    def __init__(self, offset_x, offset_y, bank_number):
        self.buttons = []
        self.sequence = ""
        self.bank_number = bank_number
        ks = 30
        gap = 5
        cols = 5
        for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
            col = i % cols
            row = i // cols
            x = offset_x + col * (ks + gap)
            y = offset_y + row * (ks + gap)
            self.buttons.append(Button(c, x, y, ks, ks))

    def draw(self, surface):
        for btn in self.buttons:
            btn.draw(surface)

    def reset_buttons(self):
        for btn in self.buttons:
            btn.reset()

    def get_button(self, char):
        for btn in self.buttons:
            if btn.char == char.upper():
                return btn
        return None

class KeytapperKeyboardPanel:
    def __init__(self, offset_x, offset_y):
        self.buttons = []
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        key_size = 50
        gap = 10
        row1 = letters[:13]
        row2 = letters[13:]
        for i, ch in enumerate(row1):
            x = offset_x + i * (key_size + gap)
            y = offset_y
            self.buttons.append(Button(ch, x, y, key_size, key_size))
        for i, ch in enumerate(row2):
            x = offset_x + i * (key_size + gap)
            y = offset_y + key_size + gap
            self.buttons.append(Button(ch, x, y, key_size, key_size))

    def draw(self, surface):
        for btn in self.buttons:
            btn.draw(surface)

    def reset_buttons(self):
        for btn in self.buttons:
            btn.reset()

    def get_button(self, char):
        for btn in self.buttons:
            if btn.char == char.upper():
                return btn
        return None

def create_flash_animation(rect):
    frames = []
    for a in (255, 200, 150, 100, 50):
        s = pygame.Surface((rect.width, rect.height))
        s.fill(YELLOW)
        s.set_alpha(a)
        frames.append((s, 50))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return (anim, rect.topleft, pygame.time.get_ticks())

def create_blue_flash_animation(rect):
    frames = []
    for a in (255, 200, 150, 100, 50):
        s = pygame.Surface((rect.width, rect.height))
        s.fill(BLUE)
        s.set_alpha(a)
        frames.append((s, 50))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return (anim, rect.topleft, pygame.time.get_ticks())

def create_red_flash_animation(rect):
    frames = []
    for a in (255, 200, 150, 100, 50):
        s = pygame.Surface((rect.width, rect.height))
        s.fill((255, 0, 0))
        s.set_alpha(a)
        frames.append((s, 50))
    anim = pyganim.PygAnimation(frames)
    anim.play()
    return (anim, rect.topleft, pygame.time.get_ticks())

class Game:
    def __init__(self):
        self.mode = "menu"
        self.animations = []
        self.active_bank = 1
        self.tone_delay = 200
        self.tone_weight = 1.0
        self.tone_length = 1.0
        self.bg_effect = BackgroundEffect(50)
        self.keyboards = {}
        panel_width = 170
        panel_height = 205
        margin_x = 30
        for idx, bank in enumerate([1, 2, 3, 4, 5]):
            x = margin_x + idx * (panel_width + margin_x)
            y = 50
            self.keyboards[bank] = KeyboardPanel(x, y, bank)
        for idx, bank in enumerate([6, 7, 8, 9, 0]):
            x = margin_x + idx * (panel_width + margin_x)
            y = panel_height + 50 + 50
            self.keyboards[bank] = KeyboardPanel(x, y, bank)

        keytapper_total_width = 770
        x_center = (WIDTH - keytapper_total_width) // 2
        y_keyboard = 400
        self.keytap_keyboard = KeytapperKeyboardPanel(x_center, y_keyboard)
        self.keytap_active_word = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        self.keytap_input = ""
        self.keytap_start_time = pygame.time.get_ticks()
        self.keytap_score = 0
        self.keytap_message = ""
        self.keytap_message_color = WHITE
        self.sequence_playback = False
        self.sequence_queue = []
        self.sequence_bank = None
        self.last_note_time = 0
        self.keytap_playback = False
        self.keytap_sequence_queue = []
        self.keytap_last_play_time = 0
        self.keytap_total_paused_duration = 0
        self.keytap_pause_timestamp = None
        self.keytap_was_correct = None
        self.autoplay = False
        self.longoly = False
        self.longoly_sounds = {}

    def draw(self, surface):
        if self.mode == "menu":
            self.draw_menu(surface)
        elif self.mode == "free":
            self.draw_free(surface)
        elif self.mode == "keytapper":
            self.draw_keytapper(surface)
        elif self.mode == "keytapper_result":
            self.draw_keytapper_result(surface)

        now = pygame.time.get_ticks()
        for anim_tuple in self.animations[:]:
            anim, pos, start = anim_tuple
            anim.blit(surface, pos)
            if now - start > 300:
                self.animations.remove(anim_tuple)

    def draw_menu(self, surface):
        surface.fill(BLACK)
        title = big_font.render("Keyboard Singer", True, YELLOW)
        opt1 = font.render("Press 1 for Free Play", True, WHITE)
        opt2 = font.render("Press 2 for Key Tapper", True, WHITE)
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))
        surface.blit(opt1, (WIDTH // 2 - opt1.get_width() // 2, 300))
        surface.blit(opt2, (WIDTH // 2 - opt2.get_width() // 2, 350))

    def draw_free(self, surface):
        surface.fill(BLACK)
        self.bg_effect.update()
        self.bg_effect.draw(surface)
        for keyboard in self.keyboards.values():
            keyboard.draw(surface)

        length_text = small_font.render("Length: {:.2f}".format(self.tone_length), True, WHITE)
        surface.blit(length_text, (10, HEIGHT - 160))

        autoplay_text = small_font.render("Autoplay: " + ("on" if self.autoplay else "off"), True, WHITE)
        surface.blit(autoplay_text, (10, HEIGHT - 140))

        longoly_text = small_font.render("Longoly: " + (("on" if self.longoly else "off") if self.autoplay else "off"), True, WHITE)
        surface.blit(longoly_text, (10, HEIGHT - 120))

        active_keyboard = self.keyboards[self.active_bank]
        if active_keyboard.sequence:
            rand_label = small_font.render("Randomizer: " + active_keyboard.sequence, True, YELLOW)
            surface.blit(rand_label, (10, HEIGHT - 100))

        delay_text = small_font.render("Delay: {} ms".format(self.tone_delay), True, WHITE)
        weight_text = small_font.render("Weight: {:.1f}".format(self.tone_weight), True, WHITE)
        surface.blit(delay_text, (10, HEIGHT - 40))
        surface.blit(weight_text, (10, HEIGHT - 20))
        self.draw_bank_labels(surface)

    def draw_bank_labels(self, surface):
        for bank, keyboard in self.keyboards.items():
            rect = pygame.Rect(keyboard.buttons[0].rect.x - 5, keyboard.buttons[0].rect.y - 30, 180, 30)
            col = GREEN if bank == self.active_bank else WHITE
            pygame.draw.rect(surface, col, rect, 2)
            lbl = small_font.render("Bank {}: {}".format(bank, bank_sounds[bank]['name']), True, WHITE)
            surface.blit(lbl, (rect.x + 5, rect.y + 5))

    def draw_keytapper(self, surface):
        surface.fill(BLACK)
        self.bg_effect.update()
        self.bg_effect.draw(surface)
        title = font.render("Key Tapper Mode", True, WHITE)
        word_text = font.render("Word: " + self.keytap_active_word, True, WHITE)
        input_text = font.render("Your Input: " + self.keytap_input, True, WHITE)
        now = pygame.time.get_ticks()

        if self.keytap_playback and self.keytap_pause_timestamp is not None:
            frozen_elapsed = (self.keytap_pause_timestamp - self.keytap_start_time - self.keytap_total_paused_duration) / 1000.0
            remaining = max(0, 5 - frozen_elapsed)
        else:
            elapsed = (now - self.keytap_start_time - self.keytap_total_paused_duration) / 1000.0
            remaining = max(0, 5 - elapsed)

        timer_text = font.render("Time Left: {:.1f}s".format(remaining), True, WHITE)
        score_text = font.render("Score: {}".format(self.keytap_score), True, WHITE)

        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        surface.blit(word_text, (WIDTH // 2 - word_text.get_width() // 2, 150))
        surface.blit(input_text, (WIDTH // 2 - input_text.get_width() // 2, 200))
        surface.blit(timer_text, (WIDTH // 2 - timer_text.get_width() // 2, 250))
        surface.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, 300))

        if self.keytap_message:
            msg_text = font.render(self.keytap_message, True, self.keytap_message_color)
            surface.blit(msg_text, (WIDTH // 2 - msg_text.get_width() // 2, 350))
        self.keytap_keyboard.draw(surface)

    def draw_keytapper_result(self, surface):
        surface.fill(BLACK)
        self.bg_effect.update()
        self.bg_effect.draw(surface)
        res_text = font.render("Game Over! Your Score: {}".format(self.keytap_score), True, WHITE)
        info_text = font.render("Press any key to return to Menu", True, WHITE)
        surface.blit(res_text, (WIDTH // 2 - res_text.get_width() // 2, HEIGHT // 2 - 50))
        surface.blit(info_text, (WIDTH // 2 - info_text.get_width() // 2, HEIGHT // 2))

    def start_free_sequence(self):
        self.sequence_queue = list(self.keyboards[self.active_bank].sequence)
        self.sequence_bank = self.active_bank
        self.last_note_time = pygame.time.get_ticks()
        self.sequence_playback = True
        self.keyboards[self.active_bank].reset_buttons()
        self.keyboards[self.active_bank].sequence = ""

    def start_keytapper(self):
        self.keytap_active_word = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        self.keytap_input = ""
        self.keytap_start_time = pygame.time.get_ticks()
        self.keytap_total_paused_duration = 0
        self.keytap_pause_timestamp = None
        self.keytap_message = ""
        self.keytap_keyboard.reset_buttons()
        self.keytap_score = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if self.mode == "menu":
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.mode = "free"
                    elif event.key == pygame.K_2:
                        self.mode = "keytapper"
                        self.start_keytapper()
        elif self.mode == "free":
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.autoplay = not self.autoplay
                        if not self.autoplay:
                            self.longoly = False
                    elif event.key == pygame.K_BACKSPACE:
                        if self.autoplay:
                            self.longoly = not self.longoly
                    elif event.key == pygame.K_ESCAPE:
                        self.mode = "menu"
                    elif event.key == pygame.K_RETURN:
                        if not self.autoplay and not self.sequence_playback:
                            self.start_free_sequence()
                    elif event.key in (pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9):
                        if event.key == pygame.K_0:
                            self.active_bank = 0
                        else:
                            self.active_bank = int(pygame.key.name(event.key))
                    elif event.key == pygame.K_RSHIFT:
                        self.tone_delay = max(50, self.tone_delay - 50)
                    elif event.key == pygame.K_RCTRL:
                        self.tone_delay += 50
                    elif event.key == pygame.K_LSHIFT:
                        self.tone_weight += 0.1
                    elif event.key == pygame.K_LCTRL:
                        self.tone_weight = max(0.1, self.tone_weight - 0.1)
                    elif event.key == pygame.K_LALT:
                        self.tone_length = max(0.1, self.tone_length - 0.1)
                    elif event.key == pygame.K_RALT:
                        self.tone_length = min(10, self.tone_length + 0.1)
                    elif pygame.K_a <= event.key <= pygame.K_z:
                        char = chr(event.key).upper()
                        if self.autoplay:
                            if self.longoly:
                                freq = key_freq[char] * bank_sounds[self.active_bank]['mult']
                                s = generate_tone(freq, duration=0.3 * self.tone_length, waveform=bank_sounds[self.active_bank]['wave'], weight=self.tone_weight)
                                channel = s.play(loops=-1)
                                self.longoly_sounds[char] = (s, channel)
                            else:
                                self.play_note(self.active_bank, char)
                        else:
                            self.keyboards[self.active_bank].sequence += char
                            btn = self.keyboards[self.active_bank].get_button(char)
                            if btn:
                                btn.active = True
                                self.animations.append(create_flash_animation(btn.rect))
                    elif event.key == pygame.K_TAB:
                        length = random.randint(3, 52)
                        random_seq = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=length))
                        self.keyboards[self.active_bank].sequence = random_seq
                elif event.type == pygame.KEYUP:
                    if self.autoplay and self.longoly:
                        if pygame.K_a <= event.key <= pygame.K_z:
                            char = chr(event.key).upper()
                            if char in self.longoly_sounds:
                                s, channel = self.longoly_sounds.pop(char)
                                channel.stop()
                                self.play_note(self.active_bank, char)
        elif self.mode == "keytapper":
            now = pygame.time.get_ticks()
            if not self.keytap_playback:
                elapsed = (now - self.keytap_start_time - self.keytap_total_paused_duration) / 1000.0
                if elapsed > 5:
                    self.keytap_message = "Time's up! Incorrect"
                    self.keytap_message_color = (255, 0, 0)
                    self.mode = "keytapper_result"

            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and not self.keytap_playback:
                        self.keytap_pause_timestamp = pygame.time.get_ticks()
                        if self.keytap_input == self.keytap_active_word:
                            self.keytap_message = "Correct"
                            self.keytap_message_color = (0, 255, 0)
                            self.keytap_sequence_queue = list(self.keytap_active_word)
                            self.keytap_last_play_time = pygame.time.get_ticks()
                            self.keytap_playback = True
                            self.keytap_was_correct = True
                            self.keytap_score += 1
                        else:
                            self.keytap_message = "Incorrect"
                            self.keytap_message_color = (255, 0, 0)
                            self.keytap_sequence_queue = list(self.keytap_input)
                            self.keytap_last_play_time = pygame.time.get_ticks()
                            self.keytap_playback = True
                            self.keytap_was_correct = False
                    elif event.key == pygame.K_BACKSPACE and not self.keytap_playback:
                        self.keytap_input = self.keytap_input[:-1]
                        self.keytap_keyboard.reset_buttons()
                        for ch in self.keytap_input:
                            btn = self.keytap_keyboard.get_button(ch)
                            if btn: btn.active = True
                    elif not self.keytap_playback and event.unicode.isalpha():
                        self.keytap_input += event.unicode.upper()
                        self.keytap_keyboard.reset_buttons()
                        for ch in self.keytap_input:
                            btn = self.keytap_keyboard.get_button(ch)
                            if btn: btn.active = True
        elif self.mode == "keytapper_result":
            for event in events:
                if event.type == pygame.KEYDOWN:
                    self.mode = "menu"

    def play_note(self, bank, char):
        freq = key_freq[char] * bank_sounds[bank]['mult']
        tone = generate_tone(freq, duration=0.3 * self.tone_length, waveform=bank_sounds[bank]['wave'], weight=self.tone_weight)
        tone.play()

    def play_note_keytap(self, char):
        freq = key_freq[char] * bank_sounds[1]['mult']
        tone = generate_tone(freq, duration=0.3 * self.tone_length, waveform=bank_sounds[1]['wave'], weight=1.0)
        tone.play()

    def update(self):
        now = pygame.time.get_ticks()
        if self.mode == "free" and self.sequence_playback:
            if self.sequence_queue:
                if now - self.last_note_time >= self.tone_delay:
                    note = self.sequence_queue.pop(0)
                    self.play_note(self.sequence_bank, note)
                    btn = self.keyboards[self.sequence_bank].get_button(note)
                    if btn:
                        self.animations.append(create_blue_flash_animation(btn.rect))
                    self.last_note_time = now
            else:
                self.sequence_playback = False
        elif self.mode == "keytapper":
            if self.keytap_playback:
                if self.keytap_sequence_queue:
                    if now - self.keytap_last_play_time >= 200:
                        letter = self.keytap_sequence_queue.pop(0)
                        self.play_note_keytap(letter)
                        btn = self.keytap_keyboard.get_button(letter)
                        if btn:
                            if self.keytap_message == "Correct":
                                self.animations.append(create_blue_flash_animation(btn.rect))
                            else:
                                self.animations.append(create_red_flash_animation(btn.rect))
                        self.keytap_last_play_time = now
                else:
                    additional_pause = pygame.time.get_ticks() - self.keytap_pause_timestamp
                    self.keytap_total_paused_duration += additional_pause
                    self.keytap_pause_timestamp = None
                    self.keytap_playback = False
                    if self.keytap_was_correct:
                        self.keytap_input = ""
                        self.keytap_keyboard.reset_buttons()
                        self.keytap_message = ""
                        self.keytap_active_word = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
                        self.keytap_start_time = pygame.time.get_ticks()
                        self.keytap_total_paused_duration = 0
                    else:
                        self.keytap_input = ""
                        self.keytap_keyboard.reset_buttons()
                        self.keytap_message = ""

game = Game()
running = True
while running:
    events = pygame.event.get()
    game.handle_events(events)
    game.update()
    screen.fill(BLACK)
    game.draw(screen)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
