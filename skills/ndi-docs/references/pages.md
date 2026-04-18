# NDI Docs — Page Catalog

Exhaustive list of pages the `ndidocs.py` script knows about, with use-cases.
All listed pages were verified HTTP-200 at time of authoring.

| Page name | URL | Purpose |
|---|---|---|
| `sdk-landing` | https://ndi.video/for-developers/ndi-sdk/ | Marketing/landing page for SDK downloads (Standard, Advanced, Tools). Pointer; not content-heavy. |
| `tech-ndi6` | https://ndi.video/tech/ndi6/ | NDI 6 feature overview — HX3 (H.265), native HDR (PQ+HLG), Agilex 7, NDI Bridge, 10/12/16-bit support. |
| `docs-root` | https://docs.ndi.video/ | docs.ndi.video landing / table of contents. |
| `sdk` | https://docs.ndi.video/all/developing-with-ndi/sdk | SDK overview under "developing with NDI". |
| `sdk-release-notes` | https://docs.ndi.video/all/developing-with-ndi/sdk/release-notes | Per-version change history — use to find when a feature shipped. |
| `sdk-port-numbers` | https://docs.ndi.video/all/developing-with-ndi/sdk/port-numbers | Authoritative port list: mDNS 5353/udp, messaging 5960/tcp, streams 5961+. Firewall reference. |
| `sdk-hdr` | https://docs.ndi.video/all/developing-with-ndi/sdk/hdr | NDI HDR spec: PQ (ST 2084) + HLG, bit depths, metadata. NDI 6+. |
| `faq-sdk-vs-advanced` | https://docs.ndi.video/all/faq/sdk/what-are-the-differences-between-the-ndi-sdk-and-the-ndi-advanced-sdk | Feature matrix: Standard SDK vs Advanced SDK — routing, multicast, access-control groups, compressed passthrough, licence terms. |
| `distroav` | https://raw.githubusercontent.com/DistroAV/DistroAV/master/README.md | DistroAV (OBS NDI plugin, successor to obs-ndi) README — install, setup, hotkeys, OBS scene integration. |

## Wire-protocol cheat sheet

| Layer | Port | Transport | Purpose |
|---|---|---|---|
| Discovery | 5353 | UDP multicast | mDNS/Bonjour — NDI Find uses this; disable for private-only deployments |
| Discovery (alt) | configurable | TCP unicast | NDI Discovery Server — use when mDNS blocked (`NDI_DISCOVERY_SERVER=ip:port`) |
| Messaging | 5960 | TCP | Source-list / routing / control messages |
| Streams | 5961+ | TCP or UDP | Each active source opens from 5961 upward |

Multicast sending (Advanced SDK only) uses RFC 3171 multicast group IPs (source chooses the specific group).

## SDK vs Advanced SDK matrix

| Feature | Standard SDK | Advanced SDK |
|---|---|---|
| Send / Receive / Find | Yes | Yes |
| Unicast TCP streams | Yes | Yes |
| Multicast sending | No | Yes |
| Access control (Groups) | No | Yes (source-level ACL by group name) |
| Compressed passthrough (send pre-encoded H.264/H.265) | No | Yes |
| Routing (relay without decode) | No | Yes |
| Custom frame-sync / clocking | No | Yes |
| C++ wrapper | No | Yes |
| Non-commercial use | Yes | Requires licence |
| Commercial redistribution | Requires licence | Requires licence (Vizrt) |

## NDI variants

| Variant | Codec | Typical bitrate @ 1080p60 | Latency | Notes |
|---|---|---|---|---|
| NDI (full) | SpeedHQ (Vizrt DCT-based) | 100–250 Mbps | ~1 frame (sub-50 ms) | I-frame only; LAN-intended |
| NDI\|HX | H.264 | 8–20 Mbps | ~5 frames | Long-GOP; hardware-friendly |
| NDI\|HX2 | H.264 (improved) | 8–20 Mbps | ~5 frames | Better low-light/motion |
| NDI\|HX3 | H.265 (HEVC) | 4–12 Mbps | ~5 frames | NDI 6; HDR-capable |

## NDI Bridge

Bridges NDI across subnets/WANs by relaying through a bridge server.
Two modes: "Host" (clients connect in) and "Join" (client connects out to a remote host).
Required when mDNS cannot cross the network segment (VLANs, NAT, WAN).

## Environment variables

| Var | Purpose |
|---|---|
| `NDI_DISCOVERY_SERVER` | `ip:port` — use Discovery Server instead of mDNS |
| `NDI_GROUPS` | comma list — restrict what groups a sender publishes to / receiver subscribes to |
| `NDI_RUNTIME_DIR_V6` | override NDI runtime path (advanced deployments) |

## Licence reminder

- **Standard SDK**: free for non-commercial distribution; commercial requires Vizrt licence.
- **Advanced SDK**: always requires commercial licence.
- **Redistribution inside an ffmpeg binary is NOT permitted** — hence why mainline ffmpeg removed libndi support and why DistroAV is a separate plugin that dlopens the system runtime.
