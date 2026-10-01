#!/usr/bin/env python3
"""Repair pass for the SBC Sustainability SG Demo Day teaser (v6 -> v7).

The original HTML/canvas source was not available, so the fixes are applied
to the rendered v6 frames:

  1. Word changes (1.25 / 1.88 / 2.5 / 3.13 / 3.75 s): the outgoing word used
     to vanish in a single frame (hard pop, empty screen). It now floats up and
     fades out over 0.2 s while the next word rises in.
  2. Skyline -> leaf wipe (~12.0 s): the old wipe crossed the screen in ~6
     frames and revealed the light scene as a hard rectangle ahead of the
     arrow. Rebuilt as the official double-chevron (exact brand geometry,
     proportions untouched) rising over 0.9 s with ease-in-out and motion
     blur; the reveal follows the arrow's outer edge.
  3. Boats/wakes sailing through the "SUSTAINABILITY" tagline are removed
     inside the tagline area (feathered), so the program name stays clean.

Usage: python3 fix_video.py v6.mp4 audio.wav out.mp4
"""
import subprocess
import sys

import numpy as np
from scipy import ndimage

W, H, FPS, N = 1920, 1080, 60, 1200
FRAME_BYTES = W * H * 3

# ---- 1. word exits --------------------------------------------------------
# 0-based index of the first frame where the previous word is gone.
WORD_CUTS = [75, 113, 150, 188, 225]
EXIT_FRAMES = 12          # 0.2 s
EXIT_RISE = 42.0          # px the old word floats up while fading
TEXT_ROWS = (150, 900)    # keep the progress ticks at the bottom out of the matte

# ---- 2. wipe --------------------------------------------------------------
WIPE_START, WIPE_END = 690, 744      # output frames rebuilt (0.9 s)
A_LAST = 718                          # last clean skyline frame in v6
B_HOLD = 737                          # light scene is static 737..743 in v6
ARROW_W = 2400.0                      # oversized official arrow, px wide
OUTER = [(0, 349), (337, 0), (674, 349), (591, 349), (337, 84), (83, 349)]
INNER = [(163, 349), (337, 168), (511, 349), (430, 349), (337, 252), (245, 349)]
SUBSTEPS = 12                         # motion-blur samples per frame

# ---- 3. tagline clean-up --------------------------------------------------
TAG_FROM = 432                        # tagline fully settled
TAG_BOX = (480, 698, 1430, 802)       # x0, y0, x1, y1
TAG_FEATHER = 40


def read_frames(path):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(FRAME_BYTES)
        if len(b) < FRAME_BYTES:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()


def smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def ease_in_out_sine(t):
    t = min(max(t, 0.0), 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * t)


# ---------------------------------------------------------------------------
def word_matte(prev, cur):
    """Alpha of the white word present in `prev` but gone in `cur`."""
    r0 = prev[..., 0].astype(np.float32)
    r1 = cur[..., 0].astype(np.float32)
    a = np.clip((r0 - r1) / np.maximum(255.0 - r1, 1.0), 0, 1)
    a[:TEXT_ROWS[0]] = 0
    a[TEXT_ROWS[1]:] = 0
    core = ndimage.binary_dilation(a > 0.5, iterations=4)
    a *= core
    return a


def apply_exit(frame, matte, k):
    t = (k + 1) / (EXIT_FRAMES + 1)
    fade = (1 - smoothstep(t)) ** 1.5
    dy = -EXIT_RISE * (1 - (1 - t) ** 3)
    a = ndimage.shift(matte, (dy, 0), order=1, mode='constant') * fade
    f = frame.astype(np.float32)
    out = f * (1 - a[..., None]) + 255.0 * a[..., None]
    return out


# ---------------------------------------------------------------------------
_X, _Y = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)


def poly_mask(pts, scale, ox, oy):
    """Polygon coverage (even-odd test); anti-aliasing comes from the
    motion-blur sub-steps."""
    X, Y = _X, _Y
    P = [(ox + x * scale, oy + y * scale) for x, y in pts]
    inside = np.zeros(X.shape, bool)
    n = len(P)
    for i in range(n):
        x1, y1 = P[i]
        x2, y2 = P[(i + 1) % n]
        if y1 == y2:
            continue
        cond = (y1 > Y) != (y2 > Y)
        xint = x1 + (Y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= cond & (X < xint)
    return inside.astype(np.float32)


def reveal_mask(scale, ox, oy):
    """Everything below the outer chevron's top edge (the wipe front)."""
    u = (_X - ox) / scale                      # arrow units
    top = np.abs(u - 337.0) * (349.0 / 337.0)  # outer edge, y below tip
    return ((_Y - oy) / scale >= top).astype(np.float32)


def wipe_layers(tip_y):
    scale = ARROW_W / 674.0
    ox = W / 2 - 337.0 * scale
    rev = reveal_mask(scale, ox, tip_y)
    band = np.maximum(poly_mask(OUTER, scale, ox, tip_y),
                      poly_mask(INNER, scale, ox, tip_y))
    return rev, band


def wipe_frame(j, A, B):
    n = WIPE_END - WIPE_START
    scale = ARROW_W / 674.0
    y_start = H + 4.0                  # tip just below the frame
    # finish once the outer band has cleared the top corners
    u_corner = 337.0 - (W / 2) / scale
    y_end = -((337.0 - u_corner) * (349.0 / 337.0) + 84.0) * scale - 4.0
    rev = np.zeros((H, W), np.float32)
    band = np.zeros((H, W), np.float32)
    for s in range(SUBSTEPS):
        t = (j + (s + 0.5) / SUBSTEPS - 0.5) / n
        p = ease_in_out_sine(t)
        r, b = wipe_layers(y_start + (y_end - y_start) * p)
        rev += r
        band += b
    rev /= SUBSTEPS
    band /= SUBSTEPS
    band *= 1 - smoothstep((j / n - 0.7) / 0.3)   # trailing chevron fades out
    out = A * (1 - rev[..., None]) + B * rev[..., None]
    out = out * (1 - band[..., None]) + 255.0 * band[..., None]
    return out


def skyline_at(j, frames):
    """Decelerating time-remap of the last clean skyline frames."""
    n = WIPE_END - WIPE_START
    s = 1 - (1 - j / n) ** 2
    pos = WIPE_START + (A_LAST - WIPE_START) * s
    i0 = int(np.floor(pos))
    i1 = min(i0 + 1, A_LAST)
    w = pos - i0
    return frames[i0].astype(np.float32) * (1 - w) + frames[i1].astype(np.float32) * w


# ---------------------------------------------------------------------------
def tag_weight():
    x0, y0, x1, y1 = TAG_BOX
    w = np.zeros((H, W), np.float32)
    w[y0:y1, x0:x1] = 1
    xs = np.arange(W, dtype=np.float32)
    ramp = np.clip(np.minimum(xs - x0, x1 - xs) / TAG_FEATHER, 0, 1)
    w *= ramp[None, :]
    return ndimage.gaussian_filter(w, (2, 0))


def clean_tagline(frame, plate, weight, strength):
    x0, y0, x1, y1 = TAG_BOX
    sl = (slice(y0 - 4, y1 + 4), slice(x0, x1))
    f = frame[sl].astype(np.float32)
    p = plate
    bright = f.mean(-1) - p.mean(-1)
    m = ndimage.binary_dilation(bright > 38, iterations=3).astype(np.float32)
    m = ndimage.gaussian_filter(m, 1.2) * weight[sl] * strength
    out = frame.astype(np.float32)
    out[sl] = f * (1 - m[..., None]) + p * m[..., None]
    return out


# ---------------------------------------------------------------------------
def main(src, audio, dst):
    print('pass 1: gathering reference frames')
    keep = set()
    for c in WORD_CUTS:
        keep |= {c - 1, c}
    keep |= set(range(WIPE_START, A_LAST + 1)) | {B_HOLD}
    keep_frames = {}
    x0, y0, x1, y1 = TAG_BOX
    tag_stack = []
    for i, fr in enumerate(read_frames(src)):
        if i in keep:
            keep_frames[i] = fr.copy()
        if TAG_FROM <= i <= A_LAST and i % 3 == 0:
            tag_stack.append(fr[y0 - 4:y1 + 4, x0:x1].copy())
    plate = np.median(np.stack(tag_stack), 0).astype(np.float32)
    mattes = {c: word_matte(keep_frames[c - 1], keep_frames[c]) for c in WORD_CUTS}
    weight = tag_weight()
    B = keep_frames[B_HOLD].astype(np.float32)

    print('pass 2: rendering')
    enc = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
        '-i', audio,
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '14', '-pix_fmt', 'yuv420p',
        '-profile:v', 'high', '-movflags', '+faststart',
        '-c:a', 'aac', '-b:a', '320k', '-ar', '48000',
        '-shortest', dst], stdin=subprocess.PIPE)
    for i, fr in enumerate(read_frames(src)):
        out = fr
        for c in WORD_CUTS:
            if c <= i < c + EXIT_FRAMES:
                out = apply_exit(out, mattes[c], i - c)
        if TAG_FROM <= i < WIPE_END:
            strength = smoothstep((i - TAG_FROM) / 12.0)
            out = clean_tagline(out, plate, weight, strength)
        if WIPE_START <= i < WIPE_END:
            j = i - WIPE_START
            A = skyline_at(j, keep_frames)
            A = clean_tagline(A, plate, weight, 1.0)
            out = wipe_frame(j, A, B)
        enc.stdin.write(np.clip(np.asarray(out) + 0.5, 0, 255).astype(np.uint8).tobytes())
        if i % 100 == 0:
            print(' frame', i)
    enc.stdin.close()
    enc.wait()


if __name__ == '__main__':
    main(*sys.argv[1:4])
