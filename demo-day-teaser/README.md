# SBC Sustainability Singapore – Demo Day teaser (v7)

`SBC_Sustainability_SG_DemoDay_Teaser_20s_v7.mp4` – 1920×1080, 60 fps, H.264 (CRF 14) + AAC 320k, 20 s.

v7 is a glitch-fix pass on v6. The original HTML/canvas source (`SBC_DemoDay_Teaser_source.zip`)
was not available, so the picture fixes are applied to the rendered v6 frames and the soundtrack
was re-synthesised from scratch with the same cue timing.

## What changed vs v6

### Video (`fix_video.py`)
| Time | v6 problem | v7 fix |
|---|---|---|
| 1.25 / 1.88 / 2.5 / 3.13 / 3.75 s | Outgoing word vanished in one frame (hard pop, momentarily empty screen) | Outgoing word floats up 42 px and fades over 0.2 s while the next word rises in |
| 11.5–12.4 s | Arrow wipe crossed the screen in ~6 frames; the light scene appeared as a hard rectangle at the bottom ahead of the arrow | Rebuilt as the official double-chevron (exact brand-book geometry, proportions unchanged, pointing up) rising over 0.9 s with sine ease and 12-sample motion blur; the reveal follows the arrow's outer edge |
| ~7–12 s | Boats/wakes sailed through the "SUSTAINABILITY" tagline | Removed inside a feathered box around the tagline (clean plate from a temporal median) |

Frame-diff QA (mean abs diff, 240×135): largest jump outside the wipe 14.3 → 5.5; inside the wipe 83.8 → 10.5 (smooth ramp, no spike).

### Audio (`audio.py`)
v6 problems found by analysis: kick waveforms flat-topped by the limiter (distortion), a constant
broadband noise bed (hiss up to 22 kHz), abrupt noise gating that showed as momentary full-band
drop-outs, and a hard start at sample 0.

The new track keeps the same structure (96 BPM, A minor, kick on every beat 0–19.375 s, word stabs,
lift at 5.0 s, skyline arp, bell on SINGAPORE, fill into 12.5 s, build from 15 s, DEMO / DAY hits,
final hit at 19.375 s) but:
- all oscillators are band-limited (no aliasing), every event has raised-cosine fades (no clicks);
- noise only in short enveloped percussion and smooth risers – no constant noise bed;
- mix normalised, then a look-ahead limiter that only touches the biggest hits (peak 0.89, no flat tops);
- 4 ms fade-in at the start, ring-out faded to silence by 20 s.
- Loudness: −14.7 to −16.6 dB RMS per 2.5 s section; zero click candidates in the encoded file.

**It still needs a listen on good speakers/headphones before release** – it was verified by
measurement, not by ear. For paid/commercial placements, consider a licensed music track or a
sound designer; the synthesised score is clean but simple.

## Rebuild
Requires python3 with numpy, scipy, Pillow, and ffmpeg.
```
python3 audio.py                                   # -> audio.wav
python3 fix_video.py <v6.mp4> audio.wav SBC_Sustainability_SG_DemoDay_Teaser_20s_v7.mp4
```
If the original HTML source is recovered, the same fixes should be ported there (word exit tween,
slower masked arrow wipe, keep boats out of the tagline rows) rather than post-processing.

## Not changed (flag for the client)
- On green, the logo bug's "Sustainability Singapore" line is Cybrus on SBC Green – low contrast at small size. Left as is because logos may only be altered as the client specified.
- Figtree is still the stand-in for Proxima Nova (fonts are baked into the v6 frames).
