#!/usr/bin/env python3
"""Whoosh + leaf-rustle SFX for the leaf swipe stinger, locked to the picture.

The green panel's edge positions are recomputed with the same easing as
stinger.html, so loudness and brightness follow the edge speed and the
stereo image pans left -> right with the swipe.

Output: whoosh.wav (48 kHz, 24-bit stereo, 3.05 s, peak -6 dBFS)
"""
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt, get_window

SR = 48000
T0, DUR = 0.27, 3.05           # must match stinger.html
T_EDGE = 1.80
W = 1920
X0, X1 = -560, W + 560
R_IN, L_OUT = 0.00, 1.62       # card leading / trailing edge
GROW_START, GROW_END = 0.95, 2.02   # logo leaves growing in
rng = np.random.default_rng(11)


def bezier(p1x, p1y, p2x, p2y):
    cx = 3 * p1x; bx = 3 * (p2x - p1x) - cx; ax = 1 - cx - bx
    cy = 3 * p1y; by = 3 * (p2y - p1y) - cy; ay = 1 - cy - by

    def f(x):
        x = np.clip(x, 0, 1)
        u = x.copy()
        for _ in range(8):
            sx = ((ax * u + bx) * u + cx) * u
            d = (3 * ax * u + 2 * bx) * u + cx
            u = np.clip(u - (sx - x) / np.where(np.abs(d) < 1e-6, 1e-6, d), 0, 1)
        return ((ay * u + by) * u + cy) * u
    return f


EASE = bezier(0.42, 0, 0.58, 1)
n = int(DUR * SR)
t = np.arange(n) / SR + T0


def edge(start):
    return X0 + (X1 - X0) * EASE((t - start) / T_EDGE)


def sweep(x):
    v = np.gradient(x) * SR                 # px / s
    return x, np.abs(v)


def fades(m, a, r):
    e = np.ones(m)
    e[:a] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    e[m - r:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return e


def swept_noise(speed, lo=250, hi=5200, blk=512):
    """Band-pass noise whose centre frequency tracks speed (overlap-add, no steps)."""
    out = np.zeros(n + 2 * blk)
    win = get_window('hann', 2 * blk)       # periodic Hann: 50% overlap sums to 1
    vmax = speed.max()
    for s in range(0, n, blk):
        k = speed[min(s + blk // 2, n - 1)] / vmax
        fc = lo * (hi / lo) ** k
        seg = rng.standard_normal(2 * blk + 2048)
        sos = butter(2, [fc / 1.6, min(fc * 1.6, 20000)], 'bandpass', fs=SR, output='sos')
        seg = sosfilt(sos, seg)[2048:]      # discard filter warm-up
        out[s:s + 2 * blk] += seg * win
    return out[:n]


def layer(x, speed, gain):
    """One whoosh: amplitude follows speed, equal-power pan follows edge x."""
    env = (speed / speed.max()) ** 1.3
    env = np.convolve(env, np.ones(480) / 480, 'same')
    body = swept_noise(speed)
    air = sosfilt(butter(2, 6000, 'highpass', fs=SR, output='sos'), rng.standard_normal(n)) * 0.25
    mono = (body + air * env) * env
    pan = np.clip(x / W, 0, 1)
    gl, gr = np.cos(pan * np.pi / 2), np.sin(pan * np.pi / 2)
    return np.stack([mono * gl, mono * gr]) * gain


def rustle(x, speed, count, gain):
    """Leaf rustle: short, smoothly enveloped grains, density follows speed."""
    out = np.zeros((2, n))
    p = (speed / speed.sum())
    idx = rng.choice(n, size=count, p=p)
    for i in idx:
        g = int(rng.uniform(0.006, 0.022) * SR)
        if i + g >= n:
            continue
        fc = rng.uniform(2200, 6500)
        sos = butter(2, [fc / 1.4, min(fc * 1.4, 20000)], 'bandpass', fs=SR, output='sos')
        grain = sosfilt(sos, rng.standard_normal(g + 512))[512:] * np.hanning(g)
        grain *= rng.uniform(0.3, 1.0) * (speed[i] / speed.max())
        pan = np.clip(x[i] / W + rng.uniform(-0.15, 0.15), 0, 1)
        out[0, i:i + g] += grain * np.cos(pan * np.pi / 2)
        out[1, i:i + g] += grain * np.sin(pan * np.pi / 2)
    return out * gain


xin, vin = sweep(edge(R_IN))
xout, vout = sweep(edge(L_OUT))
mix = layer(xin, vin, 1.0) + layer(xout, vout, 0.8)
mix += rustle(xin, vin, 420, 0.9) + rustle(xout, vout, 380, 0.75)
# soft rustle while the leaf arrow grows in (centred, bottom-up build)
grow = np.clip((t - GROW_START) / (GROW_END - GROW_START), 0, 1)
grow_rate = np.sin(np.pi * grow) * ((t > GROW_START) & (t < GROW_END))
mix += rustle(np.full(n, W / 2), grow_rate * 4000 + 1e-6, 260, 0.45)

for c in range(2):
    mix[c] = sosfilt(butter(2, 40, 'highpass', fs=SR, output='sos'), mix[c])
mix *= fades(n, int(0.003 * SR), int(0.03 * SR))
mix *= 10 ** (-6 / 20) / np.abs(mix).max()      # peak -6 dBFS: headroom for the AV mix

pcm = np.clip(mix.T * 8388607, -8388608, 8388607).astype(np.int32)
b = pcm.astype('<i4').tobytes()
b24 = b''.join(b[i:i + 3] for i in range(0, len(b), 4))
out = sys.argv[1] if len(sys.argv) > 1 else 'whoosh.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR)
    w.writeframes(b24)
print('wrote', out, 'peak -6 dBFS, rms %.1f dBFS' % (20 * np.log10(np.sqrt((mix ** 2).mean()))))
