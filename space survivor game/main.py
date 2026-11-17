# SPACE SURVIVOR
# Survive as long as you can. Monsters double every 10s, a boss arrives every 30s.
# Drops: health 3%, speed 5%, weapon 4%, shield 2%.
# Works on desktop (python main.py) and in the browser via pygbag.

import asyncio
import array
import json
import math
import os
import random
import sys

import pygame

# ---------------------------------------------------------------- settings
W, H = 1100, 620
GW = 860                 # width of the game view, the rest is the side panel
CELL = 64
MAX_ENEMIES = 340        # safety cap so the game stays smooth

DROP_TABLE = [           # (kind, chance) - one roll per kill, 14% total
    ("health", 0.03),
    ("speed", 0.05),
    ("weapon", 0.04),
    ("shield", 0.02),
]
SHIELD_TIME = 10.0       # seconds of invulnerability
SHIELD_BLINK = 3.0       # blinks during the last 3 seconds
SPEED_TIME = 8.0         # speed boost duration
SPEED_MULT = 1.6
HEAL = 25
DROP_LIFE = 12.0
BOSS_EVERY = 30          # a new boss every 30 seconds
DOUBLE_EVERY = 10        # monster count doubles every 10 seconds
START_MONSTERS = 5       # monsters on the field at the start
SPEEDUP = 0.06           # monsters get 6% faster every 10 seconds
MAX_SPEEDUP = 2.0
BOSS_COLORS = [(255, 150, 40), (60, 255, 130), (0, 235, 255), (180, 90, 255), (255, 225, 60),
               (255, 60, 190), (255, 55, 70), (120, 160, 255), (255, 255, 255)]

BG = (4, 4, 14)
WHITE = (255, 255, 255)
CYAN = (0, 235, 255)
PINK = (255, 60, 190)
YELLOW = (255, 225, 60)
RED = (255, 55, 70)
GREEN = (60, 255, 130)
ORANGE = (255, 150, 40)
PURPLE = (180, 90, 255)
GREY = (120, 125, 140)
SKIN = (222, 172, 135)
BEARD = (35, 25, 20)

SUIT_WHITE = (238, 240, 248)
SUIT_RED = (225, 40, 55)

try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
except Exception:
    pass
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Space Survivor")
clock = pygame.time.Clock()


def font(size):
    return pygame.font.Font(None, size)


F_XS, F_S, F_M, F_L, F_XL = font(19), font(23), font(30), font(54), font(92)


def here(name):
    try:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    except NameError:
        return name


# ---------------------------------------------------------------- sound (generated in code)
def make_sound(f0, f1, dur, vol=0.25, noise=False, square=True):
    try:
        init = pygame.mixer.get_init()
        if not init:
            return None
        sr, _, ch = init
        n = int(sr * dur)
        buf = array.array("h")
        ph = 0.0
        for i in range(n):
            t = i / n
            ph += 2 * math.pi * (f0 + (f1 - f0) * t) / sr
            if noise:
                s = random.uniform(-1, 1)
            elif square:
                s = 1.0 if math.sin(ph) > 0 else -1.0
            else:
                s = math.sin(ph)
            v = int(s * (1 - t) ** 2 * vol * 32767)
            for _ in range(ch):
                buf.append(v)
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None


SFX = {
    "laser": make_sound(1400, 600, 0.06, 0.05),
    "hit": make_sound(300, 120, 0.05, 0.07, noise=True),
    "kill": make_sound(500, 150, 0.08, 0.08),
    "hurt": make_sound(200, 60, 0.2, 0.25),
    "health": make_sound(600, 1200, 0.25, 0.15, square=False),
    "speed": make_sound(300, 1600, 0.3, 0.12),
    "weapon": make_sound(400, 1400, 0.4, 0.15, square=False),
    "shield": make_sound(900, 300, 0.4, 0.15, square=False),
    "boom": make_sound(160, 30, 0.4, 0.3, noise=True),
    "boss": make_sound(80, 40, 1.0, 0.35),
}
_last_play = {}


def play(name):
    s = SFX.get(name)
    if not s:
        return
    now = pygame.time.get_ticks()
    if now - _last_play.get(name, -999) < 45:
        return
    _last_play[name] = now
    try:
        s.play()
    except Exception:
        pass


# ---------------------------------------------------------------- save best time
def load_best():
    try:
        if sys.platform == "emscripten":
            import platform
            v = platform.window.localStorage.getItem("ss_best")
            return float(v) if v else 0.0
        with open(here("save.json")) as f:
            return float(json.load(f).get("best", 0))
    except Exception:
        return 0.0


def save_best(v):
    try:
        if sys.platform == "emscripten":
            import platform
            platform.window.localStorage.setItem("ss_best", str(v))
        else:
            with open(here("save.json"), "w") as f:
                json.dump({"best": v}, f)
    except Exception:
        pass


def fmt_time(t):
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


# ---------------------------------------------------------------- graphics helpers
_glow_cache = {}


def glow(r, color):
    key = (r, color)
    s = _glow_cache.get(key)
    if s is None:
        s = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            pygame.draw.circle(s, (*color, 22), (r * 2, r * 2), int(r * (0.8 + i * 0.25)))
        _glow_cache[key] = s
    return s


def poly(shape, r, cx, cy, rot=0.0):
    sides = {"square": 4, "tri": 3, "hex": 6, "diamond": 4}[shape]
    off = {"square": math.pi / 4, "tri": -math.pi / 2, "hex": 0, "diamond": 0}[shape]
    return [(cx + math.cos(off + rot + i * 2 * math.pi / sides) * r,
             cy + math.sin(off + rot + i * 2 * math.pi / sides) * r) for i in range(sides)]


def star_pts(r, cx, cy, rot, n=6):
    pts = []
    for i in range(n * 2):
        rr = r if i % 2 == 0 else r * 0.5
        a = rot + i * math.pi / n
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


def make_enemy_sprite(shape, r, color):
    size = r * 4
    c = size // 2
    out = []
    for flash in (False, True):
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.blit(glow(r, color), (0, 0))
        dark = tuple(int(v * 0.35) for v in color)
        fill = WHITE if flash else dark
        if shape == "circle":
            pygame.draw.circle(s, fill, (c, c), r)
            pygame.draw.circle(s, WHITE if flash else color, (c, c), r, 3)
        elif shape == "star":
            pts = star_pts(r, c, c, 0)
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, WHITE if flash else color, pts, 3)
        else:
            pts = poly(shape, r, c, c)
            pygame.draw.polygon(s, fill, pts)
            pygame.draw.polygon(s, WHITE if flash else color, pts, 3)
        ey = c - r * 0.15
        for dx in (-r * 0.3, r * 0.3):
            pygame.draw.circle(s, WHITE if not flash else color, (int(c + dx), int(ey)), max(2, r // 6))
        out.append(s)
    return out


# ---------------------------------------------------------------- the hero: astronaut
def load_face():
    try:
        return pygame.image.load(here("face.png")).convert_alpha()
    except Exception:
        return None


FACE = load_face()


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def make_astronaut(suit, use_photo, scale=1):
    w, h = 64, 86
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    dark = shade(suit, 0.62)
    mid = shade(suit, 0.85)
    # jetpack
    pygame.draw.rect(s, (70, 75, 90), (13, 36, 38, 30), border_radius=6)
    pygame.draw.rect(s, (95, 100, 120), (10, 38, 9, 24), border_radius=4)
    pygame.draw.rect(s, (95, 100, 120), (45, 38, 9, 24), border_radius=4)
    # legs + boots
    for lx in (19, 34):
        pygame.draw.rect(s, mid, (lx, 62, 11, 15), border_radius=4)
        pygame.draw.rect(s, dark, (lx, 62, 11, 15), 2, border_radius=4)
        pygame.draw.rect(s, (55, 60, 75), (lx - 1, 75, 13, 8), border_radius=3)
        pygame.draw.line(s, CYAN, (lx + 1, 79), (lx + 10, 79), 1)
    # arms + gloves
    for ax, gx in ((8, 11), (46, 52)):
        pygame.draw.rect(s, mid, (ax, 40, 10, 18), border_radius=5)
        pygame.draw.rect(s, dark, (ax, 40, 10, 18), 2, border_radius=5)
        pygame.draw.circle(s, (70, 75, 90), (gx, 59), 5)
    # torso
    pygame.draw.rect(s, suit, (16, 37, 32, 28), border_radius=8)
    pygame.draw.rect(s, dark, (16, 37, 32, 28), 2, border_radius=8)
    # chest control panel
    pygame.draw.rect(s, (35, 40, 60), (23, 44, 18, 11), border_radius=3)
    pygame.draw.circle(s, RED, (27, 49), 2)
    pygame.draw.circle(s, GREEN, (32, 49), 2)
    pygame.draw.circle(s, CYAN, (37, 49), 2)
    # belt
    pygame.draw.rect(s, (60, 65, 80), (16, 58, 32, 4))
    pygame.draw.rect(s, YELLOW, (29, 58, 6, 4))
    # shoulder badges
    pygame.draw.circle(s, CYAN, (19, 41), 3)
    pygame.draw.circle(s, CYAN, (45, 41), 3)
    # antenna
    pygame.draw.line(s, (170, 175, 190), (44, 8), (51, 0), 2)
    pygame.draw.circle(s, RED, (51, 2), 3)
    # helmet shell
    pygame.draw.circle(s, suit, (32, 22), 21)
    pygame.draw.circle(s, dark, (32, 22), 21, 2)
    # visor
    pygame.draw.circle(s, (15, 25, 55), (32, 23), 16)
    if use_photo and FACE is not None:
        face = pygame.transform.smoothscale(FACE, (30, 30))
        s.blit(face, (17, 8))
        tint = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(tint, (60, 140, 255, 45), (16, 16), 16)
        s.blit(tint, (16, 7))
    else:
        cx, cy = 32, 24
        pygame.draw.ellipse(s, SKIN, (cx - 11, cy - 13, 22, 25))
        pygame.draw.ellipse(s, BEARD, (cx - 11, cy - 2, 22, 15))
        pygame.draw.ellipse(s, SKIN, (cx - 8, cy - 4, 16, 6))
        pygame.draw.ellipse(s, (20, 14, 10), (cx - 5, cy + 1, 10, 4))
        pygame.draw.line(s, (170, 90, 90), (cx - 3, cy + 5), (cx + 3, cy + 5), 1)
        for ex in (cx - 4, cx + 4):
            pygame.draw.circle(s, WHITE, (ex, cy - 5), 2)
            pygame.draw.circle(s, (30, 20, 15), (ex, cy - 5), 1)
        pygame.draw.line(s, BEARD, (cx - 7, cy - 8), (cx - 2, cy - 8), 2)
        pygame.draw.line(s, BEARD, (cx + 2, cy - 8), (cx + 7, cy - 8), 2)
    # visor rim + glare
    pygame.draw.circle(s, CYAN, (32, 23), 16, 2)
    pygame.draw.arc(s, (230, 245, 255), (19, 10, 20, 20), math.radians(100), math.radians(170), 3)
    if scale != 1:
        s = pygame.transform.smoothscale(s, (w * scale, h * scale))
    return s


# ---------------------------------------------------------------- data
ETYPES = {
    "crawler":    dict(name="Crawler",    shape="square",  r=12, color=RED,             hp=14,   spd=80,  dmg=10),
    "zipper":     dict(name="Zipper",     shape="circle",  r=8,  color=YELLOW,          hp=8,    spd=150, dmg=7),
    "brute":      dict(name="Brute",      shape="hex",     r=20, color=PURPLE,          hp=80,   spd=48,  dmg=18),
    "spitter":    dict(name="Spitter",    shape="tri",     r=13, color=ORANGE,          hp=24,   spd=72,  dmg=10),
    "splitter":   dict(name="Splitter",   shape="diamond", r=16, color=GREEN,           hp=34,   spd=64,  dmg=12),
    "spawnling":  dict(name="Spawnling",  shape="circle",  r=7,  color=(140, 255, 170), hp=7,    spd=125, dmg=6),
    "mothership": dict(name="Bosses",     shape="star",    r=50, color=PINK,            hp=500,  spd=60,  dmg=30),
}
SPRITES = {k: make_enemy_sprite(v["shape"], v["r"], v["color"]) for k, v in ETYPES.items()}
ICONS = {k: pygame.transform.smoothscale(v[0], (26, 26)) for k, v in SPRITES.items()}

WEAPONS = [
    dict(name="Blue Laser",      color=(60, 140, 255), shots=1, spread=0.0,  parallel=0,  dmg=14, cd=0.36, pierce=1, width=4),
    dict(name="Green Twin",      color=(60, 255, 110), shots=2, spread=0.0,  parallel=12, dmg=12, cd=0.36, pierce=1, width=5),
    dict(name="Yellow Spread",   color=(255, 225, 50), shots=3, spread=0.20, parallel=0,  dmg=15, cd=0.32, pierce=2, width=5),
    dict(name="Red Destroyer",   color=(255, 45, 45),  shots=5, spread=0.15, parallel=0,  dmg=22, cd=0.22, pierce=3, width=7),
]
LASER_SPEED = 760


class Enemy:
    __slots__ = ("kind", "t", "x", "y", "r", "hp", "maxhp", "spd", "flash", "cd", "rot", "phase", "ptimer", "dash",
                 "color", "level", "aim_cd")

    def __init__(self, kind, x, y, hpmul=1.0):
        t = ETYPES[kind]
        self.kind, self.t = kind, t
        self.x, self.y, self.r = x, y, t["r"]
        self.hp = self.maxhp = t["hp"] * hpmul
        self.spd = t["spd"] * random.uniform(0.9, 1.1)
        self.flash = 0.0
        self.cd = random.uniform(1, 2.5)
        self.rot = 0.0
        self.phase = 0
        self.ptimer = 3.0
        self.dash = None
        self.color = t["color"]
        self.level = 0
        self.aim_cd = 2.0


def boss_color(n):
    if n <= len(BOSS_COLORS):
        return BOSS_COLORS[n - 1]
    import colorsys
    r, g, b = colorsys.hsv_to_rgb((n * 0.137) % 1, 0.85, 1)
    return int(r * 255), int(g * 255), int(b * 255)


class Game:
    def __init__(self):
        self.px = self.py = 0.0
        self.maxhp = self.hp = 100.0
        self.iframe = 0.0
        self.facing = 1
        self.walk = 0.0
        self.moving = False
        self.time = 0.0
        self.kills = {k: 0 for k in ETYPES}
        self.wlevel = 0                # index into WEAPONS
        self.wbonus = 0                # extra pickups after max tier (+5% dmg each)
        self.fire_cd = 0.0
        self.speed_t = 0.0
        self.shield_t = 0.0
        self.enemies, self.lasers, self.ebullets = [], [], []
        self.drops, self.particles, self.texts = [], [], []
        self.spawn_acc = 0.0
        self.shake = 0.0
        self.hurt_flash = 0.0
        self.slowmo = 0.0
        self.next_boss = BOSS_EVERY
        self.boss_count = 0
        self.last_wave = 0
        self.banner, self.banner_t = "", 0.0
        self.dead = False
        self.grid = {}

    @property
    def total_kills(self):
        return sum(self.kills.values())

    @property
    def speed(self):
        return 210 * (SPEED_MULT if self.speed_t > 0 else 1)

    @property
    def weapon(self):
        return WEAPONS[self.wlevel]

    # ------------------------------------------------------------ helpers
    def say(self, text, t=2.2):
        self.banner, self.banner_t = text, t

    def burst(self, x, y, color, n=10, speed=200, size=3, life=0.5):
        if len(self.particles) > 700:
            n = min(n, 3)
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * speed
            l = random.uniform(0.5, 1) * life
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, l, l, color, size])

    def float_text(self, x, y, text, color=WHITE, big=False):
        if len(self.texts) > 70:
            return
        surf = (F_M if big else F_S).render(str(text), True, color)
        self.texts.append([x + random.uniform(-8, 8), y, surf, 0.8 if big else 0.55])

    def near(self, x, y, r):
        g = self.grid
        out = []
        for cx in range(int((x - r) // CELL), int((x + r) // CELL) + 1):
            for cy in range(int((y - r) // CELL), int((y + r) // CELL) + 1):
                lst = g.get((cx, cy))
                if lst:
                    out.extend(lst)
        return out

    def build_grid(self):
        g = {}
        for e in self.enemies:
            if e.r > CELL // 2:
                for cx in range(int((e.x - e.r) // CELL), int((e.x + e.r) // CELL) + 1):
                    for cy in range(int((e.y - e.r) // CELL), int((e.y + e.r) // CELL) + 1):
                        g.setdefault((cx, cy), []).append(e)
            else:
                g.setdefault((int(e.x // CELL), int(e.y // CELL)), []).append(e)
        self.grid = g

    def nearest(self, x, y, maxd):
        best, bd = None, maxd * maxd
        for e in self.enemies:
            if e.hp <= 0:
                continue
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < bd:
                best, bd = e, d
        return best

    # ------------------------------------------------------------ combat
    def damage(self, e, dmg, kx=0.0, ky=0.0):
        if e.hp <= 0:
            return
        crit = random.random() < 0.1
        if crit:
            dmg *= 2
        e.hp -= dmg
        e.flash = 0.08
        if e.kind != "mothership":
            e.x += kx
            e.y += ky
        self.float_text(e.x, e.y - e.r, int(dmg), YELLOW if crit else WHITE)
        play("hit")
        if e.hp <= 0:
            self.kill(e)

    def kill(self, e):
        self.kills[e.kind] += 1
        self.burst(e.x, e.y, e.t["color"], 8 + e.r // 2, 160 + e.r * 4, 3, 0.5)
        play("kill")
        if e.kind == "splitter" and len(self.enemies) < MAX_ENEMIES + 80:
            for _ in range(2):
                self.enemies.append(Enemy("spawnling", e.x + random.uniform(-10, 10),
                                          e.y + random.uniform(-10, 10)))
        if e.kind == "mothership":
            self.shake = 22
            self.slowmo = 0.8
            play("boom")
            self.burst(e.x, e.y, e.color, 120, 500, 5, 1.4)
            self.burst(e.x, e.y, WHITE, 60, 350, 4, 1.0)
            k = random.choice(("weapon", "shield", "health", "speed"))
            self.drops.append([e.x, e.y, k, DROP_LIFE])
            self.say(f"BOSS #{e.level} DESTROYED!")
            return
        # one roll per kill: health 10%, speed 20%, weapon 15%, shield 10%, nothing 45%
        r = random.random()
        acc = 0.0
        for kind, chance in DROP_TABLE:
            acc += chance
            if r < acc:
                self.drops.append([e.x, e.y, kind, DROP_LIFE])
                break
        if len(self.drops) > 80:
            self.drops.pop(0)

    def hurt(self, dmg):
        if self.dead or self.iframe > 0:
            return
        if self.shield_t > 0:
            return
        self.hp -= dmg
        self.iframe = 0.6
        self.shake = max(self.shake, 8)
        self.hurt_flash = 0.3
        play("hurt")
        self.burst(self.px, self.py, RED, 10, 200)

    def pickup(self, kind):
        px, py = self.px, self.py - 50
        if kind == "health":
            self.hp = min(self.maxhp, self.hp + HEAL)
            self.float_text(px, py, f"+{HEAL} HP", GREEN, True)
            self.burst(self.px, self.py, GREEN, 14, 150)
        elif kind == "speed":
            self.speed_t = SPEED_TIME
            self.float_text(px, py, "SPEED!", SUIT_RED, True)
            self.burst(self.px, self.py, SUIT_RED, 14, 180)
        elif kind == "weapon":
            if self.wlevel < len(WEAPONS) - 1:
                self.wlevel += 1
                self.say("WEAPON UP: " + self.weapon["name"].upper())
            elif self.wbonus < 10:
                self.wbonus += 1
                self.float_text(px, py, "DAMAGE +5%", self.weapon["color"], True)
            else:
                self.float_text(px, py, "WEAPON MAXED", self.weapon["color"], True)
            self.burst(self.px, self.py, self.weapon["color"], 20, 220)
        elif kind == "shield":
            self.shield_t = SHIELD_TIME
            self.float_text(px, py, "SHIELD!", CYAN, True)
        play(kind)

    # ------------------------------------------------------------ spawning
    def spawn_pos(self, dist=None):
        a = random.uniform(0, math.tau)
        d = dist or random.uniform(560, 640)
        return self.px + math.cos(a) * d, self.py + math.sin(a) * d

    def pick_kind(self):
        t = self.time
        pool = [("crawler", 10)]
        if t > 10:
            pool.append(("zipper", 6))
        if t > 20:
            pool.append(("brute", 2 + t / 30))
        if t > 30:
            pool.append(("spitter", 3))
        if t > 40:
            pool.append(("splitter", 3))
        r = random.uniform(0, sum(w for _, w in pool))
        for k, w in pool:
            r -= w
            if r <= 0:
                return k
        return "crawler"

    def hpmul(self):
        return 1 + self.time / 90

    @property
    def wave(self):
        return int(self.time // DOUBLE_EVERY)

    @property
    def target_monsters(self):
        return min(MAX_ENEMIES, START_MONSTERS * 2 ** self.wave)

    @property
    def speed_mult(self):
        return min(MAX_SPEEDUP, 1 + SPEEDUP * self.wave)

    def new_enemy(self, kind, x, y):
        e = Enemy(kind, x, y, self.hpmul())
        e.spd *= self.speed_mult
        return e

    def spawn(self, dt):
        # every 10 seconds the number of monsters doubles
        if self.wave != self.last_wave:
            self.last_wave = self.wave
            self.say(f"MONSTERS x2!  ({self.target_monsters})", 1.6)
        alive = sum(1 for e in self.enemies if e.kind != "mothership")
        missing = self.target_monsters - alive
        if missing > 0:
            self.spawn_acc += max(3, missing * 1.5) * dt
            while self.spawn_acc >= 1 and missing > 0:
                self.spawn_acc -= 1
                missing -= 1
                x, y = self.spawn_pos()
                self.enemies.append(self.new_enemy(self.pick_kind(), x, y))
        # every 30 seconds a boss arrives with monsters surrounding you
        if self.time >= self.next_boss:
            self.next_boss += BOSS_EVERY
            self.boss_count += 1
            n = self.boss_count
            x, y = self.spawn_pos(480)
            b = Enemy("mothership", x, y, 1.75 ** (n - 1))
            b.level = n
            b.color = boss_color(n)
            b.r = min(90, 46 + n * 4)
            b.spd = (58 + n * 4) * min(1.6, 1 + 0.05 * n)
            self.enemies.append(b)
            ring = min(60, 14 + n * 6)
            ring = max(0, min(ring, MAX_ENEMIES + 80 - len(self.enemies)))
            for i in range(ring):
                a = i * math.tau / ring
                kind = "zipper" if i % 3 == 0 else "crawler"
                self.enemies.append(self.new_enemy(kind, self.px + math.cos(a) * 380, self.py + math.sin(a) * 380))
            self.say(f"BOSS #{n} INCOMING!")
            self.shake = 14
            play("boss")

    # ------------------------------------------------------------ weapon
    def fire(self, dt):
        self.fire_cd -= dt
        if self.fire_cd > 0:
            return
        target = self.nearest(self.px, self.py, 560)
        if not target:
            return
        w = self.weapon
        self.fire_cd = w["cd"]
        base = math.atan2(target.y - self.py, target.x - self.px)
        dmg = w["dmg"] * (1 + 0.05 * self.wbonus)
        n = w["shots"]
        for i in range(n):
            off = i - (n - 1) / 2
            a = base + off * w["spread"]
            sx = self.px - math.sin(base) * off * w["parallel"]
            sy = self.py + math.cos(base) * off * w["parallel"]
            self.lasers.append(dict(x=sx, y=sy, vx=math.cos(a) * LASER_SPEED, vy=math.sin(a) * LASER_SPEED,
                                    dmg=dmg, pierce=w["pierce"], life=0.9, hit=set(),
                                    color=w["color"], width=w["width"]))
        play("laser")

    # ------------------------------------------------------------ update
    def update(self, dt, keys, mouse):
        if self.dead:
            self.update_fx(dt)
            return
        if self.slowmo > 0:
            self.slowmo -= dt
            dt *= 0.35
        self.time += dt

        # movement
        mx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        my = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if mouse is not None and not (mx or my):
            dx, dy = mouse[0] - GW / 2, mouse[1] - H / 2
            if dx * dx + dy * dy > 400:
                mx, my = dx, dy
        d = math.hypot(mx, my)
        self.moving = d > 0
        if d:
            self.px += mx / d * self.speed * dt
            self.py += my / d * self.speed * dt
            if mx:
                self.facing = 1 if mx > 0 else -1
            self.walk += dt
            # jetpack exhaust
            if random.random() < 0.7:
                col = SUIT_RED if self.speed_t > 0 else random.choice((ORANGE, YELLOW))
                self.particles.append([self.px - mx / d * 14 + random.uniform(-5, 5),
                                       self.py + 6 - my / d * 14, -mx / d * 60, -my / d * 60 + 30,
                                       0.35, 0.35, col, 3])

        self.iframe -= dt
        self.hurt_flash -= dt
        self.speed_t = max(0.0, self.speed_t - dt)
        self.shield_t = max(0.0, self.shield_t - dt)

        self.spawn(dt)
        self.build_grid()
        self.fire(dt)
        px, py = self.px, self.py

        # lasers
        for b in self.lasers:
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            b["life"] -= dt
            for e in self.near(b["x"], b["y"], 60):
                if e.hp > 0 and id(e) not in b["hit"] and \
                        (e.x - b["x"]) ** 2 + (e.y - b["y"]) ** 2 < (e.r + 5) ** 2:
                    b["hit"].add(id(e))
                    self.damage(e, b["dmg"], b["vx"] * 0.01, b["vy"] * 0.01)
                    self.burst(b["x"], b["y"], b["color"], 3, 120, 2, 0.25)
                    b["pierce"] -= 1
                    if b["pierce"] <= 0:
                        b["life"] = 0
                        break
        self.lasers = [b for b in self.lasers if b["life"] > 0]

        # enemies
        for e in self.enemies:
            if e.hp <= 0:
                continue
            e.flash -= dt
            e.rot += dt
            dx, dy = px - e.x, py - e.y
            dist = math.hypot(dx, dy) or 1
            spd = e.spd
            if e.kind == "spitter":
                if dist < 260:
                    spd *= -0.4
                e.cd -= dt
                if e.cd <= 0 and dist < 500:
                    e.cd = 2.2
                    self.ebullets.append([e.x, e.y, dx / dist * 210, dy / dist * 210, 4, 9, ORANGE])
            elif e.kind == "mothership":
                spd = self.boss_ai(e, dt, dx, dy, dist, spd)
            if e.dash is None:
                e.x += dx / dist * spd * dt
                e.y += dy / dist * spd * dt
            if e.r < 30:
                for o in self.grid.get((int(e.x // CELL), int(e.y // CELL)), ()):
                    if o is e:
                        continue
                    ox, oy = e.x - o.x, e.y - o.y
                    md = e.r + o.r
                    d2 = ox * ox + oy * oy
                    if 0 < d2 < md * md:
                        dd = math.sqrt(d2)
                        push = (md - dd) * 0.5
                        e.x += ox / dd * push
                        e.y += oy / dd * push
            if dist < e.r + 15:
                if self.shield_t > 0:     # shield bounces monsters away
                    e.x -= dx / dist * 6
                    e.y -= dy / dist * 6
                self.hurt(e.t["dmg"])
            if dist > 1100 and e.kind != "mothership":
                e.x, e.y = self.spawn_pos()
        self.enemies = [e for e in self.enemies if e.hp > 0]

        # enemy bullets
        for b in self.ebullets:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            b[4] -= dt
            dd = (b[0] - px) ** 2 + (b[1] - py) ** 2
            if self.shield_t > 0 and dd < 40 ** 2:
                b[4] = 0
                self.burst(b[0], b[1], CYAN, 4, 100, 2, 0.2)
            elif dd < 16 ** 2:
                self.hurt(b[5])
                b[4] = 0
        self.ebullets = [b for b in self.ebullets if b[4] > 0]

        # drops
        for dr in self.drops:
            dr[3] -= dt
            dx, dy = px - dr[0], py - dr[1]
            d2 = dx * dx + dy * dy
            if d2 < 60 ** 2:                     # small magnet
                d = math.sqrt(d2) or 1
                dr[0] += dx / d * 300 * dt
                dr[1] += dy / d * 300 * dt
            if d2 < 24 ** 2:
                self.pickup(dr[2])
                dr[3] = 0
        self.drops = [dr for dr in self.drops if dr[3] > 0]

        self.update_fx(dt)

        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.shake = 20
            play("boom")
            self.burst(px, py, WHITE, 70, 420, 4, 1.4)
            self.burst(px, py, CYAN, 40, 300, 3, 1.0)

    def update_fx(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.92
            p[3] *= 0.92
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.texts:
            t[1] -= 40 * dt
            t[3] -= dt
        self.texts = [t for t in self.texts if t[3] > 0]
        self.shake = max(0, self.shake - 40 * dt)
        self.banner_t -= dt

    def boss_ai(self, e, dt, dx, dy, dist, spd):
        n = max(1, e.level)
        bspeed = min(330, 170 + n * 14)
        dmg = 10 + n * 2
        col = e.color
        e.ptimer -= dt
        # aimed shots at the player, always (more bullets for stronger bosses)
        e.aim_cd -= dt
        if e.aim_cd <= 0 and dist < 700:
            e.aim_cd = max(0.6, 1.8 - n * 0.12)
            shots = min(7, 1 + n // 2 * 2)
            base = math.atan2(dy, dx)
            for k in range(shots):
                a = base + (k - (shots - 1) / 2) * 0.16
                self.ebullets.append([e.x, e.y, math.cos(a) * bspeed * 1.2, math.sin(a) * bspeed * 1.2, 4, dmg, col])
        if e.dash is not None:
            e.dash[2] -= dt
            if e.dash[2] > 0.7:
                e.x += random.uniform(-2, 2)
            else:
                e.x += e.dash[0] * dt
                e.y += e.dash[1] * dt
            if e.dash[2] <= 0:
                e.dash = None
            return 0
        if e.ptimer <= 0:
            e.phase = (e.phase + 1) % 3
            e.ptimer = max(2.0, 3.2 - n * 0.1)
            if e.phase == 1:
                v = min(900, 560 + n * 30)
                e.dash = [dx / dist * v, dy / dist * v, 1.2]
            elif e.phase == 2:
                cnt = max(0, min(14, 4 + n * 2, MAX_ENEMIES + 80 - len(self.enemies)))
                for i in range(cnt):
                    a = i * math.tau / cnt
                    self.enemies.append(self.new_enemy("zipper", e.x + math.cos(a) * 80, e.y + math.sin(a) * 80))
        if e.phase == 0:
            e.cd -= dt
            if e.cd <= 0:
                e.cd = max(0.09, 0.2 - n * 0.01)
                arms = min(8, 2 + n)
                for k in range(arms):
                    a = e.rot * 2.2 + k * math.tau / arms
                    self.ebullets.append([e.x, e.y, math.cos(a) * bspeed, math.sin(a) * bspeed, 5, dmg, col])
        return spd

    # ------------------------------------------------------------ drawing
    def draw(self, surf, avatars, stars):
        sx = random.uniform(-self.shake, self.shake) if self.shake else 0
        sy = random.uniform(-self.shake, self.shake) if self.shake else 0
        cx, cy = self.px - GW / 2 + sx, self.py - H / 2 + sy
        surf.set_clip(pygame.Rect(0, 0, GW, H))
        surf.fill(BG)
        draw_stars(surf, stars, cx, cy)
        px, py = self.px - cx, self.py - cy
        t = self.time

        # drops
        for dr in self.drops:
            gx, gy = dr[0] - cx, dr[1] - cy
            if -20 < gx < GW + 20 and -20 < gy < H + 20:
                if dr[3] < 3 and int(dr[3] * 8) % 2 == 0:
                    continue          # blink before vanishing
                draw_drop(surf, dr[2], gx, gy + math.sin(t * 4 + dr[0]) * 3, self)

        # enemies
        for e in self.enemies:
            ex, ey = e.x - cx, e.y - cy
            if -90 < ex < GW + 90 and -90 < ey < H + 90:
                if e.kind == "mothership":
                    r = e.r
                    bc = e.color
                    col = YELLOW if (e.dash is not None and e.dash[2] > 0.7) else (WHITE if e.flash > 0 else bc)
                    surf.blit(glow(r, bc), (ex - r * 2, ey - r * 2))
                    pygame.draw.polygon(surf, shade(bc, 0.25), star_pts(r, ex, ey, e.rot))
                    pygame.draw.polygon(surf, col, star_pts(r, ex, ey, e.rot), 4)
                    pygame.draw.polygon(surf, col, star_pts(r * 0.45, ex, ey, -e.rot * 2, 5), 3)
                    pygame.draw.rect(surf, (60, 0, 0), (ex - 50, ey - r - 18, 100, 7))
                    pygame.draw.rect(surf, bc, (ex - 50, ey - r - 18, 100 * e.hp / e.maxhp, 7))
                    lb = F_XS.render(f"BOSS #{e.level}", True, bc)
                    surf.blit(lb, (ex - lb.get_width() / 2, ey - r - 34))
                else:
                    spr = SPRITES[e.kind][1 if e.flash > 0 else 0]
                    surf.blit(spr, (ex - e.r * 2, ey - e.r * 2))

        # lasers: colored beam + white core
        for b in self.lasers:
            bx, by = b["x"] - cx, b["y"] - cy
            sp = LASER_SPEED
            tx, ty = bx - b["vx"] / sp * 22, by - b["vy"] / sp * 22
            pygame.draw.line(surf, shade(b["color"], 0.6), (tx, ty), (bx, by), b["width"] + 4)
            pygame.draw.line(surf, b["color"], (tx, ty), (bx, by), b["width"])
            pygame.draw.line(surf, WHITE, (tx, ty), (bx, by), max(1, b["width"] // 3))

        for b in self.ebullets:
            bx, by = b[0] - cx, b[1] - cy
            if -10 < bx < GW + 10 and -10 < by < H + 10:
                bc = b[6] if len(b) > 6 else PINK
                surf.blit(glow(6, bc), (bx - 12, by - 12))
                pygame.draw.circle(surf, WHITE, (int(bx), int(by)), 4)

        # particles
        for p in self.particles:
            k = p[4] / p[5]
            pygame.draw.circle(surf, p[6], (int(p[0] - cx), int(p[1] - cy)), max(1, int(p[7] * k + 0.5)))

        # player
        if not self.dead and (self.iframe <= 0 or int(t * 20) % 2 == 0):
            bob = math.sin(self.walk * 9) * 3 if self.moving else math.sin(t * 2) * 2
            red = self.speed_t > 0
            # suit blinks back to white during the last 2 seconds of speed
            if red and self.speed_t < 2 and int(self.speed_t * 8) % 2 == 0:
                red = False
            key = ("red" if red else "white", 1 if self.facing > 0 else -1)
            pygame.draw.ellipse(surf, (0, 0, 0), (px - 16, py + 34, 32, 8))
            surf.blit(glow(20, (255, 70, 70) if red else (120, 200, 255)), (px - 40, py - 45))
            surf.blit(avatars[key], (px - 32, py - 46 + bob))

            # shield: cyan circle, blinks during the last 3 seconds
            if self.shield_t > 0:
                visible = self.shield_t > SHIELD_BLINK or int(self.shield_t * 8) % 2 == 0
                if visible:
                    rad = 48 + math.sin(t * 6) * 2
                    sh = pygame.Surface((130, 130), pygame.SRCALPHA)
                    pygame.draw.circle(sh, (0, 235, 255, 45), (65, 65), int(rad))
                    pygame.draw.circle(sh, (0, 235, 255, 220), (65, 65), int(rad), 3)
                    pygame.draw.circle(sh, (200, 255, 255, 120), (65, 65), int(rad) - 6, 1)
                    surf.blit(sh, (px - 65, py - 65))

        for tx in self.texts:
            surf.blit(tx[2], (tx[0] - cx - tx[2].get_width() / 2, tx[1] - cy))

        if self.hurt_flash > 0:
            o = pygame.Surface((GW, H), pygame.SRCALPHA)
            o.fill((255, 0, 0, int(90 * self.hurt_flash / 0.3)))
            surf.blit(o, (0, 0))

        # big clock on top of the game view
        tt = F_L.render(fmt_time(self.time), True, WHITE)
        surf.blit(tt, (GW / 2 - tt.get_width() / 2, 12))
        if self.banner_t > 0:
            b = F_L.render(self.banner, True, YELLOW)
            b.set_alpha(int(255 * min(1, self.banner_t)))
            surf.blit(b, (GW / 2 - b.get_width() / 2, H / 2 - 150))
        surf.set_clip(None)


def draw_drop(surf, kind, x, y, game):
    if kind == "health":
        surf.blit(glow(11, GREEN), (x - 22, y - 22))
        pygame.draw.rect(surf, WHITE, (x - 10, y - 10, 20, 20), border_radius=4)
        pygame.draw.rect(surf, (230, 30, 50), (x - 3, y - 7, 6, 14))
        pygame.draw.rect(surf, (230, 30, 50), (x - 7, y - 3, 14, 6))
    elif kind == "speed":
        surf.blit(glow(11, SUIT_RED), (x - 22, y - 22))
        pygame.draw.circle(surf, (60, 0, 10), (int(x), int(y)), 11)
        pygame.draw.circle(surf, SUIT_RED, (int(x), int(y)), 11, 2)
        pygame.draw.polygon(surf, YELLOW, [(x + 2, y - 9), (x - 5, y + 1), (x, y + 1),
                                           (x - 2, y + 9), (x + 5, y - 2), (x, y - 2)])
    elif kind == "weapon":
        nxt = WEAPONS[min(game.wlevel + 1, len(WEAPONS) - 1)]["color"]
        surf.blit(glow(11, nxt), (x - 22, y - 22))
        pygame.draw.rect(surf, (30, 30, 45), (x - 11, y - 8, 22, 16), border_radius=3)
        pygame.draw.rect(surf, nxt, (x - 11, y - 8, 22, 16), 2, border_radius=3)
        pygame.draw.line(surf, nxt, (x - 6, y), (x + 7, y), 3)
        pygame.draw.polygon(surf, nxt, [(x + 7, y - 4), (x + 7, y + 4), (x + 10, y)])
    elif kind == "shield":
        surf.blit(glow(11, CYAN), (x - 22, y - 22))
        pygame.draw.circle(surf, CYAN, (int(x), int(y)), 11, 3)
        pygame.draw.circle(surf, (180, 250, 255), (int(x), int(y)), 5)


def make_stars(n=260):
    return [(random.uniform(0, 2000), random.uniform(0, 2000), random.choice((0.15, 0.3, 0.6)),
             random.choice(((90, 90, 130), (160, 160, 200), (255, 255, 255), (150, 200, 255))))
            for _ in range(n)]


def draw_stars(surf, stars, cx, cy):
    for x, y, depth, col in stars:
        sx = (x - cx * depth) % 2000
        sy = (y - cy * depth) % 2000
        if sx < GW and sy < H:
            if depth > 0.5:
                pygame.draw.circle(surf, col, (int(sx), int(sy)), 2)
            else:
                surf.set_at((int(sx), int(sy)), col)


# ---------------------------------------------------------------- side panel
def bar(surf, x, y, w, h, frac, col, back=(40, 40, 60)):
    pygame.draw.rect(surf, back, (x, y, w, h), border_radius=4)
    if frac > 0:
        pygame.draw.rect(surf, col, (x, y, int(w * min(1, frac)), h), border_radius=4)


def draw_panel(surf, g, best):
    x0 = GW
    pygame.draw.rect(surf, (12, 12, 28), (x0, 0, W - GW, H))
    pygame.draw.line(surf, CYAN, (x0, 0), (x0, H), 2)
    x = x0 + 18
    pw = W - GW - 36
    y = 14
    surf.blit(F_S.render("SURVIVAL TIME", True, (150, 150, 190)), (x, y))
    y += 22
    surf.blit(F_L.render(fmt_time(g.time), True, WHITE), (x, y))
    y += 44
    surf.blit(F_XS.render(f"BEST  {fmt_time(max(best, g.time))}", True, YELLOW), (x, y))
    y += 18
    nb = max(0, g.next_boss - g.time)
    tm = g.target_monsters
    surf.blit(F_XS.render(f"MONSTERS {tm}{' (MAX)' if tm >= MAX_ENEMIES else ''}", True, (255, 120, 120)), (x, y))
    y += 17
    surf.blit(F_XS.render(f"NEXT BOSS IN {int(nb)}s", True, (255, 120, 120)), (x, y))
    y += 22

    surf.blit(F_S.render(f"HP  {int(g.hp)}/{int(g.maxhp)}", True, WHITE), (x, y))
    y += 20
    bar(surf, x, y, pw, 12, g.hp / g.maxhp, GREEN, (70, 10, 20))
    y += 24

    w = g.weapon
    surf.blit(F_S.render("WEAPON", True, (150, 150, 190)), (x, y))
    y += 20
    name = w["name"] + (f" +{g.wbonus * 5}%" if g.wbonus else "")
    surf.blit(F_S.render(name, True, w["color"]), (x, y))
    y += 22
    for i, ww in enumerate(WEAPONS):
        c = ww["color"] if i <= g.wlevel else (50, 50, 70)
        pygame.draw.rect(surf, c, (x + i * (pw // 4), y, pw // 4 - 6, 8), border_radius=3)
    y += 20

    surf.blit(F_S.render("SPEED", True, SUIT_RED if g.speed_t > 0 else (90, 90, 110)), (x, y))
    if g.speed_t > 0:
        surf.blit(F_XS.render(f"{g.speed_t:.1f}s", True, WHITE), (x + pw - 34, y + 2))
    y += 20
    bar(surf, x, y, pw, 8, g.speed_t / SPEED_TIME, SUIT_RED)
    y += 16
    surf.blit(F_S.render("SHIELD", True, CYAN if g.shield_t > 0 else (90, 90, 110)), (x, y))
    if g.shield_t > 0:
        surf.blit(F_XS.render(f"{g.shield_t:.1f}s", True, WHITE), (x + pw - 34, y + 2))
    y += 20
    bar(surf, x, y, pw, 8, g.shield_t / SHIELD_TIME, CYAN)
    y += 22

    pygame.draw.line(surf, (50, 50, 80), (x, y), (x + pw, y))
    y += 8
    surf.blit(F_M.render(f"KILLS  {g.total_kills}", True, WHITE), (x, y))
    y += 30
    for k, et in ETYPES.items():
        surf.blit(ICONS[k], (x, y - 3))
        surf.blit(F_S.render(et["name"], True, et["color"]), (x + 34, y + 2))
        c = F_S.render(str(g.kills[k]), True, WHITE)
        surf.blit(c, (x + pw - c.get_width(), y + 2))
        y += 29


# ---------------------------------------------------------------- screens
def center(surf, f, text, y, color, cx=W / 2):
    t = f.render(text, True, color)
    surf.blit(t, (cx - t.get_width() / 2, y))


def draw_menu(surf, t, big, best, use_photo, stars):
    surf.fill(BG)
    draw_stars(surf, stars, t * 40, t * 15)
    surf.set_clip(None)
    c = (int(140 + 115 * math.sin(t * 2)), 120, 255)
    center(surf, F_XL, "SPACE SURVIVOR", 40, c)
    center(surf, F_M, "how long can you survive?", 122, CYAN)
    bob = math.sin(t * 3) * 6
    surf.blit(glow(70, (120, 200, 255)), (W / 2 - 140, 300 - 140 + bob))
    surf.blit(big, (W / 2 - big.get_width() / 2, 165 + bob))
    if int(t * 2) % 2 == 0:
        center(surf, F_L, "PRESS SPACE / CLICK TO START", 440, YELLOW)
    # drop legend
    items = [("health", "Health 3%"), ("speed", "Speed 5%"), ("weapon", "Weapon 4%"), ("shield", "Shield 2%")]
    x = W / 2 - 330
    dummy = Game()
    for k, label in items:
        draw_drop(surf, k, x, 512, dummy)
        surf.blit(F_S.render(label, True, WHITE), (x + 20, 503))
        x += 175
    center(surf, F_S, "Move: WASD / arrows / hold mouse  -  lasers fire automatically  -  P = pause", 548, (170, 170, 200))
    extra = f"F = switch face ({'PHOTO' if use_photo else 'CARTOON'})   -   " if FACE is not None else ""
    center(surf, F_S, f"{extra}BEST TIME: {fmt_time(best)}", 576, (170, 170, 200))


def draw_over(surf, g, best, new_best):
    o = pygame.Surface((GW, H), pygame.SRCALPHA)
    o.fill((0, 0, 0, 175))
    surf.blit(o, (0, 0))
    cx = GW / 2
    center(surf, F_XL, "GAME OVER", 110, RED, cx)
    center(surf, F_M, "You survived", 215, (180, 180, 210), cx)
    center(surf, F_XL, fmt_time(g.time), 245, WHITE, cx)
    center(surf, F_M, f"Monsters killed: {g.total_kills}", 335, WHITE, cx)
    center(surf, F_M, "NEW RECORD!" if new_best else f"Best: {fmt_time(best)}", 375,
           YELLOW if new_best else (170, 170, 200), cx)
    center(surf, F_M, "SPACE / click = play again", 450, (170, 170, 200), cx)


# ---------------------------------------------------------------- main loop
def build_avatars(use_photo):
    av = {}
    for name, col in (("white", SUIT_WHITE), ("red", SUIT_RED)):
        img = make_astronaut(col, use_photo)
        av[(name, 1)] = img
        av[(name, -1)] = pygame.transform.flip(img, True, False)
    return av


async def main():
    use_photo = FACE is not None
    avatars = build_avatars(use_photo)
    big = make_astronaut(SUIT_WHITE, use_photo, 3)
    stars = make_stars()
    best = load_best()
    state = "menu"
    game = Game()
    mt = 0.0
    new_best = False

    while True:
        dt = min(clock.tick(60) / 1000, 1 / 20)
        mt += dt
        mouse_pos = pygame.mouse.get_pos()
        clicked = False
        pressed = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                pressed = ev.key
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                clicked = True

        if state == "menu":
            if pressed == pygame.K_f and FACE is not None:
                use_photo = not use_photo
                avatars = build_avatars(use_photo)
                big = make_astronaut(SUIT_WHITE, use_photo, 3)
            if pressed in (pygame.K_SPACE, pygame.K_RETURN) or clicked:
                game = Game()
                state = "play"
            draw_menu(screen, mt, big, best, use_photo, stars)

        elif state == "play":
            if pressed in (pygame.K_p, pygame.K_ESCAPE):
                state = "pause"
            mouse = mouse_pos if pygame.mouse.get_pressed()[0] and mouse_pos[0] < GW else None
            game.update(dt, pygame.key.get_pressed(), mouse)
            game.draw(screen, avatars, stars)
            draw_panel(screen, game, best)
            if game.dead:
                new_best = game.time > best
                if new_best:
                    best = game.time
                    save_best(best)
                state = "over"
                mt = 0

        elif state == "pause":
            game.draw(screen, avatars, stars)
            draw_panel(screen, game, best)
            o = pygame.Surface((GW, H), pygame.SRCALPHA)
            o.fill((0, 0, 0, 150))
            screen.blit(o, (0, 0))
            center(screen, F_XL, "PAUSED", 220, WHITE, GW / 2)
            center(screen, F_M, "P to continue", 320, (170, 170, 200), GW / 2)
            if pressed in (pygame.K_p, pygame.K_ESCAPE) or clicked:
                state = "play"

        elif state == "over":
            game.update(dt, pygame.key.get_pressed(), None)   # let the explosion play out
            game.draw(screen, avatars, stars)
            draw_panel(screen, game, best)
            draw_over(screen, game, best, new_best)
            if mt > 1.0 and (pressed in (pygame.K_SPACE, pygame.K_RETURN) or clicked):
                state = "menu"

        pygame.display.flip()
        await asyncio.sleep(0)


asyncio.run(main())
