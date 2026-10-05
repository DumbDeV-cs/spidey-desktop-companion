import datetime
import random
import sqlite3
import tkinter as tk
from tkinter import messagebox


# Initialize SQLite Database for Mood Tracking
def init_db():
  conn = sqlite3.connect('spidey_companion.db')
  cursor = conn.cursor()
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS mood_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            mood TEXT NOT NULL
        )
    ''')
  conn.commit()
  conn.close()


class SpideyCompanion(tk.Tk):

  def __init__(self):
    super().__init__()
    init_db()

    # Window configuration: borderless, always on top
    self.overrideredirect(True)
    self.attributes('-topmost', True)
    self.geometry('320x210+50+50')
    self.configure(bg='#1a1a2e')

    # Make the floating window draggable with the mouse
    self.bind('<ButtonPress-1>', self.start_move)
    self.bind('<B1-Motion>', self.do_move)

    # Spidey / Developer Quotes
    self.quotes = [
        "With great power comes great responsibility... like pushing your code today!",
        "Your friendly neighborhood bug-squasher is on watch!",
        "Remember: Even Spider-Man misses a web-sling sometimes. Keep debugging!",
        "Pizza Time? Not yet, finish that function first!",
        "Stuck on a bug? Step back and look at it from a different angle.",
    ]

    self.create_widgets()

  def start_move(self, event):
    self.x = event.x
    self.y = event.y

  def do_move(self, event):
    x = self.winfo_x() + (event.x - self.x)
    y = self.winfo_y() + (event.y - self.y)
    self.geometry(f'+{x}+{y}')

  def create_widgets(self):
    # Header / Title Bar
    header_frame = tk.Frame(self, bg='#16213e', height=30)
    header_frame.pack(fill=tk.X, side=tk.TOP)

    title_label = tk.Label(
        header_frame,
        text="🕷️ Desk-Spidey Companion",
        bg='#16213e',
        fg='white',
        font=('Arial', 10, 'bold'),
    )
    title_label.pack(side=tk.LEFT, padx=10, pady=5)

    close_btn = tk.Button(
        header_frame,
        text="✕",
        bg='#16213e',
        fg='white',
        bd=0,
        command=self.destroy,
        font=('Arial', 10, 'bold'),
    )
    close_btn.pack(side=tk.RIGHT, padx=10)

    # Quote Display
    self.quote_label = tk.Label(
        self,
        text=random.choice(self.quotes),
        bg='#1a1a2e',
        fg='#e94560',
        font=('Arial', 9, 'italic'),
        wraplength=290,
        justify='center',
    )
    self.quote_label.pack(pady=15, padx=15)

    # Mood Logger Buttons
    btn_frame = tk.Frame(self, bg='#1a1a2e')
    btn_frame.pack(pady=5)

    moods = [('🔥 Crushing It', 'Great'), ('💻 Stuck / Buggy', 'Struggling')]
    for text, val in moods:
      b = tk.Button(
          btn_frame,
          text=text,
          bg='#0f3460',
          fg='white',
          bd=0,
          padx=8,
          pady=5,
          command=lambda m=val: self.log_mood(m),
      )
      b.pack(side=tk.LEFT, padx=5)

    # New Quote Button
    refresh_btn = tk.Button(
        self,
        text="Get Spidey Wisdom",
        bg='#e94560',
        fg='white',
        bd=0,
        padx=10,
        pady=3,
        command=self.new_quote,
    )
    refresh_btn.pack(pady=8)

  def new_quote(self):
    self.quote_label.config(text=random.choice(self.quotes))

  def log_mood(self, mood):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('spidey_companion.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO mood_logs (timestamp, mood) VALUES (?, ?)',
        (timestamp, mood),
    )
    conn.commit()
    conn.close()
    messagebox.showinfo(
        "Logged!",
        f"Spidey logged your vibe as '{mood}' in SQLite. Keep up the grind!",
    )


if __name__ == '__main__':
  app = SpideyCompanion()
  app.mainloop()