---
name: media-ytdlp
description: >
  Download videos, audio, playlists, and channels from YouTube, Twitch, Twitter/X, TikTok, Instagram, Vimeo, Facebook, and 1000+ other sites using yt-dlp. Use when the user asks to download a YouTube video, rip a playlist, grab a Twitch VOD, download audio as MP3, extract subtitles from a web video, get best-quality stream, download channel uploads, archive web video, or fetch media from any streaming site.
argument-hint: "[url]"
---

# Media yt-dlp

**Context:** $ARGUMENTS

`yt-dlp` is an actively-maintained fork of `youtube-dl`. Always prefer it — upstream `youtube-dl` is effectively dormant and its YouTube extractors break monthly. `yt-dlp` ships a far larger extractor set (1000+ sites), smarter format selection, throttling work-arounds, SponsorBlock hooks, and native post-processors.

## Quick start

- **Grab best quality (any codec/container):** `yt-dlp -f "bv*+ba/b" URL` → Step 3
- **Best MP4 (web/Apple friendly):** `yt-dlp -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" URL` → Step 3
- **Audio only MP3:** `yt-dlp -x --audio-format mp3 --audio-quality 0 URL` → Step 3
- **Cap at 1080p:** `yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" URL` → Step 2
- **Playlist / channel / live:** → Step 3
- **Subtitles, thumbnails, metadata:** → Step 4

## When to use

- Archiving a single YouTube / Twitch / Vimeo / Twitter / TikTok / Instagram clip.
- Ripping a playlist or entire channel uploads feed.
- Extracting audio (podcast, music, lecture) as MP3 / M4A / FLAC / Opus.
- Downloading a live stream from-the-start (DVR style) while it is still airing.
- Pulling subtitles / auto-generated captions for transcription.
- Feeding downloaded media into another ffmpeg skill (cut/concat, transcode, subtitle burn-in, etc.).

## Step 1 — Install and verify

```bash
# macOS (Apple Silicon + Intel). Homebrew installs yt-dlp AND ffmpeg cleanly.
brew install yt-dlp ffmpeg

# Or keep yt-dlp on the bleeding edge with pip (extractors break weekly; pip is fastest to refresh)
python3 -m pip install -U yt-dlp

# Verify
yt-dlp --version       # e.g. 2025.10.26
ffmpeg  -version | head -1
```

`yt-dlp` needs `ffmpeg` on `$PATH` whenever a site serves video and audio as separate streams (YouTube almost always does). Without `ffmpeg` the merge step silently fails and you get a video-only or audio-only file.

Update in-place without reinstalling:

```bash
yt-dlp -U                # binary builds
python3 -m pip install -U yt-dlp  # pip installs
```

## Step 2 — Pick a format

`yt-dlp -F URL` lists every available format (id, ext, resolution, fps, vcodec, acodec, tbr, size). Then build a selector:

| Goal | Selector |
| --- | --- |
| Absolute best (any codec) | `-f "bv*+ba/b"` |
| Best MP4 (H.264+AAC) | `-f "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]"` |
| Cap resolution | `-f "bv*[height<=1080]+ba/b[height<=1080]"` |
| Cap filesize (rough) | `-f "b[filesize<500M]"` |
| Prefer AV1 → VP9 → H.264 | `-f "bv*[vcodec=av01]+ba/bv*[vcodec=vp9]+ba/bv*+ba/b"` |
| Audio only | `-f "ba/b"` |

Selector grammar: `bv*` = best video (incl. muxed), `ba` = best audio, `b` = best single muxed file, `/` = fallback, `+` = merge. See `references/ytdlp.md` for filters and sort keys.

## Step 3 — Download

```bash
# Single URL, best quality, sensible filename.
yt-dlp -f "bv*+ba/b" --restrict-filenames \
  -o "%(uploader)s - %(title)s [%(id)s].%(ext)s" URL

# Playlist (each video in its own folder, 3-digit padded index).
yt-dlp -o "%(playlist)s/%(playlist_index)03d - %(title)s.%(ext)s" PLAYLIST_URL

# Entire channel uploads.
yt-dlp 'https://www.youtube.com/@channelname/videos'

# Twitch VOD (works with the direct /videos/ID URL).
yt-dlp -f best 'https://www.twitch.tv/videos/123456789'

# Live stream, from the current start marker (catch-up DVR).
yt-dlp --live-from-start URL

# Audio-only extraction, 320kbps MP3.
yt-dlp -x --audio-format mp3 --audio-quality 0 URL

# Archive mode — skip anything already grabbed. Safe to rerun forever.
yt-dlp --download-archive archive.txt -o "%(uploader)s/%(title)s.%(ext)s" URL
```

Helper script (`scripts/ytdlp.py`) wraps common subcommands: `check`, `list-formats`, `download`, `playlist`, `live`, `audio`.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ytdlp.py check
python3 ${CLAUDE_SKILL_DIR}/scripts/ytdlp.py download --url URL --quality 1080p --subs
python3 ${CLAUDE_SKILL_DIR}/scripts/ytdlp.py playlist --url URL --outdir ./dl --archive ./dl/archive.txt
```

## Step 4 — Post-process

yt-dlp's built-in post-processors handle most cases without shelling out to ffmpeg yourself:

```bash
# Embed thumbnail + chapter markers + metadata into a single MP4/M4A.
yt-dlp --embed-thumbnail --embed-metadata --embed-chapters URL

# Pull English subtitles (and auto-generated fallback) as .srt, embed into MKV.
yt-dlp --write-subs --write-auto-subs --sub-langs "en.*" \
       --convert-subs srt --embed-subs --merge-output-format mkv URL

# Save the full metadata sidecar (handy for pipelines).
yt-dlp --write-info-json --write-description --write-thumbnail URL

# Split a video with chapters into one file per chapter.
yt-dlp --split-chapters URL
```

For anything beyond embedding (trimming around ads, stitching multiple downloads, re-encoding to a specific codec), hand the output off to another skill:

- `ffmpeg-cut-concat` — trim / concat downloaded clips.
- `ffmpeg-transcode` — re-encode to a specific codec / CRF / container.
- `ffmpeg-subtitles` — burn or convert subtitle formats.
- `media-whisper` — re-transcribe when the site's captions are missing or bad.

## Available scripts

- **`scripts/ytdlp.py`** — argparse wrapper around the yt-dlp CLI. Subcommands: `check`, `list-formats`, `download`, `playlist`, `live`, `audio`. Stdlib only, `--dry-run` and `--verbose` for safe inspection.

## Reference docs

- Read [`references/ytdlp.md`](references/ytdlp.md) when you need the full format-selector grammar, the output-template field list, site-specific quirks (YouTube / Twitch / X / TikTok / IG / Vimeo / FB / Reddit / SoundCloud / Bandcamp), cookie strategies, or the recipe gallery.

## Gotchas

- **Always prefer `yt-dlp` over `youtube-dl`.** `youtube-dl` has not had a usable release cadence in years; yt-dlp is the community fork everyone actually uses.
- **`bv*+ba/b` means "best video + best audio, fallback to best muxed".** The `*` matters — without it you only match non-muxed video.
- **Merging requires ffmpeg on `$PATH`.** On macOS that means `brew install ffmpeg` (Apple Silicon Homebrew lives at `/opt/homebrew/bin`; Intel at `/usr/local/bin`). If ffmpeg is missing, fall back to `-f b` (single muxed file) or accept a video-only download.
- **Private / age-restricted / members-only / geo-blocked videos need cookies.** Use `--cookies-from-browser chrome` (or `firefox`, `safari`, `edge`, `brave`) — yt-dlp pulls the live session cookie. Manual `--cookies cookies.txt` also works but the Netscape file format is fiddly.
- **Rate-limit for polite scraping.** `-r 1M` caps throughput at 1 MB/s. `--sleep-interval 5 --max-sleep-interval 15` randomizes per-request pauses. On large channels / playlists this avoids 429 throttle bans.
- **Live streams.** Without `--live-from-start`, yt-dlp begins recording at "now" — you lose everything before you hit enter. With it, yt-dlp walks the HLS playlist back to the stream start.
- **Playlist index padding.** `%(playlist_index)03d` sorts correctly alongside shell tools; the bare `%(playlist_index)s` does not.
- **Output templates are Python `%()s` formatting.** Useful fields: `title`, `uploader`, `uploader_id`, `channel`, `upload_date` (`YYYYMMDD`), `id`, `ext`, `height`, `width`, `fps`, `vcodec`, `acodec`, `playlist`, `playlist_index`, `epoch`, `timestamp`.
- **`--restrict-filenames`** strips shell-unsafe characters (spaces, quotes, slashes, non-ASCII). Recommended for pipelines.
- **Subtitle embedding.** `--embed-subs` works best in MKV (supports SRT/ASS natively). For MP4, subtitles must be converted to `mov_text` — yt-dlp does this automatically when you combine `--embed-subs --merge-output-format mp4`.
- **Twitter / X.** Use the canonical URL form `https://twitter.com/user/status/ID` (or `x.com`). Both work; sometimes the x.com extractor lags — fall back to `twitter.com` if you see extractor errors.
- **TikTok / Instagram** frequently require `--cookies-from-browser` even for public posts (anti-bot gating).
- **Unsupported site?** `yt-dlp --list-extractors | grep -i <site>` shows every registered extractor. If the site is missing, try `--force-generic-extractor` — yt-dlp can often pull a naked `<video>` tag or HLS manifest.
- **`--merge-output-format mkv`** forces MKV when an MP4 merge is impossible (e.g. Opus audio + VP9 video). Prefer MKV over re-encoding.
- **Extractor broken?** Update first: `yt-dlp -U` or `pip install -U yt-dlp`. The fix is almost always already shipped on master.
- **403 / 429 errors** are usually geo-block or IP throttle. Try a VPN, rotate IP, or back off with `--sleep-interval`.
- **`--no-check-certificate`** disables TLS verification. Only use it on servers you control that have broken CA trust, and understand the MITM risk. Never use it on a shared laptop.

## Examples

### Example 1 — Archive a YouTube channel's uploads to MP4, skip already-downloaded

```bash
yt-dlp \
  --download-archive ./archive.txt \
  -f "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]" \
  --merge-output-format mp4 \
  --embed-thumbnail --embed-metadata --embed-chapters \
  --write-subs --write-auto-subs --sub-langs "en.*" --convert-subs srt \
  --restrict-filenames \
  -o "%(uploader)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s" \
  'https://www.youtube.com/@channelname/videos'
```

Rerunning the same command is idempotent — `archive.txt` tracks video IDs already fetched.

### Example 2 — Rip a podcast playlist as 320kbps MP3

```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 \
  --embed-thumbnail --embed-metadata \
  -o "%(playlist)s/%(playlist_index)03d - %(title)s.%(ext)s" \
  PLAYLIST_URL
```

### Example 3 — Record a live stream from the beginning

```bash
yt-dlp --live-from-start \
  -f "bv*+ba/b" \
  -o "%(uploader)s - %(title)s - %(upload_date)s.%(ext)s" \
  URL
```

Start this as soon as you notice the stream is live; yt-dlp holds the HLS manifest open until the stream ends.

## Troubleshooting

### Error: `ERROR: Requested format is not available`

Cause: selector matched zero formats (common after a site restricts a resolution tier or changes codec availability).
Solution: run `yt-dlp -F URL` to see what's actually offered, then relax the selector — e.g. drop the `[ext=mp4]` filter, or fall back to `-f b`.

### Error: `ERROR: ffprobe/ffmpeg not found`

Cause: yt-dlp cannot merge separate video+audio streams, or cannot run an audio-extraction post-processor.
Solution: `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Debian) / `choco install ffmpeg` (Windows). Verify `ffmpeg -version` on `$PATH`.

### Error: `HTTP Error 403: Forbidden` or `HTTP Error 429: Too Many Requests`

Cause: the site is rate-limiting or geo-blocking your IP, or the video requires auth.
Solution: add `--sleep-interval 5 --max-sleep-interval 30 -r 500K`, pass `--cookies-from-browser chrome`, or route through a VPN. For YouTube specifically, a logged-in cookie often unlocks throttled streams.

### Error: `ERROR: Unable to extract ...` / extractor tracebacks

Cause: the site changed its page structure; your yt-dlp is out of date.
Solution: `yt-dlp -U` (binary) or `pip install -U yt-dlp`. If still broken, check the issue tracker at github.com/yt-dlp/yt-dlp — fixes typically land within days.

### Error: live stream saves only the tail, not the full broadcast

Cause: you launched yt-dlp without `--live-from-start`.
Solution: add `--live-from-start`. For streams that have already ended, download the VOD instead (YouTube usually publishes one within minutes of end-of-stream).
