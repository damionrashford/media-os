# NDI Tools — CLI option reference

## ndi-find — list discoverable NDI sources

Blocks for a short window listening for mDNS advertisements, then prints sources in `NAME (COMPUTER)` format.

| Option | Purpose |
|---|---|
| `--timeout N` | seconds to wait for discovery (default varies) |
| (env) `NDI_GROUPS=G1,G2` | subscribe to named groups; default is `public` |
| (env) `NDI_DISCOVERY_SERVER=ip:port` | use Discovery Server instead of mDNS |

## ndi-send — advertise a media file as an NDI source

| Option | Purpose |
|---|---|
| `--input FILE` | media file (SDK build may accept pipes and raw frames) |
| `--name NAME` | source name (shown as `host (NAME)`) |
| `--fps N` | override frame rate |
| `--loop` | loop the input |
| (env) `NDI_GROUPS=G1,G2` | publish into these groups |

## ndi-record — record NDI source to MOV (**Advanced SDK only**)

| Option | Purpose |
|---|---|
| `--source "NAME (HOST)"` | source to record (as `ndi-find` prints) |
| `--output FILE.mov` | output path; SpeedHQ video + PCM audio |
| `--duration N` | seconds to record |

## ndi-benchmark — throughput tests

| Option | Purpose |
|---|---|
| `--resolution WxH` | e.g. `1920x1080`, `3840x2160` |
| `--fps N` | frame rate |
| `--duration N` | seconds to benchmark |

## NDI Bridge (GUI)

Launch the app; in-app UI picks mode:

- **Host mode** — listens on a TCP port for remote joiners.
- **Join mode** — connects out to a remote host.

TCP only. NAT traversal requires host-side port forwarding or reverse tunnel.

## NDI Studio Monitor

macOS/Windows Qt app. Receives any source on the network. Limit: Linux has no official build; use DistroAV in OBS instead.

## Environment variables (apply to every CLI)

| Var | Effect |
|---|---|
| `NDI_GROUPS` | comma-list of groups to subscribe/publish |
| `NDI_DISCOVERY_SERVER` | `ip:port` — replace mDNS with TCP Discovery Server |
| `NDI_RUNTIME_DIR_V6` | override NDI runtime path (for dlopen) |
| `LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` / `PATH` | point to libndi location |

## DistroAV (OBS plugin)

- Repo: `https://github.com/DistroAV/DistroAV`
- Releases: `https://github.com/DistroAV/DistroAV/releases`
- Replaces legacy `obs-ndi` (which is archived).
- Requires NDI runtime installed separately (from NDI SDK or NDI Tools bundle).

After install, OBS adds:
- **Source type: NDI Source** — add to a scene to receive.
- **Filter: NDI Filter** — per-source NDI publish.
- **Dedicated Output** (OBS 29+) — program feed as NDI.

## Firewall

| Port | Transport | Role |
|---|---|---|
| 5353 | UDP multicast | mDNS discovery |
| 5960 | TCP | messaging |
| 5961–6000 | TCP+UDP | per-source streams |
| 5990 (example) | TCP | NDI Bridge listen (user-picked) |

## Bitrate ballpark

| Variant | 1080p60 | 4Kp60 |
|---|---|---|
| NDI (SpeedHQ) | ~125 Mbps | ~600 Mbps |
| NDI\|HX (H.264) | ~8–20 Mbps | ~30–80 Mbps |
| NDI\|HX3 (HEVC, NDI 6) | ~4–12 Mbps | ~20–50 Mbps |

## Licence summary

- **Standard SDK**: free for non-commercial use; commercial requires Vizrt licence.
- **Advanced SDK**: always commercial; needed for `ndi-record`, multicast, routing, compressed passthrough.
- **Redistribution inside ffmpeg is NOT permitted** (hence DistroAV is a separate plugin).
