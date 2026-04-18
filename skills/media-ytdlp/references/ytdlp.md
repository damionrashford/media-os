# yt-dlp reference

Deep reference for the `media-ytdlp` skill. `SKILL.md` covers day-to-day recipes; this file is the "when I need to think about it" layer.

---

## 1. Format selector grammar

`yt-dlp -f SELECTOR URL`. The selector is a tiny expression language.

### Primitives

| Token | Meaning |
| --- | --- |
| `b`  | best single muxed (video+audio) format |
| `w`  | worst single muxed format |
| `bv` | best video-only format (no muxed) |
| `bv*`| best video-including-muxed |
| `ba` | best audio-only format (no muxed) |
| `ba*`| best audio-including-muxed |
| `wv` / `wa` | worst video / audio |
| `all` | every format |
| `<ID>` | pick a specific format-id from `-F` output |

### Operators

| Operator | Meaning | Example |
| --- | --- | --- |
| `A + B` | merge video A and audio B into one output | `bv+ba` |
| `A / B` | fallback: try A, else B | `bv*+ba/b` |
| `A , B` | multi-download: download both A and B separately | `bv,ba` |
| `A & B` | both must succeed | rarely used |

### Filters (bracketed)

Attach `[...]` filters directly to a primitive. Supported comparisons: `=`, `!=`, `<`, `<=`, `>`, `>=`, `^=` (starts-with), `$=` (ends-with), `*=` (contains).

Common fields: `height`, `width`, `fps`, `tbr` (total bitrate kbps), `vbr`, `abr`, `asr` (sample rate), `filesize`, `filesize_approx`, `ext`, `vcodec`, `acodec`, `protocol`, `container`, `language`.

```
bv*[height<=1080][fps<=30]+ba[ext=m4a]/b[height<=1080]
bv*[vcodec^=avc1]+ba[acodec^=mp4a]/b[ext=mp4]
ba[abr>=128][ext=m4a]
```

### Sort overrides (`-S`)

Instead of filters, bias selection with `-S "KEY1,KEY2,..."`. Prefix `+` (ascending), `-` (descending, default).

```
-S "res:1080,fps,vcodec:h264,acodec:aac,size,br"
```

This is the modern "prefer 1080p H.264 AAC MP4" pattern — more robust than long filter chains because it falls back gracefully.

---

## 2. Output template fields

Template syntax is Python `%(field)s` formatting, with type suffixes `d`, `s`, `03d`, etc. Full list via `yt-dlp --help` under "OUTPUT TEMPLATE".

| Field | Notes |
| --- | --- |
| `id` | site-specific video ID |
| `title` | video title (may contain `/`; pair with `--restrict-filenames`) |
| `ext` | final extension after merge (`mp4`, `mkv`, `webm`, ...) |
| `uploader` / `uploader_id` / `channel` / `channel_id` | creator identity |
| `upload_date` | `YYYYMMDD` — sortable |
| `timestamp` / `epoch` | UNIX seconds |
| `duration` | seconds (float) |
| `view_count` / `like_count` / `comment_count` | numeric |
| `height` / `width` / `fps` / `aspect_ratio` | |
| `vcodec` / `acodec` / `vbr` / `abr` / `tbr` | |
| `format_id` / `format_note` | selector debugging |
| `playlist` / `playlist_id` / `playlist_title` | |
| `playlist_index` / `playlist_count` / `n_entries` | zero-pad with `%(playlist_index)03d` |
| `autonumber` | increments 00001, 00002... per run |
| `chapter` / `chapter_number` / `section_start` / `section_end` | for `--split-chapters` |
| `release_date` / `release_timestamp` | distinct from `upload_date` on some sites |
| `language` | subtitle/audio language (site-specific) |

Examples:

```
-o "%(upload_date)s - %(uploader)s - %(title)s [%(id)s].%(ext)s"
-o "%(channel)s/Season 01/%(upload_date)s S01E%(playlist_index)02d - %(title)s.%(ext)s"
-o "archive/%(extractor)s/%(id)s.%(ext)s"
```

Advanced: `%(FIELD&REPLACEMENT|DEFAULT)s` (conditional), arithmetic `%(playlist_index+10)03d`, slicing `%(title).50s`.

---

## 3. Site-specific notes

### YouTube
- Cookies unlock age-restricted, members-only, private, unlisted.
- Throttled? Try `--extractor-args "youtube:player_client=web,web_safari,android,ios"`.
- Live-from-start: `--live-from-start`; premieres behave like live.
- Chapters are native — `--embed-chapters` or `--split-chapters` just work.
- `yt-dlp` bypasses SponsorBlock chapters with `--sponsorblock-remove sponsor,selfpromo,interaction`.

### Twitch
- VODs (`/videos/ID`) are straightforward. Use `-f best` (audio is already muxed into HLS).
- Clips: `/clips/SLUG`.
- Live channel: `twitch.tv/CHANNEL` downloads the current live broadcast. Combine with `--wait-for-video INTERVAL` to poll until online.
- Subscriber-only streams need `--cookies-from-browser`.

### Twitter / X
- Canonical URL: `https://twitter.com/USER/status/ID` or `x.com/...`. Both are routed.
- Adult-flagged / sensitive content requires login cookies.
- Spaces (audio-only live rooms): supported; grabs as M4A.

### TikTok
- Public videos usually work, but the site ships anti-bot JS that sometimes requires `--cookies-from-browser` even for non-auth URLs.
- Slideshows (image carousels) return multiple images + audio; yt-dlp will render one file with the image-sequence post-processor.

### Instagram
- Reels, posts, stories: all require cookies. `--cookies-from-browser` is the path of least resistance.
- Story URLs expire quickly (~24h); archive immediately.

### Vimeo
- Public and password-protected videos: `--video-password 'SECRET'`.
- Showcases / channels / groups: supported.
- Whitelabel / on-demand paid: usually requires cookies AND a paid session.

### Facebook
- Public video URLs generally work.
- Private / friends-only / group video requires cookies.
- Reels: `facebook.com/reel/ID` is supported.

### Reddit
- `reddit.com/r/X/comments/ID` — v.redd.it video+audio pulled and merged.
- NSFW subs need cookies.

### SoundCloud
- Streams: `-x --audio-format mp3` works. SoundCloud Go+ tracks need a logged-in cookie.

### Bandcamp
- Free streams download as 128k MP3. To get higher quality / paid tracks, download through the artist's own download page (yt-dlp handles the Bandcamp buyer download URL format).

### Generic / unsupported sites
- `--list-extractors | grep -i <site>` first.
- If missing, try `--force-generic-extractor` — yt-dlp sniffs `<video>` tags, HLS `.m3u8`, DASH `.mpd`, JW Player JSON, and more.

---

## 4. Cookies

### `--cookies-from-browser` (preferred)

```
--cookies-from-browser chrome
--cookies-from-browser firefox:default-release
--cookies-from-browser 'chrome:Profile 1'
--cookies-from-browser safari  # macOS only
--cookies-from-browser edge
--cookies-from-browser brave
--cookies-from-browser chromium
--cookies-from-browser opera
```

yt-dlp reads the live browser cookie DB. No export step. Session must be currently logged in.

Gotcha: on macOS Chrome/Chromium encrypt the cookie DB with the Keychain; yt-dlp will prompt for Keychain access the first time. Granting "Always Allow" avoids subsequent prompts.

### `--cookies FILE` (Netscape format)

```
--cookies cookies.txt
```

Netscape tab-separated format, easy to produce via browser extensions like "Get cookies.txt LOCALLY". Useful on headless servers where no browser is installed. Keep the file out of version control — it contains live session tokens.

---

## 5. Post-processors

yt-dlp ships an in-process post-processor chain. Flags that drive them:

| Flag | Post-processor | What it does |
| --- | --- | --- |
| `-x` | FFmpegExtractAudio | strip video, keep audio |
| `--audio-format FMT` | FFmpegExtractAudio | re-encode audio (mp3/m4a/flac/opus/wav/vorbis) |
| `--recode-video FMT` | FFmpegVideoConvertor | re-encode to a container |
| `--remux-video FMT` | FFmpegVideoRemuxer | stream-copy into a new container |
| `--embed-thumbnail` | EmbedThumbnail | stick cover art into MP3/M4A/MKV/MP4 |
| `--embed-metadata` | FFmpegMetadata | write title/artist/etc. tags |
| `--embed-chapters` | FFmpegMetadata | write chapter markers |
| `--embed-subs` | FFmpegEmbedSubtitle | mux subs into MKV/MP4 |
| `--convert-subs FMT` | FFmpegSubtitlesConvertor | srt / ass / lrc / vtt |
| `--split-chapters` | FFmpegSplitChapters | one output file per chapter |
| `--remove-chapters REGEX` | ModifyChapters | drop matching chapters from output |
| `--sponsorblock-remove CATS` | SponsorBlock + ModifyChapters | cut sponsor segments |
| `--write-info-json` | (not a PP) | sidecar JSON with all metadata |

Most of these shell out to ffmpeg under the hood — which is why `ffmpeg` must be on `$PATH`.

---

## 6. Archive mode

```
--download-archive archive.txt
```

yt-dlp records a single line per successful download (`EXTRACTOR ID\n`). On subsequent runs it skips already-recorded IDs. This is the idiomatic pattern for:

- Incremental channel archiving (cron-style).
- Playlist resumption after a crash.
- Multi-machine sync (rsync the archive file between boxes).

Combine with `--break-on-existing` to short-circuit an entire channel scrape once yt-dlp hits a known ID (faster for "only fetch what's new" style).

---

## 7. Rate limiting and politeness

| Flag | Effect |
| --- | --- |
| `-r 1M` | cap download to 1 MB/s |
| `--sleep-interval 5` | sleep ≥5s between downloads |
| `--max-sleep-interval 15` | random 5–15s |
| `--sleep-requests 0.5` | sleep between internal HTTP requests |
| `--sleep-subtitles N` | sleep between subtitle downloads |
| `--retries 10` | per-URL retry count (default 10) |
| `--fragment-retries 20` | HLS/DASH fragment retries |
| `--retry-sleep linear=1:10:2` | backoff schedule |
| `--limit-rate 500K` | alias for `-r` |
| `--concurrent-fragments 4` | parallel fragment downloads (careful — some sites 429) |

For a polite overnight channel archive: `-r 500K --sleep-interval 3 --max-sleep-interval 10 --retries 20`.

---

## 8. Recipe gallery

```bash
# 1. Best 4K HDR (VP9/AV1 preferred), MKV container
yt-dlp -S "res:2160,hdr,vcodec:vp9.2,vcodec:av01,vcodec:vp9" --merge-output-format mkv URL

# 2. Audio + embedded lyrics-as-subtitle
yt-dlp -x --audio-format m4a \
       --write-subs --sub-langs "en.*" --convert-subs lrc \
       --embed-thumbnail --embed-metadata URL

# 3. Download only new videos from a channel, into a Jellyfin-friendly tree
yt-dlp --download-archive archive.txt \
       --dateafter now-7days \
       -o "%(channel)s/Season 01/%(upload_date)s - %(title)s [%(id)s].%(ext)s" \
       --write-info-json --write-thumbnail \
       --convert-thumbnails jpg \
       'https://www.youtube.com/@channel/videos'

# 4. Grab a Twitch clip + its chat as JSON
yt-dlp --write-comments -o "%(title)s.%(ext)s" 'https://clips.twitch.tv/SLUG'

# 5. Strip sponsor segments from a YouTube video automatically
yt-dlp --sponsorblock-remove sponsor,selfpromo,interaction URL

# 6. Download a playlist in parallel (4 at a time). Each invocation is a shard.
yt-dlp --playlist-items 1,5,9,13 PLAYLIST_URL &
yt-dlp --playlist-items 2,6,10,14 PLAYLIST_URL &
yt-dlp --playlist-items 3,7,11,15 PLAYLIST_URL &
yt-dlp --playlist-items 4,8,12,16 PLAYLIST_URL &
wait

# 7. Extract every chapter of a long video as its own MP4
yt-dlp --split-chapters \
       -o "chapter:%(title)s/%(section_number)03d - %(section_title)s.%(ext)s" URL

# 8. Dump metadata only (no download) — useful for scraping
yt-dlp -J URL > metadata.json            # single JSON blob
yt-dlp --flat-playlist -J PLAYLIST_URL   # list without descending

# 9. Headless-server archive with cookies copied from a local browser session
#    (run locally first, ship cookies.txt, then run on server)
yt-dlp --cookies cookies.txt \
       --no-check-certificate \
       -f "bv*+ba/b" URL

# 10. Live-from-start with 24h cap (abort if stream is too long)
yt-dlp --live-from-start --download-sections "*0-86400" URL
```

---

## 9. Debugging

- `-v` / `--verbose`: full extractor traceback, network dump.
- `-J`: print parsed metadata JSON and exit (useful to see exactly what the extractor sees).
- `--print FORMAT`: custom one-liner per video (`--print "%(id)s %(title)s"` for listing).
- `--simulate`: go through the motions, skip actual download.
- `--skip-download`: download subs/thumbnails/metadata, skip the video.
- `--cache-dir /tmp/ytdlp-cache` / `--rm-cache-dir`: clear cached extractor state when fixing a broken extractor.
