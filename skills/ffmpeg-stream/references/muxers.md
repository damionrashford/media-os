# Streaming muxer + protocol reference

Full option tables, platform ingest URLs, and latency math for the `ffmpeg-streaming` skill.

---

## 1. HLS muxer (`-f hls`)

| Option | Purpose | Typical value |
| --- | --- | --- |
| `-hls_time` | Target segment duration (seconds). Real segments end on the next keyframe. | `2` – `6` |
| `-hls_list_size` | Number of segments kept in the playlist (live sliding window). `0` = keep all. | `0` (VOD) / `6` (live) |
| `-hls_playlist_type` | `vod` (fixed, grows then locks) or `event` (grows forever, no deletion). Unset = live. | `vod` / `event` / unset |
| `-hls_flags` | `delete_segments`, `append_list`, `omit_endlist`, `independent_segments`, `program_date_time`, `discont_start`, `split_by_time`, `second_level_segment_index`, `temp_file`, `round_durations`. Combine with `+`. | `delete_segments+append_list` |
| `-hls_segment_type` | `mpegts` (default) or `fmp4` (CMAF-ish). | `mpegts` / `fmp4` |
| `-hls_fmp4_init_filename` | Init segment filename when using fmp4. | `init.mp4` |
| `-hls_segment_filename` | Segment filename pattern. `%v` expands to variant index. `%d` for sequence. | `seg_%03d.ts` |
| `-hls_base_url` | Prefix every segment URI in the playlist with this string. | `https://cdn.example.com/vid/` |
| `-hls_allow_cache` | Emit `EXT-X-ALLOW-CACHE` tag. Deprecated in HLS v7+. | unset |
| `-hls_segment_options` | Pass options to the segment muxer (mpegts or mp4). | `mpegts_m2ts_mode=1` |
| `-hls_start_number_source` | `generic`, `epoch`, `epoch_us`, `datetime`. Controls `EXT-X-MEDIA-SEQUENCE`. | `generic` |
| `-start_number` | Initial segment sequence number. | `0` |
| `-hls_key_info_file` | Path to a file describing AES-128 encryption: URI, keyfile, optional IV. | custom |
| `-hls_enc` | `1` to enable built-in AES-128 encryption (random key). | `0` |
| `-hls_enc_key`, `-hls_enc_iv`, `-hls_enc_key_url`, `-hls_enc_keyurl` | Manual encryption parameters. | varies |
| `-master_pl_name` | Write a master playlist with this name alongside variants. | `master.m3u8` |
| `-master_pl_publish_rate` | Re-publish master every N seconds (live). | `10` |
| `-var_stream_map` | Space-separated groups mapping output streams to variants. Each group is `v:N,a:N[,name:…][,agroup:…][,language:…]`. | `v:0,a:0 v:1,a:1` |
| `-cc_stream_map` | Maps closed-caption streams onto variants. | `ccgroup:cc,instreamid:CC1,language:en` |
| `-hls_ts_options` | Pass mpegts muxer options. | `mpegts_flags=+pat_pmt_at_frames` |
| `-hls_init_time` | Duration of the first segment (fragmented start). | `0` |
| `-hls_delete_threshold` | Segments older than this count are deleted. | `1` |

### HLS Low-Latency (LL-HLS) notes

- Real LL-HLS requires `EXT-X-PART` partial segments. **Upstream ffmpeg does NOT emit `EXT-X-PART`.** The closest you can get with ffmpeg alone is short segments (`-hls_time 2`) and `independent_segments` — latency floor ~3–4 s.
- For true LL-HLS (< 2 s) pipe ffmpeg → a packager that speaks LL-HLS (Shaka Packager, tsduck, Low-Latency HLS origin).
- Useful flags for short-segment HLS: `-hls_flags +independent_segments+program_date_time`, `-hls_time 2`, `-hls_list_size 10`.

---

## 2. DASH muxer (`-f dash`)

| Option | Purpose | Typical value |
| --- | --- | --- |
| `-seg_duration` | Target segment duration (seconds). | `2`–`6` |
| `-frag_duration` | Fragment duration within a segment (for CMAF chunked transfer). | `0.5` |
| `-frag_type` | `none`, `every_frame`, `duration`, `pframes`. | `duration` |
| `-use_template` | Write `SegmentTemplate` instead of `SegmentList`. | `1` |
| `-use_timeline` | Add `SegmentTimeline` (required for variable-duration segs). | `1` |
| `-init_seg_name` | Template for init segment. | `init-$RepresentationID$.m4s` |
| `-media_seg_name` | Template for media segments. | `chunk-$RepresentationID$-$Number%05d$.m4s` |
| `-adaptation_sets` | Group outputs into AdaptationSets. | `id=0,streams=v id=1,streams=a` |
| `-window_size` | Segments kept in the MPD (live). | `5` |
| `-extra_window_size` | Extra kept on disk but dropped from MPD. | `10` |
| `-remove_at_exit` | Delete all files on shutdown. | `0` |
| `-min_seg_duration` | Minimum segment duration. | `2000000` (µs) |
| `-ldash` | Enable Low-Latency DASH fields (`@availabilityTimeOffset`, `@availabilityTimeComplete`). | `1` |
| `-streaming` | Enable chunked streaming of partially-written segments (LL-DASH). | `1` |
| `-update_period` | `minimumUpdatePeriod` for live MPDs (seconds). | `2` |
| `-global_sidx` | Write a single sidx per Representation. | `0` |
| `-single_file` | Pack init+media into one file (Representation). | `0` |
| `-hls_playlist` | Also emit an HLS playlist next to the MPD (CMAF). | `1` |
| `-utc_timing_url` | Add `<UTCTiming>` pointing to an NTP server. | `https://time.akamai.com/?iso` |

---

## 3. Tee muxer (`-f tee`)

Syntax: `-f tee 'SINK1|SINK2|SINK3'`. Each sink is `[OPTS]URL`.

Per-sink options (inside brackets, colon-separated):

| Option | Meaning |
| --- | --- |
| `f=FMT` | Override format (e.g. `f=flv`, `f=hls`, `f=mpegts`, `f=mp4`). |
| `onfail=abort|ignore` | Abort whole ffmpeg or continue other sinks on failure. Default `abort`. |
| `select=STREAM_SPECIFIER` | Limit streams sent to this sink (e.g. `select=\'v:0,a:0\'`). |
| `use_fifo=1` | Wrap sink in a fifo muxer (non-blocking writes — recommended for RTMP). |
| `fifo_options=OPTS` | Options passed to the fifo muxer. |
| `bsfs=…` | Per-sink bitstream filters. |

Additional demuxer options from the target format can appear directly (e.g. `hls_time=4`, `hls_flags=delete_segments`).

Escaping:

- The separator `|` will be interpreted by the shell — ALWAYS single-quote the full tee spec.
- `:` inside per-sink opts is part of the syntax. Literal `:` or `|` in URLs must be escaped with `\:` and `\|`.
- Inside filtergraph-like quoting: a `\` needs to be doubled.

Tee examples:

```
# YouTube + local HLS + archive, with HLS behind a fifo for resilience:
-f tee '[f=flv:onfail=ignore]rtmp://a.rtmp.youtube.com/live2/KEY|[f=hls:hls_time=4:hls_list_size=6:hls_flags=delete_segments:use_fifo=1]live.m3u8|[f=mpegts]archive.ts'

# Multicast + unicast SRT:
-f tee '[f=mpegts]udp://239.0.0.1:1234?pkt_size=1316|[f=mpegts]srt://receiver:9000?mode=caller'
```

---

## 4. Protocols

### 4.1 RTMP (`rtmp://`, `rtmps://`, `rtmpt://`, `rtmpts://`, `rtmpe://`)

| Option | Meaning |
| --- | --- |
| `rtmp_app` | AMF app name (usually inferred from URL). |
| `rtmp_buffer` | Client buffer (ms). Default 3000. |
| `rtmp_conn` | Extra AMF connection params, `S:key=val` separated by spaces. |
| `rtmp_flashver` | Impersonate a Flash version string. |
| `rtmp_live` | `any` / `live` / `recorded`. Force live playback mode. |
| `rtmp_pageurl`, `rtmp_swfurl` | Referrer/SWF (for platforms that require it). |
| `rtmp_playpath` | Stream key / path (usually inferred). |
| `rtmp_subscribe` | Subscribe to a named stream. |
| `rtmp_tcurl` | Override TCURL (full app URL). |
| `rtmp_listen` | `1` to accept inbound connections (server-side). |

Output format MUST be `-f flv`. Codec constraints: H.264 (Baseline/Main/High; NO 10-bit), AAC-LC (NO HE-AAC on most CDNs), 44.1 or 48 kHz, stereo.

### 4.2 SRT (`srt://`)

Query-string options:

| Option | Meaning | Typical |
| --- | --- | --- |
| `mode` | `caller` (push), `listener` (pull), `rendezvous`. | `caller` / `listener` |
| `latency` | Target buffer in **microseconds**. Min useful ≈ 2×RTT. | `120000` (120 ms) |
| `rcvlatency`, `peerlatency` | Explicit per-direction latency. | `120000` |
| `passphrase` | 10–79 chars; enables AES encryption. | — |
| `pbkeylen` | Key length: `16`/`24`/`32` → AES-128/192/256. | `16` |
| `streamid` | Free-form string passed to the peer; many ingests use this for auth (e.g. `#!::u=user,r=room`). | — |
| `maxbw` | Max send bandwidth (bytes/s). `-1` = unlimited. | `-1` |
| `oheadbw` | Overhead bandwidth percentage. | `25` |
| `payload_size` | Max payload per packet. Live = `1316`, file = `1456`. | `1316` |
| `pkt_size` | mpegts-side packet size (keep at 1316 for SRT). | `1316` |
| `mss` | Max segment size (MTU minus overhead). | `1500` |
| `transtype` | `live` / `file`. | `live` |
| `tsbpdmode` | Time-based packet delivery mode (live = 1). | `1` |
| `connect_timeout` | ms. | `3000` |
| `tlpktdrop` | Too-late packet drop. | `1` |
| `linger` | Linger on close (seconds). | `0` |

### 4.3 RTSP (`rtsp://`)

| Option | Meaning |
| --- | --- |
| `rtsp_transport` | `udp`, `tcp`, `udp_multicast`, `http`, `https`. |
| `rtsp_flags` | `filter_src`, `listen`, `prefer_tcp`. |
| `allowed_media_types` | `video`, `audio`, `data`. |
| `min_port`, `max_port` | UDP port range for RTP. |
| `user_agent` | Client UA. |
| `reorder_queue_size` | Reorder queue for UDP. |
| `stimeout` | Socket TCP I/O timeout (µs). |
| `listen_timeout` | Listen timeout (s). |

Output: `-f rtsp -rtsp_transport tcp rtsp://server:8554/stream`.

### 4.4 UDP (`udp://host:port?opts`)

| Option | Meaning |
| --- | --- |
| `buffer_size` | OS send/recv buffer (bytes). | 
| `pkt_size` | Max payload size (use `1316` for mpegts over UDP → fits in a 1500-MTU Ethernet frame with 7×188 TS packets). |
| `localport`, `localaddr` | Bind address/port. |
| `reuse` | `1` for SO_REUSEADDR. |
| `ttl` | Multicast TTL. |
| `fifo_size` | Circular buffer capacity. |
| `overrun_nonfatal` | Keep going after a fifo overrun. |
| `broadcast` | Allow 255.255.255.255. |

Multicast: `udp://239.0.0.1:1234?pkt_size=1316&ttl=1`.

### 4.5 RTP (`rtp://host:port`) and `rtp_mpegts` muxer

| Option | Meaning |
| --- | --- |
| `rtp_mpegts` | `-f rtp_mpegts` wraps mpegts in RTP (single stream). |
| `rtp`    | `-f rtp` emits a single elementary stream per port (need SDP out-of-band). |
| `sdp_file` | Write an SDP description to this file. |
| `payload_type` | RTP PT number. |
| `ssrc` | Sync source identifier. |
| `pkt_size` | Max packet payload (keep ≤ 1316 for Ethernet). |

---

## 5. Platform ingest URL reference

| Platform | Ingest URL pattern | Notes |
| --- | --- | --- |
| YouTube Live | `rtmp://a.rtmp.youtube.com/live2/<STREAM-KEY>` | `rtmps://a.rtmps.youtube.com/live2/KEY` for TLS. 2-s keyframes. |
| YouTube backup | `rtmp://b.rtmp.youtube.com/live2?backup=1/<KEY>` | Use for redundant push. |
| Twitch | `rtmp://live.twitch.tv/app/<KEY>` | Nearest ingest: `https://ingest.twitch.tv/`. 2-s keyframes. |
| Facebook Live | `rtmps://live-api-s.facebook.com:443/rtmp/<KEY>` | RTMPS only. |
| LinkedIn Live | `rtmps://rtmp.linkedin.com:443/live/<KEY>` | RTMPS. |
| Kick | `rtmps://fa723fc1b171.global-contribute.live-video.net/<KEY>` | Varies per region. |
| Custom nginx-rtmp | `rtmp://server/app/<stream-name>` | Plain RTMP by default. |
| Mux (RTMP) | `rtmps://global-live.mux.com:443/app/<KEY>` | |
| Mux (SRT) | `srt://global-live.mux.com:6001?streamid=#!::r=<KEY>,m=publish` | `streamid` auth. |
| Cloudflare Stream (RTMPS) | `rtmps://live.cloudflare.com:443/live/<KEY>` | |
| Cloudflare Stream (SRT) | `srt://live.cloudflare.com:778?streamid=<KEY>` | |

---

## 6. Keyframe interval math

A clean segmentable stream needs a **keyframe at every segment boundary**. Target segment duration × frames-per-second = GOP.

| fps | 2-s seg | 4-s seg | 6-s seg |
| --- | --- | --- | --- |
| 24  | 48  | 96  | 144 |
| 25  | 50  | 100 | 150 |
| 30  | 60  | 120 | 180 |
| 50  | 100 | 200 | 300 |
| 60  | 120 | 240 | 360 |

Mandatory companion flags on libx264/libx265:

```
-g <GOP> -keyint_min <GOP> -sc_threshold 0 -force_key_frames 'expr:gte(t,n_forced*<SEG>)'
```

- `-g` alone permits shorter GOPs when the encoder decides. `-keyint_min` equal to `-g` forces the lower bound.
- `-sc_threshold 0` disables scene-cut keyframes (default is 40). Without it you will see `EXT-X-DISCONTINUITY` and jittery ABR switching.
- `-force_key_frames` is a belt-and-suspenders that guarantees an IDR every SEG seconds even if the encoder would otherwise skip one (filter-complex can shift PTS).

---

## 7. Latency ladder (glass-to-glass)

| Stack | Typical end-to-end latency | Notes |
| --- | --- | --- |
| SRT (live) | **120–400 ms** | `latency` param sets the floor. Contribution-grade. |
| RTP / UDP (LAN) | 50–200 ms | No reliability. Needs SDP. |
| RTSP (LAN) | 150–400 ms | Usually TCP for NAT traversal. |
| RTMP → CDN origin | 1–3 s | Into the ingest. Player-side buffering adds 1–2 s more. |
| RTMP end-to-end (watch on platform) | **2–5 s** | Typical YouTube/Twitch low-latency mode. |
| HLS LL (short segs, no EXT-X-PART) | **3–7 s** | With `-hls_time 2` + CMAF. |
| DASH LL (chunked CMAF) | 3–7 s | `-ldash 1 -streaming 1`. |
| HLS standard | **6–20 s** | Default for Safari/iOS. |
| DASH standard | 6–20 s | Default for dash.js. |

Rule: latency ≈ 3 × segment duration (player default target) + encode + CDN propagation.

---

## 8. Low-latency live encoder checklist (libx264)

```
-c:v libx264
-preset veryfast        # or ultrafast if CPU-bound
-tune zerolatency       # no B-frames, no lookahead
-profile:v high -level 4.1
-pix_fmt yuv420p
-b:v 6000k -maxrate 6000k -bufsize 12000k
-g 60 -keyint_min 60 -sc_threshold 0
-x264-params "nal-hrd=cbr:force-cfr=1"
-flags +global_header   # some muxers/CDNs require it
```

Matching audio:

```
-c:a aac -profile:a aac_low -b:a 160k -ar 48000 -ac 2
```

---

## 9. Quick sanity checks

- HLS playlist opens in Safari → working.
- RTMP ingest: `ffprobe -v error -show_format -show_streams rtmp://...` from a second machine.
- SRT: run `ffmpeg -i 'srt://origin:9000?mode=caller&latency=120000' -f null -` and watch for packet loss in stderr.
- DASH MPD: `dash.js` reference player or `shaka-packager` validator.
- Verify keyframe cadence: `ffprobe -show_frames -select_streams v -of csv=nk=1:p=0 -show_entries frame=pict_type,best_effort_timestamp_time in.ts | grep I`.
