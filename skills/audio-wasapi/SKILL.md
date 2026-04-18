---
name: audio-wasapi
description: >
  Manipulate Windows audio via WASAPI (learn.microsoft.com/coreaudio): SoundVolumeView + svcl.exe (NirSoft — set default device, per-app volumes, save/load profiles), AudioDeviceCmdlets PowerShell module (Get-AudioDevice, Set-AudioDevice, Get-AudioDevicePlaybackMute), nircmd setdefaultsounddevice. Shared mode (Windows engine resamples all streams to endpoint fixed format) vs Exclusive mode (bit-perfect, audiophile, ~sub-3ms latency with IAudioClient3 + event-driven callbacks). WASAPI then MMDevice then Audio Engine (audiodg.exe) then WDM/KS. ASIO is Steinberg's parallel stack bypassing Windows audio. Virtual audio devices: VB-Audio Virtual Cable, VoiceMeeter/Banana/Potato. Use when the user asks to change Windows default audio device, route app audio, use VoiceMeeter, install VB-Cable, set a specific device from PowerShell, or enable exclusive-mode low-latency output.
argument-hint: "[action]"
---

# Audio WASAPI

**Context:** $ARGUMENTS

## Quick start

- **List all audio endpoints:** → Step 1 (`winaudio.py list-devices`)
- **Check current default:** → Step 2 (`winaudio.py get-default`)
- **Change default output/input/communications:** → Step 3 (`winaudio.py set-default`)
- **Mute / unmute / change volume:** → Step 4 (`winaudio.py mute`/`unmute`/`volume`)
- **Check if exclusive mode is allowed on a device:** → Step 5 (`winaudio.py exclusive-test`)
- **Install VB-Cable virtual cable:** → Step 6 (`winaudio.py vbcable-install`)
- **Set up VoiceMeeter virtual mixer:** → Step 7 (`winaudio.py voicemeeter-config`)

## When to use

- User is on Windows and needs terminal / PowerShell-driven audio control.
- User wants to change the default playback/recording/communications device
  without clicking through Sound settings.
- User wants bit-perfect exclusive-mode output for audiophile playback, or to
  diagnose why an app can't grab the device in exclusive mode.
- User wants to install a virtual audio cable (VB-Cable, VoiceMeeter) to route
  system audio into OBS / streaming tools.
- User is debugging a shared-mode vs exclusive-mode mismatch (pops, silence,
  format negotiation errors).

Not for: macOS (use `audio-coreaudio`), Linux (use `audio-pipewire`).

The script exits 2 with a helpful message if run on non-Windows.

Read [`references/exclusive-vs-shared.md`](references/exclusive-vs-shared.md)
when the user asks about latency, bit-perfect playback, or
`IAudioClient::Initialize` errors.
Read [`references/virtual-cable.md`](references/virtual-cable.md) when the user
asks about OBS system-audio capture or VoiceMeeter routing.

---

## Step 1 — List devices

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py list-devices
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py list-devices --kind playback
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py list-devices --kind recording
```

Calls `Get-AudioDevice -List` (from the AudioDeviceCmdlets PowerShell module).
If the module isn't installed the PowerShell errors out — install with:

```powershell
Install-Module -Name AudioDeviceCmdlets -Scope CurrentUser
```

Output columns: `Index`, `Default`, `Type`, `Name`, `ID`.

---

## Step 2 — Get current default

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py get-default
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py get-default --kind recording
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py get-default --kind communications
```

Windows has three separate default roles:

| Role | Used by |
|---|---|
| `playback` (eMultimedia) | Music/movie apps that request "default" device |
| `recording` (eMultimedia for capture) | Your default mic |
| `communications` (eCommunications) | Zoom / Teams / Discord for voice |

---

## Step 3 — Change the default

Pass the device name exactly as `list-devices` printed it (quote for spaces):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "Speakers (Realtek High Definition Audio)"
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "Focusrite USB Audio" --kind recording
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "Shure MV7+" --kind communications
```

Alternatives not wrapped here (also valid):

- **`nircmd setdefaultsounddevice "<Name>"`** — older NirCmd, smaller.
- **`svcl.exe /SetDefault "<Name>" Playback`** — NirSoft command-line version
  of SoundVolumeView. See [`references/virtual-cable.md`](references/virtual-cable.md)
  for full `svcl` flags.

---

## Step 4 — Mute / unmute / volume

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py mute   "Speakers (Realtek High Definition Audio)"
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py unmute "Speakers (Realtek High Definition Audio)"
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py volume "Speakers (Realtek High Definition Audio)" --level 50
```

For per-app (not per-device) volume, use NirSoft's SoundVolumeView GUI or
`svcl.exe /SetAppDefault <process>.exe Playback`. Per-app volume is not
wrapped here because the app-vs-device distinction deserves explicit CLI args.

---

## Step 5 — Probe exclusive-mode permission

Exclusive mode gives an app sole ownership of the device at a negotiated
format. Bit-perfect, lowest latency, but blocks every other app.

Each endpoint has a registry flag "Allow applications to take exclusive
control of this device". The wrapper reads it:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py exclusive-test "Speakers (Realtek High Definition Audio)"
```

Output:

```
Speakers (Realtek High Definition Audio) -> exclusive mode: allowed|blocked|unknown
```

`allowed` = apps can request exclusive mode. `blocked` = Windows will always
return `AUDCLNT_E_EXCLUSIVE_MODE_NOT_ALLOWED`. The toggle lives in Sound
Control Panel → Properties → Advanced.

To **set** that flag from script you need elevation + registry write — not
wrapped here deliberately. See
[`references/exclusive-vs-shared.md`](references/exclusive-vs-shared.md) for
the manual path and the audio-engine implications.

---

## Step 6 — VB-Audio Virtual Cable

The go-to free virtual audio cable on Windows. Creates two endpoints
(CABLE Input = a virtual speaker, CABLE Output = a virtual mic) that are
internally wired. Anything played to CABLE Input is captured from CABLE Output.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py vbcable-install
```

Prints the download URL and install steps (does **not** auto-download). The
script refuses to fetch the installer itself — VB-Audio is donationware + has
paid tiers; auto-install risks violating their T&Cs.

Typical OBS system-audio pattern:

1. Install VB-Cable.
2. Set Windows default playback = VB-Cable Input. Now all system audio is
   routed into the cable instead of your speakers.
3. Configure OBS Audio Input Capture = VB-Cable Output.
4. To still hear system audio, also route VB-Cable Input out to your speakers
   via VoiceMeeter, or use "Listen to this device" on the CABLE Output
   properties.

---

## Step 7 — VoiceMeeter

VoiceMeeter is a virtual mixer that ships its own set of virtual WDM devices
(VAIO1/2/3) and acts as an ASIO host. Free for the 2-bus version, donationware
for Banana (3 physical + 2 virtual) and Potato (5+3).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py voicemeeter-config
```

Prints the install URL and basic setup. Configuration is primarily GUI; the
config XML lives under `%APPDATA%\VB\Voicemeeter`. Scriptable via the
C API (`VoicemeeterRemote.dll`) or the unofficial Python binding
`pip install voicemeeter-api`. See
[`references/virtual-cable.md`](references/virtual-cable.md) for a worked
routing example.

---

## Gotchas

- **Windows has no first-party CLI to change audio devices.** Everything here
  is third-party (AudioDeviceCmdlets, NirSoft SoundVolumeView/svcl, VB-Audio).
  Expect install steps.
- **AudioDeviceCmdlets isn't signed by Microsoft** — `Install-Module` from
  PSGallery is trust-by-repository. Users with strict execution policy may
  need `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **Device names are not stable across Windows updates.** A Windows update
  that reinstalls a Realtek driver renames endpoints from "Speakers (2-
  Realtek Audio)" to "Speakers (Realtek Audio)". Script around Name at your
  peril — prefer the immutable endpoint `Id` GUID from `Get-AudioDevice -List`.
- **`set-default` via AudioDeviceCmdlets changes the Multimedia default;
  communications is a separate flag.** Zoom/Discord pull from the
  communications endpoint by default, not the multimedia one. To change both,
  call `set-default --kind playback` then `set-default --kind communications`.
- **Exclusive mode is gated per-endpoint, not per-app.** The endpoint toggle
  blanket-allows or blanket-blocks. An app still has to successfully
  **negotiate** a format (bit depth + rate + channel layout) that the hardware
  supports in exclusive mode, or `IAudioClient::Initialize` returns
  `AUDCLNT_E_UNSUPPORTED_FORMAT`.
- **The Windows audio engine (`audiodg.exe`) always resamples shared-mode
  streams to the endpoint's fixed "mix format".** If the mix format is
  48 kHz 24-bit, a 44.1 kHz 16-bit track gets resampled before it even hits
  the device. This is why bit-perfect listeners use exclusive mode.
- **WASAPI's `IAudioClient3::InitializeSharedAudioStream` gives sub-3 ms
  latency without exclusive mode**, but requires Windows 10+ and an endpoint
  whose audio engine period is small enough (`GetSharedModeEnginePeriod`).
  Not every driver / hardware combo supports it.
- **VB-Cable is donationware + has paid A+B / C+D variants.** Installing
  multiple variants gives you multiple cables — they don't conflict, but keep
  track of which one you're pointing apps at.
- **VoiceMeeter + physical ASIO app conflict.** Only one process can hold the
  ASIO driver. If your DAW has claimed the interface's ASIO driver,
  VoiceMeeter can't bridge to it simultaneously.
- **ASIO4ALL and FlexASIO are different.** ASIO4ALL wraps WDM/KS; FlexASIO
  wraps WASAPI. Both offer an ASIO layer to apps that only speak ASIO, but
  FlexASIO plays better with modern WASAPI-aware hardware.
- **SoundVolumeView and svcl.exe are the same tool — svcl is the pure-CLI
  version.** Both are NirSoft freeware closed-source. No PSGallery equivalent.
- **The registry flag for "exclusive mode allowed" lives under
  `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\
  <GUID>\Properties\{b3f8fa53-0004-438e-9003-51a46e139bfc},2`** — that's what
  `exclusive-test` reads. Writing requires SYSTEM / admin + a reboot to take
  effect for some driver stacks.
- **After installing / removing a virtual audio driver (VB-Cable, VoiceMeeter),
  existing apps do NOT see the new device until they reopen their endpoint
  enumeration.** Most restart-to-pickup.

---

## Examples

### Example 1 — "Swap default output to my headphones for Spotify"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py list-devices --kind playback
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "Headphones (Sony WH-1000XM5 Stereo)"
```

### Example 2 — "Make Zoom use my USB mic without affecting music apps"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "Microphone (USB PnP Sound Device)" --kind communications
# Multimedia default stays on your studio interface for music/games.
```

### Example 3 — "Capture system audio into OBS"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py vbcable-install
# (run the printed installer; reboot)
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py set-default "CABLE Input (VB-Audio Virtual Cable)"
# Point OBS Audio Input Capture at "CABLE Output (VB-Audio Virtual Cable)"
```

### Example 4 — "Why does Foobar2000 say exclusive mode failed?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/winaudio.py exclusive-test "Speakers (Realtek High Definition Audio)"
# If output says "blocked", open Sound Control Panel -> the device -> Properties
# -> Advanced tab -> check "Allow applications to take exclusive control".
# If "allowed", the app's requested format is not supported at the hardware
# level — try 44100 Hz 16-bit to match CD, or inspect the endpoint's supported
# formats in that same Advanced tab.
```

### Example 5 — "Script this across many machines"

```powershell
# Skip the Python wrapper; call AudioDeviceCmdlets directly:
Import-Module AudioDeviceCmdlets
$d = Get-AudioDevice -List | Where-Object { $_.Name -like '*Focusrite*' -and $_.Type -eq 'Playback' }
Set-AudioDevice -Index $d.Index
```

The wrapper is a convenience layer; any PowerShell script targeting the same
cmdlet works fine.

---

## Troubleshooting

### `Import-Module: The specified module 'AudioDeviceCmdlets' was not loaded`

**Cause:** Module not installed.
**Fix:**

```powershell
Install-Module -Name AudioDeviceCmdlets -Scope CurrentUser -Force
```

### `Get-AudioDevice : Running scripts is disabled on this system`

**Cause:** Execution policy `Restricted` (default on Windows Server).
**Fix:**

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### `set-default` succeeded but the app still plays through old device

**Cause:** Many apps cache the endpoint at startup and don't listen for
`MMDevice` default-change notifications. Restart the app.
**Fix:** Restart the app, or for Chromium-based apps use their internal
"Audio output" setting in site permissions.

### Exclusive-mode app gets `AUDCLNT_E_UNSUPPORTED_FORMAT`

**Cause:** Requested format isn't natively supported by the driver in
exclusive mode. No resampler runs in exclusive mode.
**Fix:** Match exactly what the Properties → Advanced tab lists as a
supported format, or switch to shared mode (accepts the engine mix format
via resampling).

### VB-Cable installed but doesn't appear

**Cause:** Installer ran but driver signing was blocked; reboot skipped.
**Fix:** Reboot. If still missing, reinstall as Administrator and approve
the UAC / driver-signing prompt when it appears.

### VoiceMeeter shows "Audio Engine" stopped

**Cause:** Sample-rate mismatch between physical A1 output and VoiceMeeter's
internal engine rate.
**Fix:** Menu → System Settings/Options → set engine rate to match the
physical interface's configured sample rate.

---

## Reference docs

- Shared-mode vs exclusive-mode deep dive, latency tradeoffs, IAudioClient3 →
  [`references/exclusive-vs-shared.md`](references/exclusive-vs-shared.md).
- VB-Cable tiers, `svcl.exe` flag reference, VoiceMeeter routing examples →
  [`references/virtual-cable.md`](references/virtual-cable.md).
