# Subtitle formats, styling, and container reference

## Container × subtitle codec matrix

| Container | `mov_text` | `srt` / `subrip` | `ass` / `ssa` | `webvtt` | `dvbsub` | `dvdsub` | `hdmv_pgs` |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| MP4 (`.mp4`, `.m4v`) | yes | no | no | no | no | no | no |
| MOV (`.mov`) | yes | no | no | no | no | no | no |
| MKV (`.mkv`) | no | yes | yes | yes | yes | yes | yes |
| WebM (`.webm`) | no | no | no | yes | no | no | no |
| MPEG-TS (`.ts`) | no | no | no | no | yes | yes | yes |
| Matroska (`.mka`) | no | yes | yes | yes | no | no | no |
| AVI (`.avi`) | no | no | no | no | no | no | no *(avoid; use MKV)* |
| FLV (`.flv`) | no | no | no | no | no | no | no *(no sub support)* |

**Rule of thumb:** MKV for archival, MP4 for Apple / web, WebM for VP9/AV1 with alpha, TS only for broadcast.

`-c:s copy` only works when the source subtitle codec is valid for the destination container. Otherwise you must transcode (e.g. `-c:s mov_text`, `-c:s webvtt`).

## Per-format feature comparison

| Feature | SRT | ASS/SSA | WebVTT | SUB (MicroDVD) |
| --- | :-: | :-: | :-: | :-: |
| Text only | yes | yes | yes | yes |
| Inline bold/italic | partial (HTML-ish, player-dependent) | yes | yes | no |
| Named styles | no | yes | partial (CSS ::cue) | no |
| Per-line positioning | no | yes | yes | no |
| Karaoke / per-char timing | no | yes | partial | no |
| Color | player-dependent | yes | yes (CSS) | no |
| Unicode | yes (UTF-8) | yes | yes (UTF-8 required) | yes |
| Frame-based timing | no | no | no | yes |
| Bitmap subs | no | no | no | no |

Bitmap subs (`dvbsub`, `dvdsub`, `hdmv_pgs_subtitle`) carry no text; OCR is required to convert them to SRT/ASS.

## `force_style` parameters (subtitles filter)

`force_style` injects inline ASS overrides into whatever the subtitle filter renders. Parameters are comma-separated and the whole value must be single-quoted inside the filter:

```
-vf "subtitles=subs.srt:force_style='Fontname=Arial,Fontsize=24,...'"
```

| Parameter | Type | Notes |
| --- | --- | --- |
| `Fontname` | string | Must match an installed font known to fontconfig. Fallback font is used silently if missing. |
| `Fontsize` | int | Pixel-ish; tune with output resolution in mind (24 at 1080p, 16 at 480p). |
| `PrimaryColour` | ASS color | Main fill color. |
| `SecondaryColour` | ASS color | Karaoke fill-in color; rarely used. |
| `OutlineColour` | ASS color | Outline/border color. |
| `BackColour` | ASS color | Shadow or opaque box background. |
| `Bold` | 0 / -1 | `-1` means on. |
| `Italic` | 0 / -1 | `-1` means on. |
| `Underline` | 0 / -1 | |
| `StrikeOut` | 0 / -1 | |
| `ScaleX` | int (%) | Horizontal scale percent. |
| `ScaleY` | int (%) | Vertical scale percent. |
| `Spacing` | float | Extra inter-character spacing in pixels. |
| `Angle` | float | Rotation in degrees. |
| `BorderStyle` | 1 / 3 | `1`=outline+shadow, `3`=opaque box. |
| `Outline` | float | Outline thickness in pixels. |
| `Shadow` | float | Shadow depth in pixels. |
| `Alignment` | 1–9 (numpad layout) | `2`=bottom-center, `5`=middle-center, `8`=top-center. |
| `MarginL` | int (px) | Left margin. |
| `MarginR` | int (px) | Right margin. |
| `MarginV` | int (px) | Vertical margin from the aligned edge. |
| `Encoding` | int | Rarely needed; `1` = default, `0` = ANSI. |

## ASS color format: `&HAABBGGRR`

- `&H` = literal prefix.
- `AA` = alpha; `00` = fully opaque, `FF` = fully transparent, `80` = 50% transparent.
- `BB`, `GG`, `RR` = blue, green, red bytes — **reverse of RGB**.

| Intent | RGB hex | ASS |
| --- | --- | --- |
| Opaque white | `#FFFFFF` | `&H00FFFFFF` |
| Opaque black | `#000000` | `&H00000000` |
| Opaque red | `#FF0000` | `&H000000FF` |
| Opaque green | `#00FF00` | `&H0000FF00` |
| Opaque blue | `#0000FF` | `&H00FF0000` |
| Opaque yellow | `#FFFF00` | `&H0000FFFF` |
| Half-transparent black | `#000000` 50% | `&H80000000` |
| Netflix-ish drop shadow | `#000000` 80% | `&HCC000000` |

Conversion: `&H<AA><BB><GG><RR>` ← given `#RRGGBB` hex + alpha `AA`.

## Filter-path escaping (three levels)

A path inside `subtitles=...` or `ass=...` is interpreted by three layers:

1. **Shell** — standard quoting. Use single quotes to prevent `$` / `` ` `` expansion.
2. **Filter graph parser** — treats `:` as option separator and `,` as filter separator. Escape `:` as `\:`, and `\` as `\\`.
3. **libavfilter option value parser** — single quotes inside the filter value protect commas/spaces.

Example, Windows path `C:\Users\me\subs.srt`, POSIX shell:

```
-vf "subtitles='C\:\\Users\\me\\subs.srt'"
```

Example, POSIX path with a colon `/tmp/my:file.srt`:

```
-vf "subtitles='/tmp/my\:file.srt'"
```

When scripting, always wrap the path in single quotes inside the filter and backslash-escape `:` and `\`. The `subs.py` helper does this automatically.

## Common fontfile paths

Use these with `fontsdir=...` in the subtitles filter, or `fontfile=...` in drawtext:

| OS | Path | Notes |
| --- | --- | --- |
| macOS (system) | `/System/Library/Fonts` | Helvetica, Menlo, SF Pro. |
| macOS (user) | `~/Library/Fonts` | User-installed TTF/OTF. |
| macOS (bundled apps) | `/Library/Fonts` | Arial, Times New Roman (often present). |
| Linux (Debian/Ubuntu) | `/usr/share/fonts/truetype` | DejaVu, Liberation. |
| Linux (Fedora/Arch) | `/usr/share/fonts` | |
| Linux (user) | `~/.fonts`, `~/.local/share/fonts` | |
| Windows | `C:/Windows/Fonts` | Arial, Calibri, Consolas. |

Pointing directly at a fontfile avoids fontconfig entirely:

```
-vf "subtitles=subs.srt:fontsdir=/System/Library/Fonts:force_style='Fontname=Helvetica'"
```

## Quick burn-in style recipes

Cinematic caption (bottom, large, soft shadow):

```
force_style='Fontname=Helvetica,Fontsize=28,PrimaryColour=&H00FFFFFF,
OutlineColour=&H80000000,BorderStyle=1,Outline=1,Shadow=1,MarginV=80,Alignment=2'
```

Opaque box caption (max legibility, TV news style):

```
force_style='Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,
BackColour=&HA0000000,BorderStyle=3,Outline=6,Shadow=0,MarginV=60,Alignment=2'
```

Yellow karaoke-ish (DVD anime style):

```
force_style='Fontname=Arial,Fontsize=26,Bold=-1,PrimaryColour=&H0000FFFF,
OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,MarginV=70,Alignment=2'
```

Top-of-frame notes / translator credits:

```
force_style='Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,
OutlineColour=&H80000000,BorderStyle=1,Outline=2,MarginV=40,Alignment=8'
```

## Charset cheat-sheet for `-sub_charenc`

| Region | Typical charset |
| --- | --- |
| Western Europe (legacy) | `CP1252` / `ISO-8859-1` / `ISO-8859-15` |
| Central / Eastern Europe | `CP1250` / `ISO-8859-2` |
| Cyrillic | `CP1251` / `ISO-8859-5` / `KOI8-R` |
| Greek | `CP1253` / `ISO-8859-7` |
| Turkish | `CP1254` / `ISO-8859-9` |
| Hebrew | `CP1255` / `ISO-8859-8` |
| Arabic | `CP1256` / `ISO-8859-6` |
| Chinese (Simplified) | `GB18030` |
| Chinese (Traditional) | `Big5` |
| Japanese | `Shift_JIS` / `EUC-JP` |
| Korean | `CP949` / `EUC-KR` |

`-sub_charenc` is a **demuxer** option — it applies only to `-i subs.srt`, not to the `subtitles=` filter. For burn-in, pre-convert the file: `iconv -f CP1252 -t UTF-8 in.srt > out.srt`.
