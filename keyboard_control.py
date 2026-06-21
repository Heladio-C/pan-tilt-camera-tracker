from gpiozero import AngularServo
from time import time, sleep
import sys, tty, termios, select

# Pan  signal -> GPIO 17 (physical pin 11)
# Tilt signal -> GPIO 18 (physical pin 12)
pan = AngularServo(17, min_angle=-90, max_angle=90,
                   min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
tilt = AngularServo(18, min_angle=-90, max_angle=90,
                    min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

STEP = 8            # degrees per key press
LIMIT = 80          # don't push past +/- this many degrees
GLIDE_TIME = 0.18   # seconds to ease into each new position
GLIDE_STEPS = 12     # number of in-between micro-moves (higher = smoother)
IDLE_RELAX = 0.4    # seconds of stillness before servos go quiet

PAN_DIR = -1        # flip pan direction (was +1)
TILT_DIR = -1       # flip tilt direction (was +1)

pan_angle = 0.0
tilt_angle = 0.0
attached = False
last_move = 0.0

def clamp(v):
    return max(-LIMIT, min(LIMIT, v))

def glide_to(new_pan, new_tilt):
    """Ease smoothly from the current angles to the new ones."""
    global pan_angle, tilt_angle, attached, last_move
    start_p, start_t = pan_angle, tilt_angle
    for i in range(1, GLIDE_STEPS + 1):
        f = i / GLIDE_STEPS
        pan.angle = start_p + (new_pan - start_p) * f
        tilt.angle = start_t + (new_tilt - start_t) * f
        sleep(GLIDE_TIME / GLIDE_STEPS)
    pan_angle, tilt_angle = new_pan, new_tilt
    attached = True
    last_move = time()

def show():
    sys.stdout.write("\rPan: %+4.0f   Tilt: %+4.0f    "
                     "[arrows/WASD move, space=center, q=quit]   "
                     % (pan_angle, tilt_angle))
    sys.stdout.flush()

def read_key(timeout=0.05):
    dr, _, _ = select.select([sys.stdin], [], [], timeout)
    if not dr:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        seq = ""
        for _ in range(2):
            dr2, _, _ = select.select([sys.stdin], [], [], 0.001)
            if dr2:
                seq += sys.stdin.read(1)
        return {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT"}.get(seq)
    return ch.lower()

fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
try:
    tty.setcbreak(fd)
    print("Manual servo control. Move with arrow keys or WASD.\n")
    glide_to(0.0, 0.0)   # center to start
    show()
    while True:
        key = read_key()
        if key in ("UP", "w"):
            glide_to(pan_angle, clamp(tilt_angle + STEP * TILT_DIR)); show()
        elif key in ("DOWN", "s"):
            glide_to(pan_angle, clamp(tilt_angle - STEP * TILT_DIR)); show()
        elif key in ("LEFT", "a"):
            glide_to(clamp(pan_angle - STEP * PAN_DIR), tilt_angle); show()
        elif key in ("RIGHT", "d"):
            glide_to(clamp(pan_angle + STEP * PAN_DIR), tilt_angle); show()
        elif key in (" ", "c"):
            glide_to(0.0, 0.0); show()
        elif key == "q":
            break
        if attached and (time() - last_move) > IDLE_RELAX:
            pan.detach(); tilt.detach(); attached = False
except KeyboardInterrupt:
    pass
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
    pan.detach(); tilt.detach()
    print("\nStopped. Servos released.")
