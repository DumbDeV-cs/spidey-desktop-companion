"""Desk-Spidey Companion v3 - pixel-art desktop pet hanging from a web in the top-right corner.
Requires:  pip install pillow numpy
Controls:  drag = move | double-click = poke | right-click = menu
"""
import datetime
import math
import os
import platform
import random
import sqlite3
import tkinter as tk

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps, ImageTk

DB = 'spidey_companion.db'
WW, WH, PX = 340, 300, 245          # compact corner window; the web anchor sits near the top-right
RED, BLUE, DARK, WHITE, KEY = '#d62839', '#1f4fd8', '#0a0d1a', '#f4f7ff', '#050810'
BICUBIC = Image.BICUBIC

QUOTES = [
    "With great power comes great responsibility... like pushing your code today!",
    "Your friendly neighborhood bug-squasher is on watch!",
    "Even heroes miss a web-sling sometimes. Keep debugging!",
    "Pizza time? Not yet, finish that function first!",
    "Stuck on a bug? Hang upside down. New angle, new fix!",
    "My spidey-sense says there's an off-by-one error nearby...",
    "Commit early, commit often. Web your changes together!",
]
PRAISE = ["Thwip! That's the spirit!", "Crushing it, hero! Level up incoming!"]
HELP = ["Spidey-sense tingling! Breathe, then read the error message slowly.",
        "Explain the bug out loud to me. Rubber-duck, but web-slinging!",
        "Take a 5-minute walk. Your brain debugs in the background."]
REMINDERS = ["Hydration check! Drink some water, hero.",
             "Stretch time! Roll those shoulders.",
             "Look away from the screen for 20 seconds."]


# ============================ database ============================
def db(sql, args=(), fetch=False):
  conn = sqlite3.connect(DB)
  try:
    cur = conn.execute(sql, args)
    conn.commit()
    return cur.fetchall() if fetch else None
  finally:
    conn.close()


def init_db():
  db('CREATE TABLE IF NOT EXISTS mood_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, mood TEXT NOT NULL)')
  db('CREATE TABLE IF NOT EXISTS missions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, done INTEGER DEFAULT 0)')
  db('CREATE TABLE IF NOT EXISTS pomodoros (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL)')


def now():
  return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ============================ 3D sprite renderer (raymarched SDF) ============================
PPU, SSR = 60, 3                    # pixels per unit, supersampling
CACHE = 'spidey_cache_v3'
YAWS = (-.5, 0, .5)
HB = (-.85, .85, -.9, .75)          # head render box
FEET_Y = 44
f32 = np.float32
LINE = (.05, .02, .05)
RC = {0: (.78, .07, .18), 1: (.11, .25, .72), 2: (.60, .05, .14)}
LEGS = [[(.07, .12), (.24, .24), (.36, .2)], [(.08, .05), (.28, .1), (.4, 0)],
        [(.08, -.04), (.28, -.1), (.38, -.2)], [(.07, -.1), (.22, -.24), (.3, -.34)]]


def v3(c): return np.array(c, f32)[:, None]
def nrm(v): return np.sqrt((v * v).sum(0))
def sph(P, c, r): return nrm(P - v3(c)) - r


def cap(P, a, b, ra, rb):
  a, b = v3(a), v3(b)
  pa, ba = P - a, b - a
  h = np.clip((pa * ba).sum(0) / (ba * ba).sum(), 0, 1)
  return nrm(pa - ba * h) - (ra + (rb - ra) * h)


def ell(P, c, r):
  r = v3(r)
  q = (P - v3(c)) / r
  k0, k1 = nrm(q), nrm(q / r)
  return k0 * (k0 - 1) / np.maximum(k1, 1e-5)


def smin(a, b, k=.07):
  h = np.clip(.5 + .5 * (b - a) / k, 0, 1)
  return b * (1 - h) + a * h - k * h * (1 - h)


def body_parts(P):
  o = []
  for s in (-1, 1):
    o += [(cap(P, (s * .30, .10, .04), (s * .32, .50, .06), .20, .22), 2),
          (ell(P, (s * .34, .46, .25), (.20, .16, .24)), 2),
          (cap(P, (s * .30, .50, 0), (s * .27, 1.50, 0), .19, .30), 1),
          (sph(P, (s * .90, 2.40, 0), .30), 0)]
  o += [(ell(P, (0, 1.6, 0), (.62, .32, .40)), 1), (ell(P, (0, 1.82, 0), (.50, .40, .36)), 0),
        (ell(P, (0, 2.25, 0), (.82, .50, .46)), 0), (cap(P, (0, 2.6, 0), (0, 2.9, 0), .20, .17), 0)]
  return o, P


def arm_parts(P):
  return [(cap(P, (0, 0, 0), (.03, .60, 0), .25, .19), 0), (cap(P, (.03, .60, 0), (.02, 1.10, .03), .19, .16), 0),
          (ell(P, (.02, 1.27, .03), (.19, .24, .16)), 0)], P


def head_parts(yaw):
  c, s = math.cos(yaw), math.sin(yaw)
  R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]], f32)

  def f(P):
    Q = R @ P
    return [(ell(Q, (0, 0, 0), (.58, .62, .56)), 0), (ell(Q, (0, -.12, 0), (.52, .56, .52)), 0),
            (cap(Q, (0, -.45, 0), (0, -.72, 0), .26, .22), 0)], Q
  return f


def web(u, v, n, rings, sw=.014, rw=.014):
  r = np.hypot(u, v) + 1e-6
  th = np.arctan2(u, v)
  a = np.abs((th * n / (2 * np.pi) + .5) % 1 - .5) * (2 * np.pi / n) * r
  b = np.abs(((r + .045 * np.sin(th * n / 2) ** 2) * rings + .5) % 1 - .5) / rings
  return np.clip(2 * (1 - np.minimum(a / sw, b / rw)), 0, 1).astype(f32)


def seg(u, v, a, b):
  pa0, pa1, ba0, ba1 = u - a[0], v - a[1], b[0] - a[0], b[1] - a[1]
  h = np.clip((pa0 * ba0 + pa1 * ba1) / (ba0 * ba0 + ba1 * ba1), 0, 1)
  return np.hypot(pa0 - ba0 * h, pa1 - ba1 * h)


def emblem(u, v):
  m = (((u / .1) ** 2 + ((v + .1) / .17) ** 2 < 1) | (u ** 2 + (v - .13) ** 2 < .0036)).astype(f32)
  for sx in (-1, 1):
    for leg in LEGS:
      for a, b in zip(leg, leg[1:]):
        m = np.maximum(m, seg(u, v, (sx * a[0], a[1]), (sx * b[0], b[1])) < .017)
  return m


def lens(u, v, cu, ang, sx, sy):
  du, dv = u - cu, v - .02
  c, s = math.cos(ang), math.sin(ang)
  return ((du * c + dv * s) / (.29 * sx)) ** 2 + ((-du * s + dv * c) / (.15 * sy)) ** 2


def base(mat):
  b = np.zeros((3, mat.size), f32)
  for k, c in RC.items():
    b[:, mat == k] = v3(c)
  return b


def mixc(b, m, c): return b * (1 - m) + v3(c) * m


def paint_body(Q, mat):
  u, v = -Q[0], Q[1] - 2.25
  red = (mat == 0).astype(f32)
  b = mixc(base(mat), web(u, v, 12, 3.6) * red, LINE)
  b = mixc(b, emblem(u, v) * red * (Q[2] > 0), LINE)
  return b, np.full(mat.size, .25, f32)


def paint_arm(Q, mat):
  b = mixc(base(mat), web(-Q[0], Q[1], 8, 5), LINE)
  return b, np.full(mat.size, .25, f32)


def paint_head(mode):
  sx, sy = {'open': (1, 1), 'blink': (1, .17), 'shock': (1.3, 1.3)}[mode]

  def paint(Q, mat):
    u, v, z = -Q[0], Q[1], Q[2]
    b = mixc(base(mat), web(u, v - .64, 11, 5.5), LINE)
    d = np.minimum(lens(u, v, -.29, -.45, sx, sy), lens(u, v, .29, .45, sx, sy))
    b = mixc(b, ((d < 1.4) & (z > .05)).astype(f32), (.04, .02, .05))
    eye = (d < 1) & (z > .05)
    b = mixc(b, eye.astype(f32), (.96, .97, 1.0))
    sh = np.full(mat.size, .25, f32)
    sh[eye] = .9
    return b, sh
  return paint


def render_part(parts, box, paint):
  x0, x1, y0, y1 = box
  w, h = int((x1 - x0) * PPU), int((y1 - y0) * PPU)
  W, H = w * SSR, h * SSR
  xs = (x0 + (np.arange(W) + .5) / (PPU * SSR)).astype(f32)
  ys = (y0 + (np.arange(H) + .5) / (PPU * SSR)).astype(f32)
  X, Y = [a.ravel() for a in np.meshgrid(xs, ys)]

  def sdf(P):
    ds = parts(P)[0]
    r = ds[0][0]
    for d, _ in ds[1:]:
      r = smin(r, d)
    return r

  t, hit, alive = np.zeros(X.size, f32), np.zeros(X.size, bool), np.arange(X.size)
  for _ in range(70):
    d = sdf(np.stack([X[alive], Y[alive], 2.5 - t[alive]]))
    ok = d < .003
    hit[alive[ok]] = True
    t[alive] += d * .9
    alive = alive[~ok & (t[alive] < 5)]
    if not alive.size:
      break
  idx = np.nonzero(hit)[0]
  P = np.stack([X[idx], Y[idx], 2.5 - t[idx]])
  e = .01
  n = np.stack([sdf(P + v3(a) * e) - sdf(P - v3(a) * e) for a in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
  n /= np.maximum(nrm(n), 1e-6)
  ao = np.ones(idx.size, f32)
  for k, hh in enumerate((.06, .14, .28)):
    ao -= np.clip(hh - sdf(P + n * hh), 0, .3) * (.9 / 2 ** k)
  ao = np.clip(ao, .25, 1)
  lst, Q = parts(P)
  mat = np.array([m for _, m in lst])[np.argmin(np.stack([d for d, _ in lst]), 0)]
  col, shine = paint(Q, mat)
  L = np.array([-.45, -.62, .64], f32)
  L /= np.sqrt((L * L).sum())
  Hh = L + np.array([0, 0, 1], f32)
  Hh /= np.sqrt((Hh * Hh).sum())
  diff = np.clip(((n * L[:, None]).sum(0) + .25) / 1.25, 0, 1)
  spec = np.clip((n * Hh[:, None]).sum(0), 0, 1) ** 36 * shine
  rim = (1 - np.clip(n[2], 0, 1)) ** 3 * .45
  out = col * (.30 + .85 * diff * ao) + spec + rim * v3((.35, .55, 1.0)) * ao
  img = np.zeros((H * W, 4), np.uint8)
  img[idx, :3] = (np.clip(out, 0, 1).T * 255).astype(np.uint8)
  img[idx, 3] = 255
  im = Image.fromarray(img.reshape(H, W, 4), 'RGBA')
  edge = Image.new('RGBA', im.size, (10, 6, 14, 255))
  edge.putalpha(im.getchannel('A').filter(ImageFilter.MaxFilter(7)))
  edge.alpha_composite(im)
  return edge.resize((w, h), Image.LANCZOS)


def build_sprites():
  os.makedirs(CACHE, exist_ok=True)
  jobs = {'body': (body_parts, (-1.35, 1.35, -.05, 3.45), paint_body),
          'arm': (arm_parts, (-.5, .5, -.35, 1.6), paint_arm),
          'shock1': (head_parts(0), HB, paint_head('shock'))}
  for mode in ('open', 'blink'):
    for i, yaw in enumerate(YAWS):
      jobs[f'{mode}{i}'] = (head_parts(yaw), HB, paint_head(mode))
  sp = {}
  for i, (k, (pf, box, pt)) in enumerate(jobs.items()):
    path = f'{CACHE}/{k}.png'
    if os.path.exists(path):
      sp[k] = Image.open(path).convert('RGBA')
    else:
      print(f'Rendering 3D model {i + 1}/{len(jobs)} (first launch only)...', flush=True)
      sp[k] = render_part(pf, box, pt)
      sp[k].save(path)
  # Convert the smooth 3D render into crisp, deliberately chunky pixel art.
  for k, im in sp.items():
    small = im.resize((max(1, im.width // 4), max(1, im.height // 4)), Image.Resampling.BOX)
    sp[k] = small.resize(im.size, Image.Resampling.NEAREST)
    sp[k].save(f'{CACHE}/{k}.png')
  big = Image.new('RGBA', (170, 210), (0, 0, 0, 0))
  big.paste(sp['arm'], (55, 19))       # shoulder pivot lands at (85, 40)
  sp['armR'], sp['armL'] = big, ImageOps.mirror(big)
  return sp


def rot_pt(dx, dy, deg):
  t = math.radians(deg)
  return PX + dx * math.cos(t) + dy * math.sin(t), -dx * math.sin(t) + dy * math.cos(t)


def render(sp, a, v, t, blink, shock, yaw):
  deg = math.degrees(a)
  fig = Image.new('RGBA', (WW, WH), (0, 0, 0, 0))
  ImageDraw.Draw(fig).line([(PX, 0), (PX, FEET_Y)], fill='#e9eef9', width=2)
  fig.alpha_composite(sp['body'], (int(PX - 1.35 * PPU), int(FEET_Y - .05 * PPU)))
  if shock > 0:
    head = sp['shock1']
  else:
    m = 'blink' if blink > 0 else 'open'
    head = (Image.blend(sp[m + '1'], sp[m + '0'], -yaw) if yaw < 0 else Image.blend(sp[m + '1'], sp[m + '2'], yaw))
  head = head.rotate(3 * math.sin(t * .9) - v * 4, resample=BICUBIC, center=(51, 3))
  fig.alpha_composite(head, (PX - 51, int(FEET_Y + 3.3 * PPU - 54)))
  for sgn, key in ((1, 'armR'), (-1, 'armL')):
    ang = sgn * (6 + 3 * math.sin(t * 2.2 + sgn)) - deg * .7 - v * 6
    arm = sp[key].rotate(ang, resample=BICUBIC, center=(85, 40))
    fig.alpha_composite(arm, (int(PX + sgn * .9 * PPU - 85), int(FEET_Y + 2.4 * PPU - 40)))
  if shock > 0:
    d = ImageDraw.Draw(fig)
    for i in range(9):
      a0 = i * math.pi / 4.5 + t * 4
      r1, r2 = 54 + 4 * math.sin(t * 25 + i), 74
      d.line([(PX + r1 * math.cos(a0), 242 + r1 * math.sin(a0)), (PX + r2 * math.cos(a0), 242 + r2 * math.sin(a0))],
             fill='#ffd23f', width=3)
  return fig.rotate(deg, resample=BICUBIC, center=(PX, 0))


# ============================ app ============================
class SpideyCompanion(tk.Tk):

  def __init__(self):
    super().__init__()
    init_db()
    self.sp = build_sprites()
    self.sysname = platform.system()
    self.overrideredirect(True)
    self.attributes('-topmost', True)
    screen_right = self.winfo_screenwidth()
    self.geometry(f'{WW}x{WH}+{max(0, screen_right - WW)}+0')
    self.cv = tk.Canvas(self, width=WW, height=WH, highlightthickness=0, bd=0)
    self.cv.pack()
    if self.sysname == 'Windows':
      bg = KEY
      self.attributes('-transparentcolor', KEY)
    elif self.sysname == 'Darwin':
      bg = 'systemTransparent'
      self.attributes('-transparent', True)
    else:
      bg = KEY                      # Linux: needs a compositor for true transparency
    self.configure(bg=bg)
    self.cv.configure(bg=bg)
    self.item = self.cv.create_image(0, 0, anchor='nw')
    cb = self.cv.create_oval(WW - 26, 6, WW - 6, 26, fill='#16213e', outline='#e94560', width=2, tags='close')
    self.cv.create_text(WW - 16, 16, text='✕', fill='white', font=('Arial', 9, 'bold'), tags='close')
    self.cv.tag_bind('close', '<Button-1>', lambda e: self.after(10, self.destroy))
    self.cv.tag_bind('close', '<Enter>', lambda e: self.cv.itemconfig(cb, fill='#e94560'))
    self.cv.tag_bind('close', '<Leave>', lambda e: self.cv.itemconfig(cb, fill='#16213e'))

    self.t, self.a, self.v = 0.0, .25, 0.0
    self.blink = self.shock = 0
    self.yaw = 0.0
    self.zip, self.particles = None, []
    self.running, self.remaining, self.job = False, 0, None
    self.full, self.shown, self.bub = '', 0, 0
    self.xp, self.level = 0, 1

    self.cv.bind('<ButtonPress-1>', self.start_move)
    self.cv.bind('<B1-Motion>', self.do_move)
    self.cv.bind('<Double-Button-1>', lambda e: self.poke())
    self.build_menu()
    self.refresh_xp(announce=False)
    self.say("Hey! Double-click to poke me, right-click for the menu.")
    self.after(15000, self.auto_quote)
    self.after(30 * 60 * 1000, self.remind)
    self.tick()

  # ---- window ----
  def start_move(self, e):
    self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

  def do_move(self, e):
    self.geometry(f'+{e.x_root - self._dx}+{e.y_root - self._dy}')

  def build_menu(self):
    m = tk.Menu(self, tearoff=0)
    moods = tk.Menu(m, tearoff=0)
    for label, val in (('🔥 Crushing It', 'Great'), ('😐 Okay', 'Okay'), ('💻 Stuck', 'Struggling')):
      moods.add_command(label=label, command=lambda v=val: self.log_mood(v))
    m.add_cascade(label='Log mood', menu=moods)
    m.add_command(label='Start / stop focus timer', command=self.toggle_pomo)
    m.add_command(label='Missions', command=self.open_missions)
    m.add_command(label='Stats', command=self.open_stats)
    m.add_command(label='Web zip', command=self.web_zip)
    m.add_separator()
    m.add_command(label='Quit', command=self.destroy)
    pop = lambda e: m.tk_popup(e.x_root, e.y_root)
    self.cv.bind('<Button-3>', pop)
    self.cv.bind('<Button-2>', pop)
    self.cv.bind('<Control-Button-1>', pop)

  # ---- speech / HUD ----
  def say(self, text, frames=220):
    self.full, self.shown, self.bub = text, 0, frames

  def draw_ui(self):
    c = self.cv
    c.delete('ui')
    c.delete('bub')
    c.create_rectangle(6, 6, 118, 30, fill='#16213e', outline='#2b3a67', width=2, tags='ui')
    t = f'{self.remaining // 60:02d}:{self.remaining % 60:02d}' if self.running else 'Ready'
    c.create_text(12, 14, anchor='w', fill='white', font=('Arial', 8, 'bold'), text=f'LV {self.level} | Focus {t}', tags='ui')
    c.create_rectangle(12, 22, 112, 25, outline='#5b6aa0', tags='ui')
    c.create_rectangle(12, 22, 12 + (self.xp % 100), 25, fill='#06d6a0', width=0, tags='ui')
    if self.bub > 0 and self.full:
      txt = c.create_text(8, 42, anchor='nw', width=150, fill=DARK, font=('Arial', 8, 'bold'),
                          text=self.full[:self.shown], tags='bub')
      x0, y0, x1, y1 = c.bbox(txt)
      box = c.create_rectangle(x0 - 8, y0 - 6, x1 + 8, y1 + 6, fill=WHITE, outline=DARK, width=2, tags='bub')
      tail = c.create_polygon(x1 - 8, y0 + 4, x1 + 8, y0 + 14, x1 - 8, y0 + 20, fill=WHITE, outline=DARK, width=2, tags='bub')
      c.tag_lower(tail, txt)
      c.tag_lower(box, txt)

  # ---- animation ----
  def tick(self):
    dt = .033
    self.t += dt
    self.v += (-3.9 * self.a - .55 * self.v + .10 * math.sin(self.t * 2 * math.pi / 3.2)) * dt
    self.a = max(-.27, min(.27, self.a + self.v * dt))
    if self.blink > 0:
      self.blink -= 1
    elif random.random() < .012:
      self.blink = 5
    if self.shock > 0:
      self.shock -= 1
    look = (self.winfo_pointerx() - (self.winfo_x() + PX)) / 300
    self.yaw += (max(-1, min(1, look)) - self.yaw) * .08
    out = render(self.sp, self.a, self.v, self.t, self.blink, self.shock, self.yaw)
    self.draw_fx(out)
    if self.sysname == 'Darwin':
      img = out
    else:
      img = Image.alpha_composite(Image.new('RGBA', (WW, WH), KEY), out).convert('RGB')
    self.photo = ImageTk.PhotoImage(img)
    self.cv.itemconfig(self.item, image=self.photo)
    if self.bub > 0:
      self.bub -= 1
      self.shown = min(self.shown + 2, len(self.full))
    self.draw_ui()
    self.after(30, self.tick)

  def draw_fx(self, out):
    if not self.zip and not self.particles:
      return
    ov = Image.new('RGBA', (WW * 2, WH * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    z = self.zip
    if z:
      z['f'] += 1
      f = z['f']
      p = min(f / 7, 1) if f < 26 else max(1 - (f - 26) / 8, 0)
      hx, hy = rot_pt(54, 263, math.degrees(self.a))
      tx, ty = hx + (z['tx'] - hx) * p, hy + (z['ty'] - hy) * p
      mx, my = (hx + tx) / 2, (hy + ty) / 2 + 18 * p
      pts = [((1 - u) ** 2 * hx + 2 * u * (1 - u) * mx + u * u * tx,
              (1 - u) ** 2 * hy + 2 * u * (1 - u) * my + u * u * ty) for u in [i / 16 for i in range(17)]]
      d.line([(x * 2, y * 2) for x, y in pts], fill='#f4f7ff', width=4, joint='curve')
      if p >= 1:                       # web splat at the target
        for i in range(8):
          a0 = i * math.pi / 4
          d.line([(z['tx'] * 2, z['ty'] * 2), ((z['tx'] + 18 * math.cos(a0)) * 2, (z['ty'] + 18 * math.sin(a0)) * 2)], fill='#f4f7ff', width=3)
        d.ellipse([(z['tx'] - 10) * 2, (z['ty'] - 10) * 2, (z['tx'] + 10) * 2, (z['ty'] + 10) * 2], outline='#f4f7ff', width=3)
      if f == 7:
        self.v += 2.6 * (1 if z['tx'] > PX else -1)
      if f > 34:
        self.zip = None
    for q in self.particles[:]:
      q[0] += q[2]; q[1] += q[3]; q[3] += .2; q[4] -= 1
      if q[4] <= 0:
        self.particles.remove(q)
        continue
      d.ellipse([(q[0] - 3) * 2, (q[1] - 3) * 2, (q[0] + 3) * 2, (q[1] + 3) * 2], fill=q[5])
    out.alpha_composite(ov.resize((WW, WH), Image.BOX))

  def burst(self, x, y, colors, n=40):
    for _ in range(n):
      a, s = random.random() * 6.28, random.random() * 6 + 1
      self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s - 3, random.randint(25, 55), random.choice(colors)])

  # ---- actions ----
  def poke(self):
    self.shock = 28
    self.v += random.choice((-1, 1)) * 1.6
    self.say(random.choice(["Whoa! Spidey-sense!", "Hey, I'm working here!", "Thwip! Careful!"]))

  def web_zip(self):
    if not self.zip:
      self.zip = {'tx': random.choice((random.randint(10, 70), random.randint(270, 330))),
                  'ty': random.randint(60, 240), 'f': 0}
      self.say("Thwip!", 70)

  def log_mood(self, mood):
    db('INSERT INTO mood_logs (timestamp, mood) VALUES (?, ?)', (now(), mood))
    if mood == 'Great':
      self.burst(PX, 242, ['#ffd166', '#06d6a0', '#ef476f', '#4cc9f0'], 55)
      self.v += 1.8
      self.say(random.choice(PRAISE))
    elif mood == 'Struggling':
      self.shock = 45
      self.say(random.choice(HELP), 300)
    else:
      self.say("Steady wins the race. Keep swinging!")
    self.refresh_xp()

  def refresh_xp(self, announce=True):
    m = db('SELECT COUNT(*) FROM mood_logs', fetch=True)[0][0]
    d = db('SELECT COUNT(*) FROM missions WHERE done=1', fetch=True)[0][0]
    p = db('SELECT COUNT(*) FROM pomodoros', fetch=True)[0][0]
    self.xp = m * 10 + d * 25 + p * 30
    lvl = self.xp // 100 + 1
    if announce and lvl > self.level:
      self.burst(PX, 242, ['#ffd166', '#ffffff', '#ef476f'], 70)
      self.say(f"LEVEL UP! You're now Hero Level {lvl}!")
    self.level = lvl

  def auto_quote(self):
    if not self.running:
      self.say(random.choice(QUOTES))
    self.after(20000, self.auto_quote)

  def remind(self):
    self.say(random.choice(REMINDERS), 300)
    self.v += 1.2
    self.after(30 * 60 * 1000, self.remind)

  # ---- pomodoro ----
  def toggle_pomo(self):
    if self.running:
      self.running = False
      if self.job:
        self.after_cancel(self.job)
      self.say("Timer stopped. No shame, hero.")
    else:
      self.running, self.remaining = True, 25 * 60
      self.say("Focus mode! 25 minutes. I'll keep watch.")
      self.job = self.after(1000, self.pomo_tick)

  def pomo_tick(self):
    self.remaining -= 1
    if self.remaining <= 0:
      self.running = False
      db('INSERT INTO pomodoros (timestamp) VALUES (?)', (now(),))
      self.burst(PX, 242, ['#ffd166', '#06d6a0', '#ef476f'], 70)
      self.v += 2
      self.say("Focus session complete! +30 XP. Take a break!", 400)
      self.refresh_xp()
      return
    self.job = self.after(1000, self.pomo_tick)

  # ---- extra windows ----
  def toplevel(self, title):
    win = tk.Toplevel(self)
    win.title(title)
    win.configure(bg='#16213e')
    win.attributes('-topmost', True)
    return win

  def button(self, parent, text, cmd, bg):
    tk.Button(parent, text=text, command=cmd, bg=bg, fg='white', bd=0, padx=8, pady=4).pack(side=tk.LEFT, padx=3)

  def open_missions(self):
    win = self.toplevel('Missions')
    lb = tk.Listbox(win, width=38, height=10, bg=DARK, fg='white', bd=0, selectbackground=RED, font=('Arial', 10))
    lb.pack(padx=10, pady=10)
    ent = tk.Entry(win, bg=DARK, fg='white', insertbackground='white', bd=0)
    ent.pack(fill=tk.X, padx=10)
    ids = []

    def load():
      lb.delete(0, 'end')
      ids.clear()
      for i, t, d in db('SELECT id,title,done FROM missions ORDER BY done,id', fetch=True):
        ids.append(i)
        lb.insert('end', ('✔ ' if d else '☐ ') + t)

    def add(e=None):
      t = ent.get().strip()
      if t:
        db('INSERT INTO missions (title) VALUES (?)', (t,))
        ent.delete(0, 'end')
        load()

    def toggle(e=None):
      s = lb.curselection()
      if s:
        db('UPDATE missions SET done=1-done WHERE id=?', (ids[s[0]],))
        load()
        self.refresh_xp()
        self.say("Mission updated! Justice never sleeps.")

    def delete():
      s = lb.curselection()
      if s:
        db('DELETE FROM missions WHERE id=?', (ids[s[0]],))
        load()
        self.refresh_xp(announce=False)

    ent.bind('<Return>', add)
    lb.bind('<Double-Button-1>', toggle)
    bar = tk.Frame(win, bg='#16213e')
    bar.pack(pady=8)
    self.button(bar, 'Add', add, '#0f3460')
    self.button(bar, 'Done / Undo', toggle, '#0a7d5a')
    self.button(bar, 'Delete', delete, '#a02040')
    load()

  def open_stats(self):
    win = self.toplevel('Hero Stats')
    cv = tk.Canvas(win, width=340, height=230, bg=DARK, highlightthickness=0)
    cv.pack(padx=10, pady=10)
    days = [datetime.date.today() - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    data = {(d, m): n for d, m, n in db('SELECT substr(timestamp,1,10), mood, COUNT(*) FROM mood_logs GROUP BY 1,2', fetch=True)}
    colors = {'Great': '#06d6a0', 'Okay': '#ffd166', 'Struggling': '#ef476f'}
    mx = max([sum(data.get((str(d), m), 0) for m in colors) for d in days] + [1])
    cv.create_text(170, 14, text='Mood Log - Last 7 Days', fill='white', font=('Arial', 10, 'bold'))
    for i, d in enumerate(days):
      x, y = 20 + i * 45, 190
      for m, col in colors.items():
        h = data.get((str(d), m), 0) / mx * 140
        cv.create_rectangle(x, y - h, x + 30, y, fill=col, width=0)
        y -= h
      cv.create_text(x + 15, 205, text=d.strftime('%d/%m'), fill='#9aa5c4', font=('Arial', 8))
    poms = db('SELECT COUNT(*) FROM pomodoros WHERE substr(timestamp,1,10)=?', (str(datetime.date.today()),), fetch=True)[0][0]
    tk.Label(win, text=f'Level {self.level}  |  {self.xp} XP  |  {poms} focus sessions today',
             bg='#16213e', fg='white', font=('Arial', 9, 'bold')).pack(pady=(0, 10))


if __name__ == '__main__':
  SpideyCompanion().mainloop()

