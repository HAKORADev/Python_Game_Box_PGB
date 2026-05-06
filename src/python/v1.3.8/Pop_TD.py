#!/usr/bin/env python3

import pygame
import math
import random
import sys
import struct
import io
import numpy as np
from collections import defaultdict

_GPU_AVAILABLE = False
try:
    from OpenGL.GL import *
    from OpenGL.GL import shaders as _gl_shaders_mod
    import ctypes as _ctypes
    _GPU_AVAILABLE = True
except ImportError:
    _GPU_AVAILABLE = False

SCREEN_W, SCREEN_H = 1280, 720
GAME_W = 1020
PANEL_W = SCREEN_W - GAME_W
CELL = 40
COLS = GAME_W // CELL
ROWS = SCREEN_H // CELL
FPS = 60
SELL_RATIO = 0.7
USE_GPU_RENDER = True

C_GRASS       = (76, 153, 0)
C_GRASS2      = (68, 140, 0)
C_PATH        = (194, 154, 108)
C_PATH_EDGE   = (160, 126, 82)
C_PANEL_BG    = (40, 40, 50)
C_PANEL_BORDER= (80, 80, 100)
C_WHITE       = (255, 255, 255)
C_BLACK       = (0, 0, 0)
C_RED         = (220, 50, 50)
C_GREEN       = (50, 200, 50)
C_GOLD        = (255, 215, 0)
C_GRAY        = (150, 150, 150)
C_DARK_GRAY   = (80, 80, 80)
C_BLUE        = (50, 100, 220)
C_YELLOW      = (255, 220, 0)
C_ORANGE      = (255, 140, 0)
C_PURPLE      = (160, 50, 220)
C_CYAN        = (0, 200, 220)
C_PINK        = (255, 105, 180)
C_LIME        = (120, 255, 50)
C_BROWN       = (139, 90, 43)

DMG_SHARP     = "sharp"
DMG_EXPLOSION = "explosion"
DMG_ICE       = "ice"
DMG_ENERGY    = "energy"

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = current + word + " "
        if font.size(test)[0] <= max_width:
            current = test
        else:
            lines.append(current.strip())
            current = word + " "
    if current:
        lines.append(current.strip())
    return lines

def make_sound(func, duration, volume=0.3, sr=22050):
    n = int(sr * duration)
    t = np.linspace(0, duration, n, dtype=np.float32)
    wave = func(t).astype(np.float32)
    wave = np.clip(wave * volume, -1, 1)
    pcm = (wave * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm])
    buf = io.BytesIO()
    data_size = stereo.nbytes
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(struct.pack('<IHHIIHH', 16, 1, 2, sr, sr*4, 4, 16))
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(stereo.tobytes())
    buf.seek(0)
    return pygame.mixer.Sound(buf)

def gen_pop_sound():
    def f(t):
        freq = 800 - 600 * t / 0.1
        return np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)
    return make_sound(f, 0.1, 0.2)

def gen_place_sound():
    def f(t):
        freq = 300 + 200 * np.exp(-t * 20)
        return np.sin(2 * np.pi * freq * t) * np.exp(-t * 15)
    return make_sound(f, 0.15, 0.25)

def gen_upgrade_sound():
    def f(t):
        freq1 = 600 + 400 * t / 0.2
        return np.sin(2 * np.pi * freq1 * t) * np.exp(-t * 8)
    return make_sound(f, 0.2, 0.25)

def gen_sell_sound():
    def f(t):
        freq = 500 - 300 * t / 0.15
        return np.sin(2 * np.pi * freq * t) * np.exp(-t * 20)
    return make_sound(f, 0.15, 0.2)

def gen_round_sound():
    def f(t):
        return (np.sin(2*np.pi*400*t) + np.sin(2*np.pi*600*t)) * np.exp(-t*6) * 0.5
    return make_sound(f, 0.3, 0.25)

def gen_moab_sound():
    def f(t):
        freq = 150 + 50 * np.sin(2*np.pi*3*t)
        return np.sin(2 * np.pi * freq * t) * np.exp(-t * 3)
    return make_sound(f, 0.5, 0.3)

def gen_explosion_sound():
    rng = np.random.RandomState(42)
    def f(t):
        noise_part = rng.randn(len(t)).astype(np.float32) * np.exp(-t * 15)
        tone = np.sin(2*np.pi*80*t) * np.exp(-t*10)
        return noise_part * 0.4 + tone * 0.6
    return make_sound(f, 0.25, 0.25)

def gen_win_sound():
    def f(t):
        notes = [523, 659, 784, 1047]
        result = np.zeros_like(t)
        for i, note in enumerate(notes):
            start = i * 0.12
            mask = (t >= start).astype(np.float32)
            result += mask * np.sin(2*np.pi*note*t) * np.exp(-(t-start)*6)
        return result
    return make_sound(f, 0.6, 0.25)

def gen_lose_sound():
    def f(t):
        notes = [400, 350, 300, 200]
        result = np.zeros_like(t)
        for i, note in enumerate(notes):
            start = i * 0.15
            mask = (t >= start).astype(np.float32)
            result += mask * np.sin(2*np.pi*note*t) * np.exp(-(t-start)*5)
        return result
    return make_sound(f, 0.7, 0.25)

_sprite_cache = {}

def get_sprite(key, generator):
    if key not in _sprite_cache:
        _sprite_cache[key] = generator()
    return _sprite_cache[key]

def make_bloon_sprite(color, radius, has_stripe=False, stripe_color=None,
                      is_moab=False, hp_frac=1.0, is_rainbow=False, rainbow_t=0):
    if is_rainbow:
        colors = [C_RED, C_ORANGE, C_YELLOW, C_GREEN, C_BLUE, C_PURPLE]
        idx = int(rainbow_t * 6) % len(colors)
        color = colors[idx]

    key = ("bloon", color, radius, has_stripe, stripe_color, is_moab,
           round(hp_frac, 2), is_rainbow, int(rainbow_t * 10) % 60)
    return get_sprite(key, lambda: _gen_bloon(color, radius, has_stripe,
           stripe_color, is_moab, hp_frac))

def _gen_bloon(color, radius, has_stripe=False, stripe_color=None,
               is_moab=False, hp_frac=1.0):
    size = (radius + 6) * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    if is_moab:
        w, h = radius * 2, int(radius * 1.4)
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.ellipse(surf, color, rect)
        cockpit = pygame.Rect(cx - w//4, cy - h//4, w//2, h//3)
        pygame.draw.ellipse(surf, (200, 200, 220), cockpit)
        hl = pygame.Rect(cx - w//3, cy - h//2 + 4, w//2, h//4)
        hl_c = tuple(min(c+40,255) for c in color[:3]) + (120,)
        pygame.draw.ellipse(surf, hl_c, hl)
        bar_w, bar_h = w - 10, 6
        bar_x, bar_y = cx - bar_w // 2, cy + h//2 + 4
        pygame.draw.rect(surf, (60,60,60), (bar_x-1, bar_y-1, bar_w+2, bar_h+2))
        pygame.draw.rect(surf, C_RED, (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surf, C_GREEN, (bar_x, bar_y, int(bar_w*hp_frac), bar_h))
        pygame.draw.ellipse(surf, C_BLACK, rect, 2)
    else:
        pygame.draw.circle(surf, (0,0,0,40), (cx+2, cy+2), radius)
        pygame.draw.circle(surf, color, (cx, cy), radius)
        hl_c = tuple(min(c+80,255) for c in color[:3]) + (180,)
        pygame.draw.circle(surf, hl_c, (cx - radius//3, cy - radius//3), radius//3)
        if has_stripe and stripe_color:
            for dy in range(-3, 4):
                for dx in range(-radius, radius+1):
                    if dx*dx + dy*dy <= radius*radius:
                        px, py = cx + dx, cy + dy
                        if 0 <= px < size and 0 <= py < size:
                            surf.set_at((px, py), (*stripe_color, 180))
        pygame.draw.circle(surf, C_BLACK, (cx, cy), radius, 2)
        pygame.draw.polygon(surf, C_BLACK, [
            (cx-3, cy+radius-2), (cx+3, cy+radius-2), (cx, cy+radius+4)
        ])
    return surf

def make_tower_sprite(tower_type, upgrade_level=0):
    key = ("tower", tower_type, upgrade_level)
    return get_sprite(key, lambda: _gen_tower(tower_type, upgrade_level))

def _gen_tower(tower_type, upgrade_level):
    size = CELL
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2

    if tower_type == "dart":
        pygame.draw.circle(surf, (139, 90, 43), (cx, cy+4), 14)
        pygame.draw.circle(surf, (222, 184, 135), (cx, cy-2), 11)
        pygame.draw.circle(surf, C_WHITE, (cx-4, cy-5), 4)
        pygame.draw.circle(surf, C_WHITE, (cx+4, cy-5), 4)
        pygame.draw.circle(surf, C_BLACK, (cx-3, cy-5), 2)
        pygame.draw.circle(surf, C_BLACK, (cx+5, cy-5), 2)
        pygame.draw.arc(surf, C_BLACK, (cx-4, cy-2, 8, 6), 3.14, 6.28, 1)
        dx = cx + 10 + upgrade_level * 2
        pygame.draw.line(surf, C_YELLOW, (cx+6, cy), (dx, cy-2), 2)
        pygame.draw.polygon(surf, C_RED, [(dx, cy-5), (dx+5, cy-2), (dx, cy+1)])
    elif tower_type == "tack":
        pygame.draw.circle(surf, C_DARK_GRAY, (cx, cy), 14)
        pygame.draw.circle(surf, (180, 180, 200), (cx, cy), 12)
        n_tacks = 8 + upgrade_level * 2
        for i in range(n_tacks):
            a = 2 * math.pi * i / n_tacks
            pygame.draw.line(surf, C_RED,
                (cx+int(10*math.cos(a)), cy+int(10*math.sin(a))),
                (cx+int(16*math.cos(a)), cy+int(16*math.sin(a))), 2)
        pygame.draw.circle(surf, C_YELLOW, (cx, cy), 4)
    elif tower_type == "ice":
        pts = []
        for i in range(6):
            a = math.pi/3*i - math.pi/2
            r = 15 if i%2==0 else 8
            pts.append((cx+r*math.cos(a), cy+r*math.sin(a)))
        pygame.draw.polygon(surf, (150,220,255), pts)
        pygame.draw.polygon(surf, (100,180,230), pts, 2)
        for i in range(3):
            a = math.pi/3*i
            pygame.draw.line(surf, C_WHITE,
                (cx-8*math.cos(a), cy-8*math.sin(a)),
                (cx+8*math.cos(a), cy+8*math.sin(a)), 2)
    elif tower_type == "bomb":
        pygame.draw.rect(surf, (80,80,90), (cx-10, cy+2, 20, 14))
        pygame.draw.rect(surf, (100,100,110), (cx-4, cy-12, 8, 16))
        pygame.draw.circle(surf, (60,60,70), (cx, cy-12), 6)
        pygame.draw.circle(surf, (40,40,50), (cx, cy-12), 4)
        pygame.draw.circle(surf, (60,60,60), (cx-8, cy+16), 5)
        pygame.draw.circle(surf, (60,60,60), (cx+8, cy+16), 5)
    elif tower_type == "super":
        cape_pts = [(cx-12,cy-4),(cx-16,cy+14),(cx+16,cy+14),(cx+12,cy-4)]
        pygame.draw.polygon(surf, (200,30,30), cape_pts)
        pygame.draw.circle(surf, (60,60,120), (cx, cy+2), 12)
        pygame.draw.circle(surf, (222,184,135), (cx, cy-4), 9)
        pygame.draw.rect(surf, (60,60,120), (cx-10, cy-8, 20, 5))
        pygame.draw.circle(surf, C_WHITE, (cx-4, cy-6), 3)
        pygame.draw.circle(surf, C_WHITE, (cx+4, cy-6), 3)
        pygame.draw.circle(surf, C_RED, (cx-4, cy-6), 1)
        pygame.draw.circle(surf, C_RED, (cx+4, cy-6), 1)
    elif tower_type == "sniper":
        pygame.draw.circle(surf, (139,90,43), (cx, cy+4), 12)
        pygame.draw.circle(surf, (222,184,135), (cx, cy-2), 9)
        pygame.draw.rect(surf, (40,80,40), (cx-10, cy-12, 20, 6))
        pygame.draw.rect(surf, (40,80,40), (cx-7, cy-16, 14, 5))
        pygame.draw.line(surf, C_BLACK, (cx-6, cy-5), (cx-1, cy-5), 2)
        pygame.draw.circle(surf, C_BLACK, (cx+3, cy-5), 2)
        pygame.draw.line(surf, (80,80,80), (cx+8, cy-4), (cx+18, cy-8), 3)
    elif tower_type == "spike":
        pygame.draw.rect(surf, (120,120,130), (cx-12, cy-8, 24, 20))
        pygame.draw.rect(surf, (90,90,100), (cx-12, cy-8, 24, 20), 2)
        pygame.draw.rect(surf, (60,60,60), (cx-10, cy+2, 20, 6))
        spike_h = 6 + upgrade_level * 2
        sw = 3
        pygame.draw.polygon(surf, C_GRAY, [(cx-sw, cy-8), (cx, cy-8-spike_h), (cx+sw, cy-8)])
        pygame.draw.polygon(surf, C_GRAY, [(cx-12, cy-2-sw), (cx-12-spike_h//2, cy-2), (cx-12, cy-2+sw)])
        pygame.draw.polygon(surf, C_GRAY, [(cx+12, cy-2-sw), (cx+12+spike_h//2, cy-2), (cx+12, cy-2+sw)])

    if upgrade_level > 0:
        for i in range(upgrade_level):
            pygame.draw.circle(surf, C_GOLD, (cx-6+i*6, cy+16), 2)
    return surf

def make_projectile_sprite(proj_type):
    key = ("proj", proj_type)
    return get_sprite(key, lambda: _gen_proj(proj_type))

def _gen_proj(proj_type):
    if proj_type == "dart":
        surf = pygame.Surface((12, 6), pygame.SRCALPHA)
        pygame.draw.polygon(surf, C_YELLOW, [(0,2),(10,0),(12,3),(10,6)])
        pygame.draw.polygon(surf, C_BLACK, [(0,2),(10,0),(12,3),(10,6)], 1)
    elif proj_type == "tack":
        surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        for a in [0, math.pi/2, math.pi, 3*math.pi/2]:
            pygame.draw.line(surf, C_GRAY, (4,4), (4+int(3*math.cos(a)),4+int(3*math.sin(a))), 2)
        pygame.draw.circle(surf, C_RED, (4,4), 1)
    elif proj_type == "bomb":
        surf = pygame.Surface((10, 12), pygame.SRCALPHA)
        pygame.draw.circle(surf, (40,40,40), (5,7), 5)
        pygame.draw.circle(surf, (60,60,60), (5,7), 4)
        pygame.draw.line(surf, C_ORANGE, (5,2), (5,0), 2)
    elif proj_type == "laser":
        surf = pygame.Surface((14, 4), pygame.SRCALPHA)
        pygame.draw.rect(surf, (255,50,50,200), (0,0,14,4))
        pygame.draw.rect(surf, (255,150,150,150), (2,1,10,2))
    elif proj_type == "plasma":
        surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(surf, (180,50,255), (5,5), 5)
        pygame.draw.circle(surf, (220,150,255), (5,5), 3)
    elif proj_type == "bullet":
        surf = pygame.Surface((8, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, C_GOLD, (0,0,8,4))
    else:
        surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(surf, C_YELLOW, (3,3), 3)
    return surf

def make_spike_sprite():
    key = "spike_obj"
    return get_sprite(key, lambda: _gen_spike())

def _gen_spike():
    size = 28
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    spike_len = 7
    base_w = 4
    metal = (180, 180, 180)
    pygame.draw.polygon(surf, metal, [(cx - base_w//2, cy - 2), (cx, cy - spike_len), (cx + base_w//2, cy - 2)])
    pygame.draw.polygon(surf, C_BLACK, [(cx - base_w//2, cy - 2), (cx, cy - spike_len), (cx + base_w//2, cy - 2)], 1)
    pygame.draw.polygon(surf, metal, [(cx - base_w//2, cy + 2), (cx, cy + spike_len), (cx + base_w//2, cy + 2)])
    pygame.draw.polygon(surf, C_BLACK, [(cx - base_w//2, cy + 2), (cx, cy + spike_len), (cx + base_w//2, cy + 2)], 1)
    pygame.draw.polygon(surf, metal, [(cx - 2, cy - base_w//2), (cx - spike_len, cy), (cx - 2, cy + base_w//2)])
    pygame.draw.polygon(surf, C_BLACK, [(cx - 2, cy - base_w//2), (cx - spike_len, cy), (cx - 2, cy + base_w//2)], 1)
    pygame.draw.polygon(surf, metal, [(cx + 2, cy - base_w//2), (cx + spike_len, cy), (cx + 2, cy + base_w//2)])
    pygame.draw.polygon(surf, C_BLACK, [(cx + 2, cy - base_w//2), (cx + spike_len, cy), (cx + 2, cy + base_w//2)], 1)
    pygame.draw.circle(surf, (120, 120, 120), (cx, cy), 3)
    pygame.draw.circle(surf, C_BLACK, (cx, cy), 3, 1)
    return surf

BLOON_DEFS = {
    "red":      {"color": C_RED,       "radius": 10, "speed": 1.0, "hp": 1,
                 "children": [],                          "immunities": [], "rbe": 1},
    "blue":     {"color": C_BLUE,      "radius": 10, "speed": 1.3, "hp": 1,
                 "children": ["red"],                     "immunities": [], "rbe": 2},
    "green":    {"color": C_GREEN,     "radius": 11, "speed": 1.6, "hp": 1,
                 "children": ["blue"],                    "immunities": [], "rbe": 3},
    "yellow":   {"color": C_YELLOW,    "radius": 11, "speed": 2.2, "hp": 1,
                 "children": ["green"],                   "immunities": [], "rbe": 4},
    "pink":     {"color": C_PINK,      "radius": 11, "speed": 2.8, "hp": 1,
                 "children": ["yellow"],                  "immunities": [], "rbe": 5},
    "black":    {"color": (30,30,30),  "radius": 10, "speed": 2.0, "hp": 1,
                 "children": ["pink","pink"],             "immunities": [DMG_EXPLOSION], "rbe": 11},
    "white":    {"color": C_WHITE,     "radius": 10, "speed": 2.2, "hp": 1,
                 "children": ["pink","pink"],             "immunities": [DMG_ICE], "rbe": 11},
    "zebra":    {"color": C_WHITE,     "radius": 12, "speed": 2.0, "hp": 1,
                 "children": ["black","white"],           "immunities": [DMG_EXPLOSION, DMG_ICE], "rbe": 23,
                 "stripe": True, "stripe_color": (30,30,30)},
    "lead":     {"color": C_GRAY,      "radius": 13, "speed": 0.8, "hp": 1,
                 "children": ["black","black"],           "immunities": [DMG_SHARP], "rbe": 23},
    "rainbow":  {"color": C_RED,       "radius": 12, "speed": 2.0, "hp": 1,
                 "children": ["zebra","zebra"],           "immunities": [], "rbe": 47,
                 "rainbow": True},
    "ceramic":  {"color": C_BROWN,     "radius": 14, "speed": 2.0, "hp": 10,
                 "children": ["rainbow","rainbow"],       "immunities": [], "rbe": 104},
    "moab":     {"color": (50,70,140), "radius": 25, "speed": 0.6, "hp": 200,
                 "children": ["ceramic","ceramic","ceramic","ceramic"],
                 "immunities": [], "rbe": 616, "is_moab": True},
}

TOWER_DEFS = {
    "dart": {
        "name": "Dart Monkey", "cost": 200, "range": 150, "fire_rate": 1.2,
        "damage_type": DMG_SHARP, "proj_type": "dart", "proj_speed": 12,
        "pierce": 1, "proj_count": 1, "damage": 1,
        "description": "Throws darts at bloons",
        "upgrades": [
            {"name": "Long Range",     "cost": 150, "range_bonus": 30, "desc": "+30 range"},
            {"name": "Enhanced Sight", "cost": 250, "range_bonus": 30, "pierce_bonus": 1, "desc": "+30 range, +1 pierce"},
            {"name": "Sharp Darts",    "cost": 200, "pierce_bonus": 2, "desc": "+2 pierce"},
            {"name": "Razor Darts",    "cost": 350, "pierce_bonus": 3, "desc": "+3 pierce"},
        ]
    },
    "tack": {
        "name": "Tack Shooter", "cost": 280, "range": 100, "fire_rate": 1.0,
        "damage_type": DMG_SHARP, "proj_type": "tack", "proj_speed": 8,
        "pierce": 1, "proj_count": 8, "damage": 1,
        "description": "Shoots tacks in 8 dirs",
        "upgrades": [
            {"name": "Faster Shooting",     "cost": 200, "fire_rate_mult": 1.4, "desc": "40% faster"},
            {"name": "Even Faster",         "cost": 350, "fire_rate_mult": 1.5, "desc": "50% faster"},
            {"name": "Extra Range",         "cost": 150, "range_bonus": 30, "desc": "+30 range"},
            {"name": "Super Range",         "cost": 300, "range_bonus": 40, "proj_count_bonus": 8, "desc": "+40 range, 16 tacks"},
        ]
    },
    "ice": {
        "name": "Ice Tower", "cost": 300, "range": 90, "fire_rate": 0.7,
        "damage_type": DMG_ICE, "proj_type": "ice_spike", "proj_speed": 0,
        "pierce": 999, "proj_count": 0, "damage": 0, "freeze_duration": 1.5,
        "description": "Freezes nearby bloons",
        "upgrades": [
            {"name": "Enhanced Freeze",  "cost": 200, "freeze_dur_bonus": 0.8, "desc": "+0.8s freeze"},
            {"name": "Arctic Wind",      "cost": 450, "freeze_dur_bonus": 1.0, "range_bonus": 30, "slow_after": 0.5, "desc": "+1s, slow after thaw"},
            {"name": "Permafrost",       "cost": 250, "slow_after": 0.6, "desc": "Slow bloons after thaw"},
            {"name": "Snap Freeze",      "cost": 400, "pop_frozen": True, "desc": "Pops frozen bloons"},
        ]
    },
    "bomb": {
        "name": "Bomb Tower", "cost": 500, "range": 160, "fire_rate": 0.6,
        "damage_type": DMG_EXPLOSION, "proj_type": "bomb", "proj_speed": 8,
        "pierce": 999, "proj_count": 1, "damage": 1, "blast_radius": 40,
        "description": "Launches explosive bombs",
        "upgrades": [
            {"name": "Bigger Bombs",      "cost": 300, "blast_bonus": 20, "desc": "+20 blast radius"},
            {"name": "Missile Launcher",  "cost": 500, "blast_bonus": 15, "range_bonus": 40, "proj_speed_bonus": 3, "desc": "Better range & blast"},
            {"name": "Frag Bombs",        "cost": 350, "frag_count": 8, "desc": "Fragments on explosion"},
            {"name": "Bloon Impact",      "cost": 600, "stun_duration": 0.5, "desc": "Stuns bloons on hit"},
        ]
    },
    "super": {
        "name": "Super Monkey", "cost": 2500, "range": 170, "fire_rate": 4.0,
        "damage_type": DMG_SHARP, "proj_type": "dart", "proj_speed": 14,
        "pierce": 1, "proj_count": 1, "damage": 1,
        "description": "Attacks incredibly fast",
        "upgrades": [
            {"name": "Laser Vision",    "cost": 2000, "proj_type": "laser", "damage_type": DMG_ENERGY,
             "pierce_bonus": 2, "desc": "Laser pierces 3 bloons"},
            {"name": "Plasma Vision",   "cost": 3500, "proj_type": "plasma", "damage_type": DMG_ENERGY,
             "pierce_bonus": 4, "fire_rate_mult": 1.5, "desc": "Plasma, even faster"},
            {"name": "Epic Range",      "cost": 1500, "range_bonus": 50, "desc": "+50 range"},
            {"name": "Temporal Range",  "cost": 2500, "range_bonus": 80, "desc": "+80 range"},
        ]
    },
    "sniper": {
        "name": "Sniper Monkey", "cost": 350, "range": 9999, "fire_rate": 0.5,
        "damage_type": DMG_SHARP, "proj_type": "bullet", "proj_speed": 9999,
        "pierce": 1, "proj_count": 1, "damage": 1,
        "description": "Infinite range, slow fire",
        "upgrades": [
            {"name": "Full Metal Jacket", "cost": 350, "damage_bonus": 2, "can_pop_lead": True, "desc": "+2 dmg, pops lead"},
            {"name": "Point Five Oh",     "cost": 1500, "damage_bonus": 5, "can_pop_lead": True, "desc": "+5 dmg, pops lead"},
            {"name": "Faster Firing",     "cost": 400, "fire_rate_mult": 2.0, "desc": "2x fire rate"},
            {"name": "Semi-Auto",        "cost": 1200, "fire_rate_mult": 2.5, "desc": "2.5x fire rate"},
        ]
    },
    "spike": {
        "name": "Spike Factory", "cost": 600, "range": 0, "fire_rate": 1.5,
        "damage_type": DMG_SHARP, "proj_type": "spike", "proj_speed": 0,
        "pierce": 5, "proj_count": 0, "damage": 1, "spike_count": 5,
        "description": "Places road spikes",
        "upgrades": [
            {"name": "Bigger Stacks",      "cost": 400, "spike_bonus": 5, "desc": "+5 spikes per batch"},
            {"name": "White Hot Spikes",   "cost": 1000, "can_pop_lead": True, "desc": "Spikes pop lead"},
            {"name": "Road Spikes",        "cost": 500, "pierce_bonus": 5, "desc": "+5 pierce per spike"},
            {"name": "Spiked Mines",       "cost": 2000, "mine_explosion": True, "desc": "Spikes explode when used"},
        ]
    },
}

TOWER_ORDER = ["dart", "tack", "ice", "bomb", "super", "sniper", "spike"]

def generate_waves():
    waves = []
    def w(*bloons):
        return list(bloons)

    waves.append(w(("red", 20, 0, 25, 0, 0)))
    waves.append(w(("red", 30, 0, 20, 0, 0)))
    waves.append(w(("red", 15, 0, 25, 0, 0), ("blue", 10, 0, 25, 0, 0)))
    waves.append(w(("blue", 25, 0, 22, 0, 0)))
    waves.append(w(("red", 20, 0, 15, 0, 0), ("blue", 20, 10, 18, 0, 0)))
    waves.append(w(("blue", 15, 0, 20, 0, 0), ("green", 10, 5, 22, 0, 0)))
    waves.append(w(("green", 25, 0, 20, 0, 0)))
    waves.append(w(("green", 20, 0, 18, 0, 0), ("blue", 15, 0, 15, 0, 0)))
    waves.append(w(("yellow", 15, 0, 22, 0, 0)))
    waves.append(w(("green", 30, 0, 15, 0, 0), ("yellow", 10, 10, 20, 0, 0)))

    waves.append(w(("yellow", 25, 0, 18, 0, 0)))
    waves.append(w(("pink", 15, 0, 20, 0, 0), ("red", 10, 0, 18, -1, 0)))
    waves.append(w(("yellow", 20, 0, 15, 0, 0), ("pink", 15, 5, 18, 0, 0)))
    waves.append(w(("black", 10, 0, 25, 0, 0), ("red", 10, 0, 20, 1, 0)))
    waves.append(w(("pink", 30, 0, 12, 0, 0)))
    waves.append(w(("zebra", 8, 0, 22, 0, 0), ("blue", 12, 0, 15, -1, 0)))
    waves.append(w(("black", 10, 0, 20, 0, 0), ("white", 10, 0, 20, 1, 0)))
    waves.append(w(("lead", 8, 0, 30, 0, 0)))
    waves.append(w(("zebra", 8, 0, 20, 0, 0), ("green", 10, 0, 15, -1, 0), ("green", 10, 0, 15, 1, 0)))
    waves.append(w(("rainbow", 6, 0, 30, 0, 0)))

    waves.append(w(("rainbow", 6, 0, 25, 0, 0), ("yellow", 15, 0, 15, 0, 1)))
    waves.append(w(("ceramic", 3, 0, 40, 0, 0), ("pink", 10, 0, 15, 0, 1)))
    waves.append(w(("lead", 6, 0, 22, 0, 0), ("blue", 15, 0, 12, 0, 1)))
    waves.append(w(("ceramic", 4, 0, 35, 0, 0), ("zebra", 4, 0, 30, 0, 1)))
    waves.append(w(("rainbow", 6, 0, 18, 0, 0), ("rainbow", 4, 0, 25, 0, 1)))
    waves.append(w(("ceramic", 4, 0, 30, 0, 0), ("green", 12, 0, 10, -1, 0), ("green", 12, 5, 10, -1, 1)))
    waves.append(w(("lead", 8, 0, 20, 0, 0), ("lead", 4, 0, 25, 0, 1)))
    waves.append(w(("ceramic", 5, 0, 28, 0, 0), ("zebra", 6, 0, 18, 0, 1)))
    waves.append(w(("rainbow", 8, 0, 15, 0, 0), ("pink", 10, 0, 12, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 0)))

    waves.append(w(("ceramic", 8, 0, 20, 0, 0), ("ceramic", 4, 0, 25, -1, 0), ("ceramic", 4, 5, 25, 1, 0)))
    waves.append(w(("ceramic", 10, 0, 18, 0, 0), ("lead", 6, 0, 15, -1, 0)))
    waves.append(w(("ceramic", 6, 0, 25, 0, 0), ("rainbow", 10, 0, 12, 1, 0)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("ceramic", 6, 30, 20, -1, 0)))
    waves.append(w(("ceramic", 12, 0, 15, 0, 0), ("zebra", 6, 0, 15, -1, 0), ("zebra", 6, 3, 15, 1, 0)))
    waves.append(w(("moab", 1, 0, 1, -1, 0), ("ceramic", 6, 30, 18, 0, 0)))
    waves.append(w(("ceramic", 15, 0, 12, 0, 0), ("lead", 6, 0, 15, 1, 0)))
    waves.append(w(("rainbow", 12, 0, 10, 0, 0), ("rainbow", 6, 0, 15, -1, 0), ("rainbow", 6, 2, 15, 1, 0)))
    waves.append(w(("ceramic", 12, 0, 12, 0, 0), ("ceramic", 6, 0, 18, -1, 0)))
    waves.append(w(("moab", 1, 0, 1, 1, 0), ("ceramic", 8, 30, 15, 0, 0)))

    waves.append(w(("moab", 1, 0, 1, 0, 0), ("ceramic", 10, 30, 12, 0, 1)))
    waves.append(w(("ceramic", 12, 0, 10, 0, 0), ("ceramic", 8, 0, 12, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("ceramic", 6, 60, 15, -1, 0), ("ceramic", 6, 65, 15, -1, 1)))
    waves.append(w(("ceramic", 15, 0, 8, 0, 0), ("lead", 6, 0, 12, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 1), ("ceramic", 8, 30, 12, 0, 0)))
    waves.append(w(("ceramic", 12, 0, 8, 0, 0), ("rainbow", 10, 0, 10, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 0, 1)))
    waves.append(w(("ceramic", 15, 0, 7, 0, 0), ("ceramic", 8, 0, 10, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, -1, 0), ("ceramic", 8, 40, 10, 0, 0), ("ceramic", 8, 42, 10, 0, 1)))
    waves.append(w(("ceramic", 18, 0, 6, 0, 0), ("lead", 8, 0, 10, 0, 1)))

    waves.append(w(("moab", 2, 0, 100, 0, 0), ("ceramic", 8, 20, 10, 0, 1)))
    waves.append(w(("ceramic", 15, 0, 10, 0, 0), ("ceramic", 8, 0, 12, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 0, 1)))
    waves.append(w(("ceramic", 18, 0, 8, -1, 0), ("ceramic", 18, 0, 8, -1, 1)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("lead", 8, 20, 10, 0, 1)))
    waves.append(w(("ceramic", 15, 0, 8, 0, 0), ("rainbow", 12, 0, 8, 0, 1)))
    waves.append(w(("moab", 1, 0, 1, -1, 0), ("moab", 1, 0, 1, 1, 1)))
    waves.append(w(("ceramic", 20, 0, 7, 0, 0), ("ceramic", 10, 0, 9, 0, 1)))
    waves.append(w(("moab", 2, 0, 80, 0, 0), ("ceramic", 10, 30, 10, 0, 1)))
    waves.append(w(("ceramic", 20, 0, 6, 0, 0), ("ceramic", 12, 0, 8, 0, 1)))

    waves.append(w(("moab", 2, 0, 150, 0, 0)))
    waves.append(w(("ceramic", 20, 0, 8, 0, 0), ("ceramic", 10, 0, 10, -1, 0), ("ceramic", 10, 2, 10, 1, 0)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("ceramic", 8, 40, 12, -1, 0)))
    waves.append(w(("ceramic", 25, 0, 6, 0, 0), ("lead", 8, 0, 10, -1, 0), ("lead", 8, 2, 10, 1, 0)))
    waves.append(w(("moab", 2, 0, 100, 0, 0), ("ceramic", 8, 20, 12, 1, 0)))
    waves.append(w(("ceramic", 20, 0, 7, 0, 0), ("rainbow", 12, 0, 8, -1, 0), ("rainbow", 12, 2, 8, 1, 0)))
    waves.append(w(("moab", 1, 0, 1, -1, 0), ("moab", 1, 0, 1, 1, 0)))
    waves.append(w(("ceramic", 25, 0, 5, 0, 0), ("ceramic", 10, 0, 8, -1, 0), ("ceramic", 10, 2, 8, 1, 0)))
    waves.append(w(("moab", 2, 0, 70, 0, 0), ("ceramic", 12, 30, 8, -1, 0), ("ceramic", 12, 32, 8, 1, 0)))
    waves.append(w(("ceramic", 30, 0, 5, 0, 0), ("lead", 10, 0, 8, -1, 0), ("lead", 10, 2, 8, 1, 0)))

    waves.append(w(("moab", 3, 0, 70, 0, 0)))
    waves.append(w(("moab", 2, 0, 100, 0, 0), ("ceramic", 10, 20, 8, -1, 0), ("ceramic", 10, 22, 8, 1, 0)))
    waves.append(w(("moab", 1, 0, 1, -1, 0), ("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 1, 0)))
    waves.append(w(("ceramic", 25, 0, 5, 0, 0), ("ceramic", 12, 0, 7, -1, 0), ("ceramic", 12, 2, 7, 1, 0)))
    waves.append(w(("moab", 2, 0, 80, 0, 0), ("lead", 8, 15, 8, -1, 0), ("lead", 8, 17, 8, 1, 0)))
    waves.append(w(("moab", 2, 0, 60, 0, 0), ("moab", 1, 0, 1, -1, 0), ("moab", 1, 0, 1, 1, 0)))
    waves.append(w(("ceramic", 30, 0, 4, 0, 0), ("rainbow", 15, 0, 6, -1, 0), ("rainbow", 15, 2, 6, 1, 0)))
    waves.append(w(("moab", 3, 0, 50, 0, 0), ("ceramic", 12, 10, 6, -1, 0), ("ceramic", 12, 12, 6, 1, 0)))
    waves.append(w(("moab", 3, 0, 45, 0, 0), ("lead", 8, 0, 8, -1, 0), ("lead", 8, 2, 8, 1, 0)))
    waves.append(w(("moab", 2, 0, 60, 0, 0), ("ceramic", 15, 20, 6, -1, 0), ("ceramic", 15, 22, 6, 1, 0)))

    waves.append(w(("moab", 1, 0, 1, 0, 0), ("ceramic", 10, 20, 10, 0, 1), ("ceramic", 10, 25, 10, 0, 2)))
    waves.append(w(("ceramic", 15, 0, 8, 0, 0), ("ceramic", 15, 0, 8, 0, 1), ("ceramic", 15, 0, 8, 0, 2)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 0, 2)))
    waves.append(w(("ceramic", 20, 0, 6, 0, 0), ("ceramic", 12, 0, 8, 0, 1), ("ceramic", 12, 0, 8, 0, 2)))
    waves.append(w(("moab", 1, 0, 1, 0, 1), ("ceramic", 10, 30, 10, 0, 0), ("ceramic", 10, 32, 10, 0, 2)))
    waves.append(w(("ceramic", 20, 0, 5, -1, 0), ("ceramic", 20, 0, 5, 0, 1), ("ceramic", 20, 0, 5, 1, 2)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 0, 1), ("moab", 1, 0, 1, 0, 2)))
    waves.append(w(("ceramic", 25, 0, 5, 0, 0), ("rainbow", 15, 0, 6, 0, 1), ("rainbow", 15, 0, 6, 0, 2)))
    waves.append(w(("moab", 2, 0, 80, 0, 0), ("ceramic", 12, 20, 6, 0, 1), ("ceramic", 12, 22, 6, 0, 2)))
    waves.append(w(("moab", 1, 0, 1, 0, 0), ("moab", 1, 0, 1, 0, 1), ("moab", 1, 0, 1, 0, 2)))

    waves.append(w(("moab", 2, 0, 80, 0, 0), ("ceramic", 15, 20, 8, 0, 1)))
    waves.append(w(("moab", 2, 0, 60, 0, 0), ("moab", 1, 0, 1, 0, 1)))
    waves.append(w(("ceramic", 30, 0, 5, 0, 0), ("ceramic", 20, 0, 6, 0, 1)))
    waves.append(w(("moab", 2, 0, 50, 0, 0), ("ceramic", 15, 15, 5, -1, 0), ("ceramic", 15, 17, 5, -1, 1)))
    waves.append(w(("moab", 2, 0, 40, 0, 0), ("moab", 2, 0, 60, 0, 1)))
    waves.append(w(("ceramic", 35, 0, 4, 0, 0), ("rainbow", 20, 0, 5, 0, 1)))
    waves.append(w(("moab", 3, 0, 35, 0, 0), ("ceramic", 15, 10, 5, -1, 0), ("ceramic", 15, 12, 5, -1, 1)))
    waves.append(w(("moab", 3, 0, 30, 0, 0), ("moab", 2, 0, 50, 0, 1)))
    waves.append(w(("moab", 3, 0, 25, 0, 0), ("ceramic", 20, 10, 4, 0, 1)))
    waves.append(w(("moab", 3, 0, 20, -1, 0), ("moab", 5, 0, 20, 0, 0), ("moab", 3, 0, 20, 1, 0),
                    ("moab", 2, 0, 30, -1, 1), ("moab", 4, 0, 30, 0, 1), ("moab", 2, 0, 30, 1, 1)))

    return waves

MAP_DEFS = [
    {
        "name": "The Serpent",
        "paths": [
            [(-20, 360), (180, 360), (180, 120), (420, 120),
             (420, 560), (620, 560), (620, 200), (820, 200),
             (820, 480), (960, 480), (960, 320), (1040, 320)]
        ],
        "money": 650,
        "lives": 200,
    },
    {
        "name": "The Loop",
        "paths": [
            [(-20, 380), (200, 380), (200, 100), (500, 100),
             (500, 620), (780, 620), (780, 100), (940, 100),
             (940, 380), (1040, 380)]
        ],
        "money": 800,
        "lives": 150,
    },
    {
        "name": "Twin Rivers",
        "paths": [
            [(-20, 140), (240, 140), (240, 340), (520, 340), (520, 140), (800, 140), (800, 340), (1040, 340)],
            [(-20, 580), (240, 580), (240, 380), (520, 380), (520, 580), (800, 580), (800, 380), (1040, 380)]
        ],
        "money": 900,
        "lives": 150,
    },
    {
        "name": "The Circuit",
        "paths": [
            [(-20, 360), (300, 360), (300, 100), (700, 100),
             (700, 620), (300, 620), (300, 360), (700, 360),
             (700, 100), (960, 100), (960, 360), (1040, 360)]
        ],
        "money": 1000,
        "lives": 120,
    },
    {
        "name": "Divided Island",
        "paths": [
            [(-20, 220), (200, 220), (200, 140), (800, 140), (800, 220), (1040, 220)],
            [(-20, 500), (200, 500), (200, 580), (800, 580), (800, 500), (1040, 500)]
        ],
        "money": 1200,
        "lives": 120,
    },
    {
        "name": "The Helix",
        "paths": [
            [(-20, 140), (250, 140), (250, 580), (500, 580), (500, 140), (750, 140), (750, 360), (1040, 360)],
            [(-20, 580), (250, 580), (250, 140), (500, 140), (500, 580), (750, 580), (750, 360), (1040, 360)]
        ],
        "money": 1500,
        "lives": 100,
    },
    {
        "name": "The Zigzag",
        "paths": [
            [(-20, 360), (100, 360), (100, 80), (220, 80), (220, 640),
             (340, 640), (340, 80), (460, 80), (460, 640),
             (580, 640), (580, 80), (700, 80), (700, 640),
             (820, 640), (820, 80), (940, 80), (940, 360), (1040, 360)]
        ],
        "money": 1800,
        "lives": 100,
    },
    {
        "name": "Grand Prix",
        "paths": [
            [(-20, 600), (140, 600), (140, 120), (340, 120), (340, 600),
             (540, 600), (540, 120), (740, 120), (740, 600),
             (900, 600), (900, 360), (1040, 360)]
        ],
        "money": 2000,
        "lives": 80,
    },
    {
        "name": "Three Ways",
        "paths": [
            [(-20, 80), (300, 80), (300, 360), (700, 360), (700, 80), (1040, 80)],
            [(-20, 360), (300, 360), (700, 360), (1040, 360)],
            [(-20, 640), (300, 640), (300, 360), (700, 360), (700, 640), (1040, 640)]
        ],
        "money": 2500,
        "lives": 80,
    },
    {
        "name": "Final Siege",
        "paths": [
            [(-20, 120), (160, 120), (160, 600), (360, 600), (360, 120),
             (560, 120), (560, 600), (760, 600), (760, 360), (1040, 360)],
            [(-20, 600), (160, 600), (160, 120), (360, 120), (360, 600),
             (560, 600), (560, 120), (760, 120), (760, 360), (1040, 360)]
        ],
        "money": 3000,
        "lives": 50,
    },
]

_active_map_idx = 0
_path_lengths_cache = {}
_path_cells_cache = {}

def set_active_map(idx):
    global _active_map_idx
    _active_map_idx = idx

def path_total_length(path_idx=0):
    global _path_lengths_cache
    map_idx = _active_map_idx
    if map_idx not in _path_lengths_cache:
        _path_lengths_cache[map_idx] = {}
    if path_idx not in _path_lengths_cache[map_idx]:
        waypoints = MAP_DEFS[map_idx]["paths"][path_idx]
        total = 0
        for i in range(len(waypoints)-1):
            dx = waypoints[i+1][0] - waypoints[i][0]
            dy = waypoints[i+1][1] - waypoints[i][1]
            total += math.sqrt(dx*dx + dy*dy)
        _path_lengths_cache[map_idx][path_idx] = total
    return _path_lengths_cache[map_idx][path_idx]

def pos_on_path(progress, path_idx=0, lane_offset=0):
    waypoints = MAP_DEFS[_active_map_idx]["paths"][path_idx]
    total = path_total_length(path_idx)
    target = progress * total
    accum = 0
    for i in range(len(waypoints)-1):
        dx = waypoints[i+1][0] - waypoints[i][0]
        dy = waypoints[i+1][1] - waypoints[i][1]
        seg_len = math.sqrt(dx*dx + dy*dy)
        if accum + seg_len >= target:
            frac = (target - accum) / seg_len if seg_len > 0 else 0
            x = waypoints[i][0] + dx*frac
            y = waypoints[i][1] + dy*frac
            if lane_offset != 0 and seg_len > 0:
                perp_x = -dy / seg_len
                perp_y = dx / seg_len
                x += perp_x * lane_offset * CELL
                y += perp_y * lane_offset * CELL
            return (x, y)
        accum += seg_len
    x, y = waypoints[-1]
    if lane_offset != 0 and len(waypoints) >= 2:
        dx = waypoints[-1][0] - waypoints[-2][0]
        dy = waypoints[-1][1] - waypoints[-2][1]
        seg_len = math.sqrt(dx*dx + dy*dy)
        if seg_len > 0:
            perp_x = -dy / seg_len
            perp_y = dx / seg_len
            x += perp_x * lane_offset * CELL
            y += perp_y * lane_offset * CELL
    return (x, y)

def get_path_cells():
    global _path_cells_cache
    map_idx = _active_map_idx
    if map_idx in _path_cells_cache:
        return _path_cells_cache[map_idx]
    cells = set()
    for path_idx, waypoints in enumerate(MAP_DEFS[map_idx]["paths"]):
        for i in range(len(waypoints)-1):
            x0, y0 = waypoints[i]
            x1, y1 = waypoints[i+1]
            dist = math.sqrt((x1-x0)**2 + (y1-y0)**2)
            steps = int(dist / 5)
            for s in range(steps+1):
                t = s / max(steps, 1)
                x = x0 + (x1-x0)*t
                y = y0 + (y1-y0)*t
                col, row = int(x // CELL), int(y // CELL)
                if 0 <= col < COLS and 0 <= row < ROWS:
                    cells.add((col, row))
                    for dc, dr in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nc, nr = col+dc, row+dr
                        if 0 <= nc < COLS and 0 <= nr < ROWS:
                            cells.add((nc, nr))
    _path_cells_cache[map_idx] = cells
    return cells

class Particle:
    __slots__ = ['x','y','color','vx','vy','life','max_life','size','gravity','alive']
    def __init__(self, x, y, color, vx=0, vy=0, life=0.5, size=3, gravity=0):
        self.x, self.y = x, y
        self.color = color
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += self.gravity * dt * 60
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surface):
        alpha = max(0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], int(255*alpha)), (r, r), r)
        surface.blit(s, (int(self.x)-r, int(self.y)-r))

class EffectManager:
    def __init__(self):
        self.particles = []
        self.explosions = []
        self.freezes = []

    def add_pop(self, x, y, color):
        for _ in range(5):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(1, 3.5)
            self.particles.append(Particle(
                x, y, color,
                vx=math.cos(angle)*speed, vy=math.sin(angle)*speed,
                life=0.3, size=random.randint(2, 4)))

    def add_explosion(self, x, y, radius):
        self.explosions.append([x, y, radius, 0.3, 0.3])
        for _ in range(8):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(2, 5)
            self.particles.append(Particle(
                x, y, (255, 200, 50),
                vx=math.cos(angle)*speed, vy=math.sin(angle)*speed,
                life=0.4, size=random.randint(3, 5), gravity=0.05))

    def add_freeze(self, x, y, radius):
        self.freezes.append([x, y, radius, 0.8, 0.8])
        for _ in range(6):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(1, 2.5)
            self.particles.append(Particle(
                x, y, (150, 220, 255),
                vx=math.cos(angle)*speed, vy=math.sin(angle)*speed,
                life=0.5, size=random.randint(2, 4)))

    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        self.explosions = [[x,y,r,t-dt,mt] for x,y,r,t,mt in self.explosions if t-dt > 0]
        self.freezes = [[x,y,r,t-dt,mt] for x,y,r,t,mt in self.freezes if t-dt > 0]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        for x, y, r, t, mt in self.explosions:
            alpha = t / mt
            size = int(r * (1 + (1-alpha)*0.5)) * 2 + 4
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            cx, cy = size//2, size//2
            rad = int(r * (1 + (1-alpha)*0.5))
            pygame.draw.circle(s, (255,200,50, int(180*alpha)), (cx,cy), rad)
            pygame.draw.circle(s, (255,255,200, int(200*alpha)), (cx,cy), rad//2)
            pygame.draw.circle(s, (255,100,0, int(100*alpha)), (cx,cy), rad, 3)
            surface.blit(s, (int(x)-cx, int(y)-cy))
        for x, y, r, t, mt in self.freezes:
            alpha = t / mt
            size = r*2+4
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            cx, cy = size//2, size//2
            pygame.draw.circle(s, (150,220,255, int(80*alpha)), (cx,cy), r)
            pygame.draw.circle(s, (200,240,255, int(120*alpha)), (cx,cy), r, 3)
            surface.blit(s, (int(x)-cx, int(y)-cy))

class Bloon:
    _id_counter = 0

    def __init__(self, bloon_type, progress=0.0, lane_offset=0, path_idx=0):
        Bloon._id_counter += 1
        self.id = Bloon._id_counter
        self.type = bloon_type
        self.lane_offset = lane_offset
        self.path_idx = path_idx
        d = BLOON_DEFS[bloon_type]
        self.color = d["color"]
        self.radius = d["radius"]
        self.base_speed = d["speed"]
        self.speed = d["speed"]
        self.hp = d["hp"]
        self.max_hp = d["hp"]
        self.children = d["children"]
        self.immunities = list(d["immunities"])
        self.rbe = d["rbe"]
        self.is_moab = d.get("is_moab", False)
        self.has_stripe = d.get("stripe", False)
        self.stripe_color = d.get("stripe_color")
        self.is_rainbow = d.get("rainbow", False)

        self.progress = progress
        self.x, self.y = pos_on_path(progress, path_idx, lane_offset)
        self.alive = True
        self.reached_end = False
        self.frozen = False
        self.freeze_timer = 0
        self.slow_factor = 1.0
        self.slow_timer = 0
        self.stunned = False
        self.stun_timer = 0

    def update(self, dt):
        if not self.alive:
            return
        if self.frozen:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.frozen = False
        if self.slow_factor < 1.0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_factor = 1.0
        if self.stunned:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.stunned = False

        if not self.frozen and not self.stunned:
            move_speed = self.base_speed * self.slow_factor * 0.0007 * dt * 60
            self.progress += move_speed
            if self.progress >= 1.0:
                self.alive = False
                self.reached_end = True
                return
            self.x, self.y = pos_on_path(self.progress, self.path_idx, self.lane_offset)

    def take_damage(self, damage, damage_type):
        if damage_type in self.immunities:
            return []
        self.hp -= damage
        if self.hp <= 0:
            self.alive = False
            return self.spawn_children()
        return []

    def apply_freeze(self, duration, slow_after=0, slow_factor=0.5, pop_frozen=False):
        if DMG_ICE in self.immunities:
            return
        self.frozen = True
        self.freeze_timer = duration
        if slow_after > 0:
            self.slow_factor = slow_factor
            self.slow_timer = slow_after + duration

    def apply_stun(self, duration):
        self.stunned = True
        self.stun_timer = duration

    def spawn_children(self):
        children = []
        for ct in self.children:
            b = Bloon(ct, self.progress, lane_offset=self.lane_offset, path_idx=self.path_idx)
            b.x, b.y = self.x, self.y
            b.slow_factor = self.slow_factor
            b.slow_timer = self.slow_timer
            children.append(b)
        return children

    def draw(self, surface, game_time=0):
        rainbow_t = game_time / 1000 if self.is_rainbow else 0
        sprite = make_bloon_sprite(self.color, self.radius, self.has_stripe,
                                   self.stripe_color, self.is_moab,
                                   self.hp/self.max_hp if self.max_hp > 0 else 1,
                                   self.is_rainbow, rainbow_t)
        surface.blit(sprite, (int(self.x)-sprite.get_width()//2,
                              int(self.y)-sprite.get_height()//2))
        if self.frozen:
            s = pygame.Surface((self.radius*2+4, self.radius*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (150,220,255,120), (self.radius+2, self.radius+2), self.radius+2)
            surface.blit(s, (int(self.x)-self.radius-2, int(self.y)-self.radius-2))
        if self.lane_offset != 0:
            lane_color = (255, 100, 100) if self.lane_offset == -1 else (100, 100, 255)
            dot_y = int(self.y) + self.radius + (6 if self.is_moab else 3)
            pygame.draw.circle(surface, lane_color, (int(self.x), dot_y), 2)

class Projectile:
    MAX_LIFETIME = 5.0

    def __init__(self, x, y, target_bloon, tower_ref, angle=None):
        self.x, self.y = float(x), float(y)
        self.target = target_bloon
        self.tower = tower_ref
        self.proj_type = tower_ref.proj_type
        self.speed = tower_ref.proj_speed
        self.damage_type = tower_ref.damage_type
        self.pierce = tower_ref.pierce
        self.damage = tower_ref.damage
        self.blast_radius = tower_ref.blast_radius
        self.frag_count = tower_ref.frag_count
        self.stun_duration = tower_ref.stun_duration
        self.alive = True
        self.hit_bloons = set()
        self.lifetime = 0.0
        self.sprite = make_projectile_sprite(self.proj_type)
        if angle is not None:
            self.angle = angle
        elif target_bloon:
            self.angle = math.atan2(target_bloon.y - y, target_bloon.x - x)
        else:
            self.angle = 0

        self.target_x = target_bloon.x if target_bloon else x + math.cos(self.angle) * 100
        self.target_y = target_bloon.y if target_bloon else y + math.sin(self.angle) * 100

    def update(self, dt, bloons):
        if not self.alive:
            return []

        self.lifetime += dt
        if self.lifetime >= self.MAX_LIFETIME:
            self.alive = False
            return []

        new_bloons = []

        if self.proj_type == "bullet":
            if self.target and self.target.alive:
                children = self.target.take_damage(self.damage, self.damage_type)
                if not self.target.alive:
                    new_bloons.extend(children)
                self.hit_bloons.add(self.target.id)
            self.alive = False
            return new_bloons

        if self.proj_type == "tack":
            self.x += math.cos(self.angle) * self.speed * dt * 60
            self.y += math.sin(self.angle) * self.speed * dt * 60
            for bloon in bloons:
                if not bloon.alive or bloon.id in self.hit_bloons:
                    continue
                dx, dy = bloon.x - self.x, bloon.y - self.y
                if dx*dx + dy*dy < (bloon.radius + 5)**2:
                    self.hit_bloons.add(bloon.id)
                    children = bloon.take_damage(self.damage, self.damage_type)
                    if not bloon.alive:
                        new_bloons.extend(children)
                    self.pierce -= 1
                    if self.pierce <= 0:
                        self.alive = False
                        break
            if (self.x < -30 or self.x > GAME_W + 30 or
                self.y < -30 or self.y > SCREEN_H + 30):
                self.alive = False
            return new_bloons

        if self.proj_type == "bomb":
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 10:
                self.alive = False
                return new_bloons
            for bloon in bloons:
                if not bloon.alive or bloon.id in self.hit_bloons:
                    continue
                bx, by = bloon.x - self.x, bloon.y - self.y
                if bx*bx + by*by < (bloon.radius + 8)**2:
                    self.alive = False
                    return new_bloons
            if dist > 0:
                self.angle = math.atan2(dy, dx)
                move = min(self.speed * dt * 60, dist)
                self.x += (dx/dist) * move
                self.y += (dy/dist) * move
            return new_bloons

        if self.target and self.target.alive:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                self.angle = math.atan2(dy, dx)
                self.x += (dx/dist) * self.speed * dt * 60
                self.y += (dy/dist) * self.speed * dt * 60
        else:
            self.x += math.cos(self.angle) * self.speed * dt * 60
            self.y += math.sin(self.angle) * self.speed * dt * 60

        for bloon in bloons:
            if not bloon.alive or bloon.id in self.hit_bloons:
                continue
            dx, dy = bloon.x - self.x, bloon.y - self.y
            if dx*dx + dy*dy < (bloon.radius + 5)**2:
                self.hit_bloons.add(bloon.id)
                children = bloon.take_damage(self.damage, self.damage_type)
                if not bloon.alive:
                    new_bloons.extend(children)
                self.pierce -= 1
                if self.pierce <= 0:
                    self.alive = False
                    break

        if (self.x < -50 or self.x > GAME_W + 50 or
            self.y < -50 or self.y > SCREEN_H + 50):
            self.alive = False

        return new_bloons

    def draw(self, surface):
        if not self.alive:
            return
        if self.proj_type == "bullet":
            return
        rotated = pygame.transform.rotate(self.sprite, -math.degrees(self.angle))
        surface.blit(rotated, (int(self.x)-rotated.get_width()//2,
                               int(self.y)-rotated.get_height()//2))

class RoadSpikes:

    def __init__(self, x, y, pierce, can_pop_lead=False, mine_explosion=False):
        self.x, self.y = x, y
        self.pierce = pierce
        self.max_pierce = pierce
        self.can_pop_lead = can_pop_lead
        self.mine_explosion = mine_explosion
        self.alive = True
        self.sprite = make_spike_sprite()

    def check_bloon(self, bloon):
        if not self.alive or not bloon.alive:
            return [], False
        dx, dy = bloon.x - self.x, bloon.y - self.y
        arm_reach = 25
        arm_width = 12
        hit = False
        if abs(dx) < arm_width and abs(dy) < arm_reach:
            hit = True
        elif abs(dy) < arm_width and abs(dx) < arm_reach:
            hit = True
        if hit:
            dmg_type = DMG_ENERGY if self.can_pop_lead else DMG_SHARP
            children = bloon.take_damage(1, dmg_type)
            self.pierce -= 1
            if self.pierce <= 0:
                self.alive = False
                return children, self.mine_explosion
            return children, False
        return [], False

    def draw(self, surface):
        if not self.alive:
            return
        alpha = max(80, int(255 * self.pierce / self.max_pierce))
        s = self.sprite.copy()
        s.set_alpha(alpha)
        surface.blit(s, (self.x - s.get_width()//2, self.y - s.get_height()//2))

class Tower:
    def __init__(self, tower_type, col, row):
        self.type = tower_type
        self.col, self.row = col, row
        self.x = col * CELL + CELL // 2
        self.y = row * CELL + CELL // 2

        d = TOWER_DEFS[tower_type]
        self.name = d["name"]
        self.base_cost = d["cost"]
        self.total_cost = d["cost"]
        self.range = d["range"]
        self.fire_rate = d["fire_rate"]
        self.damage_type = d["damage_type"]
        self.proj_type = d["proj_type"]
        self.proj_speed = d["proj_speed"]
        self.pierce = d["pierce"]
        self.damage = d["damage"]
        self.proj_count = d["proj_count"]
        self.blast_radius = d.get("blast_radius", 0)
        self.freeze_duration = d.get("freeze_duration", 0)
        self.slow_after = 0
        self.slow_factor = 0.5
        self.pop_frozen = False
        self.frag_count = 0
        self.stun_duration = 0
        self.can_pop_lead = False
        self.spike_count = d.get("spike_count", 0)
        self.mine_explosion = False

        self.fire_timer = 0
        self.target = None
        self.upgrade_path1 = 0
        self.upgrade_path2 = 0
        self.angle = 0

        self.road_spikes = []
        self.spike_timer = 0

    @property
    def upgrade_level(self):
        return self.upgrade_path1 + self.upgrade_path2

    def can_upgrade_path(self, path):
        return (self.upgrade_path1 < 2) if path == 1 else (self.upgrade_path2 < 2)

    def get_upgrade(self, path):
        if path == 1:
            idx = self.upgrade_path1
        else:
            idx = self.upgrade_path2 + 2
        if idx >= 4:
            return None
        return TOWER_DEFS[self.type]["upgrades"][idx]

    def apply_upgrade(self, path):
        upgrade = self.get_upgrade(path)
        if not upgrade:
            return 0
        cost = upgrade["cost"]
        self.total_cost += cost
        if path == 1:
            self.upgrade_path1 += 1
        else:
            self.upgrade_path2 += 1

        self.range += upgrade.get("range_bonus", 0)
        self.pierce += upgrade.get("pierce_bonus", 0)
        if "fire_rate_mult" in upgrade:
            self.fire_rate *= upgrade["fire_rate_mult"]
        self.damage += upgrade.get("damage_bonus", 0)
        self.blast_radius += upgrade.get("blast_bonus", 0)
        self.proj_speed += upgrade.get("proj_speed_bonus", 0)
        self.freeze_duration += upgrade.get("freeze_dur_bonus", 0)
        self.proj_count += upgrade.get("proj_count_bonus", 0)
        self.spike_count += upgrade.get("spike_bonus", 0)
        if upgrade.get("slow_after", 0) > 0:
            self.slow_after = upgrade["slow_after"]
            self.slow_factor = 0.5
        if upgrade.get("pop_frozen", False):
            self.pop_frozen = True
        if upgrade.get("frag_count", 0) > 0:
            self.frag_count = upgrade["frag_count"]
        if upgrade.get("stun_duration", 0) > 0:
            self.stun_duration = upgrade["stun_duration"]
        if upgrade.get("can_pop_lead", False):
            self.can_pop_lead = True
        if "damage_type" in upgrade:
            self.damage_type = upgrade["damage_type"]
        if "proj_type" in upgrade:
            self.proj_type = upgrade["proj_type"]
        if upgrade.get("mine_explosion", False):
            self.mine_explosion = True
        return cost

    def find_target(self, bloons):
        best, best_progress = None, -1
        for bloon in bloons:
            if not bloon.alive:
                continue
            dx, dy = bloon.x - self.x, bloon.y - self.y
            if dx*dx + dy*dy <= self.range * self.range:
                if bloon.progress > best_progress:
                    best, best_progress = bloon, bloon.progress
        return best

    def update(self, dt, bloons, effects):
        new_projectiles = []
        new_bloons = []

        if self.type == "spike":
            self.spike_timer -= dt
            if self.spike_timer <= 0:
                self.spike_timer = 1.0 / self.fire_rate
                path_cells = get_path_cells()
                nearby = [(c,r) for c,r in path_cells
                          if abs(c*CELL+CELL//2-self.x) < CELL*3
                          and abs(r*CELL+CELL//2-self.y) < CELL*3]
                if nearby:
                    col, row = random.choice(nearby)
                    existing = any(sp.col == col and sp.row == row and sp.alive
                                  for sp in self.road_spikes)
                    if not existing:
                        sx = col*CELL + CELL//2
                        sy = row*CELL + CELL//2
                        spike = RoadSpikes(sx, sy, self.pierce,
                                          self.can_pop_lead, self.mine_explosion)
                        spike.col, spike.row = col, row
                        self.road_spikes.append(spike)

            for spike in self.road_spikes:
                if not spike.alive:
                    continue
                for bloon in bloons:
                    if not bloon.alive:
                        continue
                    children, explode = spike.check_bloon(bloon)
                    if children:
                        new_bloons.extend(children)
                    if explode:
                        effects.add_explosion(spike.x, spike.y, 50)
                        for b2 in bloons:
                            if b2.alive and b2.id != bloon.id:
                                d = math.sqrt((b2.x-spike.x)**2 + (b2.y-spike.y)**2)
                                if d < 50:
                                    new_bloons.extend(b2.take_damage(1, DMG_EXPLOSION))
            self.road_spikes = [s for s in self.road_spikes if s.alive]
            return new_projectiles, new_bloons

        if self.type == "ice":
            self.fire_timer -= dt
            if self.fire_timer <= 0:
                self.fire_timer = 1.0 / self.fire_rate
                hit_any = False
                for bloon in bloons:
                    if not bloon.alive:
                        continue
                    dx, dy = bloon.x - self.x, bloon.y - self.y
                    if dx*dx + dy*dy <= self.range * self.range:
                        bloon.apply_freeze(self.freeze_duration, self.slow_after,
                                          self.slow_factor, self.pop_frozen)
                        hit_any = True
                        if self.pop_frozen:
                            bloon.hp -= 1
                            if bloon.hp <= 0:
                                bloon.alive = False
                                new_bloons.extend(bloon.spawn_children())
                if hit_any:
                    effects.add_freeze(self.x, self.y, self.range)
            return new_projectiles, new_bloons

        self.fire_timer -= dt
        if self.fire_timer <= 0:
            target = self.find_target(bloons)
            if target:
                self.fire_timer = 1.0 / self.fire_rate
                self.target = target
                self.angle = math.atan2(target.y - self.y, target.x - self.x)

                if self.proj_count > 1:
                    for i in range(self.proj_count):
                        a = 2 * math.pi * i / self.proj_count
                        proj = Projectile(self.x, self.y, None, self, angle=a)
                        new_projectiles.append(proj)
                else:
                    proj = Projectile(self.x, self.y, target, self)
                    new_projectiles.append(proj)

        return new_projectiles, new_bloons

    def draw(self, surface, selected=False):
        sprite = make_tower_sprite(self.type, self.upgrade_level)
        surface.blit(sprite, (self.x - sprite.get_width()//2,
                              self.y - sprite.get_height()//2))
        for spike in self.road_spikes:
            spike.draw(surface)
        if selected and self.range > 0:
            vis_range = min(self.range, max(GAME_W, SCREEN_H))
            range_surf = pygame.Surface((vis_range*2+2, vis_range*2+2), pygame.SRCALPHA)
            pygame.draw.circle(range_surf, (255,255,255,40), (vis_range+1, vis_range+1), vis_range)
            pygame.draw.circle(range_surf, (255,255,255,80), (vis_range+1, vis_range+1), vis_range, 2)
            surface.blit(range_surf, (self.x-vis_range-1, self.y-vis_range-1))

class Game:
    def __init__(self):
        pygame.init()
        self.audio_available = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_available = True
        except pygame.error:
            pass

        self.use_gpu = False
        if _GPU_AVAILABLE and USE_GPU_RENDER:
            try:
                self.use_gpu = True
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H),
                    pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
                self._init_gl()
            except Exception as e:
                self.use_gpu = False
                print(f"[PopTD] OpenGL init failed ({e}), falling back to CPU rendering")

        if not self.use_gpu:
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)

        self.win_size = (SCREEN_W, SCREEN_H)

        self.render_surface = pygame.Surface((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("PopTD - Tower Defense")
        self.clock = pygame.time.Clock()

        self.font_sm = pygame.font.SysFont("arial", 13)
        self.font_md = pygame.font.SysFont("arial", 16, bold=True)
        self.font_lg = pygame.font.SysFont("arial", 22, bold=True)
        self.font_xl = pygame.font.SysFont("arial", 36, bold=True)

        self.sounds = {}
        if self.audio_available:
            try:
                self.sounds = {
                    "pop": gen_pop_sound(), "place": gen_place_sound(),
                    "upgrade": gen_upgrade_sound(), "sell": gen_sell_sound(),
                    "round": gen_round_sound(), "moab": gen_moab_sound(),
                    "explosion": gen_explosion_sound(),
                    "win": gen_win_sound(), "lose": gen_lose_sound(),
                }
            except Exception:
                self.sounds = {}
                self.audio_available = False

        self.click_regions = {}
        self.reset_game()
        self.map_surface = self._render_map()

    def play_sound(self, name):
        if self.audio_available and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

    def _init_gl(self):
        vs_src = """
        #version 120
        attribute vec2 a_pos;
        attribute vec2 a_uv;
        varying vec2 v_uv;
        void main() {
            gl_Position = vec4(a_pos, 0.0, 1.0);
            v_uv = a_uv;
        }
        """
        fs_src = """
        #version 120
        varying vec2 v_uv;
        uniform sampler2D u_tex;
        void main() {
            gl_FragColor = texture2D(u_tex, v_uv);
        }
        """

        vs = _gl_shaders_mod.compileShader(vs_src, GL_VERTEX_SHADER)
        fs = _gl_shaders_mod.compileShader(fs_src, GL_FRAGMENT_SHADER)
        self.gl_program = _gl_shaders_mod.compileProgram(vs, fs)

        self.gl_a_pos = glGetAttribLocation(self.gl_program, b"a_pos")
        self.gl_a_uv = glGetAttribLocation(self.gl_program, b"a_uv")
        self.gl_u_tex = glGetUniformLocation(self.gl_program, b"u_tex")

        quad = [
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
            -1.0,  1.0, 0.0, 1.0,
             1.0,  1.0, 1.0, 1.0,
        ]
        self.gl_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.gl_vbo)
        glBufferData(GL_ARRAY_BUFFER,
                     len(quad) * _ctypes.sizeof(_ctypes.c_float),
                     (_ctypes.c_float * len(quad))(*quad),
                     GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

        self.gl_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.gl_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        blank = b'\x00' * (SCREEN_W * SCREEN_H * 4)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, SCREEN_W, SCREEN_H, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, blank)
        glBindTexture(GL_TEXTURE_2D, 0)

        glUseProgram(self.gl_program)
        glUseProgram(0)

    def _update_win_size(self):
        try:
            if hasattr(pygame.display, 'get_window_size'):
                new_size = pygame.display.get_window_size()
                if new_size[0] > 0 and new_size[1] > 0:
                    self.win_size = new_size
                    return
        except Exception:
            pass
        try:
            new_size = self.screen.get_size()
            if new_size[0] > 0 and new_size[1] > 0:
                self.win_size = new_size
        except Exception:
            pass

    def _gl_display(self):
        self._update_win_size()

        tex_data = pygame.image.tostring(self.render_surface, "RGBA", True)

        glBindTexture(GL_TEXTURE_2D, self.gl_tex)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, SCREEN_W, SCREEN_H,
                        GL_RGBA, GL_UNSIGNED_BYTE, tex_data)

        win_w, win_h = self.win_size
        glViewport(0, 0, win_w, win_h)

        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT)

        glUseProgram(self.gl_program)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.gl_tex)
        glUniform1i(self.gl_u_tex, 0)

        glBindBuffer(GL_ARRAY_BUFFER, self.gl_vbo)
        stride = 4 * _ctypes.sizeof(_ctypes.c_float)
        pos_offset = _ctypes.c_void_p(0)
        uv_offset = _ctypes.c_void_p(2 * _ctypes.sizeof(_ctypes.c_float))

        glEnableVertexAttribArray(self.gl_a_pos)
        glVertexAttribPointer(self.gl_a_pos, 2, GL_FLOAT, GL_FALSE, stride, pos_offset)
        glEnableVertexAttribArray(self.gl_a_uv)
        glVertexAttribPointer(self.gl_a_uv, 2, GL_FLOAT, GL_FALSE, stride, uv_offset)

        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4)

        glDisableVertexAttribArray(self.gl_a_pos)
        glDisableVertexAttribArray(self.gl_a_uv)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glUseProgram(0)

        pygame.display.flip()

    def reset_game(self):
        self.current_map = 0
        set_active_map(0)
        map_def = MAP_DEFS[0]
        self.money = map_def["money"]
        self.lives = map_def["lives"]
        self.round_num = 0
        self.max_rounds = 100
        self.bloons = []
        self.towers = []
        self.projectiles = []
        self.effects = EffectManager()
        self.waves = generate_waves()
        self.wave_active = False
        self.wave_queue = []
        self.wave_frame = 0
        self.game_speed = 1
        self.paused = False
        self.game_over = False
        self.victory = False
        self.selected_tower_type = None
        self.selected_tower = None
        self.auto_start = False
        self.path_cells = get_path_cells()
        self.tower_cells = set()
        self.total_pops = 0
        self.round_pops = 0
        self.round_money = 0
        self.round_escaped = 0
        self.sniper_lines = []
        self.click_regions = {}
        self.panel_scroll = 0
        self.panel_content_height = 0
        self.map_transition = False

    def _render_map(self):
        surf = pygame.Surface((GAME_W, SCREEN_H))
        for row in range(ROWS):
            for col in range(COLS):
                x, y = col * CELL, row * CELL
                c = C_GRASS if (col+row)%2==0 else C_GRASS2
                pygame.draw.rect(surf, c, (x, y, CELL, CELL))

        path_cells = get_path_cells()
        for (col, row) in path_cells:
            pygame.draw.rect(surf, C_PATH, (col*CELL, row*CELL, CELL, CELL))
        for (col, row) in path_cells:
            x, y = col*CELL, row*CELL
            for dc, dr in [(-1,0),(1,0),(0,-1),(0,1)]:
                nc, nr = col+dc, row+dr
                if (nc,nr) not in path_cells:
                    if dc == -1: pygame.draw.line(surf, C_PATH_EDGE, (x,y), (x,y+CELL), 2)
                    elif dc == 1: pygame.draw.line(surf, C_PATH_EDGE, (x+CELL,y), (x+CELL,y+CELL), 2)
                    elif dr == -1: pygame.draw.line(surf, C_PATH_EDGE, (x,y), (x+CELL,y), 2)
                    elif dr == 1: pygame.draw.line(surf, C_PATH_EDGE, (x,y+CELL), (x+CELL,y+CELL), 2)

        return surf

    def start_wave(self):
        if self.round_num >= self.max_rounds:
            return
        self.round_num += 1
        self.wave_active = True
        self.wave_frame = 0
        self.round_pops = 0
        self.round_money = 0
        self.round_escaped = 0

        wave_data = self.waves[self.round_num - 1]
        queue = []
        for entry in wave_data:
            if len(entry) == 6:
                bloon_type, count, delay, spacing, lane_off, path_idx = entry
            elif len(entry) == 5:
                bloon_type, count, delay, spacing, lane_off = entry
                path_idx = 0
            else:
                bloon_type, count, delay, spacing = entry
                lane_off = 0
                path_idx = 0
            for i in range(count):
                actual_offset = random.choice([-1, 0, 1]) if lane_off == 2 else lane_off
                queue.append((bloon_type, delay + i * spacing, actual_offset, path_idx))
        queue.sort(key=lambda x: x[1])
        self.wave_queue = queue

        has_moab = any(bt == "moab" for bt, _, _, _ in queue)
        self.play_sound("moab" if has_moab else "round")

    def place_tower(self, tower_type, col, row):
        if ((col, row) in self.path_cells or (col, row) in self.tower_cells or
            col < 0 or col >= COLS or row < 0 or row >= ROWS):
            return False
        cost = TOWER_DEFS[tower_type]["cost"]
        if self.money < cost:
            return False
        self.money -= cost
        tower = Tower(tower_type, col, row)
        self.towers.append(tower)
        self.tower_cells.add((col, row))
        self.play_sound("place")
        return True

    def sell_tower(self, tower):
        sell_price = int(tower.total_cost * SELL_RATIO)
        self.money += sell_price
        self.tower_cells.discard((tower.col, tower.row))
        self.towers.remove(tower)
        self.play_sound("sell")

    def upgrade_tower(self, tower, path):
        upgrade = tower.get_upgrade(path)
        if not upgrade or not tower.can_upgrade_path(path):
            return False
        if self.money < upgrade["cost"]:
            return False
        cost = tower.apply_upgrade(path)
        self.money -= cost
        self.play_sound("upgrade")
        return True

    def _process_pop(self, bloon):
        self.total_pops += 1
        self.round_pops += 1
        reward = 1
        if bloon.is_moab: reward = 50
        elif bloon.type == "ceramic": reward = 3
        elif bloon.type in ("rainbow","lead","zebra"): reward = 2
        self.money += reward
        self.round_money += reward
        self.play_sound("pop")
        self.effects.add_pop(bloon.x, bloon.y, bloon.color)
        if bloon.is_moab:
            self.effects.add_explosion(bloon.x, bloon.y, 60)

    def update(self, dt):
        if self.game_over or self.victory or self.paused or self.map_transition:
            return
        dt *= self.game_speed
        dt = min(dt, 0.05)

        alive_before = {b.id: b for b in self.bloons if b.alive}

        if self.wave_active:
            self.wave_frame += dt * 60
            while self.wave_queue and self.wave_queue[0][1] <= self.wave_frame:
                bt, _, lane_off, path_idx = self.wave_queue.pop(0)
                self.bloons.append(Bloon(bt, lane_offset=lane_off, path_idx=path_idx))

            if not self.wave_queue and not any(b.alive for b in self.bloons):
                self.wave_active = False
                if self.round_escaped == 0:
                    bonus = 100 + self.round_num
                    self.money += bonus
                    self.round_money += bonus
                if self.round_num >= self.max_rounds:
                    self.victory = True
                    self.play_sound("win")
                elif self.round_num % 10 == 0 and self.round_num < self.max_rounds:
                    self.map_transition = True
                    self.play_sound("win")
                elif self.auto_start:
                    self.start_wave()

        for bloon in self.bloons:
            if not bloon.alive:
                continue
            bloon.update(dt)
            if not bloon.alive and bloon.reached_end:
                self.lives -= bloon.rbe
                self.round_escaped += 1
                if self.lives <= 0:
                    self.lives = 0
                    self.game_over = True
                    self.play_sound("lose")

        for tower in self.towers:
            projs, new_bloons = tower.update(dt, self.bloons, self.effects)
            self.projectiles.extend(projs)
            self.bloons.extend(new_bloons)

        for proj in self.projectiles:
            if not proj.alive:
                continue
            new_bloons = proj.update(dt, self.bloons)
            self.bloons.extend(new_bloons)

            if not proj.alive and proj.blast_radius > 0 and proj.proj_type == "bomb":
                self.effects.add_explosion(proj.x, proj.y, proj.blast_radius)
                self.play_sound("explosion")
                for bloon in self.bloons:
                    if bloon.alive and bloon.id not in proj.hit_bloons:
                        d = math.sqrt((bloon.x-proj.x)**2 + (bloon.y-proj.y)**2)
                        if d < proj.blast_radius:
                            children = bloon.take_damage(1, DMG_EXPLOSION)
                            if not bloon.alive:
                                self.bloons.extend(children)
                            if proj.stun_duration > 0:
                                bloon.apply_stun(proj.stun_duration)
                if proj.frag_count > 0:
                    for i in range(proj.frag_count):
                        angle = 2*math.pi*i/proj.frag_count
                        fx = proj.x + math.cos(angle)*proj.blast_radius*0.7
                        fy = proj.y + math.sin(angle)*proj.blast_radius*0.7
                        for bloon in self.bloons:
                            if bloon.alive:
                                if math.sqrt((bloon.x-fx)**2+(bloon.y-fy)**2) < 25:
                                    children = bloon.take_damage(1, DMG_SHARP)
                                    if not bloon.alive:
                                        self.bloons.extend(children)

            if proj.proj_type == "bullet" and proj.alive:
                tower = proj.tower
                if proj.target:
                    self.sniper_lines.append(
                        [tower.x, tower.y, proj.target.x, proj.target.y, 0.1])

        popped_ids = set()
        for bloon in self.bloons:
            if (bloon.id in alive_before and not bloon.alive
                and not bloon.reached_end and bloon.id not in popped_ids):
                popped_ids.add(bloon.id)
                self._process_pop(bloon)

        self.sniper_lines = [[x1,y1,x2,y2,t-dt] for x1,y1,x2,y2,t in self.sniper_lines if t-dt > 0]
        if len(self.sniper_lines) > 50:
            self.sniper_lines = self.sniper_lines[-50:]

        self.projectiles = [p for p in self.projectiles if p.alive]
        self.bloons = [b for b in self.bloons if b.alive]
        self.effects.update(dt)

    def draw(self):
        self.render_surface.blit(self.map_surface, (0, 0))

        self.render_surface.set_clip((0, 0, GAME_W, SCREEN_H))

        if self.selected_tower_type:
            for col in range(COLS):
                for row in range(ROWS):
                    x, y = col*CELL, row*CELL
                    if (col,row) not in self.path_cells and (col,row) not in self.tower_cells:
                        s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                        s.fill((0, 255, 0, 20))
                        self.render_surface.blit(s, (x, y))
                    elif (col,row) not in self.tower_cells:
                        s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                        s.fill((255, 0, 0, 20))
                        self.render_surface.blit(s, (x, y))

        game_time = pygame.time.get_ticks()
        for bloon in sorted(self.bloons, key=lambda b: b.progress):
            if bloon.alive:
                bloon.draw(self.render_surface, game_time)

        for tower in self.towers:
            tower.draw(self.render_surface, selected=(self.selected_tower == tower))

        for proj in self.projectiles:
            proj.draw(self.render_surface)

        for x1,y1,x2,y2,t in self.sniper_lines:
            alpha = int(255 * t / 0.1)
            pygame.draw.line(self.render_surface, (255,255,100, alpha),
                           (int(x1),int(y1)), (int(x2),int(y2)), 2)

        self.effects.draw(self.render_surface)

        if self.selected_tower_type and not self.selected_tower:
            mx, my = self._map_mouse(pygame.mouse.get_pos())
            if mx < GAME_W:
                col, row = mx // CELL, my // CELL
                valid = ((col,row) not in self.path_cells and
                        (col,row) not in self.tower_cells and
                        0 <= col < COLS and 0 <= row < ROWS and
                        self.money >= TOWER_DEFS[self.selected_tower_type]["cost"])
                color = (0,255,0,60) if valid else (255,0,0,60)
                s = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                s.fill(color)
                self.render_surface.blit(s, (col*CELL, row*CELL))
                rv = TOWER_DEFS[self.selected_tower_type]["range"]
                if rv > 0:
                    cx, cy = col*CELL+CELL//2, row*CELL+CELL//2
                    max_vis_range = max(GAME_W, SCREEN_H)
                    vis_range = min(rv, max_vis_range)
                    rs = pygame.Surface((vis_range*2+2, vis_range*2+2), pygame.SRCALPHA)
                    pygame.draw.circle(rs, (255,255,255,30), (vis_range+1,vis_range+1), vis_range)
                    pygame.draw.circle(rs, (255,255,255,60), (vis_range+1,vis_range+1), vis_range, 2)
                    self.render_surface.blit(rs, (cx-vis_range-1, cy-vis_range-1))
                preview = make_tower_sprite(self.selected_tower_type)
                self.render_surface.blit(preview, (col*CELL+CELL//2-preview.get_width()//2,
                                                   row*CELL+CELL//2-preview.get_height()//2))

        self.render_surface.set_clip(None)

        self._draw_panel()

        if self.game_over:
            o = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            o.fill((0,0,0,150))
            self.render_surface.blit(o, (0,0))
            t = self.font_xl.render("GAME OVER", True, C_RED)
            self.render_surface.blit(t, (GAME_W//2-t.get_width()//2, SCREEN_H//2-50))
            s = self.font_md.render(f"Survived {self.round_num} rounds", True, C_WHITE)
            self.render_surface.blit(s, (GAME_W//2-s.get_width()//2, SCREEN_H//2+10))
            s2 = self.font_md.render("Press R to restart", True, C_YELLOW)
            self.render_surface.blit(s2, (GAME_W//2-s2.get_width()//2, SCREEN_H//2+40))

        if self.victory:
            o = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            o.fill((0,0,0,150))
            self.render_surface.blit(o, (0,0))
            t = self.font_xl.render("VICTORY!", True, C_GOLD)
            self.render_surface.blit(t, (GAME_W//2-t.get_width()//2, SCREEN_H//2-50))
            s = self.font_md.render(f"All {self.max_rounds} rounds completed!", True, C_WHITE)
            self.render_surface.blit(s, (GAME_W//2-s.get_width()//2, SCREEN_H//2+10))
            s2 = self.font_md.render("Press R to play again", True, C_YELLOW)
            self.render_surface.blit(s2, (GAME_W//2-s2.get_width()//2, SCREEN_H//2+40))

        if self.map_transition:
            o = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            o.fill((0,0,0,180))
            self.render_surface.blit(o, (0,0))
            map_name = MAP_DEFS[self.current_map]["name"]
            t = self.font_xl.render("Map Complete!", True, C_GOLD)
            self.render_surface.blit(t, (GAME_W//2-t.get_width()//2, SCREEN_H//2-100))
            t2 = self.font_lg.render(f"{map_name} cleared!", True, C_WHITE)
            self.render_surface.blit(t2, (GAME_W//2-t2.get_width()//2, SCREEN_H//2-55))
            bonus = 100 + (self.current_map + 1) * 50
            sell_refund = sum(int(tw.total_cost * SELL_RATIO) for tw in self.towers)
            next_map_idx = min(self.current_map + 1, 9)
            next_map = MAP_DEFS[next_map_idx]
            total_money = next_map["money"] + bonus + sell_refund
            t3 = self.font_md.render(f"Next map starts: ${next_map['money']} + ${bonus} bonus + ${sell_refund} sell refund = ${total_money}", True, C_GREEN)
            self.render_surface.blit(t3, (GAME_W//2-t3.get_width()//2, SCREEN_H//2-15))
            t4 = self.font_md.render(f"Lives: {next_map['lives']}  |  Auto-start: OFF", True, C_CYAN)
            self.render_surface.blit(t4, (GAME_W//2-t4.get_width()//2, SCREEN_H//2+15))
            t5 = self.font_md.render(f"Next: Map {next_map_idx+1} - {next_map['name']}", True, C_WHITE)
            self.render_surface.blit(t5, (GAME_W//2-t5.get_width()//2, SCREEN_H//2+45))
            t6 = self.font_md.render("Press SPACE to continue", True, C_YELLOW)
            self.render_surface.blit(t6, (GAME_W//2-t6.get_width()//2, SCREEN_H//2+80))

        if self.paused and not self.game_over and not self.victory and not self.map_transition:
            o = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            o.fill((0,0,0,100))
            self.render_surface.blit(o, (0,0))
            t = self.font_xl.render("PAUSED", True, C_WHITE)
            self.render_surface.blit(t, (GAME_W//2-t.get_width()//2, SCREEN_H//2-20))

        if self.use_gpu:
            self._gl_display()
        else:
            self._update_win_size()
            win_w, win_h = self.win_size
            if win_w != SCREEN_W or win_h != SCREEN_H:
                scaled = pygame.transform.smoothscale(self.render_surface, (win_w, win_h))
                self.screen.blit(scaled, (0, 0))
            else:
                self.screen.blit(self.render_surface, (0, 0))
            pygame.display.flip()

    def _draw_panel(self):
        self.click_regions = {}
        panel_x = GAME_W
        pygame.draw.rect(self.render_surface, C_PANEL_BG, (panel_x, 0, PANEL_W, SCREEN_H))
        pygame.draw.line(self.render_surface, C_PANEL_BORDER, (panel_x, 0), (panel_x, SCREEN_H), 3)

        x = panel_x + 8
        y = 8
        pw = PANEL_W - 16

        t = self.font_lg.render("PopTD", True, C_GOLD)
        self.render_surface.blit(t, (x, y)); y += 28

        for text, color in [
            (f"Map {self.current_map+1}: {MAP_DEFS[self.current_map]['name']}", C_CYAN),
            (f"Money: ${self.money}", C_GOLD),
            (f"Lives: {self.lives}", C_RED if self.lives < 50 else C_GREEN),
            (f"Round: {self.round_num}/{self.max_rounds}", C_WHITE),
        ]:
            t = self.font_md.render(text, True, color)
            self.render_surface.blit(t, (x, y)); y += 18

        for text, color in [
            (f"Pops: {self.total_pops}", C_GRAY),
            (f"Speed: {self.game_speed}x{' [PAUSED]' if self.paused else ''}", C_CYAN),
            (f"FPS: {int(self.clock.get_fps())} {'[GPU]' if self.use_gpu else '[CPU]'}", (100,180,100) if self.use_gpu else C_GRAY),
        ]:
            t = self.font_sm.render(text, True, color)
            self.render_surface.blit(t, (x, y)); y += 15

        y += 5
        pygame.draw.line(self.render_surface, C_PANEL_BORDER, (x, y), (x+pw, y), 1)
        y += 5

        content_top = y
        content_height = SCREEN_H - content_top

        scroll_rect = pygame.Rect(panel_x, content_top, PANEL_W, content_height)
        self.render_surface.set_clip(scroll_rect)

        content_y = content_top - self.panel_scroll

        if self.selected_tower:
            content_y = self._draw_tower_info(x, content_y, pw)
        else:
            content_y = self._draw_tower_shop(x, content_y, pw)

        self.panel_content_height = content_y - content_top + self.panel_scroll

        self.render_surface.set_clip(None)

        if self.panel_content_height > content_height:
            max_scroll = self.panel_content_height - content_height
            self.panel_scroll = min(self.panel_scroll, max_scroll)
            bar_h = max(30, int(content_height * content_height / self.panel_content_height))
            bar_y = content_top + int(self.panel_scroll * (content_height - bar_h) / max_scroll) if max_scroll > 0 else content_top
            pygame.draw.rect(self.render_surface, (60,60,70), (panel_x + PANEL_W - 6, bar_y, 4, bar_h), border_radius=2)
        else:
            self.panel_scroll = 0

    def advance_map(self):
        sell_refund = 0
        for tower in self.towers:
            sell_refund += int(tower.total_cost * SELL_RATIO)

        self.current_map += 1
        set_active_map(self.current_map)
        map_def = MAP_DEFS[self.current_map]

        bonus = 100 + self.current_map * 50

        self.money = map_def["money"] + bonus + sell_refund

        self.lives = map_def["lives"]

        self.auto_start = False

        self.towers = []
        self.tower_cells = set()
        self.bloons = []
        self.projectiles = []
        self.effects = EffectManager()
        self.path_cells = get_path_cells()
        self.map_surface = self._render_map()
        self.selected_tower = None
        self.selected_tower_type = None
        self.sniper_lines = []

    def _draw_tower_shop(self, x, y, pw):
        mouse_pos = self._map_mouse(pygame.mouse.get_pos())
        t = self.font_md.render("TOWERS", True, C_WHITE)
        self.render_surface.blit(t, (x, y)); y += 22

        for i, ttype in enumerate(TOWER_ORDER):
            td = TOWER_DEFS[ttype]
            btn_rect = pygame.Rect(x, y, pw, 48)
            is_selected = (self.selected_tower_type == ttype)
            can_afford = self.money >= td["cost"]
            is_hovered = btn_rect.collidepoint(mouse_pos)

            if is_selected: bg = (60,100,60)
            elif is_hovered and can_afford: bg = (60,60,80)
            else: bg = (50,50,60)
            pygame.draw.rect(self.render_surface, bg, btn_rect, border_radius=5)
            border = C_GOLD if is_selected else (C_WHITE if can_afford else C_GRAY)
            pygame.draw.rect(self.render_surface, border, btn_rect, 2, border_radius=5)

            icon = make_tower_sprite(ttype)
            icon = pygame.transform.scale(icon, (30, 30))
            self.render_surface.blit(icon, (x+4, y+9))

            name_c = C_WHITE if can_afford else C_GRAY
            nt = self.font_sm.render(td["name"], True, name_c)
            self.render_surface.blit(nt, (x+38, y+4))
            ct = self.font_sm.render(f"${td['cost']}", True, C_GOLD if can_afford else C_RED)
            self.render_surface.blit(ct, (x+38, y+18))

            max_text_w = pw - 38 - 6
            desc_lines = wrap_text(td["description"], self.font_sm, max_text_w)
            desc_h = len(desc_lines) * 14
            btn_h = max(48, 32 + desc_h + 4)
            btn_rect.height = btn_h

            for j, line in enumerate(desc_lines):
                dt_text = self.font_sm.render(line, True, (140,140,160))
                self.render_surface.blit(dt_text, (x+38, y+32 + j*14))

            self.click_regions[f"tower_{ttype}"] = btn_rect
            y += btn_h + 4

        y += 5
        pygame.draw.line(self.render_surface, C_PANEL_BORDER, (x, y), (x+pw, y), 1)
        y += 5

        controls = [
            "SPACE: Start wave  1/2/3: Speed",
            "P: Pause  R: Restart  A: Auto",
            "Right-click: Deselect",
        ]
        for ctrl in controls:
            t = self.font_sm.render(ctrl, True, (130,130,150))
            self.render_surface.blit(t, (x, y)); y += 14

        y += 8
        if not self.wave_active and self.round_num < self.max_rounds:
            btn_rect = pygame.Rect(x, y, pw, 30)
            is_hovered = btn_rect.collidepoint(mouse_pos)
            color = (60,140,60) if is_hovered else (40,100,40)
            pygame.draw.rect(self.render_surface, color, btn_rect, border_radius=6)
            pygame.draw.rect(self.render_surface, C_GREEN, btn_rect, 2, border_radius=6)
            text = self.font_md.render(f"Start Wave {self.round_num + 1}", True, C_WHITE)
            self.render_surface.blit(text, (x + pw//2 - text.get_width()//2, y+6))
            self.click_regions["start_wave"] = btn_rect
            y += 35

        at = self.font_sm.render(f"Auto-start: {'ON' if self.auto_start else 'OFF'}", True,
                                  C_GREEN if self.auto_start else C_GRAY)
        self.render_surface.blit(at, (x, y)); y += 20

        return y


    def _draw_tower_info(self, x, y, pw):
        mouse_pos = self._map_mouse(pygame.mouse.get_pos())
        tower = self.selected_tower
        td = TOWER_DEFS[tower.type]

        back_rect = pygame.Rect(x, y, pw, 22)
        is_hovered = back_rect.collidepoint(mouse_pos)
        color = (100,60,60) if is_hovered else (80,40,40)
        pygame.draw.rect(self.render_surface, color, back_rect, border_radius=4)
        pygame.draw.rect(self.render_surface, C_RED, back_rect, 1, border_radius=4)
        t = self.font_sm.render("< Back to shop", True, C_WHITE)
        self.render_surface.blit(t, (x+5, y+3))
        self.click_regions["back"] = back_rect
        y += 26

        icon = make_tower_sprite(tower.type, tower.upgrade_level)
        icon = pygame.transform.scale(icon, (48, 48))
        self.render_surface.blit(icon, (x + pw//2 - 24, y))
        y += 52

        t = self.font_md.render(tower.name, True, C_WHITE)
        self.render_surface.blit(t, (x, y)); y += 18

        stats = [
            f"Range: {tower.range}",
            f"Fire Rate: {tower.fire_rate:.1f}/s",
            f"Pierce: {tower.pierce}  Damage: {tower.damage}",
            f"Type: {tower.damage_type.capitalize()}",
        ]
        if tower.blast_radius: stats.append(f"Blast: {tower.blast_radius}")
        if tower.freeze_duration: stats.append(f"Freeze: {tower.freeze_duration:.1f}s")
        if tower.can_pop_lead: stats.append("Pops Lead!")
        for stat in stats:
            t = self.font_sm.render(stat, True, (170,170,190))
            self.render_surface.blit(t, (x, y)); y += 14

        y += 5
        pygame.draw.line(self.render_surface, C_PANEL_BORDER, (x, y), (x+pw, y), 1)
        y += 5

        t = self.font_md.render("UPGRADES", True, C_GOLD)
        self.render_surface.blit(t, (x, y)); y += 20

        max_text_w = pw - 8

        t = self.font_sm.render("Path 1:", True, C_CYAN)
        self.render_surface.blit(t, (x, y)); y += 16

        for i in range(2):
            idx = i
            upg = td["upgrades"][idx]
            if idx < tower.upgrade_path1:
                t = self.font_sm.render(f"  OK {upg['name']}", True, C_GREEN)
                self.render_surface.blit(t, (x, y)); y += 14
            elif idx == tower.upgrade_path1:
                name_text = f"{upg['name']} ${upg['cost']}"
                desc_lines = wrap_text(upg['desc'], self.font_sm, max_text_w)
                btn_h = 26 + max(0, len(desc_lines)-1) * 14
                btn_rect = pygame.Rect(x, y, pw, btn_h)
                can_afford = self.money >= upg["cost"]
                is_hovered = btn_rect.collidepoint(mouse_pos) and can_afford
                color = (60,80,60) if is_hovered else (50,50,60)
                pygame.draw.rect(self.render_surface, color, btn_rect, border_radius=4)
                border = C_GOLD if can_afford else C_GRAY
                pygame.draw.rect(self.render_surface, border, btn_rect, 1, border_radius=4)
                t = self.font_sm.render(name_text, True, C_WHITE if can_afford else C_GRAY)
                self.render_surface.blit(t, (x+4, y+2))
                for j, line in enumerate(desc_lines):
                    dt = self.font_sm.render(line, True, (140,140,160))
                    self.render_surface.blit(dt, (x+4, y+13 + j*14))
                self.click_regions[f"upgrade_1_{i}"] = btn_rect
                y += btn_h + 2
            else:
                t = self.font_sm.render("  ??? (locked)", True, (70,70,70))
                self.render_surface.blit(t, (x, y)); y += 14

        y += 3
        t = self.font_sm.render("Path 2:", True, C_CYAN)
        self.render_surface.blit(t, (x, y)); y += 16

        for i in range(2):
            idx = i + 2
            upg = td["upgrades"][idx]
            if idx - 2 < tower.upgrade_path2:
                t = self.font_sm.render(f"  OK {upg['name']}", True, C_GREEN)
                self.render_surface.blit(t, (x, y)); y += 14
            elif idx - 2 == tower.upgrade_path2:
                name_text = f"{upg['name']} ${upg['cost']}"
                desc_lines = wrap_text(upg['desc'], self.font_sm, max_text_w)
                btn_h = 26 + max(0, len(desc_lines)-1) * 14
                btn_rect = pygame.Rect(x, y, pw, btn_h)
                can_afford = self.money >= upg["cost"]
                is_hovered = btn_rect.collidepoint(mouse_pos) and can_afford
                color = (60,80,60) if is_hovered else (50,50,60)
                pygame.draw.rect(self.render_surface, color, btn_rect, border_radius=4)
                border = C_GOLD if can_afford else C_GRAY
                pygame.draw.rect(self.render_surface, border, btn_rect, 1, border_radius=4)
                t = self.font_sm.render(name_text, True, C_WHITE if can_afford else C_GRAY)
                self.render_surface.blit(t, (x+4, y+2))
                for j, line in enumerate(desc_lines):
                    dt = self.font_sm.render(line, True, (140,140,160))
                    self.render_surface.blit(dt, (x+4, y+13 + j*14))
                self.click_regions[f"upgrade_2_{i}"] = btn_rect
                y += btn_h + 2
            else:
                t = self.font_sm.render("  ??? (locked)", True, (70,70,70))
                self.render_surface.blit(t, (x, y)); y += 14

        y += 8
        pygame.draw.line(self.render_surface, C_PANEL_BORDER, (x, y), (x+pw, y), 1)
        y += 5

        sell_price = int(tower.total_cost * SELL_RATIO)
        sell_rect = pygame.Rect(x, y, pw, 26)
        is_hovered = sell_rect.collidepoint(mouse_pos)
        color = (120,60,60) if is_hovered else (80,40,40)
        pygame.draw.rect(self.render_surface, color, sell_rect, border_radius=6)
        pygame.draw.rect(self.render_surface, C_RED, sell_rect, 2, border_radius=6)
        st = self.font_md.render(f"Sell for ${sell_price}", True, C_GOLD)
        self.render_surface.blit(st, (x + pw//2 - st.get_width()//2, y+4))
        self.click_regions["sell"] = sell_rect
        y += 30

        t = self.font_sm.render(f"Invested: ${tower.total_cost}", True, C_GRAY)
        self.render_surface.blit(t, (x, y)); y += 20

        return y


    def _map_mouse(self, pos):
        mx, my = pos
        ww, wh = self.win_size
        rx = int(mx * SCREEN_W / ww)
        ry = int(my * SCREEN_H / wh)
        return (rx, ry)


    def _handle_panel_click(self, pos):
        mx, my = pos

        if self.selected_tower:
            if "back" in self.click_regions and self.click_regions["back"].collidepoint(mx, my):
                self.selected_tower = None
                return
            if "sell" in self.click_regions and self.click_regions["sell"].collidepoint(mx, my):
                self.sell_tower(self.selected_tower)
                self.selected_tower = None
                return
            for path in [1, 2]:
                for i in range(2):
                    key = f"upgrade_{path}_{i}"
                    if key in self.click_regions and self.click_regions[key].collidepoint(mx, my):
                        self.upgrade_tower(self.selected_tower, path)
                        return
            return

        for ttype in TOWER_ORDER:
            key = f"tower_{ttype}"
            if key in self.click_regions and self.click_regions[key].collidepoint(mx, my):
                if self.money >= TOWER_DEFS[ttype]["cost"]:
                    self.selected_tower_type = ttype
                    self.selected_tower = None
                return

        if "start_wave" in self.click_regions and self.click_regions["start_wave"].collidepoint(mx, my):
            self.start_wave()

    def handle_click(self, pos):
        mx, my = self._map_mouse(pos)
        if self.game_over or self.victory:
            return

        if mx >= GAME_W:
            self._handle_panel_click((mx, my))
            return


        if self.selected_tower:
            clicked_tower = None
            for tower in self.towers:
                if abs(mx - tower.x) < CELL//2 and abs(my - tower.y) < CELL//2:
                    clicked_tower = tower
                    break
            if clicked_tower and clicked_tower != self.selected_tower:
                self.selected_tower = clicked_tower
                self.selected_tower_type = None
            else:
                self.selected_tower = None
            return

        if self.selected_tower_type:
            col, row = mx // CELL, my // CELL
            if self.place_tower(self.selected_tower_type, col, row):
                if self.money < TOWER_DEFS[self.selected_tower_type]["cost"]:
                    self.selected_tower_type = None
            return

        for tower in self.towers:
            if abs(mx - tower.x) < CELL//2 and abs(my - tower.y) < CELL//2:
                self.selected_tower = tower
                return

    def handle_right_click(self, pos):
        self.selected_tower_type = None
        self.selected_tower = None

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.win_size = (event.w, event.h)
                    if not self.use_gpu:
                        self.screen = pygame.display.set_mode(
                            (event.w, event.h), pygame.RESIZABLE)
                elif event.type in (pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED,
                                    pygame.WINDOWMAXIMIZED, pygame.WINDOWRESTORED):
                    self._update_win_size()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 3:
                        self.handle_right_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = self._map_mouse(pygame.mouse.get_pos())
                    if mx >= GAME_W and self.panel_content_height > 0:
                        scroll_amount = -event.y * 30
                        max_scroll = max(0, self.panel_content_height - (SCREEN_H - 300))
                        self.panel_scroll = max(0, min(self.panel_scroll - scroll_amount, max_scroll))
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.selected_tower_type = None
                        self.selected_tower = None
                    elif event.key == pygame.K_SPACE:
                        if self.map_transition:
                            self.advance_map()
                            self.map_transition = False
                        elif not self.wave_active and not self.game_over and not self.victory:
                            self.start_wave()
                    elif event.key == pygame.K_1:
                        self.game_speed = 1
                    elif event.key == pygame.K_2:
                        self.game_speed = 2
                    elif event.key == pygame.K_3:
                        self.game_speed = 3
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.current_map = 0
                        set_active_map(0)
                        self.reset_game()
                        self.map_surface = self._render_map()
                    elif event.key == pygame.K_a:
                        self.auto_start = not self.auto_start

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
