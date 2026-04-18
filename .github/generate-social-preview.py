# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow>=10.0"]
# ///
"""Generate the media-os social preview image (1200x630 PNG).

Used when the repo is linked on Twitter/X, Hacker News, Reddit, LinkedIn.
Upload via GitHub Settings → Social preview.

Run:  uv run .github/generate-social-preview.py
Out:  .github/social-preview.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


W, H = 1200, 630
BG = (11, 15, 20)          # #0B0F14 near-black
ACCENT = (255, 107, 53)     # FFmpeg-ish orange #FF6B35
FG = (238, 240, 244)        # #EEF0F4 off-white
DIM = (148, 158, 170)       # #949EAA

OUT = Path(__file__).parent / "social-preview.png"


def pick_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates += [
            "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    candidates += [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_diagonal_stripes(draw: ImageDraw.ImageDraw) -> None:
    for i in range(-H, W + H, 48):
        draw.line([(i, 0), (i + H, H)], fill=(18, 24, 32), width=1)


def draw_corner_bracket(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple) -> None:
    t = 6
    draw.rectangle([x, y, x + size, y + t], fill=color)
    draw.rectangle([x, y, x + t, y + size], fill=color)


def main() -> int:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_diagonal_stripes(draw)

    # Left accent bar
    draw.rectangle([0, 0, 16, H], fill=ACCENT)

    # Corner brackets
    draw_corner_bracket(draw, 72, 72, 44, ACCENT)
    draw_corner_bracket(draw, W - 72 - 44, H - 72 - 44, 44, ACCENT)
    draw.rectangle([W - 72, 72, W - 72 + 6, 72 + 44], fill=ACCENT)
    draw.rectangle([W - 72 - 44 + 6, 72, W - 72 + 6, 72 + 6], fill=ACCENT)

    # Tag
    tag_font = pick_font(22, bold=True)
    tag = "CLAUDE CODE PLUGIN"
    bbox = draw.textbbox((0, 0), tag, font=tag_font)
    tag_w = bbox[2] - bbox[0]
    tag_h = bbox[3] - bbox[1]
    pad_x, pad_y = 18, 10
    tag_x, tag_y = 96, 136
    draw.rounded_rectangle(
        [tag_x, tag_y, tag_x + tag_w + 2 * pad_x, tag_y + tag_h + 2 * pad_y],
        radius=6,
        outline=ACCENT,
        width=2,
    )
    draw.text((tag_x + pad_x, tag_y + pad_y - 2), tag, fill=ACCENT, font=tag_font)

    # Title
    title_font = pick_font(128, bold=True)
    draw.text((96, 200), "media-os", fill=FG, font=title_font)

    # Subtitle
    sub_font = pick_font(38, bold=True)
    draw.text(
        (96, 352),
        "Professional media production, in Claude Code.",
        fill=FG,
        font=sub_font,
    )

    # Tagline
    tag2_font = pick_font(26)
    draw.text(
        (96, 408),
        "FFmpeg  •  HDR / Dolby Vision  •  OBS  •  GStreamer",
        fill=DIM,
        font=tag2_font,
    )
    draw.text(
        (96, 444),
        "MediaMTX  •  NDI  •  WebRTC  •  Whisper  •  AI media",
        fill=DIM,
        font=tag2_font,
    )

    # Divider
    draw.rectangle([96, 510, 400, 512], fill=ACCENT)

    # Stat strip
    stat_label = pick_font(20)
    stat_num = pick_font(44, bold=True)

    stats = [
        ("96", "SKILLS"),
        ("7", "AGENTS"),
        ("13", "WORKFLOWS"),
        ("1", "COMMAND"),
    ]
    x = 96
    for i, (num, label) in enumerate(stats):
        draw.text((x, 530), num, fill=ACCENT, font=stat_num)
        nb = draw.textbbox((0, 0), num, font=stat_num)
        draw.text((x, 578), label, fill=DIM, font=stat_label)
        lb = draw.textbbox((0, 0), label, font=stat_label)
        x += max(nb[2] - nb[0], lb[2] - lb[0]) + 64

    # Footer right — install hint
    foot_font = pick_font(22)
    foot = "/plugin install media-os@media-os"
    bbox = draw.textbbox((0, 0), foot, font=foot_font)
    fw = bbox[2] - bbox[0]
    fh = bbox[3] - bbox[1]
    draw.rounded_rectangle(
        [W - 96 - fw - 28, H - 96 - fh - 20, W - 96, H - 96],
        radius=6,
        outline=DIM,
        width=1,
    )
    draw.text((W - 96 - fw - 14, H - 96 - fh - 12), foot, fill=FG, font=foot_font)

    img.save(OUT, format="PNG", optimize=True)
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({W}x{H}, {size_kb:.0f} KB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
