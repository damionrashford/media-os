---
name: gphoto2-tether
description: >
  Tether DSLR / mirrorless cameras via USB or PTP/IP using gphoto2 (gphoto.org) + libgphoto2: --auto-detect, --list-cameras, --capture-image, --capture-image-and-download, --capture-preview (live-view JPEG), --capture-movie, --capture-tethered (wait for shutter release), --list-files, --get-file, --get-all-files, --summary, --list-config / --get-config / --set-config (shutterspeed, aperture/f-number, ISO, focusmode, autofocusdrive, manualfocusdrive, drivemode, batterylevel - key names vary per camera driver), --wait-event, --shell, --stdout (pipe mode). PTP/IP over Wi-Fi via ptpip:IP or ptpip:IP:PORT syntax. Supports Canon, Nikon, Sony, Fujifilm, Panasonic, Olympus, Pentax, Leica, Hasselblad and more (live list at gphoto.org/proj/libgphoto2/support.php). Use when the user asks to tether a DSLR, auto-capture from Python, bulk-download from a camera, remotely change aperture/ISO/shutter, drive live-view, build a photobooth/timelapse, or connect over PTP/IP.
argument-hint: "[action]"
---

# Gphoto2 Tether

**Context:** $ARGUMENTS

## Quick start

- **What camera do I have plugged in?** -> Step 1 (`tether.py detect`)
- **Take one shot + pull it to disk:** -> Step 2 (`tether.py shoot --download`)
- **Live-view preview as MJPEG / JPEGs:** -> Step 3 (`tether.py preview`)
- **Record movie on camera:** -> Step 4 (`tether.py movie`)
- **Download every photo on the card:** -> Step 5 (`tether.py bulk-download`)
- **Change a setting (shutter / ISO / aperture):** -> Step 6 (`tether.py config-*`)
- **Timelapse:** -> Step 7 (`tether.py timelapse`)
- **Connect via Wi-Fi (PTP/IP):** -> Step 8 (`tether.py ptpip`)

## When to use

- A supported DSLR/mirrorless is on USB (or on Wi-Fi via PTP/IP) and you want CLI control.
- Building a timelapse rig, photobooth, studio tether, automated capture loop.
- Remote focus pull, ISO/shutter/aperture bracketing, battery check.
- Always pair with `media-exiftool` after capture if you need to tag EXIF / IPTC / XMP.
- Not for video editing — use `ffmpeg-transcode` / `moviepy` after download.

---

## Step 1 — Detect the camera

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py detect
```

Expands to:

```bash
gphoto2 --auto-detect
```

Output is a table of "Model | Port" pairs. Port is usually `usb:NNN,MMM` (bus, device). Use `tether.py config-list` afterwards to confirm config keys exist for that camera.

---

## Step 2 — Capture (and optionally download)

Shoot one frame, keep it on the card:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py shoot
```

Shoot and pull to the current directory:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py shoot --download
```

Burst of 10 shots, all downloaded:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py shoot --download --count 10
```

Under the hood (single shot):

```bash
gphoto2 --capture-image-and-download --filename "%Y%m%d-%H%M%S-%n.%C"
```

The `%C` specifier uses the file's actual extension (JPG, CR2, NEF, ARW, ...).

---

## Step 3 — Preview / live-view

Dump a live-view JPEG to stdout once:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py preview --once --out frame.jpg
```

Stream live-view at ~10 fps as a sequence to a directory:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py preview --fps 10 --dest ./live/
```

Under the hood:

```bash
# Single frame:
gphoto2 --capture-preview --filename frame.jpg --force-overwrite
# Loop: gphoto2 --shell in a pipe, or repeated --capture-preview.
```

**Note:** live-view requires mirror-up (DSLR) or EVF-mode (mirrorless). Cameras that only expose live-view through the proprietary USB mode may not work.

---

## Step 4 — Movie record

Start movie record for N seconds then stop:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py movie --duration 30
```

Expands to:

```bash
gphoto2 --capture-movie=30s
```

Captures to the card; use `bulk-download` afterwards to pull the MOV/MP4 off.

---

## Step 5 — Bulk download

Pull every file on the card (leaves originals on card):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py bulk-download --dest ./ingest/
```

Expands to:

```bash
cd ./ingest && gphoto2 --get-all-files --skip-existing
```

Add `--delete` to wipe the card after successful download.

---

## Step 6 — Config (shutter / aperture / ISO / focus / etc.)

**List every config key the camera exposes:**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-list
```

Expands to `gphoto2 --list-config`.

**Get one key's current value + allowed values:**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-get --key /main/capturesettings/shutterspeed
```

Expands to `gphoto2 --get-config /main/capturesettings/shutterspeed`.

**Set a value:**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-set --key /main/imgsettings/iso --value 400
```

Expands to `gphoto2 --set-config /main/imgsettings/iso=400`.

**Key names differ per manufacturer.** Read [`references/config-keys.md`](references/config-keys.md) for the Canon / Nikon / Sony mapping (e.g. Canon uses `aperture`, Nikon uses `f-number`).

---

## Step 7 — Timelapse

Shoot 120 frames, one every 5 seconds, into `./tl/`:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py timelapse \
  --interval 5 --count 120 --dest ./tl/
```

Under the hood the script loops:

```bash
gphoto2 --capture-image-and-download --filename "./tl/%Y%m%d-%H%M%S-%n.%C"
# sleep 5
```

Convert the result to a video afterwards with `ffmpeg-frames-images`.

---

## Step 8 — PTP/IP (Wi-Fi) connection

Modern Nikon / Canon bodies expose PTP over Wi-Fi. Pair the camera once in its own menu (store an entry in `~/.gphoto/`), then:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py ptpip --host 192.168.1.120 -- shoot --download
```

The trailing `--` separates the ptpip host args from the nested subcommand and its options. Expands to:

```bash
gphoto2 --port ptpip:192.168.1.120 --capture-image-and-download
```

Port defaults to 15740 (PTP/IP standard). Override with `--port 15741`.

---

## Gotchas

- **`http://gphoto.org` uses HTTP only** — their HTTPS cert has long been invalid. Don't `curl https://gphoto.org/...` in scripts; use `http://` or pin to the mirror. Documentation URLs: manual at `http://gphoto.org/doc/manual/`, API at `https://gphoto.org/doc/api/`, supported-cameras list at `http://gphoto.org/proj/libgphoto2/support.php`.
- **`gphoto2-cam-conf` and `gphoto2-config` DO NOT EXIST.** Camera config is a subcommand family of the single `gphoto2` binary: `--list-config`, `--get-config`, `--set-config`, `--set-config-index`, `--set-config-value`. Correct the user if they reference a separate binary.
- **Config key paths are per-camera, not a universal schema.** `/main/capturesettings/aperture` on Canon is `/main/capturesettings/f-number` on Nikon. ISO is commonly `/main/imgsettings/iso` (both). Always run `config-list` first on an unknown body.
- **macOS hijacks cameras via PTPCamera.** The system process `PTPCamera` (or the Image Capture app) grabs the camera on USB connect. Run `killall PTPCamera` before gphoto2, or disable `~/Library/Image Capture/Devices/` hot-plug handlers. Linux doesn't have this problem.
- **Linux needs udev rules** for non-root access. libgphoto2 ships `udev/` rules; without them you get `Claiming USB device: Could not claim the USB device`. Install via `apt install libgphoto2-dev` or copy `/lib/udev/rules.d/40-libgphoto2.rules` from the source tree, then `udevadm control --reload`.
- **`--capture-preview` is not supported on every camera.** Some cameras (older Canon Rebels, most Sony A7 series via USB) only expose preview over their proprietary protocol. If you get `Operation not supported` here, the camera needs to be put in movie/live-view mode manually.
- **PTP/IP pairing GUID lives in `~/.gphoto/`.** Delete that file to re-pair; some cameras refuse a second connection without forgetting the host on the camera menu too.
- **`--capture-image-and-download` may write to the card first AND pull the file.** Some cameras can be set to "sdram" (memory-only) via `/main/settings/capturetarget=0`; others force card writes. To save both: leave default. To skip card: try `capturetarget=0` first.
- **`%n` counter in `--filename` template is per-gphoto2-invocation**, not per-camera. Start a fresh invocation and your numbering resets. Use `%Y%m%d-%H%M%S` timestamps for monotonicity across runs.
- **Sony cameras in "PC Remote" mode vs mass-storage mode.** Sony's default is mass-storage = invisible to gphoto2. Switch the camera menu to "PC Remote" (or "Connect to Smartphone" for PTP/IP) before plugging in.
- **Battery drain.** Tethered live-view with `capture-preview` loops drains the battery fast. Use a dummy battery / DC coupler for long sessions.
- **Don't `input(` for confirmations in scripts.** gphoto2 itself doesn't prompt; keep the wrapper non-interactive.

---

## Examples

### Example 1: "What camera is plugged in?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py detect
```

### Example 2: "Shoot 100-frame bracket, download each, name by timestamp"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py shoot --download --count 100 \
  --template "shoot-%Y%m%d-%H%M%S-%04n.%C"
```

### Example 3: "Set f/8, ISO 200, 1/125s then fire"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-set --key /main/capturesettings/aperture --value 8
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-set --key /main/imgsettings/iso --value 200
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py config-set --key /main/capturesettings/shutterspeed --value 1/125
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py shoot --download
```

### Example 4: "24-hour timelapse, one frame every 60 seconds"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py timelapse \
  --interval 60 --count 1440 --dest ./24h-tl/
```

Then assemble with ffmpeg: `ffmpeg -framerate 30 -pattern_type glob -i '24h-tl/*.JPG' -c:v libx264 -crf 20 timelapse.mp4`.

### Example 5: "Grab one live-view frame every second for 5 minutes"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py preview --fps 1 --duration 300 --dest ./lv/
```

### Example 6: "Connect to Nikon Z over Wi-Fi, download new shots"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/tether.py ptpip --host 192.168.1.50 -- bulk-download --dest ./ingest/
```

---

## Troubleshooting

### Error: `Could not claim the USB device`

**Cause:** Another process (PTPCamera on macOS, gvfs-gphoto2-volume-monitor on GNOME) is holding the device.
**Solution:** macOS: `killall PTPCamera`. GNOME: `systemctl --user stop gvfs-gphoto2-volume-monitor`.

### Error: `Unknown model`

**Cause:** Camera is in wrong USB mode or libgphoto2 is too old for that body.
**Solution:** Check camera menu for "PC Remote" / "PTP" / "MTP" and pick PTP. Update libgphoto2 (`brew upgrade libgphoto2` / `apt install libgphoto2-6`).

### Error: `bad parameter` on `--set-config`

**Cause:** The value isn't in the allowed list for that key.
**Solution:** `config-get --key <key>` shows the allowed values (`Choice: 0 Auto`, `Choice: 1 100`, ...). Pass the exact string or the index via `--set-config-index`.

### `--capture-preview` returns "Operation not supported"

**Cause:** Camera doesn't expose live-view over PTP, or is in the wrong mode.
**Solution:** Put camera into movie / live-view mode manually; for Sony, switch mode to "PC Remote". Some bodies only give preview when the mirror is up (press live-view button on body).

### Camera works on first shot then hangs

**Cause:** USB driver bug — libgphoto2 leaves file handle open.
**Solution:** Upgrade libgphoto2 to >= 2.5.28. Or run each shot in a fresh subprocess (the wrapper does this by default).

### PTP/IP connect hangs

**Cause:** Camera hasn't saved the host, or Wi-Fi is on wrong SSID.
**Solution:** Re-pair in camera menu; verify camera IP via `ping`; confirm port 15740 is open (no firewall).

---

## Reference docs

- Per-camera config-key differences (Canon vs Nikon vs Sony key paths) -> [`references/config-keys.md`](references/config-keys.md). Load when user asks about shutter/aperture/ISO keys.
