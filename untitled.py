# -*- coding: utf-8 -*-
"""
PsychoPy script (auto white count + controllable phase spread):
- num_targets is even; num_white_dots = (num_targets // 2) - 1 (one pair for green dot).
- All white dots start from the left-side target when phase_spread=0.
- A single parameter `phase_spread` in [0..1] controls their relative phase difference:
    * 0.0 -> all in sync (same phase; left-start preserved)
    * 1.0 -> evenly spaced by ~1 / num_white_dots in phase
- Green dot = mouse; green pair is marked.
- Beep (1000 Hz, 200 ms) on overlap if audio backend (PTB/pyo) available.
- No 'psychopy-sounddevice' plugin required.
"""
from psychopy import prefs
prefs.hardware['audioLib'] = ['ptb', 'pyo']

from psychopy import visual, event, core
import numpy as np
import math

try:
    from psychopy import sound
    _sound_ok = True
except Exception as e:
    print("[Audio] psychopy.sound import failed:", e)
    sound = None
    _sound_ok = False

# -------------------- Parameters --------------------
win_size = [1000, 800]
bg_color = [-1, -1, -1]
units = "pix"

num_targets = 20                # number of targets (must be even)
num_pairs = num_targets // 2
num_white_dots = num_pairs - 1  # reserve one pair for the green dot

# Phase control: 0.0 -> all same phase; 1.0 -> evenly spaced by 1/num_white_dots
phase_spread = 1.0

ring_radius = 250
target_radius = 16
white_dot_radius = 8
green_radius = 10

ellipse_b_scale = 0.35
speed_uniform = 0.15
overlap_thresh = 36

outline_color = [1, 1, 1]
fill_color = [1, 1, 1]
target_outline_black = [-1, -1, -1]
green_color = [-0.2, 1.0, -0.2]

# -------------------- Window & Mouse --------------------
win = visual.Window(win_size, color=bg_color, units=units)
mouse = event.Mouse(visible=True, win=win)

# -------------------- Sound --------------------
beep = None
if _sound_ok:
    try:
        beep = sound.Sound(value=1000, secs=0.2, stereo=True, hamming=True)
        beep.setVolume(1.0)
        print("[Audio] Using backend:", sound.audioLib)
    except Exception as e:
        print("[Audio] Failed to create beep sound:", e)
        beep = None

# -------------------- Build targets --------------------
targets = []
angles = np.linspace(0, 2*np.pi, num_targets, endpoint=False)
for ang in angles:
    x = ring_radius * math.cos(ang)
    y = ring_radius * math.sin(ang)
    circ = visual.Circle(
        win=win,
        radius=target_radius,
        lineColor=target_outline_black,
        lineWidth=2,
        fillColor=fill_color,
        pos=(x, y),
        edges=64
    )
    targets.append(circ)

# -------------------- Opposite pairs --------------------
green_pair_index = 0  # pair for green dot
# Choose the first num_white_dots pairs (excluding the green one) for white dots
available_pairs = [i for i in range(num_pairs) if i != green_pair_index]
white_pair_indices = available_pairs[:num_white_dots]

a = ring_radius
b = a * float(ellipse_b_scale)

# -------------------- White shuttle dots --------------------
white_shuttles = []   # (dot, theta)
white_speeds = []     # uniform speeds
base_phases = []      # phase that places the dot at the left-side target
for i in white_pair_indices:
    theta = angles[i]
    dot = visual.Circle(
        win=win,
        radius=white_dot_radius,
        lineColor=outline_color,
        fillColor=fill_color,
        lineWidth=1.5,
        edges=32
    )
    white_shuttles.append((dot, theta))
    white_speeds.append(speed_uniform)

    # Determine left-side start for this pair: use 0.0 if the target at 'theta' is left (x<0), otherwise 0.5
    base_phases.append(0.0 if math.cos(theta) < 0 else 0.5)

# Build final phase offsets with a single 'phase_spread' parameter
# gap = phase_spread * (1/num_white_dots); offsets accumulate across dots
nwd = max(1, len(white_shuttles))
gap = phase_spread * (1.0 / nwd)
phase_offsets = [ (base_phases[j] + j * gap) % 1.0 for j in range(nwd) ]

# -------------------- Green dot and pair markers --------------------
green_dot = visual.Circle(
    win=win,
    radius=green_radius,
    lineColor=green_color,
    fillColor=green_color,
    lineWidth=0,
    pos=(0, 0),
    edges=32
)

idx_a = green_pair_index
idx_b = (green_pair_index + num_pairs) % num_targets
ang_a = angles[idx_a]
ang_b = angles[idx_b]
green_pair_pos_a = (ring_radius * math.cos(ang_a), ring_radius * math.sin(ang_a))
green_pair_pos_b = (ring_radius * math.cos(ang_b), ring_radius * math.sin(ang_b))

green_marker_radius = 5
green_marker_a = visual.Circle(win=win, radius=green_marker_radius,
    lineColor=green_color, fillColor=green_color, pos=green_pair_pos_a)
green_marker_b = visual.Circle(win=win, radius=green_marker_radius,
    lineColor=green_color, fillColor=green_color, pos=green_pair_pos_b)

# -------------------- Helpers --------------------
clock = core.Clock()
last_beep_time = -1.0

def ellipse_position(phase, theta, a, b):
    t = 2 * np.pi * phase
    ex = a * np.cos(t)
    ey = b * np.sin(t)
    c, s = np.cos(theta), np.sin(theta)
    x = ex * c - ey * s
    y = ex * s + ey * c
    return (x, y)

def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

# -------------------- Main Loop --------------------
running = True
while running:
    if event.getKeys(keyList=["escape", "esc"]):
        running = False
        break

    for tgt in targets:
        tgt.draw()

    green_marker_a.draw()
    green_marker_b.draw()

    t = clock.getTime()
    for i, (dot, theta) in enumerate(white_shuttles):
        phase = (t * white_speeds[i] + phase_offsets[i]) % 1.0
        pos = ellipse_position(phase, theta, a, b)
        dot.pos = pos
        dot.draw()

    mpos = mouse.getPos()
    green_dot.pos = mpos
    green_dot.draw()

    overlap = any(distance(dot.pos, green_dot.pos) < overlap_thresh for dot, _ in white_shuttles)
    now = clock.getTime()
    if beep is not None and overlap and (now - last_beep_time >= 0.22):
        beep.play()
        last_beep_time = now

    win.flip()

win.close()
core.quit()
