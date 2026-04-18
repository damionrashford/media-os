---
name: media-cloud-upload
description: >
  Upload processed media to cloud platforms: Cloudflare Stream, Mux Video, Bunny Stream, YouTube Data API, AWS S3 + CloudFront, Vimeo API, rclone to any cloud. Use when the user asks to upload to Cloudflare Stream, push to Mux, upload a video to YouTube, deploy to Bunny Stream, sync to S3, publish a finished encode to CDN, or distribute media to a video platform.
argument-hint: "[service] [file]"
---

# Media Cloud Upload

**Context:** $ARGUMENTS

## Quick start

- **Cloudflare Stream (fast, HLS+DASH auto):** → Step 3a
- **Mux Video (signed URL, pro API):** → Step 3b
- **Bunny Stream (cheap CDN):** → Step 3c
- **AWS S3 + CloudFront (DIY):** → Step 3d
- **YouTube (OAuth required):** → Step 3e
- **Vimeo (tus via PyVimeo):** → Step 3f
- **rclone to any cloud (Drive/OneDrive/B2/...):** → Step 3g

## When to use

- Finished ffmpeg encode needs adaptive-bitrate delivery (Cloudflare Stream / Mux).
- Raw MP4 needs to sit on a CDN with a URL (S3 + CloudFront, Bunny).
- Publishing to a consumer video platform (YouTube, Vimeo).
- Backup, archive, or sync media to arbitrary cloud storage (rclone).

## Step 1 — Pick a service and gather credentials

| Service            | Env vars                                     | Notes                               |
|--------------------|----------------------------------------------|-------------------------------------|
| Cloudflare Stream  | `CF_TOKEN`, `CF_ACCOUNT_ID`                  | API token with Stream:Edit          |
| Mux                | `MUX_TOKEN`, `MUX_SECRET`                    | Access-token pair (Basic Auth)      |
| Bunny Stream       | `BUNNY_KEY`, `BUNNY_LIB_ID`                  | Library-level AccessKey             |
| AWS S3             | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Or `~/.aws/credentials`             |
| YouTube Data API   | OAuth 2.0 client JSON + stored refresh token | Upload costs 1600 quota units       |
| Vimeo              | `VIMEO_TOKEN`                                | Personal access token, `upload` scope |
| rclone             | `rclone config` remote                       | Token stored in `~/.config/rclone`  |

Never commit tokens. Read from env only. Rotate leaked tokens immediately.

## Step 2 — Install SDK / CLI

```bash
# Universal: curl (present), rclone, aws CLI
brew install curl rclone awscli            # macOS
# YouTube + Vimeo
pip install google-api-python-client google-auth-oauthlib PyVimeo
# Resumable uploads (Cloudflare Stream / Vimeo TUS)
pip install tuspy
```

Check everything with:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cloud.py check
```

## Step 3 — Upload

### 3a. Cloudflare Stream

Direct upload (≤ 200 MB):

```bash
curl -X POST -H "Authorization: Bearer $CF_TOKEN" \
  -F "file=@video.mp4" \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/stream"
```

TUS resumable (any size, required > 200 MB):

```bash
# 1. Create upload URL
curl -X POST -H "Authorization: Bearer $CF_TOKEN" \
  -H "Tus-Resumable: 1.0.0" \
  -H "Upload-Length: $(stat -f%z video.mp4)" \
  -H "Upload-Metadata: name $(echo -n video.mp4 | base64)" \
  "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/stream?direct_user=true" -D -
# 2. Then PATCH the returned Location with tus-js-client or `tuspy`
```

Response includes `uid`; playback URLs:

```
https://customer-<code>.cloudflarestream.com/<uid>/manifest/video.m3u8     # HLS
https://customer-<code>.cloudflarestream.com/<uid>/manifest/video.mpd      # DASH
https://customer-<code>.cloudflarestream.com/<uid>/downloads/default.mp4   # MP4
https://customer-<code>.cloudflarestream.com/<uid>/thumbnails/thumbnail.jpg
```

### 3b. Mux Video

```bash
# 1. Create direct upload slot
curl -X POST -u $MUX_TOKEN:$MUX_SECRET \
  -H "Content-Type: application/json" \
  -d '{"new_asset_settings":{"playback_policy":["public"]},"cors_origin":"*"}' \
  https://api.mux.com/video/v1/uploads
# Response → .data.url
# 2. PUT the file to that signed URL
curl -X PUT --data-binary @video.mp4 "$SIGNED_URL"
# 3. Poll upload → asset_id → playback_ids[0].id
```

Playback: `https://stream.mux.com/<playback_id>.m3u8`, thumbnail `https://image.mux.com/<playback_id>/thumbnail.jpg`.

### 3c. Bunny Stream

```bash
# 1. Create video shell
curl -X POST -H "AccessKey: $BUNNY_KEY" -H "Content-Type: application/json" \
  -d '{"title":"My Clip"}' \
  "https://video.bunnycdn.com/library/$BUNNY_LIB_ID/videos"
# Response → .guid  (VIDEO_ID)
# 2. Upload bytes
curl -X PUT -H "AccessKey: $BUNNY_KEY" --upload-file video.mp4 \
  "https://video.bunnycdn.com/library/$BUNNY_LIB_ID/videos/$VIDEO_ID"
```

Playback: `https://iframe.mediadelivery.net/embed/$BUNNY_LIB_ID/$VIDEO_ID` or HLS at `https://vz-<hash>.b-cdn.net/$VIDEO_ID/playlist.m3u8`.

### 3d. AWS S3 + CloudFront

```bash
aws s3 cp video.mp4 s3://my-bucket/videos/clip.mp4 \
  --content-type video/mp4 --acl public-read --cache-control "max-age=31536000"
```

Pre-signed URL for private buckets:

```bash
aws s3 presign s3://my-bucket/videos/clip.mp4 --expires-in 3600
```

CloudFront: create a distribution with the bucket as origin, enable CORS, use the CloudFront URL (`https://d12345.cloudfront.net/videos/clip.mp4`).

### 3e. YouTube Data API v3

Requires OAuth 2.0 (installed-app flow). Run once with the user present to get a refresh token; subsequent runs are silent:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cloud.py youtube \
  --file video.mp4 --title "My Title" --description "desc" \
  --tags demo,ffmpeg --privacy unlisted
```

Uses `googleapiclient.http.MediaFileUpload` with resumable chunked upload.

### 3f. Vimeo

```python
import vimeo, os
v = vimeo.VimeoClient(token=os.environ["VIMEO_TOKEN"])
uri = v.upload("video.mp4", data={"name": "Clip", "description": "..."})
print(v.get(uri + "?fields=link,player_embed_url").json())
```

PyVimeo uses TUS under the hood and resumes automatically.

### 3g. rclone (any cloud)

```bash
rclone config                                      # one-time setup
rclone copy --progress video.mp4 gdrive:videos/    # upload
rclone link gdrive:videos/video.mp4                # get public URL (providers that support it)
rclone mount gdrive: /mnt/gdrive                   # stream-mount for ffmpeg to read directly
```

Supports Google Drive, OneDrive, Dropbox, Backblaze B2, S3, R2, Azure Blob, FTP, SFTP, WebDAV, and many more behind one CLI.

## Step 4 — Verify and get playback URL

1. `curl -I <playback_url>` — expect `200` and a video content-type (or `application/vnd.apple.mpegurl` for HLS).
2. Drop the URL into `ffplay` or `mpv` to smoke-test playback.
3. For HLS manifests, check that both master + variant playlists load:
   ```bash
   curl -s "$PLAYBACK_URL" | head -40
   ```
4. For Mux / Cloudflare Stream, poll the API until `status: ready` before sharing the link — the upload returns before the transcode finishes.
5. Register a webhook (Mux → Settings → Webhooks; Cloudflare → Stream webhooks) to avoid polling in production.

## Available scripts

- **`scripts/cloud.py`** — unified CLI: `check`, `cloudflare-stream`, `mux`, `bunny`, `s3`, `rclone`, `youtube`, `vimeo`. Stdlib + system `curl`/`rclone`/`aws`. `--dry-run` prints the command, `--verbose` dumps full JSON.

## Reference docs

- Read [`references/cloud.md`](references/cloud.md) for: service comparison, upload-protocol cheatsheet (direct POST vs TUS vs signed URL vs multipart), auth method per service, webhook/callback patterns, the exact shape of playback URLs, and end-to-end recipes (post-encode → Cloudflare, podcast → S3 → CloudFront, CI → Mux on merge).

## Gotchas

- **Tokens in env only.** Never hardcode, never commit `.env`, never echo in dry-run unless explicitly asked.
- **Cloudflare Stream 200 MB cap on direct POST.** Larger files MUST use TUS (`?direct_user=true`).
- **Cloudflare Stream output is always HLS + DASH + MP4 + thumb.** You do not generate manifests yourself; they are produced after transcode finishes (≈ real-time).
- **Mux uploads return before encoding.** Poll `GET /video/v1/assets/<id>` until `status == "ready"` or use webhooks.
- **Mux `playback_policy`.** `public` = open HLS URL; `signed` = you must mint a JWT per play (HS256 with signing key from Mux). Pick `public` unless you really need DRM-lite.
- **Bunny Stream is two-step.** Create video shell → PUT bytes. Skipping step 1 just 404s.
- **YouTube Data API quota.** 10,000 units/day default; an upload costs 1,600. Three uploads/day before you hit quota. Apply for a quota increase for production.
- **YouTube OAuth flow.** Installed-app flow stores a refresh token; keep it in `~/.config/yt-upload-token.json` (gitignored). `yt-dlp --cookies-from-browser chrome` works for *personal* re-auth but violates YouTube ToS for commercial use.
- **Vimeo tier caps weekly upload quota.** Basic = 500 MB/week; Plus/Pro/Business raise it. Check `/me` → `upload_quota` before large jobs.
- **S3 CORS for web playback.** MP4 in a `<video>` tag needs a `CORSRule` allowing `GET` from your origin. HLS needs `Range` in `AllowedHeaders`.
- **CloudFront propagation.** New distributions take 5–15 min to deploy globally. Invalidations cost money past the free tier — cache-bust with filename hashes instead.
- **OAI vs OAC for private S3 origins.** Origin Access Identity is legacy; use Origin Access Control (OAC) for new distributions.
- **Cloudflare Stream + Mux auto-transcode to ABR.** You do not need to pre-package HLS; ship a single H.264/HEVC MP4 and they ladder it for you.
- **rclone parallelism.** `--transfers 8 --checkers 16 --fast-list` for big batches; `--progress` for live ETA.
- **TUS for resumable.** Always prefer TUS when available (Cloudflare Stream, Vimeo, some S3 front-ends) — survives network blips.
- **Parallel batch:** `ls *.mp4 | parallel -j 4 'rclone copy {} myremote:path/'` is the simplest many-file pattern.
- **Timing curls:** `curl -w "\ntime: %{time_total}s\n"` measures upload wall clock without extra tooling.
- **Webhooks > polling.** Both Mux and Cloudflare POST a JSON body when encoding completes — wire them into a queue instead of a poll loop.
- **Always validate the playback URL** with `curl -I` or `ffprobe` before claiming the job is done.

## Examples

### Example 1: Push an ffmpeg encode to Cloudflare Stream

```bash
ffmpeg -i master.mov -c:v libx264 -crf 20 -preset slow -c:a aac -b:a 192k encoded.mp4
uv run ${CLAUDE_SKILL_DIR}/scripts/cloud.py cloudflare-stream --file encoded.mp4
# → prints { uid, playback: { hls, dash }, thumbnail }
```

### Example 2: Mux for a CI encode pipeline

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cloud.py mux --file out.mp4 --verbose
# Wait for webhook `video.asset.ready`, then embed https://stream.mux.com/<id>.m3u8
```

### Example 3: Mirror a render to Backblaze B2 via rclone

```bash
rclone copy --progress --transfers 8 render/ b2:my-bucket/renders/2026-04-17/
```

### Example 4: Upload a podcast MP3 to S3 with a public URL

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/cloud.py s3 \
  --file ep42.mp3 --bucket my-podcast --key 2026/ep42.mp3 --acl public-read
# https://my-podcast.s3.amazonaws.com/2026/ep42.mp3
```

## Troubleshooting

### Error: `401 Unauthorized` on Cloudflare Stream

Cause: `CF_TOKEN` lacks `Stream:Edit` scope or targets the wrong account.
Solution: Create a scoped token at https://dash.cloudflare.com/profile/api-tokens; verify `$CF_ACCOUNT_ID` matches the dashboard URL.

### Error: Mux upload returns URL but `ffprobe` on playback URL fails

Cause: The asset is still transcoding. Mux creates the playback ID immediately but the manifest is not written until encoding finishes.
Solution: Poll `GET /video/v1/assets/{asset_id}` until `status == "ready"`, or subscribe to the `video.asset.ready` webhook.

### Error: YouTube upload fails with `quotaExceeded`

Cause: Daily 10,000-unit quota consumed (≈ 6 uploads).
Solution: Wait until Pacific midnight reset, or request a quota increase at https://support.google.com/youtube/contact/yt_api_form.

### Error: `SignatureDoesNotMatch` on S3 upload

Cause: System clock skew, wrong region in endpoint, or credentials for a different AWS account.
Solution: `aws configure list`, sync clock (`sudo sntp -sS time.apple.com`), ensure `--region` matches the bucket.

### Error: Bunny Stream PUT returns `404`

Cause: `VIDEO_ID` not created first, or `BUNNY_LIB_ID` wrong.
Solution: POST to `.../library/$BUNNY_LIB_ID/videos` first, capture the `guid`, then PUT to that exact ID.

### Error: `rclone: failed to create file system` for Google Drive

Cause: OAuth token expired or `client_id/client_secret` misconfigured.
Solution: `rclone config reconnect <remote>:` and complete the browser flow.
