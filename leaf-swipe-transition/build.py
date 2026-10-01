#!/usr/bin/env python3
"""Encode the AV deliverables for the leaf swipe stinger.

usage: python3 build.py <workdir> <outdir>
  <workdir> must contain frames_60/, frames_50/ (from render.js) and whoosh.wav
"""
import os
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DUR = 2.64
CUT = 1.30            # recommended transition point (inside the full-cover window)
NAME = 'SBC_LeafSwipe_Stinger'


def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *args], check=True)


def placeholder(path, label, sub, bg, fg):
    """Simple stand-in slides for the preview (not part of the stinger)."""
    im = Image.new('RGB', (1920, 1080), bg)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 120)
    small = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 44)
    d.text((960, 500), label, font=big, fill=fg, anchor='mm')
    d.text((960, 620), sub, font=small, fill=fg, anchor='mm')
    d.text((960, 1020), 'PREVIEW ONLY – placeholder content', font=small, fill=fg, anchor='mm')
    im.save(path)


def main(work, out):
    os.makedirs(out, exist_ok=True)
    wav = os.path.join(work, 'whoosh.wav')
    shutil.copy(wav, os.path.join(out, f'{NAME}_whoosh_48k24.wav'))
    a = os.path.join(work, 'slide_a.png')
    b = os.path.join(work, 'slide_b.png')
    placeholder(a, 'ITEM A', 'Outgoing content', '#E8F5F8', '#30454A')
    placeholder(b, 'ITEM B', 'Incoming content', '#FFFFFF', '#008C8C')

    for fps in (60, 50):
        frames = os.path.join(work, f'frames_{fps}', 'frame_%04d.png')
        tag = f'{NAME}_1080p{fps}'

        # 1) ProRes 4444 + alpha, embedded 24-bit PCM whoosh (vMix, QLab, Resolume, Premiere, Resolve, OBS)
        ff('-framerate', str(fps), '-i', frames, '-i', wav,
           '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le',
           '-alpha_bits', '16', '-vendor', 'apl0', '-qscale:v', '4',
           '-c:a', 'pcm_s24le', '-t', str(DUR), os.path.join(out, f'{tag}_ProRes4444_alpha.mov'))
        # 2) WebM VP9 + alpha, Opus audio (OBS stinger, browser sources)
        ff('-framerate', str(fps), '-i', frames, '-i', wav,
           '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', '-b:v', '0', '-crf', '16',
           '-auto-alt-ref', '0', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '1',
           '-c:a', 'libopus', '-b:a', '192k', '-t', str(DUR), os.path.join(out, f'{tag}_VP9_alpha.webm'))
        # 3) Fill + Key pair (switchers with separate fill/key inputs, e.g. ATEM; premultiplied fill)
        ff('-framerate', str(fps), '-i', frames,
           '-vf', 'premultiply=inplace=1,format=yuv420p', '-c:v', 'libx264', '-crf', '10',
           '-preset', 'slow', '-profile:v', 'high', '-t', str(DUR),
           os.path.join(out, f'{tag}_FILL_premultiplied.mp4'))
        ff('-framerate', str(fps), '-i', frames,
           '-vf', 'alphaextract,format=yuv420p', '-c:v', 'libx264', '-crf', '10',
           '-preset', 'slow', '-profile:v', 'high', '-t', str(DUR),
           os.path.join(out, f'{tag}_KEY.mp4'))
        # 4) PNG sequence (straight alpha) for media servers / ATEM media pool
        zp = os.path.join(out, f'{tag}_PNG_sequence_alpha.zip')
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:
            for f in sorted(os.listdir(os.path.join(work, f'frames_{fps}'))):
                z.write(os.path.join(work, f'frames_{fps}', f), f'{tag}_PNG/{f}')

    # 5) Preview: 1 s of A, stinger (cut to B at CUT), 1 s of B, with audio
    fps = 60
    frames = os.path.join(work, 'frames_60', 'frame_%04d.png')
    cut_f = round(CUT * fps)
    ff('-loop', '1', '-framerate', str(fps), '-t', str(DUR + 2), '-i', a,
       '-loop', '1', '-framerate', str(fps), '-t', str(DUR + 2), '-i', b,
       '-framerate', str(fps), '-i', frames,
       '-i', wav,
       '-filter_complex',
       # base = A until 1.0 s + cut point, then B
       f"[0:v][1:v]blend=all_expr='if(lt(N,{60 + cut_f}),A,B)'[base];"
       f"[2:v]setpts=PTS+1.0/TB[st];"
       f"[base][st]overlay=eof_action=pass:format=auto,format=yuv420p[v];"
       f"[3:a]adelay=1000|1000,apad=whole_dur={DUR + 2}[a]",
       '-map', '[v]', '-map', '[a]', '-t', str(DUR + 2),
       '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-c:a', 'aac', '-b:a', '256k',
       os.path.join(out, f'{NAME}_PREVIEW_A-to-B.mp4'))
    print('done ->', out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
