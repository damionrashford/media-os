# Media Cloud Upload — Reference

## 1. Service comparison

| Service            | Strengths                                          | Weaknesses                          | Pricing model (shape)          | Output formats                  |
|--------------------|----------------------------------------------------|-------------------------------------|--------------------------------|---------------------------------|
| Cloudflare Stream  | Auto ABR, HLS+DASH+MP4, global CDN, simple API     | Opinionated output, no custom LADDER | Per-minute stored + per-minute delivered | HLS, DASH, MP4, JPG thumb       |
| Mux Video          | Pro API, webhooks, analytics, simulcast, live      | More expensive at scale             | Per-minute encoded + delivered | HLS, thumbnails, animated GIFs  |
| Bunny Stream       | Cheap CDN, library model, transcode included       | Smaller PoP footprint               | Per-GB storage + delivery      | HLS, iframe embed, MP4          |
| AWS S3 + CloudFront| Total control, biggest ecosystem                   | DIY: you pre-encode ABR (MediaConvert) | Per-GB storage + per-GB transfer + requests | Whatever you upload             |
| YouTube Data API   | Free hosting, massive reach                        | Hard quota (10k/day), OAuth, ToS    | Free                           | YouTube-player URL, no HLS      |
| Vimeo              | Clean player, privacy controls                     | Weekly upload quota by tier         | Subscription tier              | HLS via Pro+, mp4 progressive   |
| rclone remotes     | Works with Drive/OneDrive/B2/R2/Dropbox/SFTP/...   | No transcode; just bytes            | Depends on underlying remote   | Raw files only                  |

## 2. Upload protocols cheatsheet

| Protocol              | Who uses it                                | When to pick it                              |
|-----------------------|--------------------------------------------|----------------------------------------------|
| Direct POST (multipart) | Cloudflare Stream ≤ 200 MB, Bunny (PUT)   | Small/medium files, single-shot              |
| TUS (tus.io)          | Cloudflare Stream > 200 MB, Vimeo          | Resumable, survives network drops            |
| Signed URL (PUT)      | Mux (from API), S3 presigned URLs          | Delegate upload to a client browser          |
| Multipart S3          | AWS S3 for > 5 GB files                    | Parallel chunks, retry per chunk             |
| Chunked resumable     | YouTube Data API (`MediaFileUpload`)       | Big uploads with auto-resume over HTTP       |
| rclone `copy`         | Any rclone remote                          | When you just want bytes mirrored            |

Rule of thumb: **if the file is > 200 MB or the network is flaky, pick a resumable protocol**.

## 3. Auth methods per service

| Service            | Auth                                                            |
|--------------------|-----------------------------------------------------------------|
| Cloudflare Stream  | Bearer token (scoped: `Stream:Edit`, `Stream:Read`)             |
| Mux                | HTTP Basic with `access_token_id` + `secret_key`                |
| Bunny Stream       | `AccessKey:` header (library-scoped key)                        |
| AWS S3             | SigV4 signed requests (via aws CLI / boto3 / IAM role)          |
| YouTube Data API   | OAuth 2.0 (installed-app or web flow); refresh token stored     |
| Vimeo              | Bearer token with `upload`, `edit` scopes                       |
| rclone             | Per-remote: OAuth token for Drive/OneDrive, keys for S3/B2, etc.|

Never hardcode. Always `os.environ[...]`. Prefer `.env` loaded by `direnv` or `1password` CLI.

## 4. Webhook + callback patterns

| Event                 | Cloudflare Stream                       | Mux                                                   |
|-----------------------|-----------------------------------------|-------------------------------------------------------|
| Upload finished       | `video.live_input.connected` / asset API | `video.upload.asset_created`                          |
| Transcode finished    | `video.stream.video_ready`              | `video.asset.ready`                                   |
| Transcode failed      | `video.stream.video_error`              | `video.asset.errored`                                 |
| Playback started      | N/A                                     | `video.asset.static_renditions.ready`                 |

Webhook hygiene:
- Verify HMAC signature on every request (`Mux-Signature` / `CF-Webhook-Auth`).
- Reply 2xx within 5 seconds; queue actual work.
- Idempotent handlers — webhooks retry and duplicate.
- Reserve a URL you control (Cloudflare Worker or Lambda behind API Gateway works well).

## 5. Output URL shapes

```
Cloudflare Stream
  HLS  :  https://customer-<code>.cloudflarestream.com/<uid>/manifest/video.m3u8
  DASH :  https://customer-<code>.cloudflarestream.com/<uid>/manifest/video.mpd
  MP4  :  https://customer-<code>.cloudflarestream.com/<uid>/downloads/default.mp4
  Thumb:  https://customer-<code>.cloudflarestream.com/<uid>/thumbnails/thumbnail.jpg
  Embed:  https://iframe.videodelivery.net/<uid>

Mux
  HLS  :  https://stream.mux.com/<playback_id>.m3u8
  Thumb:  https://image.mux.com/<playback_id>/thumbnail.jpg?time=1
  GIF  :  https://image.mux.com/<playback_id>/animated.gif?start=1&end=6
  MP4  :  https://stream.mux.com/<playback_id>/high.mp4   (static renditions)

Bunny Stream
  HLS  :  https://vz-<hash>.b-cdn.net/<video_id>/playlist.m3u8
  Thumb:  https://vz-<hash>.b-cdn.net/<video_id>/thumbnail.jpg
  Embed:  https://iframe.mediadelivery.net/embed/<lib_id>/<video_id>

S3 + CloudFront
  Direct : https://<bucket>.s3.<region>.amazonaws.com/<key>
  CDN    : https://<dist>.cloudfront.net/<key>
  Signed : aws s3 presign s3://<bucket>/<key> --expires-in 3600

YouTube
  Page :  https://youtu.be/<video_id>
  Embed:  https://www.youtube.com/embed/<video_id>

Vimeo
  Page :  https://vimeo.com/<video_id>
  Embed:  https://player.vimeo.com/video/<video_id>
```

## 6. Recipe book

### Recipe A — Post-encode → Cloudflare Stream

```bash
ffmpeg -i master.mov -c:v libx264 -crf 20 -preset slow -c:a aac -b:a 192k encoded.mp4
uv run scripts/cloud.py cloudflare-stream --file encoded.mp4 --verbose
# JSON: { "result": { "uid": "...", "preview": "...", "playback": { "hls": "..." } } }
```

Cloudflare runs its own ladder; you hand off a single H.264 MP4 and they ABR-package it.

### Recipe B — Podcast → S3 → CloudFront

```bash
ffmpeg -i raw.wav -c:a libmp3lame -b:a 128k ep42.mp3
uv run scripts/cloud.py s3 \
  --file ep42.mp3 --bucket my-podcast --key 2026/ep42.mp3 \
  --content-type audio/mpeg --acl public-read \
  --cache-control "public, max-age=31536000, immutable"
# RSS feed points at https://<dist>.cloudfront.net/2026/ep42.mp3
```

Use an immutable cache header + versioned filenames (hash or date) so you never invalidate CloudFront.

### Recipe C — CI → Mux on merge

`.github/workflows/publish.yml` sketch:

```yaml
- name: Transcode
  run: ffmpeg -i in.mov -c:v libx264 -crf 20 out.mp4
- name: Upload to Mux
  env:
    MUX_TOKEN: ${{ secrets.MUX_TOKEN }}
    MUX_SECRET: ${{ secrets.MUX_SECRET }}
  run: uv run scripts/cloud.py mux --file out.mp4 --verbose
- name: Wait for ready (webhook in prod; polling here)
  run: ./scripts/wait-mux-ready.sh "$ASSET_ID"
```

Wire Mux webhook → queue → site rebuild (Next.js ISR / Astro incremental) so the page only publishes after `video.asset.ready`.

### Recipe D — Archive renders to Backblaze B2 via rclone

```bash
rclone copy --progress --transfers 8 --checkers 16 \
  renders/ b2:my-archive/renders/$(date +%F)/
```

Runs happily on every local render, cheap cold storage, restorable via `rclone copy` in reverse.

### Recipe E — Mux with signed playback (JWT per play)

1. Create asset with `playback_policy: ["signed"]`.
2. Download signing key from Mux dashboard (`signing_key.pem`).
3. Per play, mint a short-lived JWT:
   ```python
   import jwt, time
   token = jwt.encode(
       {"sub": playback_id, "aud": "v", "exp": int(time.time()) + 3600, "kid": key_id},
       private_key, algorithm="RS256", headers={"kid": key_id},
   )
   url = f"https://stream.mux.com/{playback_id}.m3u8?token={token}"
   ```
4. Never expose the signing key; mint tokens server-side.

### Recipe F — YouTube upload from CI (one-time OAuth)

First run, local machine with browser:
```bash
python cloud.py youtube --file hello.mp4 --title "Setup" --privacy private
# browser opens → consent → token saved to ~/.config/yt-upload-token.json
```

Copy that JSON into a CI secret; subsequent runs reuse the refresh token silently. Remember: ~6 uploads/day before quota exhaustion.

### Recipe G — rclone mount for on-the-fly ffmpeg reads

```bash
rclone mount gdrive: /mnt/gdrive --vfs-cache-mode full &
ffmpeg -i /mnt/gdrive/archive/master.mov -c copy local.mp4
```

Great for pulling source files you don't want to persist locally.
