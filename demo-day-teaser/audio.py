#!/usr/bin/env python3
"""Soundtrack for the SBC Sustainability SG Demo Day teaser (v7).

20 s, 96 BPM (beat = 0.625 s), A minor, 48 kHz stereo -> audio.wav

Rewritten from scratch for v7 to remove the v6 problems:
  * kick waveforms were flat-topped by the limiter (audible distortion)
  * constant broadband hiss from noise layers, and abrupt noise gating that
    showed up as momentary full-band drop-outs (choppy/"crackle")
  * hard start at sample 0

Design rules used here:
  * every oscillator is band-limited (additive, partials kept < 14 kHz), so
    there is no aliasing
  * every event has a raised-cosine fade in and out, so nothing starts or
    stops on a non-zero sample
  * noise is only used for short, enveloped percussion and smooth risers;
    there is no constant noise bed
  * mix headroom first, then a look-ahead peak limiter that only acts on
    rare peaks (no clipping, no flat tops)

Cue sheet (matches the picture):
  0.000 3 MONTHS   1.250 OF BUILDING.   1.875 TESTING.   2.500 PIVOTING.
  3.125 SCALING.   3.750 ALL FOR        4.0625 ONE STAGE.
  5.000 skyline lift     ~6.9 SINGAPORE lands
  11.5-12.4 arrow wipe   12.5 leaf scene   15.0 build
  16.5625 DEMO           16.875 DAY        19.375 final hit
"""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
import wave

SR = 48000
DUR = 20.0
N = int(SR * DUR)
B = 0.625              # one beat
S16 = B / 4
rng = np.random.default_rng(7)

L = np.zeros(N)
R = np.zeros(N)
# separate buses so the kick can duck the tonal parts and reverb is sent selectively
bus = {k: np.zeros((2, N)) for k in ('drums', 'bass', 'tonal', 'fx')}
send = np.zeros((2, N))   # reverb send


def note_hz(name):
    names = {'C': -9, 'C#': -8, 'D': -7, 'D#': -6, 'E': -5, 'F': -4, 'F#': -3,
             'G': -2, 'G#': -1, 'A': 0, 'A#': 1, 'B': 2}
    n, o = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (o - 4)) / 12)


CHORDS = {
    'Am': ['A3', 'C4', 'E4'], 'F': ['F3', 'A3', 'C4'], 'C': ['C4', 'E4', 'G4'],
    'G': ['G3', 'B3', 'D4'], 'E': ['E3', 'G#3', 'B3'], 'Dm': ['D4', 'F4', 'A4'],
}
ROOT = {'Am': 'A1', 'F': 'F1', 'C': 'C2', 'G': 'G1', 'E': 'E1', 'Dm': 'D2'}


def fades(n, a, r):
    """Envelope of ones with raised-cosine fade-in a and fade-out r samples."""
    e = np.ones(n)
    a = max(min(a, n // 2), 1)
    r = max(min(r, n - a), 1)
    e[:a] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    e[n - r:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, r))
    return e


def adsr(n, a, d, s, r):
    """Smooth attack/decay/sustain/release envelope over n samples."""
    t = np.arange(n) / SR
    e = np.where(t < a, 0.5 - 0.5 * np.cos(np.pi * np.clip(t / max(a, 1e-4), 0, 1)),
                 s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    return e * fades(n, 1, int(r * SR))


def saw(f, t, bright=1.0, maxf=14000.0):
    """Band-limited sawtooth (additive). bright<1 rolls off upper partials."""
    out = np.zeros_like(t)
    k_max = int(maxf / f)
    for k in range(1, max(k_max, 1) + 1):
        out += np.sin(2 * np.pi * k * f * t) / k * (bright ** (k - 1))
    return out * (2 / np.pi)


def place(dst_l, dst_r, x, t0, pan=0.0, gain=1.0):
    """Mix mono/stereo signal x at time t0 with equal-power pan."""
    i0 = int(round(t0 * SR))
    if x.ndim == 1:
        gl = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2)
        gr = np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
        xl, xr = x * gl, x * gr
    else:
        xl, xr = x[0], x[1]
    if i0 < 0:
        xl, xr = xl[-i0:], xr[-i0:]
        i0 = 0
    n = min(len(xl), N - i0)
    if n <= 0:
        return
    dst_l[i0:i0 + n] += xl[:n] * gain
    dst_r[i0:i0 + n] += xr[:n] * gain


def add(busname, x, t0, pan=0.0, gain=1.0, rev=0.0):
    b = bus[busname]
    place(b[0], b[1], x, t0, pan, gain)
    if rev:
        place(send[0], send[1], x, t0, pan, gain * rev)


def filt(x, kind, f, order=2):
    sos = butter(order, f, kind, fs=SR, output='sos')
    return sosfilt(sos, x)


# ---------------------------------------------------------------- instruments
def kick(big=False):
    n = int((0.55 if big else 0.38) * SR)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (0.30 if big else 0.18))
    click = filt(rng.standard_normal(n), 'bandpass', [1500, 5000]) * np.exp(-t / 0.004) * 0.12
    x = (body + click) * fades(n, 24, int(0.03 * SR))
    return x * 0.95


def clap():
    n = int(0.28 * SR)
    t = np.arange(n) / SR
    nz = filt(rng.standard_normal(n), 'bandpass', [900, 4500])
    env = np.zeros(n)
    for k, off in enumerate((0.0, 0.009, 0.018)):
        tt = np.clip(t - off, 0, None)
        ramp = 0.5 - 0.5 * np.cos(np.pi * np.clip(tt / 0.0005, 0, 1))
        env += np.where(t >= off, ramp * np.exp(-tt / (0.012 if k < 2 else 0.09)), 0)
    return nz * env * fades(n, 24, int(0.05 * SR)) * 0.30


def snare():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.5
    nz = filt(rng.standard_normal(n), 'bandpass', [1200, 7000]) * np.exp(-t / 0.07)
    return (tone + nz) * fades(n, 24, int(0.04 * SR)) * 0.32


def hat(open_=False):
    n = int((0.16 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    nz = filt(rng.standard_normal(n), 'highpass', 7500, 4)
    nz = filt(nz, 'lowpass', 14000, 2)
    return nz * np.exp(-t / (0.045 if open_ else 0.012)) * fades(n, 24, int(0.02 * SR)) * 0.10


def crash(length=1.6, gain=0.16):
    n = int(length * SR)
    t = np.arange(n) / SR
    nz = np.stack([filt(rng.standard_normal(n), 'highpass', 3500, 2) for _ in range(2)])
    nz = np.stack([filt(c, 'lowpass', 12000, 2) for c in nz])
    env = np.exp(-t / (length * 0.32)) * fades(n, 48, int(0.4 * SR))
    return nz * env * gain


def sub_boom(length=1.4):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.5)
    return x * fades(n, 48, int(0.3 * SR)) * 0.75


def bass_note(name, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = note_hz(name)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) \
        + 0.18 * saw(f * 2, t, bright=0.6, maxf=2500)
    x = np.tanh(1.3 * x) / np.tanh(1.3)
    return x * adsr(n, 0.004, 0.18, 0.55, 0.03) * 0.30


def stab(chord, length=0.5, gain=0.16):
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    notes = CHORDS[chord] + [CHORDS[chord][0][:-1] + str(int(CHORDS[chord][0][-1]) + 1)]
    for nm in notes:
        f = note_hz(nm)
        for side, det in ((0, -0.006), (1, 0.006)):
            out[side] += saw(f * (1 + det), t, bright=0.82, maxf=9000)
            out[side] += 0.6 * saw(f * (1 - det * 0.5), t + 0.0013 * side, bright=0.82, maxf=9000)
    env = adsr(n, 0.004, 0.13, 0.25, 0.12)
    return out * env * gain / len(notes)


def pad(chord, length, gain=0.07):
    n = int(length * SR)
    t = np.arange(n) / SR
    out = np.zeros((2, n))
    for nm in CHORDS[chord]:
        f = note_hz(nm)
        for side, det in ((0, -0.004), (1, 0.004)):
            out[side] += saw(f * (1 + det), t, bright=0.70, maxf=5000)
            out[side] += saw(f * (1 - det) / 2, t, bright=0.65, maxf=3000) * 0.5
    env = fades(n, int(0.12 * SR), int(0.12 * SR))
    return out * env * gain / len(CHORDS[chord])


def pluck(name, length=0.35, gain=0.10):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = note_hz(name)
    x = np.zeros(n)
    for k in range(1, 9):
        if k * f > 12000:
            break
        x += np.sin(2 * np.pi * k * f * t) * np.exp(-t * (6 + 5 * k)) / k
    return x * fades(n, 12, int(0.06 * SR)) * gain


def bell(name, length=1.8, gain=0.10):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = note_hz(name)
    x = np.zeros(n)
    for ratio, amp, dec in ((1, 1, 1.4), (2.0, 0.5, 0.9), (2.76, 0.35, 0.6),
                            (4.07, 0.2, 0.35), (5.4, 0.1, 0.2)):
        if ratio * f < 13000:
            x += amp * np.sin(2 * np.pi * ratio * f * t) * np.exp(-t / dec)
    return x * fades(n, 24, int(0.3 * SR)) * gain


def blip(freq, gain=0.05):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
    return x * np.exp(-t / 0.025) * fades(n, 24, int(0.03 * SR)) * gain


def riser(length, gain=0.12, f0=300, f1=5000):
    """Smooth riser: band-pass-swept noise (block-wise) plus a rising tone."""
    n = int(length * SR)
    t = np.arange(n) / SR
    p = t / length
    out = np.zeros((2, n))
    blk = 1024
    for c in range(2):
        nz = rng.standard_normal(n + blk)
        y = np.zeros(n)
        # overlap-add of short filtered blocks, raised-cosine windowed (no steps)
        win = np.hanning(2 * blk)
        for s in range(0, n, blk):
            fc = f0 * (f1 / f0) ** (s / n)
            seg = nz[s:s + 2 * blk]
            if len(seg) < 2 * blk:
                seg = np.pad(seg, (0, 2 * blk - len(seg)))
            seg = filt(seg, 'bandpass', [fc * 0.7, min(fc * 1.4, 20000)])
            e = min(s + 2 * blk, n)
            y[s:e] += (seg * win)[:e - s]
        out[c] = y
    tone_f = 110 * (8 ** p)
    tone = np.sin(2 * np.pi * np.cumsum(tone_f) / SR) * 0.25
    env = (p ** 2) * fades(n, int(0.05 * SR), int(0.02 * SR))
    return (out * 0.5 + tone) * env * gain


# ---------------------------------------------------------------- arrangement
# Chord per beat (32 beats; beat i starts at i*B)
prog = (['Am', 'Am', 'F', 'F', 'G', 'G', 'E', 'E']            # intro 0-5 s (words)
        + ['Am', 'Am', 'F', 'F', 'C', 'C', 'G', 'G', 'Am', 'Am', 'F', 'F']  # skyline 5-12.5
        + ['C', 'C', 'G', 'G']                                 # leaf scene 12.5-15
        + ['F', 'F', 'G']                                      # build 15-16.875
        + ['Am', 'F', 'C', 'G', 'Am'])                         # finale 16.875-20
assert len(prog) == 32

# --- drums: kick on every beat 0..31, never drops out
for i in range(32):
    big = i in (0, 8, 20, 27, 31)
    add('drums', kick(big), i * B, gain=1.0)

# claps on 2 and 4 except under the transitions' hits
for i in range(32):
    if i % 2 == 1 and i not in (19,):
        add('drums', clap(), i * B, pan=0.0, rev=0.25)

# hats: off-beat open hats in intro, 16ths in skyline/finale
for i in range(32):
    t = i * B
    if i < 8 or 20 <= i < 24:
        add('drums', hat(True), t + B / 2, pan=0.25)
    else:
        for k in range(4):
            if k == 0:
                continue
            g = 1.0 if k == 2 else 0.6
            add('drums', hat(k == 2) * g, t + k * S16, pan=0.25 if k % 2 else -0.2)

# snare roll into skyline lift (4.4 -> 5.0), fill into leaf scene, build roll 15.0 -> 16.875
def roll(t0, t1, start_div, end_div, g0, g1):
    t = t0
    while t < t1 - 1e-6:
        p = (t - t0) / (t1 - t0)
        add('drums', snare() * (g0 + (g1 - g0) * p), t, pan=0.0, rev=0.2)
        div = start_div + (end_div - start_div) * p
        t += B / div


roll(4.375, 5.0, 4, 8, 0.35, 0.9)
roll(11.875, 12.5, 4, 6, 0.4, 0.85)
roll(15.0, 16.875, 2, 8, 0.25, 1.0)

# crashes at section downbeats only (sparse -> no constant hiss)
for t, g in ((0.0, 0.14), (5.0, 0.16), (12.5, 0.15), (16.875, 0.18), (19.375, 0.16)):
    add('fx', crash(1.8, g), t)
add('fx', sub_boom(), 5.0, gain=0.8)
add('fx', sub_boom(), 16.875, gain=1.0)
add('fx', sub_boom(1.0), 19.375, gain=0.9)

# risers
add('fx', riser(0.9, 0.10), 5.0 - 0.9)
add('fx', riser(0.75, 0.08), 12.5 - 0.75)
add('fx', riser(1.85, 0.12), 16.875 - 1.85)

# --- bass: 8th notes on the chord root
for i, ch in enumerate(prog):
    if i == 31:
        add('bass', bass_note(ROOT[ch], 0.6), i * B)
        continue
    for k in range(2):
        nm = ROOT[ch]
        if k == 1 and i >= 8:
            nm = nm[:-1] + str(int(nm[-1]) + 1)   # octave bounce in the groove
        add('bass', bass_note(nm, B / 2 - 0.01), i * B + k * B / 2)

# --- intro word stabs (on the words) + ONE STAGE
for t, ch in ((0.0, 'Am'), (1.25, 'F'), (1.875, 'F'), (2.5, 'G'), (3.125, 'G'),
              (3.75, 'E'), (4.0625, 'E')):
    add('tonal', stab(ch, 0.55, 0.17), t, rev=0.35)
for k in range(8):   # quiet pad bed under the intro so it never feels empty
    add('tonal', pad(prog[k], B + 0.12, 0.035), k * B - 0.06, rev=0.3)

# --- skyline: pad bed + 16th pluck arpeggio (+octave layer from 8.75 s)
for i in range(8, 20):
    ch = prog[i]
    add('tonal', pad(ch, B + 0.12, 0.07), i * B - 0.06, rev=0.5)
    tones = CHORDS[ch] + [CHORDS[ch][1][:-1] + str(int(CHORDS[ch][1][-1]) + 1)]
    for k in range(4):
        t = i * B + k * S16
        nm = tones[(k + i) % len(tones)]
        nm5 = nm[:-1] + str(int(nm[-1]) + 1)
        add('tonal', pluck(nm5, 0.3, 0.085), t, pan=-0.3 + 0.2 * k, rev=0.4)
        if t >= 8.75:
            nm6 = nm[:-1] + str(int(nm[-1]) + 2)
            add('tonal', pluck(nm6, 0.25, 0.04), t + 0.004, pan=0.35 - 0.2 * k, rev=0.5)

# network blips (business arcs) and the SINGAPORE bell sting
for t, f in ((6.25, 1760), (6.5625, 2093), (6.875, 2637), (7.5, 1760), (8.125, 2349),
             (9.375, 2093), (10.0, 2637), (10.9375, 2349)):
    add('fx', blip(f), t, pan=rng.uniform(-0.6, 0.6), rev=0.6)
add('tonal', bell('E5', 2.0, 0.09), 6.875, pan=-0.15, rev=0.6)
add('tonal', bell('A5', 2.0, 0.07), 6.875 + 0.01, pan=0.15, rev=0.6)

# --- leaf scene 12.5-15: pad + growing leaf plucks on 16ths
for i in range(20, 24):
    add('tonal', pad(prog[i], B + 0.12, 0.06), i * B - 0.06, rev=0.5)
leaf_pattern = [0, 3, 6, 8, 10, 11, 13, 14, 15]
for bi, i in enumerate(range(20, 24)):
    ch = prog[i]
    tones = [n[:-1] + str(int(n[-1]) + 1) for n in CHORDS[ch]] + [CHORDS[ch][0][:-1] + str(int(CHORDS[ch][0][-1]) + 2)]
    density = [2, 3, 4, 4][bi]
    for k in range(4):
        if k >= density:
            continue
        add('tonal', pluck(tones[(k * 2 + bi) % 4], 0.35, 0.08), i * B + k * S16,
            pan=rng.uniform(-0.5, 0.5), rev=0.5)

# --- build 15-16.875: pad swells under the roll
for i in range(24, 27):
    add('tonal', pad(prog[i], B + 0.12, 0.05 + 0.02 * (i - 24)), i * B - 0.06, rev=0.4)

# --- finale: DEMO (16.5625) / DAY (16.875) and groove to the final hit
add('tonal', stab('G', 0.3, 0.14), 16.5625, rev=0.4)
add('tonal', stab('Am', 0.9, 0.20), 16.875, rev=0.45)
add('tonal', bell('A5', 2.2, 0.08), 16.875, pan=-0.2, rev=0.6)
add('tonal', bell('E6', 2.2, 0.05), 16.885, pan=0.2, rev=0.6)
for i in range(27, 31):
    ch = prog[i]
    add('tonal', pad(ch, B + 0.12, 0.075), i * B - 0.06, rev=0.5)
    if i > 27:
        add('tonal', stab(ch, 0.35, 0.10), i * B, rev=0.4)
    tones = CHORDS[ch] + [CHORDS[ch][1][:-1] + str(int(CHORDS[ch][1][-1]) + 1)]
    for k in range(4):
        nm = tones[(k + i) % 4]
        add('tonal', pluck(nm[:-1] + str(int(nm[-1]) + 1), 0.3, 0.07), i * B + k * S16,
            pan=-0.3 + 0.2 * k, rev=0.4)
# final hit with ring-out
add('tonal', stab('Am', 0.62, 0.20), 19.375, rev=0.6)
add('tonal', bell('A5', 0.62, 0.07), 19.375, rev=0.6)


# ---------------------------------------------------------------- mix
def kick_envelope():
    """Sidechain envelope: dips at each kick, recovers over ~0.18 s."""
    e = np.ones(N)
    t = np.arange(int(0.25 * SR)) / SR
    att = 0.5 - 0.5 * np.cos(np.pi * np.clip(t / 0.006, 0, 1))
    dip = 1 - 0.45 * att * np.exp(-t / 0.07)
    for i in range(32):
        i0 = int(i * B * SR)
        n = min(len(dip), N - i0)
        e[i0:i0 + n] = np.minimum(e[i0:i0 + n], dip[:n])
    # smooth so the duck never steps
    k = int(0.003 * SR)
    return np.convolve(e, np.ones(k) / k, 'same')


def reverb_ir(length=1.4):
    n = int(length * SR)
    t = np.arange(n) / SR
    ir = []
    for _ in range(2):
        x = rng.standard_normal(n) * np.exp(-t / (length / 5.5))
        x = filt(x, 'lowpass', 6000, 2)
        x = filt(x, 'highpass', 250, 2)
        x *= fades(n, int(0.008 * SR), int(0.2 * SR))
        ir.append(x / np.sqrt((x ** 2).sum()))
    return ir


sc = kick_envelope()
mix = np.zeros((2, N))
mix += bus['drums']
mix += bus['bass'] * sc
mix += bus['tonal'] * (0.35 + 0.65 * sc)
mix += bus['fx']
ir = reverb_ir()
for c in range(2):
    wet = fftconvolve(send[c], ir[c])[:N]
    mix[c] += wet * 0.55

# master: DC/sub cleanup, gentle tilt, then look-ahead limiter
for c in range(2):
    mix[c] = filt(mix[c], 'highpass', 28, 2)


def limiter(x, ceiling=0.89, look=0.005, release=0.08):
    """Look-ahead peak limiter. Every step keeps gain <= the gain each sample
    needs, so peaks never exceed the ceiling, and the gain curve is smooth."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    need = np.minimum(1.0, ceiling / np.maximum(np.max(np.abs(x), axis=0), 1e-9))
    coef = np.exp(-1 / (release * SR))
    g = np.empty_like(need)
    cur = 1.0
    for i in range(len(need)):           # instant attack, exponential release
        cur = need[i] if need[i] < cur else need[i] + (cur - need[i]) * coef
        g[i] = cur
    la = int(look * SR)
    g = minimum_filter1d(g, la + 1)      # look ahead/behind la/2
    g = uniform_filter1d(g, la + 1)      # smooth attack ramp, still <= need
    return x * g


# normalise to a consistent level before limiting
rms = np.sqrt((mix ** 2).mean())
mix *= 10 ** (-15.5 / 20) / rms
mix = limiter(mix)
# master fades: 4 ms in (no click at t=0), ring-out tail faded to silence by 20 s
mf = np.ones(N)
mf[:int(0.004 * SR)] = np.linspace(0, 1, int(0.004 * SR))
tail0 = int(19.62 * SR)
mf[tail0:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, N - tail0))
mix *= mf
mix = np.clip(mix, -0.98, 0.98)   # safety only; limiter keeps peaks below 0.89

pcm = (mix.T * 32767).astype(np.int16)
with wave.open('audio.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('peak %.3f  rms %.1f dBFS' % (np.abs(mix).max(), 20 * np.log10(np.sqrt((mix ** 2).mean()))))
