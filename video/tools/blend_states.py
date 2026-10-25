"""Fades between the four rendered series and writes video/frames/blended/.

s0 = scan only, s1 = + bezel, s2 = + shell, s3 = + stand (see video/fusion_scripts/RPi5Render).
The fade windows must match the ones in the Fusion script. Requires ffmpeg (winget install Gyan.FFmpeg).
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES_DIR = os.path.join(ROOT, "frames", sys.argv[1] if len(sys.argv) > 1 else "")
FF_DIR = os.path.join(ROOT, "frames")
OUT = os.path.join(FF_DIR, "blended")
FF = "ffmpeg"
FRAMES = 144
FIRST_IN = (0.06, 0.30)    # bezel
SECOND_IN = (0.32, 0.56)   # shell
THIRD_IN = (0.58, 0.82)    # stand
ALL_OUT = (0.88, 0.99)
# The video starts where the first part begins to appear; the frames before it go to the end, so the loop is seamless.
START = int(FIRST_IN[0] * FRAMES)


def smooth(a, b, t):
    x = min(1.0, max(0.0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)


def frame(state, i):
    return os.path.join(FRAMES_DIR, "s%d" % state, "frame_%04d.png" % i)


def mix(i):
    """Returns [(state, weight), ...] for frame i."""
    t = i / FRAMES
    if t >= ALL_OUT[0]:
        w = smooth(*ALL_OUT, t)
        return [(3, 1 - w), (0, w)]
    level = smooth(*FIRST_IN, t) + smooth(*SECOND_IN, t) + smooth(*THIRD_IN, t)
    k = min(int(level), 2)
    f = level - k
    return [(k, 1 - f), (k + 1, f)]


shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
missing = []
for n in range(FRAMES):
    i = (n + START) % FRAMES
    parts = [(s, w) for s, w in mix(i) if w > 0.001]
    if len(parts) == 2 and parts[1][1] > 0.999:
        parts = [parts[1]]
    if len(parts) == 2 and parts[0][1] > 0.999:
        parts = [parts[0]]
    for s, _ in parts:
        if not os.path.exists(frame(s, i)):
            missing.append((s, i))
    if any(not os.path.exists(frame(s, i)) for s, _ in parts):
        continue
    dst = os.path.join(OUT, "frame_%04d.png" % n)
    if len(parts) == 1:
        shutil.copy(frame(parts[0][0], i), dst)
    else:
        (a, wa), (b, wb) = parts
        expr = "A*%.4f+B*%.4f" % (wa, wb)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", frame(a, i), "-i", frame(b, i), "-filter_complex",
                        "[0][1]blend=all_expr='%s'" % expr, "-frames:v", "1", dst], check=True)
if missing:
    print("Missing frames (state, index):", missing[:20], "... total", len(missing))
else:
    print("Blended frames in %s: now run slowmo.py" % OUT)
