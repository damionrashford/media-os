# media-batch reference

Deep reference for GNU parallel, xargs, joblog forensics, sizing, and recipe patterns. Load when SKILL.md's Step 3/4 aren't enough.

## GNU parallel vs. xargs

| Capability | GNU parallel | xargs -P |
|---|---|---|
| Fan out N jobs concurrently | yes (`-j N`) | yes (`-P N`) |
| Auto-quote `{}` | yes | no — must wrap in `"{}"` |
| Null-separated input | yes (`-0` or `--null`) | yes (`-0`) |
| Per-job log with exit codes | yes (`--joblog`) | no |
| Resume failed jobs after a crash | yes (`--resume-failed`) | no |
| Retry failed jobs | yes (`--retries N`) | no |
| Progress bar | yes (`--bar`) | no |
| Per-job stdout/stderr saved | yes (`--results DIR`) | no |
| Placeholder substitutions (`{.}`, `{/}`, `{//}`, `{#}`, `{=perl=}`) | yes | `-I {}` only (single var) |
| SSH fan-out across hosts | yes (`--sshloginfile`) | no |
| Citation nag once | yes (`--citation`) | no |
| Preinstalled on every Unix | usually | yes |

Pick xargs only when you can't install parallel (locked-down container, embedded). Everywhere else, parallel is strictly more capable.

Note on Debian/Ubuntu: there are two binaries called `parallel` — GNU parallel (package `parallel`) and `moreutils`' `parallel` (package `moreutils`). Only GNU parallel has `--joblog`, `--resume-failed`, `--bar`. Verify with `parallel --version | head -1`.

## GNU parallel placeholders

Given input line `/archive/clips/2024/shoot-01.mov`:

| Placeholder | Expands to | Example |
|---|---|---|
| `{}`  | whole input, auto-quoted | `/archive/clips/2024/shoot-01.mov` |
| `{.}` | input minus extension | `/archive/clips/2024/shoot-01` |
| `{/}` | basename | `shoot-01.mov` |
| `{//}` | dirname | `/archive/clips/2024` |
| `{/.}` | basename minus extension | `shoot-01` |
| `{#}` | job sequence number (1-indexed) | `42` |
| `{%}` | job slot number (1..N) | `3` |
| `{=perl expr=}` | arbitrary perl on `$_` | `{= s/\.mov$/.mp4/ =}` → `shoot-01.mp4` |
| `{1}`, `{2}` | with `-a file -a file` or `:::` multi-input, selects column/arg | — |

Chain them: `out/{//}/{/.}.mp4` preserves directory structure and swaps extension.

Multi-input:
```bash
parallel echo {1} -> {2} ::: a b c ::: 1 2 3
# 9 jobs: all pairs
```

## joblog schema

`--joblog FILE` produces a tab-separated file with a header:

```
Seq  Host  Starttime     JobRuntime  Send  Receive  Exitval  Signal  Command
1    :     1713368425.7  12.344      0     0        0        0       ffmpeg -i a.mov ...
2    :     1713368425.9  8.112       0     0        1        0       ffmpeg -i b.mov ...
3    host-2  1713368438.1  61.002    1024  2048     0        0       ffmpeg -i c.mov ...
```

Columns:

| Field | Meaning |
|---|---|
| Seq | 1-indexed input order |
| Host | `:` for local; hostname for SSH |
| Starttime | unix epoch (float seconds) |
| JobRuntime | wall-clock seconds |
| Send / Receive | bytes transferred when using `--transferfile` / `--return` |
| Exitval | command exit code (see below) |
| Signal | signal number that killed the job (0 if none) |
| Command | the exact command line parallel ran |

Exit-code triage:

| Exitval | Meaning | Typical cause |
|---|---|---|
| 0 | success | — |
| 1 | ffmpeg/tool reported failure | bad input, unsupported codec, out-of-space |
| 2 | shell misuse | quoting bug in the command template |
| 127 | command not found | `PATH` missing in cron / SSH env |
| 130 | SIGINT | Ctrl-C |
| 137 | SIGKILL | OOM-killer, `kill -9` |
| 143 | SIGTERM | manual termination |
| 255 | job killed by parallel | `--timeout`, `--halt`, worker crash |

Quick queries:

```bash
# count by exitcode
awk 'NR>1 {c[$7]++} END {for (k in c) print k, c[k]}' jobs.log

# failed commands only
awk -F '\t' 'NR>1 && $7!=0 {print $7 "\t" $NF}' jobs.log

# jobs slower than 120s
awk -F '\t' 'NR>1 && $4>120 {print $4 "\t" $NF}' jobs.log | sort -rn

# median runtime
awk -F '\t' 'NR>1 {print $4}' jobs.log | sort -n | \
  awk '{a[NR]=$1} END {print (NR%2 ? a[(NR+1)/2] : (a[NR/2]+a[NR/2+1])/2)}'
```

## CPU / IO sizing

Rule of thumb:

```
jobs * threads_per_job  ~=  physical_cores     (CPU-bound)
jobs                    ~=  2 * spindles       (HDD, I/O-bound)
jobs                    ~=  cores              (SSD, many small files)
jobs                    ~=  1-2 per GPU engine (NVENC, VideoToolbox)
```

- ffmpeg software encoders (`libx264`, `libx265`, `libaom-av1`) parallelize internally; `-threads 0` lets ffmpeg choose, but in batch you want to cap it: `-threads 2` or `-threads 4`.
- Hardware encoders (NVENC, VideoToolbox, QSV) have a fixed number of concurrent sessions on the GPU. More `-j` than sessions = queueing and failures. Check GPU docs (NVENC consumer GPUs: 3–8 simultaneous sessions).
- Images and audio: startup dominates. Go wide: `-j $(nproc)` with `-threads 1`.
- NAS / NFS: usually `-j 2` to `-j 4` max. Use `iostat -x 1` to find the saturation point.

macOS portability: `nproc` is GNU-only. Use `sysctl -n hw.ncpu` (logical cores) or `hw.physicalcpu` (physical).

## Error detection patterns

Stream errors to a single log, append-safe:

```bash
parallel -j 4 '... 2>>errors.log' ::: *.mov
```

Per-job stdout/stderr trees:

```bash
parallel --results logs/ -j 4 '...' ::: *.mov
# logs/1/1/stderr, logs/1/1/stdout, logs/1/1/seq, logs/1/1/exitval, logs/1/1/time
```

Live error watch:

```bash
tail -f errors.log | grep -E -i 'error|invalid|failed|unable'
```

Classify ffmpeg errors:

| Message substring | Usually means |
|---|---|
| `Invalid data found when processing input` | truncated / corrupt input |
| `moov atom not found` | MP4 wasn't finalized (recording cut off) |
| `Conversion failed!` | generic — look above it for the real cause |
| `No such file or directory` | path with unescaped chars, or missing input |
| `Unknown encoder 'X'` | ffmpeg build lacks the codec (try `ffmpeg -encoders | grep X`) |
| `Error while opening encoder for output stream` | bad codec params (e.g. non-power-of-2 dim for yuv420p) |

## Docker batch patterns

Version-pinned:

```bash
find . -name '*.mov' | parallel -j 4 \
  'docker run --rm -v "$PWD":/w -w /w jrottenberg/ffmpeg:7.0 \
     -nostdin -y -i {} -c:v libx264 -crf 20 {.}.mp4'
```

GPU (NVENC):

```bash
find . -name '*.mov' | parallel -j 2 \
  'docker run --rm --gpus all -v "$PWD":/w -w /w jrottenberg/ffmpeg:7.0-nvidia \
     -nostdin -y -hwaccel cuda -i {} -c:v h264_nvenc -cq 22 {.}.mp4'
```

Use a local Dockerfile for custom filter builds; otherwise the `jrottenberg/ffmpeg` images are well-maintained.

Overhead: ~0.5–1.5s of container startup per job. Irrelevant for long encodes, devastating for 10k tiny jobs — skip Docker in that case.

## SSH distributed patterns

Hosts file (`nodes.txt`):

```
# jobs-per-host/user@host:port
4/encoder-1.lan
4/encoder-2.lan
8/bigbox.lan
```

Basic fan-out with file transfer:

```bash
parallel \
  --sshloginfile nodes.txt \
  --workdir . \
  --transferfile {} \
  --return {.}.mp4 \
  --cleanup \
  --joblog cluster.log \
  'ffmpeg -nostdin -y -i {} -c:v libx264 -crf 22 {.}.mp4' \
  ::: *.mov
```

Requirements:

- SSH key auth to every host (no password prompts).
- Same ffmpeg version / codec availability on every host — otherwise `--verbose` and probe: `parallel --nonall --sshloginfile nodes.txt 'ffmpeg -version | head -1'`.
- Clock skew matters for `--joblog` start times but not correctness.

Scale-up checklist:

1. `parallel --nonall --sshloginfile nodes.txt 'hostname; nproc'` — sanity-check hosts.
2. Dry-run: `parallel --dry-run --sshloginfile nodes.txt ...`.
3. Small batch first (10 files) to verify transfer + return works before unleashing 10k.
4. Local shared storage? Drop `--transferfile`/`--return`/`--cleanup` and use `--workdir /mnt/shared`.

## Recipe book

### Library transcode (idempotent, resumable)

```bash
cd /srv/library
find . -name "*.mkv" -o -name "*.avi" | parallel \
  --bar --joblog ~/transcode.log --resume-failed --timeout 7200 \
  -j 4 \
  'ffmpeg -nostdin -hide_banner -loglevel error -y -i {} \
     -c:v libx264 -crf 20 -preset slow -c:a aac -b:a 192k \
     -movflags +faststart \
     /srv/library-mp4/{/.}.mp4' \
  2>> ~/transcode-errors.log
```

- Rerun until `parallel status --joblog ~/transcode.log` shows 0 failed.
- `--timeout 7200` kills any single encode stuck over 2 hours.

### Photo batch (RAW → JPG, dimension-capped)

```bash
mkdir -p out
find shoot -iname '*.cr2' -print0 | \
  parallel -0 --bar --joblog dev.log -j "$(sysctl -n hw.ncpu)" \
  'magick {} -colorspace sRGB -resize 2048x2048\> -quality 90 -strip out/{/.}.jpg'
```

- `2048x2048\>` = fit inside, shrink-only.
- `-strip` removes EXIF (good for web; bad for archival — drop it if you need metadata).

### Podcast loudness normalize (EBU R128 streaming target)

```bash
find episodes -name "*.wav" | parallel --bar --joblog norm.log -j 4 \
  'ffmpeg-normalize {} \
     -t -16 -tp -1 -lra 11 \
     -c:a aac -b:a 192k \
     -o published/{/.}.m4a'
```

- `-t -16 -tp -1 -lra 11` = Apple Podcasts / Spotify target (Spotify now -14; adjust).
- `ffmpeg-normalize` runs a 2-pass loudnorm under the hood and preserves multi-track layouts.

### Scale-out encode across a cluster

```bash
parallel \
  --sshloginfile nodes.txt --workdir . \
  --transferfile {} --return {.}.mp4 --cleanup \
  --joblog cluster.log --resume-failed \
  'ffmpeg -nostdin -y -hide_banner -loglevel error \
     -i {} -c:v libx264 -crf 22 -c:a aac -b:a 192k {.}.mp4' \
  ::: *.mov
```

### Thumbnail sheet for a library

```bash
find videos -name '*.mp4' | parallel -j "$(nproc)" --bar --joblog thumbs.log \
  'ffmpeg -nostdin -y -i {} -vf "fps=1/10,scale=320:-1,tile=5x5" -frames:v 1 thumbs/{/.}.jpg'
```

### Probe-only (JSON per file)

```bash
find . -name '*.mp4' | parallel -j 8 \
  'ffprobe -v error -print_format json -show_format -show_streams {} > probe/{/.}.json'
```

### Delete only files successfully transcoded

After a run with `--joblog transcode.log`:

```bash
awk -F '\t' 'NR>1 && $7==0 {print $NF}' transcode.log | \
  grep -oE '[^ ]+\.mov' | xargs -I {} echo rm {}
# review, then drop the `echo`
```

### Cron-safe invocation

```cron
# /etc/cron.d/nightly-transcode
PATH=/usr/local/bin:/usr/bin:/bin
SHELL=/bin/bash
0 2 * * * ingest cd /srv/ingest && /usr/bin/find . -name '*.mov' | /usr/bin/parallel --joblog /var/log/transcode.log --resume --timeout 3600 -j 4 'ffmpeg -nostdin -y -i {} -c:v libx264 -crf 20 /srv/out/{/.}.mp4' >> /var/log/transcode.out 2>&1
```

Set `PATH` explicitly (cron's default is tiny); redirect both streams; use absolute binary paths if you've seen `command not found` in cron.

## Gotchas recap

- `-nostdin` on every ffmpeg in batch (not negotiable).
- `--joblog` + `--resume-failed` = cheap idempotence; always add them.
- Quote with `{}` in parallel; quote with `"{}"` in xargs.
- Use `-print0 | ... -0` on xargs pipelines.
- Watch exit 255 vs 1 to tell infra failure from encode failure.
- Stage NAS files to local SSD scratch for I/O-bound workloads.
- Cron needs `PATH`; SSH needs keys; `tmux` protects long runs from disconnects.
- `--timeout` prevents runaway stuck jobs from blocking workers forever.
