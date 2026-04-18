# Virtual audio cables + mixers on Windows

Reference for the two dominant free-ish options: VB-Cable (single cable) and
VoiceMeeter (mixer with many virtual buses). Both ship from VB-Audio
(<https://vb-audio.com/>). Plus the NirSoft `svcl.exe` CLI reference that
`audio-wasapi` recommends when `AudioDeviceCmdlets` doesn't suffice.

---

## VB-Audio Virtual Cable

<https://vb-audio.com/Cable/>

One installer creates two endpoints internally wired:

- **CABLE Input** — appears as a playback device. Anything routed here is
  "played into the cable".
- **CABLE Output** — appears as a recording device. Captures whatever was
  played to CABLE Input.

Install:

1. Download `VBCABLE_Driver_Pack.zip` from the page above.
2. Unzip, right-click `VBCABLE_Setup_x64.exe`, Run as administrator.
3. Reboot.

Uninstall: `VBCABLE_Setup_x64.exe` has an "Uninstall Driver" button.

Tiers (multiple simultaneous cables):

| Product | Cables |
|---|---|
| VB-Cable (free / donationware) | 1 pair |
| VB-Cable A+B (paid) | +2 named pairs |
| VB-Cable C+D (paid) | +2 more named pairs |

Each paid tier is a separate installer and shows distinct device names.

Typical uses:

- **Capture system audio into OBS:** Set Windows default output =
  CABLE Input. In OBS, Audio Input Capture = CABLE Output.
- **Route a specific app's output to a transcription tool:** Per-app output
  device (Windows 10+ App volume and device preferences) = CABLE Input.
  Transcription tool reads from CABLE Output.
- **Send two different audio streams to two different apps:** Need A+B
  cables (or VoiceMeeter). Assign music app to A, chat to B.

Gotchas:

- **"Listen to this device" on CABLE Output sends the audio to your speakers
  as well** — the go-to trick for monitoring while also capturing.
- VB-Cable is **WDM**-based (audiodg goes through it). It IS affected by
  system-volume changes and sample-rate format negotiation.
- Sample rate is set per-cable in its Control Panel app (VBCABLE_ControlPanel.exe).
  Mismatch with the source endpoint → the audio engine resamples, audible
  artifacts on critical listening.

---

## VoiceMeeter / Banana / Potato

<https://voicemeeter.com/>

Virtual mixer + virtual audio devices (VAIO inputs/outputs) + ASIO host.

| Edition | Physical ins | Virtual ins | Physical outs | Virtual outs |
|---|---|---|---|---|
| VoiceMeeter (free) | 2 | 1 | 1 | 1 |
| Banana (donationware) | 3 | 2 | 3 | 2 |
| Potato (donationware) | 5 | 3 | 5 | 3 |

Install:

1. Download the exe for your edition.
2. Run as admin. Reboot.
3. Open VoiceMeeter. Each strip on the left = input, each bus at the top =
   output.

Core mental model:

- **Virtual inputs** (VAIO 1/2/3) appear as playback devices to Windows. Route
  apps' output to them.
- **Virtual outputs** (VAIO OUT 1/2/3) appear as recording devices. Route the
  mixer's output here so OBS / Discord / etc. can pick it up.
- **Physical inputs** are your mic / line-in / ASIO.
- **Physical outputs** are your speakers / headphones.
- Every strip can be routed to any combination of A1/A2/A3 (physical) and
  B1/B2 (virtual) buses with per-strip gain / EQ / compressor.

Common routing — OBS while hearing everything yourself:

```
Input strip 1 (Windows Default playback = VoiceMeeter Input)
  → A1 (your speakers) AND B1 (virtual out 1)
Input strip 2 (your mic on physical in 3)
  → A1 (so you hear yourself) AND B1 (so OBS captures you)
OBS Audio Input Capture source: VoiceMeeter Output (VB-Audio VoiceMeeter VAIO)
```

Scriptable control:

- `VoicemeeterRemote.dll` C API — get/set parameters, subscribe to level
  meters.
- Python: `pip install voicemeeter-api` (unofficial) wraps the DLL.
- MIDI + OSC integration for stage control.

Config files (GUI-edited): `%APPDATA%\VB\Voicemeeter\*.xml` (one per edition).

Gotchas:

- **Sample rate of the engine must match the physical A1 device.** Otherwise
  the Audio Engine stops. Menu → System Settings → "Preferred Main SampleRate".
- **Only one process can use the ASIO driver.** If your DAW has Focusrite
  ASIO, VoiceMeeter can't also use it — one will fail.
- **Latency adds up.** VoiceMeeter adds ~10–15 ms on top of the physical path.
  Not appropriate for live monitoring while recording vocals.

---

## NirSoft `svcl.exe` flag reference

<https://www.nirsoft.net/utils/sound_volume_command_line.html>

Freeware, single binary. Useful when AudioDeviceCmdlets isn't installable or
the user is scripting old machines.

| Flag | Meaning |
|---|---|
| `/SetDefault "<Name>" [Role]` | Set default device. Role = `all`, `Console`, `Multimedia`, `Communications`. |
| `/SetAppDefault "<Name>" [Role] <process>` | Per-app default (Windows 10+). |
| `/SetVolume "<Name>" <0-100>` | Device or app volume. |
| `/ChangeVolume "<Name>" <±%>` | Relative change. |
| `/Mute "<Name>"` | Mute. |
| `/Unmute "<Name>"` | Unmute. |
| `/Switch "<Name>"` | Toggle mute. |
| `/GetPercent "<Name>"` | Print percent to stdout. |
| `/GetColumnValue "<Name>" <column>` | E.g. `"Device State"` returns Active/Disabled. |
| `/Disable "<Name>"` | Disable endpoint. |
| `/Enable "<Name>"` | Enable endpoint. |
| `/SaveProfile <file>` | Save current audio state. |
| `/LoadProfile <file>` | Restore from a saved state. |
| `/stab <file>` | Save device list to tab-separated file. |
| `/scomma <file>` | Save device list to CSV. |

`<Name>` matches by full name or by `DeviceName\ItemName` (e.g.
`"Speakers\Realtek High Definition Audio"`).

Example — save current audio state, set up an OBS routing, then restore:

```cmd
svcl.exe /SaveProfile pre-obs.cfg
svcl.exe /SetDefault "CABLE Input (VB-Audio Virtual Cable)" all
REM ...stream here...
svcl.exe /LoadProfile pre-obs.cfg
```

Profiles are great for launcher scripts that switch device layouts per-game
or per-app.
