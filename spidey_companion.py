"""Desk Spidey v12: polished vector comic hero in an upside-down web-grab pose.

Requires: pip install pillow
Controls: click = swing, double-click = THWIP (impact frames!), right-click = menu, drag = move.

What's new in v11
  * Smooth, high-resolution comic art with a bold ink outline, red-and-blue suit, mask webbing,
    white lenses, and chest emblem
  * Hands clasp the web overhead, knees fold outward, and the mask hangs below the torso
  * Hanging pose stays clear through the existing pendulum swing and impact effects
  * Everything else kept: orb web, impact frames, THWIP, particles, pendulum swing
"""
import math
import os
import random
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
    # Keep the orb web as a compact corner flourish; the hero stays the focus.
    length = 132
    rings = [16, 27, 39, 52, 66, 81, 98, 118]

    def pt(r, a):
        return (A[0] + math.cos(a) * r, A[1] + math.sin(a) * r)

    # ring threads (sagging toward the anchor) first, so radials sit on top
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
    # radial strands
    for a in angs:
        p = pt(length, a)
        d.line((A[0] * SS, A[1] * SS, p[0] * SS, p[1] * SS), fill=(214, 228, 248, 130), width=SS)
    # dragline Spidey hangs from (soft glow + bright core)
    ctrl = ((A[0] + PIVOT[0]) / 2 + 4, (A[1] + PIVOT[1]) / 2 + 12)
    drag = [(x * SS, y * SS) for x, y in bezier(A, ctrl, PIVOT, 20)]
    d.line(drag, fill=(150, 195, 255, 48), width=6 * SS, joint='curve')
    d.line(drag, fill=(244, 249, 255, 240), width=2 * SS, joint='curve')
    # glowing anchor knot
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
HERO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'spidey_reference_cutout.png')
with Image.open(HERO_PATH) as _hero_file:
    _hero_art = _hero_file.convert('RGBA')
_HERO_BASE = Image.new('RGBA', (SPR_W, SPR_H), (0, 0, 0, 0))
_hero_h = SPR_H
_hero_w = round(_hero_art.width * _hero_h / _hero_art.height)
_HERO_BASE.alpha_composite(_hero_art.resize((_hero_w, _hero_h), Image.Resampling.LANCZOS),
                           ((SPR_W - _hero_w) // 2, 0))

@lru_cache(maxsize=64)
def make_spidey(idx=0, blink=0, waving=False, squint=False):
    """Load the polished, transparent comic illustration used by the pet."""
    return _HERO_BASE.copy()

# --------------------------------------------------------------------------- the scene (pure PIL)
class Scene:
    """All the animation + impact-frame logic; step() returns one RGBA frame."""

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

    # -- coordinates
    def xf(self, ux, uy):
        """Sprite unit (1 unit = S px) -> window pixel (follows the swing)."""
        dx, dy = ux * S, uy * S
        c, s = math.cos(self.ang), math.sin(self.ang)
        return (PIVOT[0] + dx * c + dy * s, PIVOT[1] - dx * s + dy * c)

    # -- events
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
        # web-shot leaves the left glove side of the hero and splats somewhere on screen
        self.shot = {'age': 0, 'a': self.xf(-52, HEAD_PX / S - 4),
                     'b': (random.uniform(25, 150), random.uniform(110, 265))}

    # -- per-frame update
    def step(self):
        self.tick += 1
        k = self.imp
        if not (k is not None and k < 5):                       # hit-stop freezes the swing
            self.vel += -.0105 * self.ang + .0004 * math.sin(self.tick * .045)
            self.vel *= .992
            self.ang = max(-.24, min(.24, self.ang + self.vel))
        # blink / timers
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

    # -- layers
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
        # halftone dots on the red core
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


# --------------------------------------------------------------------------- the desktop pet
class DeskSpidey(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Desk Spidey')
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
        self.scene = Scene()
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
        self.cv.bind('<ButtonPress-1>', self.start_drag)
        self.cv.bind('<B1-Motion>', self.move_window)
        self.cv.bind('<ButtonRelease-1>', self.release_click)
        self.cv.bind('<Double-Button-1>', lambda e: self.thwip())
        self.cv.bind('<Button-3>', self.menu)
        self.cv.bind('<Button-2>', self.menu)
        self.say('Hey! Your friendly neighborhood focus buddy is here.', 6)
        self.after(45000, self.auto_line)
        self.after(9000, self.auto_tingle)
        self.animate()

    # ---- drawing
    def rrect(self, x1, y1, x2, y2, r=8, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
               x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.cv.create_polygon(pts, smooth=True, **kw)

    def draw_hud(self):
        c, s = self.cv, self.scene
        c.delete('hud')
        k = s.imp
        if k is not None and k <= 2:           # pure impact frames: no UI on top
            return
        timer = f'{self.focus_left // 60:02d}:{self.focus_left % 60:02d}' if self.focus_left else '25:00'
        dot = '#42e08a' if self.focus_active else ('#ffcc4d' if self.focus_left else '#6d7f9c')
        self.rrect(8, 8, 156, 34, 9, fill='#0e1a2e', outline='#33507f', width=1, tags='hud')
        c.create_oval(16, 17, 24, 25, fill=dot, outline='', tags='hud')
        c.create_text(32, 21, anchor='w', fill='#f4f7ff', font=('Consolas', 9, 'bold'),
                      text=f'{self.mood}  {timer}' + (' II' if self.focus_left and not self.focus_active else ''),
                      tags='hud')
        if self.focus_left:
            frac = 1 - self.focus_left / (25 * 60)
            c.create_rectangle(10, 38, 154, 42, fill='#16233a', outline='', tags='hud')
            c.create_rectangle(10, 38, 10 + 144 * frac, 42, fill='#ed1826', outline='', tags='hud')
        if self.message and s.tick < self.message_until:
            text = self.message[:58]
            lines = max(1, math.ceil(len(text) / 23))
            bh = 14 + 12 * lines
            x2, hy = PIVOT[0] - 86, PIVOT[1] + 175
            x1, y1 = x2 - 152, hy - 62
            self.rrect(x1, y1, x2, y1 + bh, 10, fill='#fff8e8', outline='#131722', width=2, tags='hud')
            c.create_polygon(x2 - 2, y1 + bh - 18, x2 + 22, hy - 14, x2 - 2, y1 + bh - 4,
                             fill='#fff8e8', outline='#131722', width=2, tags='hud')
            c.create_rectangle(x2 - 3, y1 + bh - 17, x2 - 1, y1 + bh - 5, fill='#fff8e8', outline='', tags='hud')
            c.create_text(x1 + 9, y1 + 7, anchor='nw', width=134, fill='#151923',
                          font=('Arial', 8, 'bold'), text=text, tags='hud')
        if k is not None and 3 <= k <= 9:      # THWIP! comic lettering
            cx, cy = s.center
            size = 20 + min(k - 3, 3) * 4
            tx, ty = max(90, cx - 95), max(30, cy - 78)
            font = ('Arial Black', size, 'bold')
            for ox, oy in ((-2, -2), (2, -2), (-2, 2), (2, 2), (3, 3)):
                c.create_text(tx + ox, ty + oy, text=s.sfx, font=font, fill='#10121b', angle=-9, tags='hud')
            c.create_text(tx, ty, text=s.sfx, font=font, fill='#ffe04a', angle=-9, tags='hud')
        c.create_text(10, H - 10, anchor='w', fill='#abb8cb', font=('Arial', 7),
                      text=f'\u2605 {self.sessions} focus sessions   \u2022   {len(self.missions)} missions',
                      tags='hud')

    def animate(self):
        s = self.scene
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
            self.say(random.choice(['Wheee!', 'Web swing!', 'Nice and easy...']))
        self.drag = None

    # ---- behaviour
    def say(self, text, seconds=4, wave=True):
        self.message = text
        self.message_until = self.scene.tick + int(seconds * 25)
        if wave:
            self.scene.wave(60)

    def thwip(self, text='THWIP!', line='THWIP! Spidey-sense activated!'):
        self.scene.thwip(text)
        self.say(line)

    def auto_line(self):
        if random.random() < .45:
            self.say(random.choice(['One tiny task at a time, hero.', 'Web-slinging focus mode: ready!',
                                    'Stretch break? Even heroes need one.', 'Looking sharp, citizen!']), 5)
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
        m.add_command(label='\U0001F578  Swing!', command=lambda: self.scene.poke(random.choice((-.09, .09))))
        m.add_command(label='\U0001F4A5  THWIP! (impact frames)', command=self.thwip)
        m.add_command(label='\u23F1  Start / pause 25-minute focus', command=self.focus)
        m.add_command(label='\U0001F3AF  Add / view mission', command=self.show_missions)
        m.add_command(label='\u2705  Complete next mission', command=self.complete_mission)
        moods = tk.Menu(m, tearoff=0)
        for label in ('Great', 'Okay', 'Stuck'):
            moods.add_command(label=label, command=lambda v=label: self.set_mood(v))
        m.add_cascade(label='\U0001F60A  Log mood', menu=moods)
        m.add_separator()
        m.add_command(label='Quit Desk Spidey', command=self.destroy)
        m.tk_popup(e.x_root, e.y_root)


if __name__ == '__main__':
    DeskSpidey().mainloop()


