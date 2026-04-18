---
name: ndi-tools
description: >
  Use NDI SDK tools and CLIs (Vizrt/NewTek NDI): NDI Send, NDI Find, NDI Recorder, NDI Studio Monitor, NDI Bridge, NDI Discovery Service, NDI Benchmark, DistroAV (OBS plugin formerly obs-ndi). Source SRGB/HDR video over LAN via mDNS discovery + SpeedHQ codec on TCP/UDP 5960+, redistribute with Advanced SDK routing, integrate with OBS/ffmpeg/GStreamer plugins. Use when the user asks to send an NDI stream, receive NDI, find NDI sources on the network, record NDI to disk, bridge NDI over WAN, install NDI Tools, use DistroAV in OBS, or work with NDI sources from the command line.
argument-hint: "[action]"
---

# NDI Tools

**Context:** $ARGUMENTS

## Quick start

- **Find sources on the LAN:** → Step 2 (`ndictl.py find`)
- **Send a file as an NDI source:** → Step 3 (`ndictl.py send`)
- **Record an NDI source to disk:** → Step 4 (`ndictl.py record`)
- **Preview sources visually:** → Step 5 (`ndictl.py studio-monitor`)
- **Bridge NDI across subnets/WAN:** → Step 6 (`ndictl.py bridge`)
- **Integrate with OBS:** → Step 7 (DistroAV)
- **Check install / point user at SDK:** → Step 1 (`ndictl.py install-sdk`)

## When to use

- User wants to discover, send, receive, record, or bridge NDI sources from the CLI.
- User wants to install the NDI SDK or the standalone NDI Tools bundle (which contains the runtime).
- User wants to integrate NDI into OBS via DistroAV.
- User wants to benchmark NDI throughput / network capability.
- For NDI protocol details (ports, HDR, SDK vs Advanced SDK), use `ndi-docs` instead.

---

## Step 1 — Install the SDK / Tools (pointer, not auto-install)

The NDI SDK installer requires an end-user licence acceptance step. This skill does NOT download it automatically. It prints the URL and install path for the user to accept manually:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py install-sdk --platform <mac|win|linux>
```

Official downloads (always from `ndi.video`):

| Product | Purpose | URL |
|---|---|---|
| NDI SDK | Build against libndi (Send/Recv/Find/Bridge headers + libs) | https://ndi.video/for-developers/ndi-sdk/ |
| NDI Advanced SDK | Routing, multicast, compressed passthrough, access control | https://ndi.video/for-developers/ndi-advanced-sdk/ (sales gate) |
| NDI Tools | End-user apps: Studio Monitor, Test Patterns, Scan Converter, Bridge, Recorder, Screen Capture | https://ndi.video/tools/ |

Bundled CLIs after install (paths vary):

| CLI | Role | macOS path | Linux path |
|---|---|---|---|
| `ndi-send` | Send a file/pipe as an NDI source | `/Library/NDI SDK for Apple/examples/bin/` | `/usr/local/bin/` (SDK Linux) |
| `ndi-find` | List discoverable NDI sources | same | same |
| `ndi-record` | Record an NDI source to MOV (Advanced SDK) | same | same |
| `ndi-benchmark` | Measure encode/decode throughput | same | same |
| NDI Studio Monitor | Qt viewer | `/Applications/NDI Studio Monitor.app` | (Windows-native; Linux: no official; use DistroAV in OBS) |
| NDI Bridge | Cross-subnet relay | `/Applications/NDI Bridge.app` | Windows-native |
| NDI Discovery Service | Optional mDNS replacement | `/Applications/NDI Discovery Service.app` | Windows-native |

DistroAV (OBS plugin — successor to obs-ndi): `https://github.com/DistroAV/DistroAV/releases`.

Read [`references/tools.md`](references/tools.md) for the full CLI option tables.

---

## Step 2 — Find NDI sources on the network

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py find --timeout 5
```

Wraps `ndi-find` and prints sources in `name@address:port` form. Needs multicast mDNS working on the LAN (UDP 5353); if blocked, use a Discovery Server:

```bash
NDI_DISCOVERY_SERVER=10.0.0.5:5960 \
  uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py find --timeout 5
```

---

## Step 3 — Send a file / test pattern as an NDI source

Non-interactive wrapper around `ndi-send`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py send \
  --input video.mov --name "My Source" --group PUBLIC
```

For screen / capture-device input, use ffmpeg → NDI via DistroAV OBS output, or pipe from ffmpeg into `ndi-send` stdin (build-dependent).

---

## Step 4 — Record an NDI source

Requires **NDI Advanced SDK** (`ndi-record` is Advanced-only):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py record \
  --source "CAMERA1 (Studio A)" --output studioA.mov --duration 60
```

Output is MOV with SpeedHQ video + PCM audio. Use ffmpeg afterwards to transcode.

Without Advanced SDK, use OBS + DistroAV to record to MKV/MP4.

---

## Step 5 — Preview sources (Studio Monitor)

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py studio-monitor
```

Launches the macOS/Windows app. Linux has no official Studio Monitor — use DistroAV inside OBS, or `ffplay` if your ffmpeg was built with libndi (rare — usually disabled due to redistribution).

---

## Step 6 — Bridge NDI across subnets / WAN

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py bridge \
  --mode host --listen 0.0.0.0:5990
```

Modes: `host` (listen for incoming bridged clients) or `join` (connect out to a remote host). Required when mDNS cannot cross network segments. TCP only; works through NAT if the host side has a public port.

---

## Step 7 — OBS integration (DistroAV)

DistroAV is the OBS plugin. **Don't install "obs-ndi" — that repo is archived/stale.** Install from DistroAV releases:

- macOS: `.pkg` installer under GitHub Releases
- Windows: `.exe` installer under GitHub Releases
- Linux: `.deb` / `.rpm` / Flatpak per distro

The plugin adds:
- **NDI Source** (add to a scene to receive)
- **NDI Filter** (per-source NDI output)
- **NDI Dedicated Output** (program feed as NDI) — requires OBS 29+

DistroAV requires the NDI runtime to be installed separately (from the NDI SDK installer or the standalone NDI Tools installer).

---

## Step 8 — Benchmark network / CPU capacity

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py benchmark \
  --resolution 1920x1080 --fps 60 --duration 30
```

Wraps `ndi-benchmark` if available. Reports encode fps, decode fps, bandwidth.

---

## Gotchas

- **NDI runtime cannot be bundled inside ffmpeg.** Mainline ffmpeg removed NDI support (non-redistributable SDK). If `ffmpeg -f libndi_newtek ...` fails, your build doesn't include NDI. Use DistroAV in OBS or the ndi-send/ndi-record CLIs instead.
- **NDI Advanced SDK is needed for `ndi-record`, multicast sending, routing, and compressed passthrough.** Standard SDK is send/recv/find only.
- **obs-ndi is dead; DistroAV is the successor.** Install from `github.com/DistroAV/DistroAV/releases`. The old `obs-ndi` binaries may still exist on disk — uninstall them first so plugin loaders don't conflict.
- **DistroAV needs the NDI runtime installed separately.** On macOS the SDK installer drops `libndi.dylib` to `/usr/local/lib/`. On Windows the installer puts DLLs under `C:\Program Files\NDI\NDI 6 Runtime\`. On Linux, the SDK ships `libndi.so` — set `LD_LIBRARY_PATH` or copy into `/usr/local/lib`.
- **mDNS multicast (UDP 5353) must traverse the VLAN / subnet.** Many managed switches and corporate APs drop mDNS. Symptoms: `ndi-find` returns zero sources even though the sender swears it's on. Fix: run NDI Discovery Service OR use NDI Bridge.
- **Firewall ports:** open UDP 5353 (mDNS) plus TCP/UDP 5960-6000 (messaging + streams). Per-source streams start at 5961 and increment.
- **Sources are advertised with a `Machine (Name)` tuple.** `ndi-send --name foo` produces `hostname (foo)`. Many receivers expect the full tuple; passing just `foo` to a receiver will not match.
- **Groups are ACL-like filters** (`NDI_GROUPS=PUBLIC,PROD`). A receiver only sees sources in the groups it subscribes to. Default group is `public`. Required for separating production from on-air feeds.
- **Bitrate expectations:** NDI (full SpeedHQ) ~125 Mbps for 1080p60; NDI|HX ~8-20 Mbps; NDI|HX3 (HEVC, NDI 6) ~4-12 Mbps. A gigabit LAN handles ~7 concurrent full-NDI 1080p60 streams at most.
- **NDI HDR (PQ/HLG) requires NDI 6** on both sender and receiver. Pre-NDI-6 receivers will get SDR-flagged output.
- **License:** Standard SDK free for non-commercial use; commercial use and Advanced SDK require Vizrt licencing — **do not automate SDK downloads in CI/CD** without confirming licence.
- **Linux has no Studio Monitor app.** Use DistroAV inside OBS for a GUI preview.
- **The script is stdlib-only.** It wraps the bundled NDI CLIs that ship with the SDK/Tools installer — it does NOT reimplement the NDI protocol.

---

## Examples

### Example 1 — "Find NDI sources on my network"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py find --timeout 5
```

If empty: check firewall (5353/udp), check `NDI_GROUPS` env, or use Discovery Server.

### Example 2 — "Send a .mov file as an NDI source called 'Demo'"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py send \
  --input clip.mov --name Demo --loop
```

### Example 3 — "Record 'Camera 1 (Main)' for 60s to MOV"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py record \
  --source "Camera 1 (Main)" --output cam1.mov --duration 60
```

Needs Advanced SDK.

### Example 4 — "Install DistroAV so I can receive NDI inside OBS"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py install-sdk --platform mac
# Opens https://github.com/DistroAV/DistroAV/releases — accept licence, run .pkg
```

### Example 5 — "Bridge NDI from studio to remote site"

On the studio machine (host / listener):
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py bridge \
  --mode host --listen 0.0.0.0:5990
```

On remote site (joiner):
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/ndictl.py bridge \
  --mode join --remote studio.example.com:5990
```

---

## Troubleshooting

### `ndi-find` returns zero sources even though I know one is broadcasting

- Confirm both are on the same subnet (NDI is LAN-only unless bridging).
- Check mDNS (UDP 5353) isn't blocked — corporate APs often drop multicast.
- Verify `NDI_GROUPS` matches on both sides.
- Try NDI Discovery Service as a replacement.
- Try `ping <sender-ip>` to confirm L3 reachability.

### `libndi.dylib: image not found`

DistroAV or the example CLIs can't find the NDI runtime.
- macOS: reinstall NDI SDK; it places libs under `/usr/local/lib`.
- Linux: set `LD_LIBRARY_PATH=/path/to/ndi/lib`.
- Windows: add NDI Runtime directory to `PATH`.

### `ndi-record: unknown command`

You have the Standard SDK, not Advanced. `ndi-record` is Advanced-only. Use OBS + DistroAV to record, or get the Advanced SDK.

### Bridge mode can't connect through NAT

Host side needs a public IP/port. Use a reverse SSH tunnel or port-forward 5990 (or whichever listen port). Bridge is TCP-only.

---

## Reference docs

- CLI option tables for `ndi-send`, `ndi-find`, `ndi-record`, `ndi-benchmark`, and environment variables → `references/tools.md`.
