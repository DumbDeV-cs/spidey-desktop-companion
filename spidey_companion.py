"""Desk Spidey v4: tiny pixel-art hero hanging upside down in a web corner.
Requires: pip install pillow
Controls: click = swing, double-click = thwip, right-click = menu, drag = move.
"""
import math
import random
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk

W, H = 236, 194
BG = '#050810'
RED, BLUE, INK, WHITE = '#ed1826', '#1454c5', '#10121b', '#fff8e8'


def make_spidey():
    """Draw at a tiny native resolution, then enlarge with nearest-neighbour."""
    im = Image.new('RGBA', (24, 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # Limbs fan up and out: bent legs above the torso, arms spread below it.
    # Black pixel outlines first, then suit colors inset by one pixel.
    shapes = [
        ([(8, 13), (6, 9), (3, 7), (2, 5)], INK),
        ([(15, 13), (17, 9), (20, 7), (21, 5)], INK),
        ([(8, 17), (5, 18), (3, 21), (1, 22)], INK),
        ([(15, 17), (18, 18), (20, 21), (22, 22)], INK),
    ]
    for pts, col in shapes:
        d.line(pts, fill=col, width=4, joint='curve')
    for pts, col in [
        ([(8, 13), (6, 9), (3, 7), (2, 5)], RED),
        ([(15, 13), (17, 9), (20, 7), (21, 5)], RED),
        ([(8, 17), (5, 18), (3, 21), (1, 22)], BLUE),
        ([(15, 17), (18, 18), (20, 21), (22, 22)], BLUE),
    ]:
        d.line(pts, fill=col, width=2, joint='curve')
    # Boots and gloves, deliberately squared off like a game sprite.
    for x, y in [(1, 3), (20, 3), (0, 21), (21, 21)]:
        d.rectangle((x, y, x + 2, y + 2), fill=INK)
        d.rectangle((x + 1, y, x + 2, y + 1), fill=RED if y < 10 else BLUE)
    # Compact torso with classic red chest / blue abdomen split.
    d.rectangle((7, 11, 16, 21), fill=INK)
    d.rectangle((8, 12, 15, 16), fill=RED)
    d.rectangle((8, 17, 15, 20), fill=BLUE)
    d.rectangle((10, 16, 13, 18), fill=INK)
    # Head hangs down; broad white eyes and black stepped outlines.
    d.rectangle((8, 20, 15, 28), fill=INK)
    d.rectangle((9, 21, 14, 27), fill=RED)
    d.polygon([(9, 23), (11, 22), (12, 24), (11, 26), (9, 25)], fill=INK)
    d.polygon([(14, 23), (12, 22), (11, 24), (12, 26), (14, 25)], fill=INK)
    d.polygon([(10, 23), (11, 23), (11, 25), (10, 25)], fill=WHITE)
    d.polygon([(13, 23), (12, 23), (12, 25), (13, 25)], fill=WHITE)
    # Tiny chest spider emblem.
    d.rectangle((11, 13, 12, 15), fill=INK)
    d.point((10, 13), fill=INK); d.point((13, 13), fill=INK)
    # A few clean pixel highlights.
    d.point((9, 12), fill='#ff6970'); d.point((14, 12), fill='#ff6970')
    return im.resize((96, 120), Image.Resampling.NEAREST)


class DeskSpidey(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Desk Spidey')
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-transparentcolor', BG)
        self.configure(bg=BG)
        self.geometry(f'{W}x{H}+{max(0, self.winfo_screenwidth()-W)}+0')
        self.cv = tk.Canvas(self, width=W, height=H, bg=BG, bd=0, highlightthickness=0)
        self.cv.pack()
        self.sprite = make_spidey()
        self.photo = None
        self.t = 0.0
        self.swing = 0.0
        self.speed = 0.0
        self.blink = 0
        self.message = 'Hey! Your friendly neighborhood focus buddy is here.'
        self.message_until = 0
        self.focus_left = 0
        self.focus_job = None
        self.sessions = 0
        self.mood = 'Ready'
        self.missions = []
        self.particles = []
        self.drag = None
        self.cv.bind('<ButtonPress-1>', self.start_drag)
        self.cv.bind('<B1-Motion>', self.move_window)
        self.cv.bind('<ButtonRelease-1>', self.release_click)
        self.cv.bind('<Double-Button-1>', lambda e: self.thwip())
        self.cv.bind('<Button-3>', self.menu)
        self.cv.bind('<Button-2>', self.menu)
        self.after(80, self.auto_line)
        self.animate()

    def corner_web(self, d):
        # Fine silvery web strands and a bright knot at the top-right anchor.
        ax, ay = W - 7, 4
        d.ellipse((ax-31, ay-1, ax+1, ay+31), outline='#34465e', width=1)
        d.ellipse((ax-22, ay-1, ax+1, ay+22), outline='#42566e', width=1)
        d.ellipse((ax-13, ay-1, ax+1, ay+13), outline='#52677f', width=1)
        for deg in (90, 112, 135, 158, 180, 202, 225, 248, 270):
            a = math.radians(deg)
            x, y = ax + 31 * math.cos(a), ay + 31 * math.sin(a)
            d.line((ax, ay, x, y), fill='#71849a', width=1)
        d.ellipse((ax-2, ay-2, ax+2, ay+2), fill='#e9f2ff')

    def draw_hud(self):
        c = self.cv
        c.delete('hud')
        timer = f'{self.focus_left//60:02d}:{self.focus_left%60:02d}' if self.focus_left else '25:00'
        c.create_rectangle(8, 8, 98, 27, fill='#111b2c', outline='#415574', width=1, tags='hud')
        c.create_text(14, 17, anchor='w', fill='#f4f7ff', font=('Consolas', 8, 'bold'),
                      text=f'{self.mood}  {timer}', tags='hud')
        if self.message and self.t < self.message_until:
            text = self.message[:53]
            c.create_rectangle(9, 36, 145, 61, fill='#fff8e8', outline='#131722', width=2, tags='hud')
            c.create_text(15, 40, anchor='nw', width=124, fill='#151923',
                          font=('Arial', 8, 'bold'), text=text, tags='hud')
            c.create_polygon(129, 59, 140, 70, 135, 57, fill='#fff8e8', outline='#131722', tags='hud')
        c.create_text(10, H-10, anchor='w', fill='#abb8cb', font=('Arial', 7),
                      text=f'★ {self.sessions} focus sessions   •   {len(self.missions)} missions', tags='hud')

    def animate(self):
        self.t += .08
        self.speed *= .92
        self.swing = max(-.22, min(.22, self.swing + self.speed))
        self.speed += (-self.swing * .025) + .002 * math.sin(self.t * 1.4)
        frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(frame)
        self.corner_web(d)
        anchor = (W-9, 6)
        # A little web cluster fans down from the corner into the hanging point.
        hx, hy = 142 + int(math.sin(self.t)*3), 26
        d.line((anchor, (207, 13), (178, 18), (hx, hy)), fill='#d7e4f5', width=2)
        for i in range(4):
            d.line((anchor[0]-i*4, anchor[1]+i*3, anchor[0]-32-i*5, 27+i*4), fill='#6e8299', width=1)
        # Thread to the raised feet; character sways gently below the corner cluster.
        pivot = (hx, hy)
        rad = math.radians(math.sin(self.t)*2 + self.swing*55)
        foot = (pivot[0] + 10*math.sin(rad), pivot[1] + 15)
        d.line((pivot, foot), fill='#f1f5ff', width=2)
        rotated = self.sprite.rotate(math.degrees(rad), resample=Image.Resampling.NEAREST, expand=True)
        frame.alpha_composite(rotated, (int(pivot[0]-rotated.width/2), int(pivot[1])))
        # Floating pixel sparkles on thwip and completed focus sessions.
        alive = []
        for x, y, vy, life, color in self.particles:
            y += vy; life -= 1
            if life > 0:
                d.rectangle((x, y, x+2, y+2), fill=color)
                alive.append((x, y, vy, life, color))
        self.particles = alive
        self.photo = ImageTk.PhotoImage(frame)
        self.cv.delete('art')
        self.cv.create_image(0, 0, anchor='nw', image=self.photo, tags='art')
        self.cv.tag_lower('art')
        self.draw_hud()
        self.after(40, self.animate)

    def start_drag(self, e):
        self.drag = (e.x_root-self.winfo_x(), e.y_root-self.winfo_y(), e.x, e.y)

    def move_window(self, e):
        if self.drag:
            dx, dy, _, _ = self.drag
            self.geometry(f'+{e.x_root-dx}+{e.y_root-dy}')

    def release_click(self, e):
        if self.drag and abs(e.x-self.drag[2]) < 5 and abs(e.y-self.drag[3]) < 5:
            self.speed += random.choice((-0.09, 0.09))
            self.say(random.choice(['Wheee!', 'Web swing!', 'Nice and easy...']))
        self.drag = None

    def say(self, text, seconds=4):
        self.message = text
        self.message_until = self.t + seconds / .04

    def thwip(self):
        self.speed += random.choice((-0.18, 0.18))
        self.say('THWIP! Spidey-sense activated!')
        for _ in range(22):
            self.particles.append((random.randint(120, 190), random.randint(40, 120),
                                  random.uniform(-1.4, -.2), random.randint(18, 40),
                                  random.choice(['#fff0a6', '#ff5363', '#55b9ff'])))

    def auto_line(self):
        if random.random() < .45:
            self.say(random.choice(['One tiny task at a time, hero.', 'Web-slinging focus mode: ready!',
                                    'Stretch break? Even heroes need one.', 'Looking sharp, citizen!']), 5)
        self.after(45000, self.auto_line)

    def focus(self):
        if self.focus_left:
            self.focus_left = 0
            self.say('Focus timer paused. Take a breather.')
            return
        self.focus_left = 25 * 60
        self.say('25-minute focus session started. I have your back!', 6)
        self.countdown()

    def countdown(self):
        if not self.focus_left:
            return
        self.focus_left -= 1
        if self.focus_left <= 0:
            self.sessions += 1
            self.say('Focus complete! You did amazing. Take a short break!', 10)
            self.thwip()
            return
        self.after(1000, self.countdown)

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

    def set_mood(self, mood):
        self.mood = mood
        self.say({'Great':'You are crushing it! Keep going!', 'Okay':'Steady progress is progress.',
                  'Stuck':'Pause, breathe, then tackle one small piece.'}[mood])

    def menu(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label='🕸  Swing!', command=self.thwip)
        m.add_command(label='⏱  Start / pause 25-minute focus', command=self.focus)
        m.add_command(label='🎯  Add / view mission', command=self.show_missions)
        moods = tk.Menu(m, tearoff=0)
        for label in ('Great', 'Okay', 'Stuck'):
            moods.add_command(label=label, command=lambda v=label: self.set_mood(v))
        m.add_cascade(label='😊  Log mood', menu=moods)
        m.add_separator()
        m.add_command(label='Quit Desk Spidey', command=self.destroy)
        m.tk_popup(e.x_root, e.y_root)


if __name__ == '__main__':
    DeskSpidey().mainloop()

