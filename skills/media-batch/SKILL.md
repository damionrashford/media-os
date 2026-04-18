---
name: media-batch
description: >
  Batch ffmpeg and media processing at scale with GNU parallel, xargs, and shell patterns: parallel transcode fleets, shard jobs across cores, log aggregation, retry logic, idempotent pipelines, find + parallel recipes, progress reporting. Use when the user asks to batch transcode a folder, parallelize ffmpeg jobs, use GNU parallel with ffmpeg, build a media processing pipeline at scale, process a large media library, or scale ffmpeg to many cores with safe job isolation.
argument-hint: "[pattern]"
---

# Media Batch

**Context:** $ARGUMENTS

Fan a single ffmpeg/ImageMagick/ffmpeg-normalize command out across a folder (or a cluster) with GNU parallel, a joblog, and resume-on-failure. The goal is senior devops-for-media quality: idempotent reruns, no lost work, CPU/IO sized to the machine, no interactive prompts.

## Quick start

- **Transcode a folder of MOVs to MP4:** → Step 3, "simple parallel transcode"
- **Resume a batch that failed halfway:** → Step 4, `--resume-failed`
- **Batch resize a photo library:** → Step 3, ImageMagick recipe
- **Loudness-normalize a podcast library:** → Step 3, `ffmpeg-normalize` recipe
- **Distribute encodes across SSH nodes:** → Step 3, `--sshloginfile`
- **Turn an ad-hoc shell one-liner into a managed pipeline:** → use `scripts/batch.py`

## When to use

- 10+ files to process with the same operation.
- You want progress bars, per-job logs, retries, and resume without writing a queue system.
- You need idempotent reruns (rerunning the command skips what already succeeded).
- You want to shard across local cores today and SSH nodes tomorrow with the same command.

Not for: single-file jobs (just run ffmpeg directly); pipelines where each step depends on the previous file (parallel doesn't orchestrate DAGs — use a Makefile); realtime streams.

## Step 1 — Install GNU parallel

```bash
# macOS
brew install parallel

# Debian/Ubuntu
sudo apt install parallel

# RHEL/Fedora
sudo dnf install parallel

# verify
parallel --version | head -1
```

First run pops a citation notice — silence it once: `parallel --citation` (answer "will cite").

`xargs` is preinstalled everywhere and works for simple fan-out, but has no joblog, no retry, no resume, no progress bar. Use GNU parallel for anything you actually care about; reach for `xargs -P` only inside one-liners where parallel isn't available.

## Step 2 — Pick a parallelism model

Decide two numbers before running anything:

- **`-j` (jobs in flight):** how many ffmpeg processes run at once.
- **`-threads` per ffmpeg:** how many threads each process uses internally.

Total CPU pressure ≈ `jobs × threads-per-job`. Two working defaults:

| Profile | `-j` | ffmpeg `-threads` | Best for |
|---|---|---|---|
| Many small files | `$(nproc)` (or `sysctl -n hw.ncpu` on macOS) | `1` | Short clips, images, audio — startup overhead dominates |
| Few big files | `2`–`4` | `4`–`8` | Long H.264/HEVC/AV1 encodes — per-job parallelism scales better |
| I/O-bound (NAS, spinning disk) | `2` | `2` | Storage is the bottleneck, not CPU |
| GPU (NVENC/QSV/VideoToolbox) | `1`–`2` | n/a | One encode per GPU engine; more causes contention |

Shortcuts: `-j +0` = 100% of cores, `-j 50%` = half, `-j 200%` = 2× (useful when jobs are I/O-bound and CPU sits idle during reads).

## Step 3 — Run

### Simple parallel transcode (MOV → MP4)

```bash
find . -name "*.mov" | parallel -j 4 \
  'ffmpeg -nostdin -hide_banner -loglevel error -y -i {} \
     -c:v libx264 -crf 20 -preset medium \
     -c:a aac -b:a 192k \
     {.}.mp4'
```

Placeholders: `{}` = input path (auto-quoted), `{.}` = path without extension, `{/}` = basename only, `{//}` = dirname, `{#}` = job index.

### Always dry-run first

```bash
find . -name "*.mov" | parallel --dry-run -j 4 'ffmpeg -i {} ... {.}.mp4' | head
```

Read the first few commands. If they look right, drop `--dry-run`.

### Progress bar + joblog + resume

```bash
find . -name "*.mov" | parallel --bar --joblog jobs.log -j 4 \
  'ffmpeg -nostdin -hide_banner -loglevel error -y -i {} \
     -c:v libx264 -crf 20 -c:a aac {.}.mp4'

# something failed or you Ctrl-C'd — resume only the failures
parallel --resume-failed --joblog jobs.log -j 4 \
  'ffmpeg -nostdin ... {.}.mp4' :::: <(find . -name "*.mov")

# resume un-attempted work too (e.g. new files added since)
parallel --resume --joblog jobs.log ...
```

`--joblog` + `--resume-failed` is the single most important idiom. Treat your parallel invocation as idempotent: rerun it as many times as needed, it only touches outstanding work.

### Idempotent by output check

Belt-and-braces alongside `--joblog`:

```bash
find . -name "*.mov" | parallel -j 4 \
  '[ -f {.}.mp4 ] || ffmpeg -nostdin -y -i {} -c:v libx264 -crf 20 {.}.mp4'
```

### Batch image resize with ImageMagick

```bash
find photos -name "*.jpg" | parallel --bar --joblog resize.log -j "$(nproc)" \
  'magick {} -resize 1280x1280\> -quality 85 -strip out/{/}'
```

### Batch loudness normalize with ffmpeg-normalize

```bash
pipx install ffmpeg-normalize  # once

find podcast -name "*.wav" | parallel --bar --joblog norm.log -j 4 \
  'ffmpeg-normalize {} -t -16 -c:a aac -b:a 192k -o out/{/.}.m4a'
```

### xargs fallback (no parallel installed)

```bash
find . -name "*.mov" -print0 | \
  xargs -0 -P 4 -I {} ffmpeg -nostdin -y -i "{}" -c:v libx264 -crf 20 "{}.mp4"
```

`-print0` + `-0` is mandatory — without it, filenames with spaces/newlines break.

### Distribute across SSH nodes

```bash
cat > nodes.txt <<'EOF'
4/encoder-1.lan
4/encoder-2.lan
8/encoder-3.lan
EOF

find . -name "*.mov" | parallel \
  --sshloginfile nodes.txt \
  --workdir . \
  --transferfile {} \
  --return {.}.mp4 \
  --cleanup \
  --joblog cluster.log \
  'ffmpeg -nostdin -y -i {} -c:v libx264 -crf 20 {.}.mp4'
```

The `4/host` prefix sets `-j` per node. `--transferfile` ships the input, `--return` pulls the output back, `--cleanup` wipes remote temp.

### Dockerized batch (reproducibility)

```bash
find . -name "*.mov" | parallel -j 4 \
  'docker run --rm -v "$PWD":/w -w /w jrottenberg/ffmpeg:7.0 \
     -nostdin -y -i {} -c:v libx264 -crf 20 {.}.mp4'
```

Adds ~1s/container overhead — only worth it for version-pinned reproducibility.

### Low-priority background batch

```bash
nice -n 19 ionice -c 3 parallel -j 2 --bar --joblog jobs.log \
  'ffmpeg -nostdin ...' ::: *.mov
```

`nice` = CPU priority, `ionice -c 3` = idle-class I/O. Lets you transcode a library without freezing your desktop.

## Step 4 — Monitor and retry

```bash
# tail errors live
tail -f errors.log | grep -E -i 'error|invalid|failed'

# joblog summary (columns: Seq Host Starttime JobRuntime Send Receive Exitval Signal Command)
awk 'NR>1 {c[$7]++} END {for (k in c) print k, c[k]}' jobs.log

# re-run only failures with up to 3 retries
parallel --retry-failed --retries 3 --joblog jobs.log ...

# kill on any error (for CI where one failure = abort)
parallel --halt now,fail=1 --joblog jobs.log ...

# kill runaway jobs after 10 minutes each
parallel --timeout 600 --joblog jobs.log ...
```

Exit codes in joblog: `0` = success, `1` = ffmpeg encode error, `255` = job killed (Ctrl-C, timeout, signal). If you see a mix, address 255 first (infrastructure) before retrying 1 (data).

## Gotchas

- **`-nostdin` is mandatory in batch.** Without it, ffmpeg reads from the terminal, blocks or eats keystrokes, and mysteriously hangs jobs. Never use `< /dev/null` as a workaround — use `-nostdin`.
- **Always pass `-y` (overwrite) or `-n` (no-clobber).** Interactive "Overwrite? [y/N]" prompts freeze parallel workers forever.
- **Quiet logs: `-hide_banner -loglevel error`.** ffmpeg prints megabytes of banner/progress noise per job. Without this, `parallel --bar` is unreadable.
- **`{}` in GNU parallel is auto-quoted; in xargs it is not.** Always quote `"{}"` in xargs (`-I {}`) for files with spaces. `parallel` handles it for you.
- **`find | xargs` without `-print0 -0` is a footgun.** Spaces, quotes, newlines in filenames will split one path into multiple args. Null-terminate.
- **GNU parallel vs. `moreutils` parallel.** Debian/Ubuntu may ship both. `which parallel` — if it's `/usr/bin/parallel` from moreutils, install GNU parallel (`apt install parallel`) — the flags in this doc require GNU.
- **`-j +0` = 100% CPUs and can thrash.** On a laptop, prefer `-j 50%` or `-j $(nproc)-1` so the machine stays usable.
- **I/O, not CPU, is usually the ceiling on NAS/spinning disks.** Measure with `iostat -x 1` or `nfsstat`. Use local SSD scratch (`/tmp`, `/var/tmp`) for temp and copy the result back.
- **Total threads = `-j × -threads`.** If `-j 8` and ffmpeg `-threads 8`, you have 64 software threads fighting for 8 cores — slower than `-j 8 -threads 1` or `-j 2 -threads 8`.
- **`--resume-failed` only works with `--joblog`.** If you forgot `--joblog`, parallel has no state and will rerun everything.
- **Per-job log files via `--results DIR`.** Each job gets `DIR/1/seq/<n>/{stdout,stderr,seq,exitval,time}`. Invaluable when ten jobs fail with cryptic errors — grep `DIR/*/stderr`.
- **Collect errors in one file: `2>> errors.log`.** Safe because append-writes under 4KB are atomic on POSIX; each job's stderr blob lands intact.
- **Docker containers add ~1s startup per job.** Fine for a 30-min encode, awful for 10k thumbnails.
- **Network mounts: stage to local scratch.** `rsync` in, transcode on local SSD, `rsync` out. Cuts random-IO seek storms.
- **Cron: set `PATH`.** `crontab -e` environments don't inherit your shell's PATH — ffmpeg and parallel will be "not found" even though they work interactively. Set `PATH=/usr/local/bin:/usr/bin:/bin` at the top of the crontab.
- **Long batches: use `tmux` or `screen`.** An SSH drop kills your parallel process. `tmux new -s batch` then `Ctrl-b d` to detach, `tmux a -t batch` to reattach.
- **Signal handling: `trap` SIGTERM/SIGINT for cleanup.** If your wrapper script creates temp dirs, trap and `rm -rf` them on exit; otherwise Ctrl-C leaves orphans.
- **OOM on huge batches: `-j` too high.** ffmpeg memory scales with resolution and codec. 4K HEVC at `-j 16` will OOM an 8GB box. Watch `dmesg | grep -i oom`.
- **`--timeout N` kills runaways.** A broken input that loops forever will hog a worker slot until you timeout it.

## Available scripts

- **`scripts/batch.py`** — stdlib-only wrapper. Subcommands: `check`, `transcode`, `resize`, `audio-normalize`, `status`, `retry`. Generates the parallel command; runs it unless `--dry-run`.

Usage:

```bash
# preflight
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py check

# transcode a folder
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py transcode \
  --indir ~/Videos/raw --outdir ~/Videos/mp4 \
  --pattern "*.mov" \
  --ffmpeg-args "-c:v libx264 -crf 20 -c:a aac" \
  --joblog jobs.log --jobs 4

# image resize with ImageMagick
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py resize \
  --indir photos --outdir out --width 1280 --pattern "*.jpg"

# loudness normalize
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py audio-normalize \
  --indir podcast --outdir podcast/norm --target -16

# check status of a run
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py status --joblog jobs.log

# retry only the failed jobs
uv run ${CLAUDE_SKILL_DIR}/scripts/batch.py retry --joblog jobs.log
```

Every subcommand supports `--dry-run` (prints the parallel command) and `--verbose`.

## Reference docs

- Read [`references/batch.md`](references/batch.md) for the placeholder cheatsheet, joblog schema, CPU/IO sizing formulas, Docker/SSH patterns, and a recipe book (library transcode, photo batch, podcast normalize, scale-out encode).

## Examples

### Library transcode, resumable

```bash
find library -name "*.mkv" | parallel \
  --bar --joblog transcode.log --resume-failed \
  -j 4 \
  'ffmpeg -nostdin -hide_banner -loglevel error -y -i {} \
     -c:v libx264 -crf 20 -preset slow -c:a aac -b:a 192k \
     out/{/.}.mp4' 2>> transcode-errors.log
```

Kick it off. Machine reboots? Same command — resumes where it stopped.

### Photo batch with ImageMagick

```bash
mkdir -p out
find shoot -iname "*.cr2" -print0 | \
  parallel -0 --bar --joblog dev.log -j "$(sysctl -n hw.ncpu)" \
  'magick {} -colorspace sRGB -resize 2048x2048\> -quality 90 out/{/.}.jpg'
```

### Podcast normalize (EBU R128)

```bash
find episodes -name "*.wav" | parallel --bar --joblog norm.log -j 4 \
  'ffmpeg-normalize {} -t -16 -tp -1 -lra 11 \
     -c:a aac -b:a 192k -o published/{/.}.m4a'
```

### Scale-out encode across 3 machines

```bash
parallel --sshloginfile nodes.txt --workdir . \
  --transferfile {} --return {.}.mp4 --cleanup \
  --joblog cluster.log \
  'ffmpeg -nostdin -y -i {} -c:v libx264 -crf 22 {.}.mp4' \
  ::: *.mov
```

### Cron nightly: transcode whatever's new

```cron
PATH=/usr/local/bin:/usr/bin:/bin
0 2 * * * cd /srv/ingest && /usr/bin/parallel --joblog /var/log/transcode.log --resume --timeout 3600 -j 4 'ffmpeg -nostdin -y -i {} -c:v libx264 -crf 20 /srv/out/{/.}.mp4' ::: $(find . -name "*.mov")
```

## Troubleshooting

### ffmpeg jobs hang forever, no progress

Cause: missing `-nostdin`. ffmpeg is reading from the parallel worker's stdin and blocking.
Solution: add `-nostdin` to every ffmpeg invocation in the batch.

### "parallel: --joblog: unknown option"

Cause: you're running `moreutils` parallel, not GNU parallel.
Solution: `apt install parallel` (Debian/Ubuntu) or `brew install parallel` (macOS). Verify with `parallel --version | head -1` — it should say "GNU parallel".

### Output files empty or half-written after Ctrl-C

Cause: parallel killed ffmpeg mid-write; the partial file remains.
Solution: rerun with `--resume-failed --joblog jobs.log`. For max safety write to `{.}.tmp.mp4` then `mv` on success inside the quoted command.

### Some files fail with exit 255, others with exit 1

255 = job killed (signal, timeout, worker crash). 1 = ffmpeg encode failure (bad input, unsupported codec). Investigate 255 first — something is killing your workers. Filter: `awk '$7==255' jobs.log` and `awk '$7==1' jobs.log`.

### "Argument list too long"

Cause: `parallel ... ::: $(find ...)` with tens of thousands of files.
Solution: pipe: `find ... | parallel ...` — parallel reads stdin incrementally.

### Machine becomes unusable during batch

Cause: `-j` too aggressive.
Solution: `nice -n 19 ionice -c 3 parallel -j 50% ...`. Or cap jobs and re-run.

### Per-job logs are interleaved garbage

Cause: all jobs writing to the same stderr stream.
Solution: `parallel --results logdir/ ...` — each job gets its own `logdir/1/.../stderr` file.
