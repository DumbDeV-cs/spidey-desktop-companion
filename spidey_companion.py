"""Desk Companion v14: Spidey, cozy cats, and five tiny pixel robot friends.

Requires: pip install pillow
Controls: click = swing / pet, double-click = THWIP / MEOW (impact!), right-click = menu, drag = move.
Pick a companion: right-click -> "Choose companion"  (your choice is remembered).
Start straight as the cat:  python spidey_companion.py cat

What's new in v14
  * Five new pixel robots inspired by the supplied reference: Scout, Buddy, Sprout,
    Beeper, and Tinker, each with a distinct silhouette and color palette
  * All companions share gentle idle animation, friendly click reactions, and the
    existing focus, mission, and mood tools
  * Companion selection and command-line shortcuts include every robot

What's new in v13
  * NEW: Tiny chibi pixel cat (Midnight black or Ginger) on a little ledge - its window is only 150x141 px
  * Cat animations: breathing, blinking, ear flicks, swishing tail, eyes that follow your mouse,
    purr-bobbing with floating hearts when petted, yawns, sleeping with floating Zzz after a while,
    a "!" when its senses tingle, and a MEOW! hop with a comic starburst on double-click
  * Companion choice is saved next to the script (companion.txt)
  * Everything from Spidey v12 is kept untouched
"""
import math
import os
import random
import sys
import tkinter as tk
from functools import lru_cache

from PIL import Image, ImageDraw, ImageOps, ImageTk

# --------------------------------------------------------------------------- layout
W, H = 380, 340
BG = '#050810'                 # window colour that gets keyed out as transparent
PIVOT = (236, 48)              # web grip near the top-right corner
SPR_W, SPR_H = 210, 280        # transparent hero canvas (px)
SPR_PIV = (105, 0)             # sprite attaches directly at the hanging strand
S = 1.5                        # px per "unit" used by Scene.xf()
HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(HERE, 'companion.txt')


# --------------------------------------------------------------------------- helpers
def blit(dst, src, x, y):
    """alpha_composite with clipping so sprites may hang off the edge."""
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + src.width, dst.width), min(y + src.height, dst.height)
    if x1 <= x0 or y1 <= y0:
        return
    dst.alpha_composite(src.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def zoom(img, s, c):
    """Scale a window-sized layer by s (>1) around point c."""
    if s <= 1.001:
        return img
    big = img.resize((int(W * s), int(H * s)), Image.Resampling.BICUBIC)
    ox, oy = int(c[0] * (s - 1)), int(c[1] * (s - 1))
    return big.crop((ox, oy, ox + W, oy + H))


def speed_lines(d, c, rng, color, n=50, inner=(40, 90), outer=460):
    """Tapered manga speed lines radiating from c (thin tip inside, wide at the edge)."""
    for _ in range(n):
        a = rng.uniform(0, math.tau)
        r0 = rng.uniform(*inner)
        w = rng.uniform(.008, .03)
        d.polygon([(c[0] + math.cos(a) * r0, c[1] + math.sin(a) * r0),
                   (c[0] + math.cos(a - w) * outer, c[1] + math.sin(a - w) * outer),
                   (c[0] + math.cos(a + w) * outer, c[1] + math.sin(a + w) * outer)], fill=color)


def bezier(p0, c, p1, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]))
    return pts


# --------------------------------------------------------------------------- the web
def make_web():
    """Orb web in the top-right corner, drawn 3x supersampled. Returns (image, glint nodes)."""
    SS = 3
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = random.Random(11)
    A = (W - 3, 3)
    n_rad = 9
    angs = [math.radians(88 + i * (94 / (n_rad - 1)) + rng.uniform(-1.5, 1.5)) for i in range(n_rad)]
    length = 132
    rings = [16, 27, 39, 52, 66, 81, 98, 118]

    def pt(r, a):
        return (A[0] + math.cos(a) * r, A[1] + math.sin(a) * r)

    nodes = []
    for ri, r in enumerate(rings):
        for i in range(n_rad - 1):
            r0 = r * (1 + rng.uniform(-.025, .025))
            r1 = r * (1 + rng.uniform(-.025, .025))
            p0, p1 = pt(r0, angs[i]), pt(r1, angs[i + 1])
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            ctrl = (mid[0] + (A[0] - mid[0]) * .30, mid[1] + (A[1] - mid[1]) * .30)
            pts = [(x * SS, y * SS) for x, y in bezier(p0, ctrl, p1, 12)]
            d.line(pts, fill=(176, 202, 232, 92), width=SS, joint='curve')
        for a in angs[1:-1]:
            nodes.append(pt(r, a))
    for a in angs:
        p = pt(length, a)
        d.line((A[0] * SS, A[1] * SS, p[0] * SS, p[1] * SS), fill=(214, 228, 248, 130), width=SS)
    ctrl = ((A[0] + PIVOT[0]) / 2 + 4, (A[1] + PIVOT[1]) / 2 + 12)
    drag = [(x * SS, y * SS) for x, y in bezier(A, ctrl, PIVOT, 20)]
    d.line(drag, fill=(150, 195, 255, 48), width=6 * SS, joint='curve')
    d.line(drag, fill=(244, 249, 255, 240), width=2 * SS, joint='curve')
    for r, a in ((9, 40), (6, 90), (3, 220)):
        d.ellipse(((A[0] - r) * SS, (A[1] - r) * SS, (A[0] + r) * SS, (A[1] + r) * SS),
                  fill=(210, 232, 255, a))
    im = im.resize((W, H), Image.Resampling.LANCZOS)
    rng.shuffle(nodes)
    return im, nodes[:12]


# --------------------------------------------------------------------------- the hero
HEAD_PX = 246
CHEST_PX = 170
TINGLE_R = 62
HERO_PATH = os.path.join(HERE, 'spidey_reference_cutout.png')


def _load_hero():
    """Load the comic illustration; fall back to a simple drawn hero if the PNG is missing."""
    base = Image.new('RGBA', (SPR_W, SPR_H), (0, 0, 0, 0))
    try:
        with Image.open(HERO_PATH) as f:
            art = f.convert('RGBA')
        w = round(art.width * SPR_H / art.height)
        base.alpha_composite(art.resize((w, SPR_H), Image.Resampling.LANCZOS), ((SPR_W - w) // 2, 0))
    except (OSError, FileNotFoundError):
        d = ImageDraw.Draw(base)
        d.line((105, 0, 105, 60), fill=(240, 246, 255, 255), width=3)
        ink = (17, 23, 42, 255)
        d.ellipse((70, 150, 140, 270), fill=(45, 82, 180, 255), outline=ink, width=4)
        d.ellipse((62, 58, 148, 170), fill=(226, 51, 70, 255), outline=ink, width=4)
        # Friendly oversized mask eyes and a tiny chest spider brighten the fallback.
        d.polygon([(76, 126), (94, 117), (101, 124), (96, 143), (83, 140)], fill=(255, 250, 236, 255))
        d.polygon([(134, 126), (116, 117), (109, 124), (114, 143), (127, 140)], fill=(255, 250, 236, 255))
        d.ellipse((99, 189, 111, 201), fill=(19, 31, 71, 255))
        d.line((105, 195, 96, 210), fill=(19, 31, 71, 255), width=2)
        d.line((105, 195, 114, 210), fill=(19, 31, 71, 255), width=2)
    return base


_HERO_BASE = _load_hero()


@lru_cache(maxsize=64)
def make_spidey(idx=0, blink=0, waving=False, squint=False):
    """Load the polished, transparent comic illustration used by the pet."""
    return _HERO_BASE.copy()


# --------------------------------------------------------------------------- Spidey scene (pure PIL)
class Scene:
    """All the animation + impact-frame logic; step() returns one RGBA frame."""
    flat_frames = True                      # hard black/white impact frames hide the HUD
    text_pos = None                         # use default THWIP! position
    compact = False
    size = (W, H)
    text_base = 20
    bubble = (PIVOT[0] - 86, PIVOT[1] + 175)  # speech bubble anchor

    def __init__(self):
        self.web, self.nodes = make_web()
        self.phases = [random.uniform(0, math.tau) for _ in self.nodes]
        self.tick = 0
        self.ang, self.vel = 0.0, 0.055
        self.blink_seq, self.blink_cd, self.blink_frame = [], 50, 0
        self.squint = self.wave_left = self.tingle = 0
        self.imp = None
        self.imp_seed = 1
        self.sfx = 'THWIP!'
        self.particles = []
        self.shot = None
        self.shake = 0.0
        self.center = (PIVOT[0], PIVOT[1] + CHEST_PX)

    def xf(self, ux, uy):
        """Sprite unit (1 unit = S px) -> window pixel (follows the swing)."""
        dx, dy = ux * S, uy * S
        c, s = math.cos(self.ang), math.sin(self.ang)
        return (PIVOT[0] + dx * c + dy * s, PIVOT[1] - dx * s + dy * c)

    def poke(self, amount):
        self.vel += amount
        self.squint = max(self.squint, 8)

    def wave(self, ticks=60):
        self.wave_left = max(self.wave_left, ticks)

    def thwip(self, text='THWIP!'):
        self.imp, self.imp_seed, self.sfx = 0, random.randint(1, 10 ** 6), text
        self.vel += random.choice((-.1, .1))
        self.squint = 40

    def on_hit(self):
        c = self.center
        self.shake = 9.0
        for _ in range(34):
            a, sp = random.uniform(0, math.tau), random.uniform(3, 9)
            life = random.randint(14, 30)
            self.particles.append([c[0] + math.cos(a) * 18, c[1] + math.sin(a) * 18,
                                   math.cos(a) * sp, math.sin(a) * sp - 1, life, life,
                                   random.choice(((255, 224, 90), (255, 84, 98), (96, 190, 255), (255, 255, 255))),
                                   random.uniform(2, 4.5)])
        self.shot = {'age': 0, 'a': self.xf(-52, HEAD_PX / S - 4),
                     'b': (random.uniform(25, 150), random.uniform(110, 265))}

    def step(self):
        self.tick += 1
        k = self.imp
        if not (k is not None and k < 5):                       # hit-stop freezes the swing
            self.vel += -.0105 * self.ang + .0004 * math.sin(self.tick * .045)
            self.vel *= .992
            self.ang = max(-.24, min(.24, self.ang + self.vel))
        if self.blink_seq:
            self.blink_frame = self.blink_seq.pop(0)
        else:
            self.blink_frame = 0
            self.blink_cd -= 1
            if self.blink_cd <= 0:
                self.blink_seq, self.blink_cd = [1, 2, 2, 1], random.randint(55, 140)
        waving = self.wave_left > 0
        self.wave_left = max(0, self.wave_left - 1)
        self.squint = max(0, self.squint - 1)
        spr = make_spidey(self.tick % 48, self.blink_frame, waving, self.squint > 0)
        rot = spr.rotate(math.degrees(self.ang), resample=Image.Resampling.BICUBIC, center=SPR_PIV)
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        blit(layer, rot, PIVOT[0] - SPR_PIV[0], PIVOT[1] - SPR_PIV[1])
        self.center = self.xf(0, CHEST_PX / S)

        if k is not None and k <= 2:
            out = self._flat_frame(k, layer)
        else:
            if k == 3:
                self.on_hit()
            out = self.web.copy()
            back = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            bd = ImageDraw.Draw(back)
            self._sparkles(bd)
            if k is not None:
                self._burst(bd, k)
                layer = zoom(layer, 1 + .10 * max(0, 1 - (k - 3) / 4), self.center)
            out.alpha_composite(back)
            out.alpha_composite(layer)
            front = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            fd = ImageDraw.Draw(front)
            self._shot(fd)
            self._particles(fd)
            self._tingle(fd)
            out.alpha_composite(front)
        if k is not None:
            self.imp = k + 1 if k < 11 else None
        return out

    def _flat_frame(self, k, layer):
        """Hard black/white anime impact frames with speed lines; last one is inverted."""
        c = self.center
        base = Image.new('RGBA', (W, H), (255, 255, 255, 255))
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        speed_lines(ImageDraw.Draw(ov), c, random.Random(self.imp_seed + k), (0, 0, 0, 255),
                    n=64, inner=(34, 80))
        base.alpha_composite(ov)
        base.alpha_composite(zoom(layer, 1.04 + .04 * k, c))
        thr = (125, 150, 125)[k]
        g = base.convert('L').point(lambda v, t=thr: 255 if v > t else 0)
        if k == 2:
            g = ImageOps.invert(g)
        return g.convert('RGBA')

    def _burst(self, d, k):
        t = k - 3
        a = 255 if t < 3 else int(255 * max(0, 1 - (t - 3) / 6))
        if a <= 0:
            return
        c = self.center
        R0 = 50 + t * 22
        rng = random.Random(self.imp_seed * 13 + 5)
        n = 15
        outer = []
        for i in range(n * 2):
            ang = i * math.pi / n
            rr = R0 * (1.0 if i % 2 == 0 else .56) * rng.uniform(.88, 1.12)
            outer.append((c[0] + math.cos(ang) * rr, c[1] + math.sin(ang) * rr))
        inner = [(c[0] + (x - c[0]) * .66, c[1] + (y - c[1]) * .66) for x, y in outer]
        d.polygon(outer, fill=(255, 214, 64, a))
        d.line(outer + [outer[0]], fill=(10, 12, 20, a), width=3, joint='curve')
        d.polygon(inner, fill=(232, 28, 42, a))
        for gx in range(-90, 91, 9):
            for gy in range(-90, 91, 9):
                dist = math.hypot(gx, gy)
                if R0 * .22 < dist < R0 * .5:
                    rad = 1 + 2.2 * (dist - R0 * .22) / (R0 * .28)
                    d.ellipse((c[0] + gx - rad, c[1] + gy - rad, c[0] + gx + rad, c[1] + gy + rad),
                              fill=(150, 14, 28, a))
        speed_lines(d, c, random.Random(self.imp_seed + 99), (255, 255, 255, int(a * .8)),
                    n=30, inner=(R0 * .95, R0 * 1.15))
        rr = 28 + t * 46
        d.ellipse((c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr),
                  outline=(255, 255, 255, int(a * .9)), width=max(1, 5 - t // 2))

    def _sparkles(self, d):
        for (x, y), ph in zip(self.nodes, self.phases):
            v = math.sin(self.tick * .07 + ph)
            if v > .6:
                a = (v - .6) / .4
                L = 2 + 5 * a
                col = (255, 255, 255, int(230 * a))
                d.line((x - L, y, x + L, y), fill=col, width=1)
                d.line((x, y - L, x, y + L), fill=col, width=1)
                d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=col)

    def _shot(self, d):
        s = self.shot
        if not s:
            return
        age = s['age']
        s['age'] += 1
        if age > 34:
            self.shot = None
            return
        (ax, ay), (bx, by) = s['a'], s['b']
        p = min(1.0, age / 4)
        fade = 1.0 if age < 22 else max(0.0, 1 - (age - 22) / 12)
        pts = []
        for i in range(13):
            u = i / 12 * p
            pts.append((ax + (bx - ax) * u, ay + (by - ay) * u + math.sin(u * math.pi) * 10 * (1 - p * .6)))
        d.line(pts, fill=(160, 200, 255, int(70 * fade)), width=5, joint='curve')
        d.line(pts, fill=(250, 252, 255, int(235 * fade)), width=2, joint='curve')
        if p >= 1:
            sp = min(1.0, (age - 4) / 3)
            r = 16 * sp
            col = (250, 252, 255, int(230 * fade))
            for j in range(8):
                a = j * math.pi / 4 + .2
                d.line((bx, by, bx + math.cos(a) * r, by + math.sin(a) * r), fill=col, width=1)
            ring = [(bx + math.cos(j * math.pi / 4 + .2) * r * .55, by + math.sin(j * math.pi / 4 + .2) * r * .55)
                    for j in range(8)]
            d.line(ring + [ring[0]], fill=col, width=1)

    def _particles(self, d):
        alive = []
        for p in self.particles:
            x, y, vx, vy, life, mx, col, sz = p
            x += vx
            y += vy
            vy += .18
            vx *= .97
            life -= 1
            if life > 0:
                r = sz * (.5 + .5 * life / mx)
                d.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)],
                          fill=col + (int(255 * life / mx),))
                alive.append([x, y, vx, vy, life, mx, col, sz])
        self.particles = alive

    def _tingle(self, d):
        if self.tingle <= 0:
            return
        self.tingle -= 1
        hx, hy = self.xf(0, HEAD_PX / S)
        al = int(255 * min(1, self.tingle / 6))
        for i in range(8):
            a = i * math.pi / 4 + .39
            r0 = TINGLE_R + 3 * math.sin(self.tick * .9 + i)
            ca, sa = math.cos(a), math.sin(a)
            px, py = -sa, ca
            pts = [(hx + ca * r0, hy + sa * r0),
                   (hx + ca * (r0 + 4) + px * 2.5, hy + sa * (r0 + 4) + py * 2.5),
                   (hx + ca * (r0 + 9), hy + sa * (r0 + 9))]
            d.line(pts, fill=(10, 12, 20, al), width=4)
            d.line(pts, fill=(255, 255, 255, al), width=2)


# --------------------------------------------------------------------------- the pixel cat
PX = 3                           # screen pixels per cat-art pixel (small = cute + tiny footprint)
LW, LH = 50, 47                  # low-res canvas the little cat world is drawn on
CW, CH = LW * PX, LH * PX        # compact window size: 150 x 141
CAT_O = (14, 20)                 # where the cat's own pixel grid starts on that canvas
LEDGE_Y = CAT_O[1] + 23          # top row of the little wooden ledge

PALETTES = {
    'Midnight': dict(body=(11, 11, 16), rim=(34, 38, 66), line=(26, 26, 40), paw=(52, 52, 74),
                     stripe=(26, 26, 38), chest=(20, 20, 30), lid=(64, 64, 90), eye=(255, 210, 60),
                     pupil=(8, 8, 12), ear=(236, 132, 146), whisker=(150, 156, 186), blush=(214, 104, 136)),
    'Ginger': dict(body=(222, 128, 48), rim=(248, 180, 104), line=(184, 96, 32), paw=(250, 228, 192),
                   stripe=(172, 84, 24), chest=(250, 228, 192), lid=(118, 56, 18), eye=(112, 216, 124),
                   pupil=(18, 40, 20), ear=(250, 170, 170), whisker=(255, 246, 228), blush=(244, 120, 120)),
}
HEART = (".#.#.", "#####", ".###.", "..#..")
ZEE = ("###", "..#", ".#.", "#..", "###")
PLUS = (".#.", "###", ".#.")


class CatScene:
    """Tiny chibi pixel cat on a ledge. Same interface as Scene so the app can swap them."""
    flat_frames = False
    compact = True                             # tells the app to use the small HUD
    size = (CW, CH)                            # window size for this companion
    text_pos = (CW // 2, 34)                   # where MEOW! lettering goes
    text_base = 10
    bubble = (0, 0)                            # unused (compact bubble is laid out by the app)
    HOP = (0, 1, 2, 3, 3, 3, 2, 2, 1, 0, 0, 0)

    def __init__(self, coat='Midnight'):
        self.pal = PALETTES[coat]
        rng = random.Random(7)
        self.stars = []
        while len(self.stars) < 9:
            x, y = rng.randint(1, LW - 2), rng.randint(1, 17)
            if x >= 38 and y < 12:
                continue
            self.stars.append((x, y, rng.uniform(0, math.tau)))
        self.tick = 0
        self.imp, self.imp_seed, self.sfx = None, 1, 'MEOW!'
        self.shake, self.tingle = 0.0, 0
        self.blink_seq, self.blink_cd, self.blink_frame = [], 40, 0
        self.purr = self.chat = self.idle = self.yawn = self.twitch = 0
        self.twitch_cd, self.yawn_cd = 90, 500
        self.sleeping = False
        self.look = 0
        self.parts = []
        self.center = ((CAT_O[0] + 10) * PX, (CAT_O[1] + 11) * PX)

    # -- events (same names the app already calls)
    def wake(self):
        self.idle = 0
        self.sleeping = False

    def poke(self, amount=0):
        self.wake()
        self.purr = 80
        for _ in range(3):
            self._heart()

    def wave(self, ticks=60):
        self.chat = max(self.chat, ticks)

    def thwip(self, text='MEOW!'):
        self.wake()
        self.imp, self.imp_seed, self.sfx = 0, random.randint(1, 10 ** 6), text
        self.purr = 0

    def on_hit(self):
        self.shake = 4.0
        cx, cy = CAT_O[0] + 10, CAT_O[1] + 10
        cols = ((255, 224, 90), (255, 110, 150), (130, 210, 255), (255, 255, 255))
        for _ in range(18):
            a, sp = random.uniform(0, math.tau), random.uniform(.4, 1.2)
            self._spawn('spark', cx, cy, math.cos(a) * sp, math.sin(a) * sp - .3,
                        random.randint(10, 22), random.choice(cols))
        for _ in range(3):
            self._heart()

    # -- particles
    def _spawn(self, kind, x, y, vx, vy, life, col):
        self.parts.append([x, y, vx, vy, life, life, kind, col])

    def _heart(self):
        hx, hy = CAT_O[0] + 10, CAT_O[1] - 2
        self._spawn('heart', hx + random.uniform(-6, 6), hy, random.uniform(-.06, .06), -.14, 40,
                    random.choice(((255, 92, 130), (255, 150, 180), (255, 70, 100))))

    # -- per-frame update
    def step(self):
        self.tick += 1
        t, k = self.tick, self.imp
        self.idle += 1
        if self.idle > 700 and k is None and not self.purr:
            self.sleeping = True
        if self.blink_seq:
            self.blink_frame = self.blink_seq.pop(0)
        else:
            self.blink_frame = 0
            self.blink_cd -= 1
            if self.blink_cd <= 0:
                self.blink_seq, self.blink_cd = [1, 2, 2, 1], random.randint(55, 150)
        self.twitch_cd -= 1
        if self.twitch_cd <= 0 and not self.sleeping:
            self.twitch, self.twitch_cd = 10, random.randint(70, 200)
        if not self.sleeping and not self.yawn:
            self.yawn_cd -= 1
            if self.yawn_cd <= 0:
                self.yawn, self.yawn_cd = 28, random.randint(500, 1100)
        for name in ('twitch', 'yawn', 'purr', 'chat', 'tingle'):
            setattr(self, name, max(0, getattr(self, name) - 1))
        if self.purr and t % 14 == 0:
            self._heart()
        if self.sleeping and t % 38 == 0:
            self._spawn('z', CAT_O[0] + 16, CAT_O[1] - 1, .08, -.1, 56, (190, 205, 255))

        hop = self.HOP[k] if k is not None else 0
        if k == 3:
            self.on_hit()
        self.center = ((CAT_O[0] + 10) * PX + PX // 2, (CAT_O[1] - hop + 11) * PX)

        lay = Image.new('RGBA', (LW, LH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        self._backdrop(d)
        half = max(4, 8 - hop)                                     # shadow shrinks as the cat hops
        sx = CAT_O[0] + 10
        d.rectangle((sx - half, LEDGE_Y, sx + half, LEDGE_Y), fill=(60, 38, 24, 255))
        if k is not None and k >= 3:
            self._burst(d, k)
        self._cat(d, hop)
        self._parts(d)
        if k is not None:
            self.imp = k + 1 if k < 11 else None
        return lay.resize((CW, CH), Image.Resampling.NEAREST)

    # -- drawing helpers
    @staticmethod
    def _px(d, x, y, rows, col):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == '#':
                    d.point((x + i, y + j), fill=col)

    def _backdrop(self, d):
        t = self.tick
        for x, y, ph in self.stars:
            v = math.sin(t * .06 + ph)
            if v > .55:
                self._px(d, x - 1, y - 1, PLUS, (255, 255, 255, 235))
            elif v > -.2:
                d.point((x, y), fill=(190, 205, 255, 210))
        # tiny crescent moon
        d.ellipse((41, 3, 47, 9), fill=(255, 238, 170, 255))
        d.ellipse((43, 2, 49, 8), fill=(0, 0, 0, 0))
        # little wooden ledge
        y0 = LEDGE_Y
        d.rectangle((4, y0, LW - 1, y0), fill=(192, 130, 80, 255))
        d.rectangle((4, y0 + 1, LW - 1, y0 + 2), fill=(142, 94, 56, 255))
        d.rectangle((4, y0 + 3, LW - 1, y0 + 3), fill=(96, 62, 38, 255))
        for gx in range(7, LW - 1, 6):
            d.point((gx, y0 + 1), fill=(112, 72, 42, 255))
        # mini potted plant that sways
        d.rectangle((40, y0 - 3, 44, y0 - 3), fill=(190, 104, 66, 255))
        d.rectangle((41, y0 - 2, 43, y0 - 1), fill=(156, 78, 50, 255))
        sway = round(math.sin(t * .04))
        g1, g2 = (86, 190, 110, 255), (130, 226, 140, 255)
        d.line((42, y0 - 4, 42 + sway, y0 - 7), fill=g1)
        d.line((42, y0 - 4, 40, y0 - 6), fill=g1)
        d.line((42, y0 - 4, 44, y0 - 6), fill=g1)
        d.point((42 + sway, y0 - 8), fill=g2)

    def _burst(self, d, k):
        t = k - 3
        a = 255 if t < 3 else int(255 * max(0, 1 - (t - 3) / 4))
        if a <= 0:
            return
        cx, cy = CAT_O[0] + 10, CAT_O[1] + 10
        r0 = 5 + t * 1.6
        rng = random.Random(self.imp_seed)
        pts = []
        for i in range(20):
            ang = i * math.pi / 10
            rr = r0 * (1 if i % 2 == 0 else .55) * rng.uniform(.9, 1.1)
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
        d.polygon(pts, fill=(255, 214, 64, a))
        inner = [(cx + (x - cx) * .62, cy + (y - cy) * .62) for x, y in pts]
        d.polygon(inner, fill=(255, 110, 150, a))

    def _parts(self, d):
        keep = []
        for p in self.parts:
            x, y, vx, vy, life, mx, kind, col = p
            x += vx
            y += vy
            if kind == 'spark':
                vy += .04
            life -= 1
            if life > 0:
                c = col + (int(255 * min(1, life / mx * 2.5)),)
                if kind == 'heart':
                    self._px(d, int(x + math.sin(life * .25) * 1.2), int(y), HEART, c)
                elif kind == 'z':
                    self._px(d, int(x + math.sin(life * .15) * 2), int(y), ZEE, c)
                else:
                    d.point((int(x), int(y)), fill=c)
                keep.append([x, y, vx, vy, life, mx, kind, col])
        self.parts = keep

    def _cat(self, d, hop):
        P, t = self.pal, self.tick
        ox, oy = CAT_O[0], CAT_O[1] - hop

        def R(x0, y0, x1, y1, c):
            d.rectangle((ox + x0, oy + y0, ox + x1, oy + y1), fill=c + (255,))

        def Q(x, y, c):
            d.point((ox + x, oy + y), fill=c + (255,))

        happy, sleepy = self.purr > 0, self.sleeping
        closed = sleepy or self.blink_frame > 0 or self.yawn > 0
        wide = self.imp is not None
        rate = .5 if happy else (.045 if sleepy else .075)
        hy = (1 if math.sin(t * rate) > .25 else 0) + (1 if sleepy else 0)   # breathing / purr bob

        # tail (swishes, tip curls up)
        speed = .34 if (happy or self.chat) else (.04 if sleepy else .12)
        for i in range(8):
            sway = math.sin(t * speed - i * .5) * i * .18
            by = 19 - max(0, i - 4) + round(sway)
            R(4 - i, by, 4 - i, by + 1, P['stripe'] if i % 3 == 2 else P['body'])

        # small round body
        for y in range(14, 23):
            grow = (1 if y >= 16 else 0) + (1 if y >= 19 else 0)
            R(6 - grow, y, 14 + grow, y, P['body'])
            Q(6 - grow, y, P['rim'])
        R(9, 15, 11, 18, P['chest'])
        R(10, 20, 10, 22, P['line'])
        R(5, 21, 8, 22, P['paw'])
        R(12, 21, 15, 22, P['paw'])

        # big cute head
        R(3, 5 + hy, 17, 12 + hy, P['body'])
        R(4, 4 + hy, 16, 13 + hy, P['body'])
        R(6, 4 + hy, 14, 4 + hy, P['rim'])
        # ears (flick on twitch, perk up on tingle)
        perk = self.tingle > 0
        eL = -1 if perk else (1 if self.twitch and (self.twitch // 2) % 2 == 0 else 0)
        eR = -1 if perk else 0
        for j in range(4):
            R(3, 1 + j + eL, 3 + j, 1 + j + eL, P['body'])
            R(17 - j, 1 + j + eR, 17, 1 + j + eR, P['body'])
        Q(4, 3 + eL, P['ear'])
        Q(16, 3 + eR, P['ear'])
        # forehead stripes (subtle on black, bold on ginger)
        R(8, 5 + hy, 8, 6 + hy, P['stripe'])
        R(10, 5 + hy, 10, 7 + hy, P['stripe'])
        R(12, 5 + hy, 12, 6 + hy, P['stripe'])
        # big sparkly eyes
        for ex in (5, 13):
            if closed:
                R(ex, 10 + hy, ex + 2, 10 + hy, P['lid'])
            elif happy:
                Q(ex, 10 + hy, P['eye'])
                Q(ex + 1, 9 + hy, P['eye'])
                Q(ex + 2, 10 + hy, P['eye'])
            else:
                top = 7 if wide else 8
                R(ex, top + hy, ex + 2, 10 + hy, P['eye'])
                pc = ex + 1 + self.look
                R(pc, top + hy, pc, 10 + hy, P['pupil'])
                Q(ex if pc != ex else ex + 2, top + hy, (255, 250, 222))   # eye shine
        if not wide:
            Q(4, 11 + hy, P['blush'])
            Q(16, 11 + hy, P['blush'])
        # nose + tiny "w" mouth
        Q(10, 11 + hy, P['ear'])
        if self.yawn > 0 and not sleepy:
            R(9, 12 + hy, 11, 13 + hy, (122, 31, 51))
        else:
            Q(9, 12 + hy, P['lid'])
            Q(11, 12 + hy, P['lid'])
        # whiskers
        wv = 1 if (self.twitch and self.twitch % 4 < 2) else 0
        R(0, 10 + hy - wv, 2, 10 + hy - wv, P['whisker'])
        R(1, 12 + hy + wv, 2, 12 + hy + wv, P['whisker'])
        R(18, 10 + hy - wv, 20, 10 + hy - wv, P['whisker'])
        R(18, 12 + hy + wv, 19, 12 + hy + wv, P['whisker'])
        # spidey-sense style "!" over the head
        if perk:
            R(10, -5, 10, -2, (255, 224, 74))
            Q(10, 0, (255, 224, 74))


# --------------------------------------------------------------------------- tiny pixel robots
ROBOT_PALETTES = {
    'Scout':  dict(shell=(100, 220, 228), shade=(35, 153, 177), dark=(20, 48, 66),
                   screen=(18, 43, 61), glow=(126, 239, 255), accent=(255, 179, 59), shape='visor'),
    'Buddy':  dict(shell=(112, 226, 237), shade=(49, 163, 189), dark=(25, 43, 58),
                   screen=(31, 53, 68), glow=(25, 230, 255), accent=(255, 117, 78), shape='box'),
    'Sprout': dict(shell=(215, 245, 229), shade=(109, 198, 188), dark=(26, 53, 67),
                   screen=(217, 250, 241), glow=(27, 51, 65), accent=(255, 130, 86), shape='round'),
    'Beeper': dict(shell=(55, 190, 207), shade=(29, 127, 157), dark=(20, 49, 64),
                   screen=(104, 223, 229), glow=(29, 64, 83), accent=(240, 228, 83), shape='stack'),
    'Tinker': dict(shell=(99, 180, 225), shade=(45, 112, 171), dark=(23, 45, 76),
                   screen=(114, 194, 236), glow=(25, 52, 73), accent=(255, 192, 59), shape='box'),
}


class RobotScene:
    """A small animated pixel robot; each named bot has its own silhouette."""
    flat_frames = False
    compact = True
    size = (240, 150)
    text_pos = (120, 36)
    text_base = 12
    bubble = (0, 0)
    SCALE = 3

    def __init__(self, name):
        self.name = name
        self.pal = ROBOT_PALETTES[name]
        self.tick = 0
        self.imp, self.imp_seed, self.sfx = None, 1, 'BEEP!'
        self.shake, self.tingle = 0.0, 0
        self.blink_seq, self.blink_cd, self.blink_frame = [], 60, 0
        self.purr = self.chat = self.idle = 0
        self.look = 0
        self.parts = []
        self.center = (120, 88)

    def poke(self, amount=0):
        self.purr = 55
        for _ in range(2):
            self.parts.append([random.randint(34, 46), 20, random.uniform(-.12, .12), -.28,
                               34, 34, 'heart', random.choice(((255, 116, 153), (255, 197, 93)))])

    def wave(self, ticks=60):
        self.chat = max(self.chat, ticks)

    def thwip(self, text='BEEP!'):
        self.imp, self.imp_seed, self.sfx = 0, random.randint(1, 10 ** 6), text

    def step(self):
        self.tick += 1
        t, k = self.tick, self.imp
        self.chat = max(0, self.chat - 1)
        self.purr = max(0, self.purr - 1)
        if self.blink_seq:
            self.blink_frame = self.blink_seq.pop(0)
        else:
            self.blink_frame = 0
            self.blink_cd -= 1
            if self.blink_cd <= 0:
                self.blink_seq, self.blink_cd = [1, 2, 1], random.randint(65, 155)
        sw, sh = self.size
        im = Image.new('RGBA', (sw // self.SCALE, sh // self.SCALE), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # soft floating glints and a little ground shadow
        for i in range(5):
            x = 8 + ((i * 17 + t // (8 + i)) % 64)
            y = 5 + (i * 7) % 35
            if (t // 12 + i) % 3 == 0:
                d.point((x, y), fill=(189, 239, 240, 190))
        d.ellipse((27, 39, 53, 43), fill=(10, 33, 48, 95))
        bob = round(math.sin(t * (.19 if self.purr else .075)))
        p, shape = self.pal, self.pal['shape']
        x, y = 40, 13 + bob
        # antenna and the characteristic silhouette
        if shape == 'visor':
            d.line((x + 15, y + 2, x + 15, y - 7), fill=p['dark'], width=2)
            d.ellipse((x + 12, y - 12, x + 18, y - 6), fill=p['accent'], outline=p['dark'])
            d.rectangle((x + 1, y + 1, x + 29, y + 18), fill=p['shell'], outline=p['dark'], width=2)
            d.rectangle((x + 4, y + 4, x + 26, y + 13), fill=p['screen'], outline=p['shade'])
            d.line((x + 8, y + 11, x + 22, y + 5), fill=p['glow'], width=2)
        elif shape == 'round':
            d.line((x + 15, y + 4, x + 15, y - 3), fill=p['dark'], width=2)
            d.ellipse((x + 12, y - 7, x + 18, y - 1), fill=p['accent'], outline=p['dark'])
            d.rounded_rectangle((x + 2, y + 1, x + 28, y + 21), radius=5, fill=p['shell'], outline=p['dark'], width=2)
            d.rectangle((x + 5, y + 7, x + 25, y + 16), fill=p['screen'], outline=p['shade'])
        elif shape == 'stack':
            d.rounded_rectangle((x + 6, y + 1, x + 24, y + 27), radius=5, fill=p['shell'], outline=p['dark'], width=2)
            for yy in (6, 13, 20):
                d.rectangle((x + 8, y + yy, x + 22, y + yy + 3), fill=p['shade'])
            d.rectangle((x + 9, y + 8, x + 21, y + 12), fill=p['screen'], outline=p['glow'])
        else:
            d.rectangle((x + 2, y + 2, x + 28, y + 21), fill=p['shell'], outline=p['dark'], width=2)
            d.rectangle((x + 5, y + 5, x + 25, y + 16), fill=p['screen'], outline=p['shade'])
            if shape == 'box':
                d.line((x + 15, y + 2, x + 15, y - 5), fill=p['dark'], width=2)
                d.rectangle((x + 13, y - 9, x + 17, y - 5), fill=p['accent'], outline=p['dark'])
        # friendly face: little pixel eyes, blush, and a changing smile
        blink = self.blink_frame > 0
        for ex in (x + 10, x + 20):
            ey = y + (10 if shape == 'visor' else 11)
            d.line((ex, ey, ex + 2, ey), fill=p['glow'], width=2) if blink else d.rectangle((ex, ey, ex + 2, ey + 2), fill=p['glow'])
        d.line((x + 13, y + 15, x + 17, y + 15), fill=p['dark'], width=1)
        d.point((x + 7, y + 15), fill=(255, 142, 157, 255))
        d.point((x + 23, y + 15), fill=(255, 142, 157, 255))
        # body, tiny arms, and feet
        by = y + (19 if shape == 'visor' else (23 if shape == 'stack' else 22))
        d.rectangle((x + 6, by, x + 24, by + 11), fill=p['shell'], outline=p['dark'], width=2)
        d.rectangle((x + 9, by + 3, x + 21, by + 5), fill=p['accent'])
        d.line((x + 3, by + 2, x + 3, by + 8), fill=p['dark'], width=2)
        d.line((x + 27, by + 2, x + 27, by + 8), fill=p['dark'], width=2)
        d.rectangle((x + 8, by + 11, x + 12, by + 14), fill=p['dark'])
        d.rectangle((x + 18, by + 11, x + 22, by + 14), fill=p['dark'])
        d.rectangle((x + 6, by + 14, x + 13, by + 16), fill=p['accent'])
        d.rectangle((x + 17, by + 14, x + 24, by + 16), fill=p['accent'])
        if k is not None and k >= 3:
            # celebratory pixel burst, kept small and friendly
            r = 3 + (k % 4)
            for dx, dy in ((-r, -2), (r, 1), (0, -r), (2, r)):
                d.point((x + 15 + dx, y + 12 + dy), fill=(255, 218, 86, 255))
        keep = []
        for a, b, vx, vy, life, mx, kind, col in self.parts:
            a, b, life = a + vx, b + vy, life - 1
            if life > 0:
                if kind == 'heart':
                    d.rectangle((round(a), round(b), round(a + 1), round(b + 1)), fill=col + (255,))
                keep.append([a, b, vx, vy, life, mx, kind, col])
        self.parts = keep
        if k is not None:
            self.imp = k + 1 if k < 9 else None
        return im.resize(self.size, Image.Resampling.NEAREST)


# --------------------------------------------------------------------------- companions
COMPANIONS = ('Spidey', 'Midnight Cat', 'Ginger Cat', 'Scout Robot', 'Buddy Robot',
              'Sprout Robot', 'Beeper Robot', 'Tinker Robot')


def build_scene(name):
    if name == 'Midnight Cat':
        return CatScene('Midnight')
    if name == 'Ginger Cat':
        return CatScene('Ginger')
    if name.endswith(' Robot'):
        return RobotScene(name[:-6].rstrip())
    return Scene()


VOICE = {
    'spidey': dict(
        greet='Hey! Your friendly neighborhood focus buddy is here.',
        poke=['Wheee!', 'Web swing!', 'Nice and easy...'],
        idle=['One tiny task at a time, hero.', 'Web-slinging focus mode: ready!',
              'Stretch break? Even heroes need one.', 'Looking sharp, citizen!'],
        thwip='THWIP! Spidey-sense activated!', sfx='THWIP!'),
    'cat': dict(
        greet='Mrrp! Soft paws, sharp focus. Let us begin.',
        poke=['Purrrr...', 'Mrrow!', 'Pat pat pat~', 'Right behind the ears...'],
        idle=['One tiny task at a time. Purr.', 'Hydrate, human. Then back to it.',
              'I will guard your focus. Mew.', 'Stretch break? I did, twice.'],
        thwip=None, sfx='MEOW!'),
    'robot': dict(
        greet='Beep boop! Your tiny helper is ready to roll.',
        poke=['Boop received!', 'Happy circuits!', 'Beep! That tickles.'],
        idle=['One little task at a time!', 'You have got this, human friend.',
              'Charging up your focus!', 'Tiny break? I will keep watch.'],
        thwip='BEEP!', sfx='BEEP!'),
}


def load_choice():
    for a in sys.argv[1:]:
        if a.lower() in ('cat', '--cat'):
            return 'Midnight Cat'
        if a.lower() in ('ginger', '--ginger'):
            return 'Ginger Cat'
        if a.lower() in ('spidey', '--spidey'):
            return 'Spidey'
        if a.lower() in ('robot', '--robot', 'scout', '--scout'):
            return 'Scout Robot'
        if a.lower() in ('buddy', '--buddy'):
            return 'Buddy Robot'
        if a.lower() in ('sprout', '--sprout'):
            return 'Sprout Robot'
        if a.lower() in ('beeper', '--beeper'):
            return 'Beeper Robot'
        if a.lower() in ('tinker', '--tinker'):
            return 'Tinker Robot'
    try:
        with open(SAVE_PATH) as f:
            name = f.read().strip()
        if name in COMPANIONS:
            return name
    except OSError:
        pass
    return 'Spidey'


# --------------------------------------------------------------------------- the desktop pet
class DeskSpidey(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Desk Companion')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        try:
            self.attributes('-transparentcolor', BG)      # Windows only
        except tk.TclError:
            pass
        self.configure(bg=BG)
        self.pos = (max(0, self.winfo_screenwidth() - W), 0)
        self.geometry(f'{W}x{H}+{self.pos[0]}+{self.pos[1]}')
        self.cv = tk.Canvas(self, width=W, height=H, bg=BG, bd=0, highlightthickness=0)
        self.cv.pack()
        self.photo = None
        self.message = ''
        self.message_until = 0
        self.focus_left = 0
        self.focus_active = False
        self.focus_job = None
        self.sessions = 0
        self.mood = 'Ready'
        self.missions = []
        self.drag = None
        self.companion, self.kind, self.scene = 'Spidey', 'spidey', None
        self.pick(load_choice(), greet=False)
        self.cv.bind('<ButtonPress-1>', self.start_drag)
        self.cv.bind('<B1-Motion>', self.move_window)
        self.cv.bind('<ButtonRelease-1>', self.release_click)
        self.cv.bind('<Double-Button-1>', lambda e: self.thwip())
        self.cv.bind('<Button-3>', self.menu)
        self.cv.bind('<Button-2>', self.menu)
        self.say(self.voice['greet'], 6)
        self.after(45000, self.auto_line)
        self.after(9000, self.auto_tingle)
        self.animate()

    @property
    def voice(self):
        return VOICE[self.kind]

    def pick(self, name, greet=True):
        """Switch to another companion."""
        self.companion = name
        self.kind = 'cat' if 'Cat' in name else ('robot' if name.endswith(' Robot') else 'spidey')
        self.scene = build_scene(name)
        self.message, self.message_until = '', 0
        self.win = getattr(self.scene, 'size', (W, H))
        w, h = self.win
        self.cv.config(width=w, height=h)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.pos = (max(0, sw - w), 0) if self.kind == 'spidey' else (max(0, sw - w - 24), max(0, sh - h - 64))
        self.geometry(f'{w}x{h}+{self.pos[0]}+{self.pos[1]}')
        if greet:
            try:
                with open(SAVE_PATH, 'w') as f:
                    f.write(name)
            except OSError:
                pass
            self.say(self.voice['greet'], 5)

    # ---- drawing
    def rrect(self, x1, y1, x2, y2, r=8, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
               x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def draw_hud(self):
        c, s = self.cv, self.scene
        w, h = self.win
        c.delete('hud')
        k = s.imp
        if k is not None and k <= 2 and s.flat_frames:   # pure impact frames: no UI on top
            return
        timer = f'{self.focus_left // 60:02d}:{self.focus_left % 60:02d}' if self.focus_left else '25:00'
        dot = '#42e08a' if self.focus_active else ('#ffcc4d' if self.focus_left else '#6d7f9c')
        paused = ' II' if self.focus_left and not self.focus_active else ''
        if s.compact:
            if self.focus_left or self.mood != 'Ready':       # tiny status pill, only when useful
                self.rrect(4, 4, 92, 20, 7, fill='#0e1a2e', outline='#33507f', width=1, tags='hud')
                c.create_oval(10, 9, 16, 15, fill=dot, outline='', tags='hud')
                c.create_text(22, 12, anchor='w', fill='#f4f7ff', font=('Consolas', 8, 'bold'),
                              text=f'{self.mood} {timer}{paused}', tags='hud')
                if self.focus_left:
                    frac = 1 - self.focus_left / (25 * 60)
                    c.create_rectangle(6, 23, 90, 26, fill='#16233a', outline='', tags='hud')
                    c.create_rectangle(6, 23, 6 + 84 * frac, 26, fill='#ed1826', outline='', tags='hud')
        else:
            self.rrect(8, 8, 156, 34, 9, fill='#0e1a2e', outline='#33507f', width=1, tags='hud')
            c.create_oval(16, 17, 24, 25, fill=dot, outline='', tags='hud')
            c.create_text(32, 21, anchor='w', fill='#f4f7ff', font=('Consolas', 9, 'bold'),
                          text=f'{self.mood}  {timer}{paused}', tags='hud')
            if self.focus_left:
                frac = 1 - self.focus_left / (25 * 60)
                c.create_rectangle(10, 38, 154, 42, fill='#16233a', outline='', tags='hud')
                c.create_rectangle(10, 38, 10 + 144 * frac, 42, fill='#ed1826', outline='', tags='hud')
        if self.message and s.tick < self.message_until:
            text = self.message[:58]
            if s.compact:                                   # small bubble above the cat's head
                lines = max(1, math.ceil(len(text) / 20))
                bh = 12 + 12 * lines
                x1, x2, y1 = 4, w - 4, 4
                cx = (CAT_O[0] + 10) * PX
                self.rrect(x1, y1, x2, y1 + bh, 10, fill='#fff8e8', outline='#131722', width=2, tags='hud')
                c.create_polygon(cx - 8, y1 + bh - 1, cx + 8, y1 + bh - 1, cx, y1 + bh + 9,
                                 fill='#fff8e8', outline='#131722', width=2, tags='hud')
                c.create_rectangle(cx - 7, y1 + bh - 3, cx + 7, y1 + bh + 1, fill='#fff8e8', outline='', tags='hud')
                c.create_text(x1 + 8, y1 + 6, anchor='nw', width=w - 24, fill='#151923',
                              font=('Arial', 8, 'bold'), text=text, tags='hud')
            else:
                lines = max(1, math.ceil(len(text) / 23))
                bh = 14 + 12 * lines
                x2, hy = s.bubble
                x1, y1 = x2 - 152, hy - 62
                self.rrect(x1, y1, x2, y1 + bh, 10, fill='#fff8e8', outline='#131722', width=2, tags='hud')
                c.create_polygon(x2 - 2, y1 + bh - 18, x2 + 22, hy - 14, x2 - 2, y1 + bh - 4,
                                 fill='#fff8e8', outline='#131722', width=2, tags='hud')
                c.create_rectangle(x2 - 3, y1 + bh - 17, x2 - 1, y1 + bh - 5, fill='#fff8e8', outline='', tags='hud')
                c.create_text(x1 + 9, y1 + 7, anchor='nw', width=134, fill='#151923',
                              font=('Arial', 8, 'bold'), text=text, tags='hud')
        if k is not None and 3 <= k <= 9:      # THWIP! / MEOW! comic lettering
            cx, cy = s.center
            size = s.text_base + min(k - 3, 3) * 4
            tx, ty = s.text_pos or (max(90, cx - 95), max(30, cy - 78))
            font = ('Arial Black', size, 'bold')
            for ox, oy in ((-2, -2), (2, -2), (-2, 2), (2, 2), (3, 3)):
                c.create_text(tx + ox, ty + oy, text=s.sfx, font=font, fill='#10121b', angle=-9, tags='hud')
            c.create_text(tx, ty, text=s.sfx, font=font, fill='#ffe04a', angle=-9, tags='hud')
        if not s.compact:
            c.create_text(10, h - 10, anchor='w', fill='#abb8cb', font=('Arial', 7),
                          text=f'\u2605 {self.sessions} focus sessions   \u2022   {len(self.missions)} missions',
                          tags='hud')

    def animate(self):
        s = self.scene
        if self.kind == 'cat':                             # eyes follow the mouse
            px = self.winfo_pointerx() - (self.winfo_rootx() + (CAT_O[0] + 10) * PX)
            s.look = -1 if px < -45 else (1 if px > 45 else 0)
        frame = s.step()
        self.photo = ImageTk.PhotoImage(frame)
        self.cv.delete('art')
        self.cv.create_image(0, 0, anchor='nw', image=self.photo, tags='art')
        self.cv.tag_lower('art')
        self.draw_hud()
        if s.shake > .4:                                   # screen shake on impact
            self.geometry(f'+{int(self.pos[0] + random.uniform(-1, 1) * s.shake)}'
                          f'+{int(self.pos[1] + random.uniform(-1, 1) * s.shake)}')
            s.shake *= .78
        elif s.shake:
            s.shake = 0.0
            self.geometry(f'+{self.pos[0]}+{self.pos[1]}')
        self.after(40, self.animate)

    # ---- mouse
    def start_drag(self, e):
        self.drag = (e.x_root - self.pos[0], e.y_root - self.pos[1], e.x, e.y)

    def move_window(self, e):
        if self.drag:
            dx, dy, _, _ = self.drag
            self.pos = (e.x_root - dx, e.y_root - dy)
            self.geometry(f'+{self.pos[0]}+{self.pos[1]}')

    def release_click(self, e):
        if self.drag and abs(e.x - self.drag[2]) < 5 and abs(e.y - self.drag[3]) < 5:
            self.scene.poke(random.choice((-.06, .06)))
            self.say(random.choice(self.voice['poke']))
        self.drag = None

    # ---- behaviour
    def say(self, text, seconds=4, wave=True):
        self.message = text
        self.message_until = self.scene.tick + int(seconds * 25)
        if wave:
            self.scene.wave(60)

    def thwip(self, text=None, line=None):
        if self.kind in ('cat', 'robot') and text in (None, 'THWIP!', 'POW!'):
            text = 'MEOW!' if self.kind == 'cat' else 'BEEP!'
        text = text or self.voice['sfx']
        line = line or self.voice['thwip']
        self.scene.thwip(text)
        if line:
            self.say(line)

    def auto_line(self):
        if random.random() < .45:
            self.say(random.choice(self.voice['idle']), 5)
        self.after(45000, self.auto_line)

    def auto_tingle(self):
        self.scene.tingle = 22
        self.after(random.randint(9000, 16000), self.auto_tingle)

    def focus(self):
        if self.focus_active:
            self.focus_active = False
            if self.focus_job is not None:
                self.after_cancel(self.focus_job)
                self.focus_job = None
            self.say('Focus timer paused. Pick it up when you are ready.')
            return
        if not self.focus_left:
            self.focus_left = 25 * 60
        self.focus_active = True
        self.say('Focus session running. I have your back!', 6)
        self.countdown()

    def countdown(self):
        self.focus_job = None
        if not self.focus_left or not self.focus_active:
            return
        self.focus_left -= 1
        if self.focus_left <= 0:
            self.focus_active = False
            self.sessions += 1
            self.thwip('NICE!', 'Focus complete! You did amazing. Take a short break!')
            self.message_until = self.scene.tick + 250
            return
        self.focus_job = self.after(1000, self.countdown)

    def add_mission(self):
        from tkinter import simpledialog
        title = simpledialog.askstring('New mission', 'What is your next small win?', parent=self)
        if title and title.strip():
            self.missions.append(title.strip())
            self.say('Mission added: ' + title.strip()[:28])

    def show_missions(self):
        if self.missions:
            self.say('Next up: ' + self.missions[0][:34])
        else:
            self.add_mission()

    def complete_mission(self):
        if self.missions:
            done = self.missions.pop(0)
            self.thwip('POW!', 'Mission complete: ' + done[:28] + '!')
        else:
            self.say('No missions queued. Add a small win!')

    def set_mood(self, mood):
        self.mood = mood
        self.scene.tingle = 20 if mood == 'Stuck' else 0
        self.say({'Great': 'You are crushing it! Keep going!', 'Okay': 'Steady progress is progress.',
                  'Stuck': 'Pause, breathe, then tackle one small piece.'}[mood])

    def menu(self, e):
        m = tk.Menu(self, tearoff=0)
        who = tk.Menu(m, tearoff=0)
        for name in COMPANIONS:
            mark = '\u25CF  ' if name == self.companion else '      '
            who.add_command(label=mark + name, command=lambda n=name: self.pick(n))
        m.add_cascade(label='\U0001F43E  Choose companion', menu=who)
        m.add_separator()
        if self.kind == 'cat':
            m.add_command(label='\U0001F431  Pet the cat',
                          command=lambda: self.scene.poke(0))
            m.add_command(label='\U0001F4A5  MEOW! (hop + starburst)', command=self.thwip)
        elif self.kind == 'robot':
            m.add_command(label='\U0001F916  Boop the robot', command=lambda: self.scene.poke(0))
            m.add_command(label='\U0001F4AB  BEEP! (happy sparkles)', command=self.thwip)
        else:
            m.add_command(label='\U0001F578  Swing!',
                          command=lambda: self.scene.poke(random.choice((-.09, .09))))
            m.add_command(label='\U0001F4A5  THWIP! (impact frames)', command=self.thwip)
        m.add_command(label='\u23F1  Start / pause 25-minute focus', command=self.focus)
        m.add_command(label='\U0001F3AF  Add / view mission', command=self.show_missions)
        m.add_command(label='\u2705  Complete next mission', command=self.complete_mission)
        moods = tk.Menu(m, tearoff=0)
        for label in ('Great', 'Okay', 'Stuck'):
            moods.add_command(label=label, command=lambda v=label: self.set_mood(v))
        m.add_cascade(label='\U0001F60A  Log mood', menu=moods)
        m.add_separator()
        m.add_command(label='Quit Desk Companion', command=self.destroy)
        m.tk_popup(e.x_root, e.y_root)


if __name__ == '__main__':
    DeskSpidey().mainloop()
