---
name: ffmpeg-broadcast
description: >
  Broadcast and film delivery plus media encryption with ffmpeg. Use when the user asks to author an MXF file (OP1a, OP-Atom, D-10/IMX), deliver an IMF/IMP package to Netflix or a studio, encode DNxHD, DNxHR, ProRes, or XDCAM HD422 mezzanines, stamp SMPTE drop-frame or non-drop-frame timecode, hit a broadcast or AS-11/AS-10/DPP delivery spec, read SMPTE 2022/2110 IP essences, encrypt an HLS stream with AES-128, build an HLS key info file, rotate HLS keys, do SAMPLE-AES, package MPEG-DASH Common Encryption (CENC, cbcs, cenc-aes-ctr), set up ClearKey, Widevine, PlayReady, or FairPlay-ready CMAF, generate a KID, or decrypt a segment for QA.
argument-hint: "[operation] [input]"
---

# ffmpeg-broadcast

**Context:** $ARGUMENTS

Professional broadcast/film mastering (MXF, IMF, ProRes, XDCAM, SMPTE timecode, SDI, 2110) and media encryption (HLS AES-128, DASH CENC, ClearKey/Widevine/PlayReady/FairPlay handoff). Always invoke `ffmpeg-docs` first to confirm any flag or filter before recommending it — it is the anti-hallucination guardrail.

## When to use

- Broadcast exchange delivery (MXF OP1a to a TV network QC dept; AS-11/AS-10/DPP profiles).
- Avid ingest / export (MXF OP-Atom, one essence per file).
- Studio / streamer mastering: ProRes mezzanine, DNxHD/DNxHR, IMF delivery to Netflix/Disney/Apple/Amazon.
- Embedding or restamping SMPTE timecode (drop-frame vs non-drop-frame).
- Reading SMPTE 2022 / 2110 IP essences or DeckLink SDI capture (niche, build-dependent).
- Protecting VOD or live HLS with AES-128 full-segment encryption (key info files, key rotation).
- Packaging MPEG-DASH with Common Encryption (CENC, cbcs, cenc-aes-ctr) for ClearKey, or Widevine/PlayReady/FairPlay-ready workflows.
- Generating keys/KIDs, signaling ClearKey in an MPD, or decrypting a segment for QA.
- Any time the user says "MXF", "IMF", "IMP", "XDCAM", "DNxHD", "ProRes", "SMPTE", "broadcast deliverable", "Netflix spec", "AES-128 HLS", "CENC", "DRM", "ClearKey", "Widevine", "PlayReady", or "FairPlay".

## Techniques

- Read `references/mxf-imf.md` when authoring broadcast/film deliverables: MXF OP1a / OP-Atom / D-10 mux, IMF essence, DNxHD/DNxHR/ProRes/XDCAM encoding, SMPTE timecode stamping (DF vs NDF), IMF package limitations, SDI capture.
- Read `references/mxf-imf-formats.md` when you need exact codec-profile tables: MXF operational patterns, DNxHD/DNxHR/ProRes/XDCAM profiles, timecode syntax, IMF ST 2067 spec parts, Netflix/Disney/Apple delivery notes, external IMF tooling (Photon, asdcplib), SMPTE 2022/2110 overview, DeckLink format codes.
- Read `references/drm.md` when encrypting or packaging protected media: HLS AES-128 (key info file, inline, periodic rekey), DASH CENC (cenc-aes-ctr / cenc-aes-cbc), `crypto:` playback, segment decryption for QA, and the Shaka/Bento4 handoff boundary.
- Read `references/drm-schemes.md` when you need the deep DRM matrix: HLS vs CENC scheme comparison, MPD `ContentProtection` templates (ClearKey/Widevine/PlayReady/FairPlay), browser/device DRM support matrix, ClearKey test server, key-rotation strategies, debug/inspection cheatsheet, operational checklist.

## Gotchas

- **MXF Operational Patterns differ.** `-f mxf` = OP1a (single file, broadcast default). `-f mxf_opatom` = OP-Atom (one essence per file, Avid + IMF). `-f mxf_d10` = D-10 / IMX. Mixing them up causes silent ingest rejection.
- **Drop-frame timecode uses SEMICOLON.** `01:00:00;00` = drop-frame; `01:00:00:00` = non-drop-frame. The semicolon-vs-colon is load-bearing — it is how ffmpeg selects DF. 29.97 NDF is not the same as 29.97 DF.
- **Broadcast interlacing needs flags.** TFF wants `-vf setfield=tff` on output plus `-flags +ildct+ilme -top 1` for MPEG-2. Missing these produces ingest-rejecting files. Use `pcm_s24le` @ 48 kHz audio — never AAC in broadcast MXF.
- **ffmpeg cannot author an IMF package.** It writes the MXF essence (J2K ST 2067-20 or ProRes ST 2067-21) but not the XML CPL/PKL/ASSETMAP. Use Netflix Photon or asdcplib to wrap + validate; never pretend ffmpeg alone produces an IMP.
- **HLS key info file format is exact** — three lines: URI / local-path / IV-hex. A blank line, CRLF mix, or a leading `0x` on the IV silently breaks encrypt or decrypt. The key file must be exactly 16 bytes (`openssl rand 16`, not `echo`). IV is exactly 32 hex chars, no `0x`.
- **`-hls_enc 1` with no explicit key** auto-generates a key and writes it next to the playlist — insecure default; always pass your own key + URL.
- **`-encryption_key` and `-encryption_kid` are 32 hex chars each (16 bytes).** 64 hex (256-bit) is wrong — silent no-op or "encryption key must be 16 bytes" error. KID must be unique per asset.
- **ffmpeg does not emit PSSH boxes or FairPlay signaling.** CENC fmp4 from ffmpeg needs Shaka Packager / Bento4 (`mp4encrypt --pssh`) for Widevine/PlayReady, and Apple `mediafilesegmenter` or Shaka for FairPlay SAMPLE-AES. ClearKey works for staging only.

## Scripts

- **`scripts/mxfimf.py`** — subcommands `mxf-op1a`, `mxf-opatom`, `prores-mov`, `xdcam-hd422`, `set-timecode`, `identify-imf`. Each accepts `--dry-run` and `--verbose`.

  ```bash
  uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py mxf-op1a \
    --input in.mov --output out.mxf --codec dnxhd --timecode "01:00:00:00"
  uv run ${CLAUDE_SKILL_DIR}/scripts/mxfimf.py identify-imf --input suspect.mxf
  ```

- **`scripts/drm.py`** — subcommands `gen-key`, `gen-iv`, `hls-aes128`, `dash-cenc`, `decrypt-segment`. Global flags `--dry-run`, `--verbose` (keys only printed with `--verbose`).

  ```bash
  uv run ${CLAUDE_SKILL_DIR}/scripts/drm.py hls-aes128 \
    --input in.mp4 --outdir out --key-url https://cdn.example.com/keys/enc.key --key enc.key
  uv run ${CLAUDE_SKILL_DIR}/scripts/drm.py dash-cenc \
    --input in.mp4 --outdir out --key <hex> --kid <hex> --scheme cenc-aes-ctr
  ```
