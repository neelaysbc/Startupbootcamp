# SBC Leaf Swipe – stinger transition

Left-to-right, full-height transition using the SBC leaves and official arrow.
**AV team: see [AV_CUE_SHEET.md](AV_CUE_SHEET.md)** (cut point 1300 ms, file formats, OBS / vMix / ATEM / QLab setup).

- `deliverables/` – ProRes 4444 alpha, VP9 alpha WebM, fill/key MP4s, whoosh WAV and preview, at 1080p50 and 1080p60.
- PNG sequences (85–100 MB zipped) are not committed; rebuild them with the steps below.

## Source
- `stinger.html` – the animation (`window.draw(t)` on a transparent 1920×1080 canvas). Timing,
  easing, colours, leaf counts and the cover window are all constants at the top of the script.
- `render.js` – renders motion-blurred PNG frames with Playwright/Chromium:
  `node render.js 60 work/frames_60` and `node render.js 50 work/frames_50`
- `whoosh.py` – synthesises the SFX from the same edge motion: `python3 whoosh.py work/whoosh.wav`
- `build.py` – encodes every deliverable: `python3 build.py work out`

If timing is changed in `stinger.html`, mirror `T0`, `DUR`, `T_EDGE`, `X0/X1` and the green band
times in `whoosh.py`, re-check the full-cover window (all-opaque frames) and update the cut point
in `build.py` and the cue sheet.
