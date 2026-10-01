# SBC Leaf Swipe – stinger transition · AV cue sheet

A left-to-right, full-height brand swipe in SBC Green with a wave of leaves on both edges,
Morning Glory and Cybrus accent bands, and the official SBC arrow on the panel.
Use it between two items (speakers, slides, segments) on stage screens and on the stream.

## Key numbers

| | 1080p60 files | 1080p50 files |
|---|---|---|
| Duration | 1.40 s = **84 frames** | 1.40 s = **70 frames** |
| Screen 100 % covered | frames **18–59** (0.30–0.98 s) | frames **15–49** (0.30–0.98 s) |
| **Transition / cut point** | **600 ms = frame 36** | **600 ms = frame 30** |
| First / last frame | fully transparent | fully transparent |

Cut anywhere inside the covered window and the change is invisible; 600 ms is the recommended
point (≈0.3 s of margin both sides, so cueing jitter is safe).

Pick the frame rate that matches the production output: **50p** for 50 Hz systems (typical in
Australia / Singapore), **60p** for 60 Hz systems. For 25p or 30p outputs use the 50p / 60p file
respectively (frames are dropped cleanly). 4K or other rates can be re-rendered from source.

## Files

| File | Use it for |
|---|---|
| `*_ProRes4444_alpha.mov` | vMix, QLab, Resolume, Millumin, Watchout, Premiere/Resolve, OBS. Alpha + embedded 24-bit PCM whoosh |
| `*_VP9_alpha.webm` | OBS Stinger (lightest, reliable alpha), browser sources. Opus whoosh |
| `*_FILL_premultiplied.mp4` + `*_KEY.mp4` | Switchers with separate fill/key inputs (e.g. ATEM via external playback). Fill is **premultiplied** |
| `*_PNG_sequence_alpha.zip` | Media servers, ATEM media-pool clip import |
| `SBC_LeafSwipe_Stinger_whoosh_48k24.wav` | The sound on its own (48 kHz / 24-bit, 1.40 s, peak −6 dBFS, pans L→R with the swipe) |
| `SBC_LeafSwipe_Stinger_PREVIEW_A-to-B.mp4` | Reference only: shows the stinger cutting from a placeholder Item A to Item B |

Audio is embedded in the .mov and .webm. If the show runs its own transition sound, mute or
detach the stinger audio in the switcher.

## Setup notes

**OBS Studio** – Scene Transitions → **+** → *Stinger* → Video File: the `_VP9_alpha.webm` (or `.mov`).
Transition Point Type: *Time (milliseconds)* → **600**. Audio Monitoring: *Monitor and Output* if
the whoosh should reach the stream; Audio Fade Style: *Fade out to transition point* is fine.

**vMix** – Settings → Transitions → Stinger 1 → load the `.mov` → **Transition Point: 600 ms**.

**ATEM (models with media-pool clips)** – import the PNG sequence as Clip 1 in ATEM Software
Control. Transition style *Stinger*: Source = Media Player 1, **Pre Multiplied Key: on**,
Clip Duration = 84 (60p) / 70 (50p), **Trigger Point = 36 (60p) / 30 (50p)**, Mix Rate = 1 frame,
Pre Roll per your playback delay. ATEM Mini models cannot play clips: play the FILL/KEY files
from external playback into two inputs, or run the stinger in vMix/OBS.

**QLab / media servers** – put the ProRes or PNG sequence on a layer above the content and fire
the content change 600 ms after the stinger GO (e.g. a follow-on cue with 0.60 s pre-wait).

## Rehearsal checklist
- [ ] Correct frame-rate file loaded (50p vs 60p).
- [ ] Transition point set to 600 ms (or frame 36 / 30).
- [ ] Item B appears only once the green panel has fully covered the screen.
- [ ] Whoosh level checked on PA and on the stream mix (or muted if not wanted).
- [ ] Test on the LED/projector: the swipe covers the full height edge to edge.

## Brand notes
SBC Green `#008C8C`, Cybrus `#30454A`, Morning Glory `#92D2D7`, White; leaves use the leaf-logo
greens. The double-chevron arrow uses the official geometry and is always upright (never rotated
to point in the swipe direction).
