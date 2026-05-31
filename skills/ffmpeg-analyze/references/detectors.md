# ffmpeg detect filters — reference

Per-filter option catalogs, sample stderr, parse regex, and recipes for the detect-and-act workflow. Everything here is read-only — no file is modified.

All detectors pair with `-f null -` as the sink. Standard invocation shape:

```
ffmpeg -hide_banner [-ss T] -i INPUT [-t T] -vf FILTER[=opts] -f null -   # video
ffmpeg -hide_banner             -i INPUT        -af FILTER[=opts] -f null -   # audio
```

Output lives in **stderr**. Capture with `2>&1 | grep PATTERN`.

---

## cropdetect

Detect non-black bounding rectangle of picture content for autocrop.

**Options:**
| name | default | description |
|---|---|---|
| `limit` | 24 | max pixel value to consider "black" (0–255 on 8-bit; 0.0–1.0 float accepted) |
| `round` | 16 | round output dimensions to a multiple (use 2 for "just even") |
| `reset` / `reset_count` | 0 | reset after N frames (0 = never) |
| `skip` | 2 | how many frames to skip between detections |
| `mode` | black | `black` / `mv_edges` (edge-based, more accurate in noise) |

**Sample stderr (every ~few frames):**
```
[Parsed_cropdetect_0 @ 0x...] x1:0 x2:1919 y1:140 y2:939 w:1920 h:800 x:0 y:140 pts:... t:... crop=1920:800:0:140
```

**Regex:** `r"crop=(\d+:\d+:\d+:\d+)"` — take the LAST match; values stabilize as more frames accumulate.

**Apply:** `ffmpeg -i in -vf crop=1920:800:0:140 -c:a copy out.mp4`

**Tip:** `round=2` is friendlier than 16 — it keeps dims even (codec requirement) without over-cropping. `round=16` guarantees macroblock alignment for H.264/HEVC.

---

## silencedetect

Find silent regions in audio.

**Options:**
| name | default | description |
|---|---|---|
| `n` / `noise` | -60dB | amplitude threshold (dB or linear 0–1) |
| `d` / `duration` | 2 | minimum silence duration (seconds) |
| `mono` | false | detect per-channel independently |

**Sample stderr:**
```
[silencedetect @ 0x...] silence_start: 12.345
[silencedetect @ 0x...] silence_end: 14.890 | silence_duration: 2.545
```

**Regex:**
- start: `r"silence_start:\s*([\-\d.]+)"`
- end + duration: `r"silence_end:\s*([\-\d.]+)\s*\|\s*silence_duration:\s*([\-\d.]+)"`

Pair lines by order. If starts outnumber ends, file ended in silence.

**Tip:** `-30dB` is podcast/dialogue pause territory; `-40dB` to `-50dB` is room tone; below `-60dB` is near-digital silence.

---

## blackdetect

Detect black video segments.

**Options:**
| name | default | description |
|---|---|---|
| `d` / `black_min_duration` | 2.0 | minimum black run length (seconds) |
| `pix_th` / `picture_black_ratio_th` | 0.98 | fraction of frame pixels that must be "black" |
| `pixel_black_th` | 0.1 | per-pixel black threshold (0–1) |

**Sample stderr:**
```
[blackdetect @ 0x...] black_start:120.5 black_end:122.3 black_duration:1.8
```

**Regex:** `r"black_start:([\-\d.]+)\s+black_end:([\-\d.]+)\s+black_duration:([\-\d.]+)"`

---

## freezedetect

Detect frozen (nearly identical) frames.

**Options:**
| name | default | description |
|---|---|---|
| `n` / `noise` | 0.001 | noise tolerance (normalized 0–1; use higher for noisy source) |
| `d` / `duration` | 2 | minimum freeze duration (seconds) |

**Sample stderr (emitted as separate lines per event):**
```
[freezedetect @ 0x...] lavfi.freezedetect.freeze_start: 45.2
[freezedetect @ 0x...] lavfi.freezedetect.freeze_duration: 3.1
[freezedetect @ 0x...] lavfi.freezedetect.freeze_end: 48.3
```

**Regex:** `r"freeze_start:\s*([\-\d.]+)"`, `r"freeze_duration:\s*([\-\d.]+)"`, `r"freeze_end:\s*([\-\d.]+)"` — zip by index.

---

## blurdetect

Per-frame blur score via Laplacian variance.

**Options:**
| name | default | description |
|---|---|---|
| `radius` | 50 | blur kernel radius |
| `block_pct` | 80 | percentage of blocks to keep for score |
| `block_width` / `block_height` | -1 | block size (auto) |
| `planes` | 0xF | Y/U/V/A mask |

Writes `lavfi.blur` per-frame metadata. Capture via `,metadata=mode=print`. Higher score = sharper; lower = blurrier. Threshold is content-dependent — benchmark against a known-good clip.

---

## blockdetect

Per-frame blocking-artifact score.

**Options:**
| name | default | description |
|---|---|---|
| `period_min` / `period_max` | 3 / 24 | expected macroblock period range |
| `planes` | 0x1 | Y only by default |

Writes `lavfi.block` per frame. Good for comparing encode settings — pair with `ffmpeg-quality` VMAF/PSNR for a full QC picture.

---

## scdet

Scene-change detection with explicit scores.

**Options:**
| name | default | description |
|---|---|---|
| `threshold` / `t` | 10.0 | cut score threshold (0–100) |
| `sc_pass` / `s` | 0 | set to 1 to emit one log line per detected cut |

**Sample stderr with `s=1:t=10`:**
```
[scdet @ 0x...] lavfi.scd.score: 14.237 lavfi.scd.time: 23.458
[scdet @ 0x...] lavfi.scd.score: 22.001 lavfi.scd.time: 45.771
```

**Regex:** `r"lavfi\.scd\.score:\s*([\d.]+).*?lavfi\.scd\.time:\s*([\d.]+)"`

**Recipe (auto-chapters):** dump scores to file, pick cuts over threshold, emit `CHAPTER##=hh:mm:ss.ms` entries, or feed the times to concat-style segmenting in **ffmpeg-cut-concat**.

---

## idet

Interlace detection.

**Options:**
| name | default | description |
|---|---|---|
| `intl_thres` | 1.04 | interlace confidence threshold |
| `prog_thres` | 1.5 | progressive confidence threshold |
| `rep_thres` | 3.0 | repeat confidence threshold |
| `half_life` | 0 | frames for statistics weight to halve (0 = all-history) |

**Sample stderr (end of run):**
```
[Parsed_idet_0 @ 0x...] Repeated Fields: Neither: 996 Top:    2 Bottom:   2
[Parsed_idet_0 @ 0x...] Single frame detection: TFF:  872 BFF:    3 Progressive:  125 Undetermined:  0
[Parsed_idet_0 @ 0x...] Multi frame detection:  TFF:  982 BFF:    3 Progressive:   15 Undetermined:  0
```

**Interpretation:**
- *Single frame detection* looks at one frame in isolation — noisy.
- *Multi frame detection* uses temporal context — **use this for decisions**.
- *Repeated fields* counts telecine pull-down pattern signals (non-zero Top/Bottom → 3:2 pulldown likely).
- "Current TFF" vs "multi TFF": the current-line is a running counter; the summary block at the end is the total.

**Decision rule of thumb:**
- `progressive > 90%` of total → no deinterlace.
- `TFF` dominant → `-vf yadif=1:0` (or `bwdif=0:0:0`) for TFF.
- `BFF` dominant → `-vf yadif=1:1` (or `bwdif=0:1:0`) for BFF.
- Repeated fields non-zero → source is telecined; consider `fieldmatch,yadif` or `pullup,fps=24000/1001`.

Run on ≥1000 frames for confidence. Re-run on multiple segments if mixed.

---

## signalstats

Broadcast QC per-frame statistics.

**Frame metadata keys** (all under `lavfi.signalstats.*`):
| key | meaning |
|---|---|
| `YMIN`, `YMAX`, `YAVG` | luma min/max/average |
| `UMIN`, `UMAX`, `UAVG` | chroma U |
| `VMIN`, `VMAX`, `VAVG` | chroma V |
| `SATMIN`, `SATMAX`, `SATAVG` | saturation min/max/average |
| `HUEMED`, `HUEAVG` | hue median/average |
| `YDIF`, `UDIF`, `VDIF`, `SATDIF` | temporal differences |
| `TOUT` | temporal outlier fraction (pixel dropouts) |
| `VREP` | vertical repeat (duplicate-line fraction) |

**Extraction pattern:**
```
ffmpeg -hide_banner -i IN -vf "signalstats,metadata=mode=print:file=-" \
  -an -f null - 2>&1 | grep lavfi.signalstats
```

**QC rules (legal/broadcast-safe, 8-bit limited range):**
- `YMIN < 16` or `YMAX > 235` → out of legal range.
- `SATMAX > 118.2` → over 75% saturation limit (NTSC bars).
- `TOUT > 0.005` → pixel-level dropouts / noise spikes.
- `VREP > 0.5` → possible frame-repeat or stuck interlace field.

---

## readeia608

Read CEA-608 bytes from VBI lines of SD broadcast content.

**Options:**
| name | default | description |
|---|---|---|
| `scan_min` / `scan_max` | 0 / 29 | VBI line range to scan |
| `spw` | 0.27 | sync-pulse width |
| `chp` | 0 | enable parity check |
| `lp` | 1 | enforce line parity |

Writes `lavfi.readeia608.N.cc` (raw bytes, field 1/2) per frame. Does NOT handle CEA-708, teletext, or DVB subs — for those, see the **ffmpeg-captions** skill.

Quick 608 → SRT (simplified — CC1 only, approximate):
```
ffmpeg -i broadcast.ts -vf readeia608 -c:s srt out.srt
```

Real conversions usually need ccextractor or a dedicated 608 decoder — use the **ffmpeg-captions** skill.

---

## readvitc

Read VITC (vertical interval timecode) from the video image.

**Options:**
| name | default | description |
|---|---|---|
| `scan_max` | 45 | maximum scanline to check |
| `thr_b` | 0.2 | black threshold |
| `thr_w` | 0.6 | white threshold |

Writes `lavfi.readvitc.tc_str=HH:MM:SS:FF` per frame.

---

## volumedetect

Peak and mean dBFS levels for an audio stream (NOT LUFS).

**Sample stderr (end of run):**
```
[Parsed_volumedetect_0 @ 0x...] n_samples: 4410000
[Parsed_volumedetect_0 @ 0x...] mean_volume: -22.4 dB
[Parsed_volumedetect_0 @ 0x...] max_volume: -1.3 dB
[Parsed_volumedetect_0 @ 0x...] histogram_0db: 3
...
```

**Regex:** `r"mean_volume:\s*([\-\d.]+)\s*dB"`, `r"max_volume:\s*([\-\d.]+)\s*dB"`

For EBU R128 / ITU-R BS.1770 loudness (LUFS), use `loudnorm=print_format=summary` from the **ffmpeg-audio-filter** skill — volumedetect is a peak tool, not a loudness meter.

---

## astats

Detailed per-stream audio statistics (DC offset, RMS, peak, flat/zero factor, etc.).

```
ffmpeg -hide_banner -i IN -af astats=metadata=1:reset=0 -f null - 2>&1 | grep lavfi.astats
```

Useful before `loudnorm` to detect extreme DC offset or dead channels.

---

## Recipes

### 1. Auto-chapter from scdet

```bash
ffmpeg -hide_banner -i movie.mkv -vf "scdet=s=1:t=15" -f null - 2>&1 \
  | awk '/lavfi.scd.time/ {for(i=1;i<=NF;i++) if($i~/time:/) print $(i+1)}'
# → list of cut timestamps; feed into ffmetadata chapters or segment muxer
```

### 2. Silence-trim pipeline

```bash
# Step 1: detect
python3 detect.py silences --input in.wav --noise-db -35 --min-duration 0.7 > sil.json
# Step 2: invert to "keep" ranges in your script, then:
ffmpeg -i in.wav -ss 0    -to 12.3  -c copy part01.wav
ffmpeg -i in.wav -ss 14.8 -to 120.4 -c copy part02.wav
# Step 3: concat demuxer — see ffmpeg-cut-concat skill
```

### 3. Broadcast QC pass

```bash
ffmpeg -hide_banner -i master.mov \
  -vf "signalstats,metadata=mode=print:file=qc.log" -an -f null -
# Then grep for violations:
awk -F'=' '/YMAX=/ && $2+0 > 235   {print "OUT-OF-RANGE: "$0}' qc.log
awk -F'=' '/SATMAX=/ && $2+0 > 118 {print "OVER-SAT: "$0}'    qc.log
awk -F'=' '/TOUT=/   && $2+0 > 0.005 {print "DROPOUT: "$0}'   qc.log
```

### 4. Combined detect-and-act: autocrop + deinterlace + trim silence

```bash
CROP=$(python3 detect.py crop      --input in.mkv)         # crop=1920:800:0:140
ILACE=$(python3 detect.py interlace --input in.mkv | jq -r .decision)
VF="$CROP"
case "$ILACE" in
  interlaced-tff) VF="$VF,yadif=1:0" ;;
  interlaced-bff) VF="$VF,yadif=1:1" ;;
esac
ffmpeg -i in.mkv -vf "$VF" -c:v libx264 -crf 19 -c:a copy out.mp4
```
