---
name: audio-pipewire
description: >
  Route and introspect Linux audio/video/MIDI graphs with PipeWire: pw-cli (interactive object/module control), pw-dump (full graph JSON with --monitor), pw-link (list/create/destroy port links), pw-cat / pw-play / pw-record (playback+record), pw-top (real-time DSP load + xrun viewer), pw-metadata (shared metadata store), pw-loopback (source/sink bridges), pw-midiplay/pw-midirecord, pw-jack (JACK client compat shim), pw-mon, pw-profiler. WirePlumber session manager handles routing/defaults/profiles. Replaces PulseAudio (via pipewire-pulse) and JACK (via libjack.so shim) simultaneously. Use when the user asks to route Linux audio, link two apps, list audio devices on Linux, create a loopback, record system audio, monitor the audio graph, or set up a virtual audio device on modern Linux.
argument-hint: "[action]"
---

# Audio PipeWire

**Context:** $ARGUMENTS

## Quick start

- **List audio graph objects:** → Step 1 (`pwctl.py list`)
- **Dump the whole graph as JSON:** → Step 2 (`pwctl.py dump`)
- **Render a compact ASCII graph:** → Step 2 (`pwctl.py graph`)
- **Connect app A → device B:** → Step 3 (`pwctl.py link <src> <dst>`)
- **Play / record a file:** → Step 4 (`pwctl.py play` / `record`)
- **Create a virtual cable (loopback):** → Step 5 (`pwctl.py loopback`)
- **Watch DSP load / xruns:** → Step 6 (`pwctl.py top`)
- **Change default sink/source:** → Step 7 (`pwctl.py metadata-set`)

## When to use

- User is on Linux and wants to route audio between apps or devices.
- User asks about PipeWire, `pw-*` commands, or WirePlumber.
- User needs to list/filter nodes and ports, create port-level links, or set the
  default sink/source.
- User asks how to create a virtual audio device on Linux — use `pw-loopback`.
- User wants to debug audio latency or xruns on Linux.

Not for: macOS (use `audio-coreaudio`), Windows (use `audio-wasapi`), or JACK-specific
workflows (use `audio-jack` — but note that on modern Linux, `jackd` is almost always
the PipeWire libjack shim anyway).

---

## Step 1 — List objects

Probe the current graph for every node/port/link/device/module/metadata object:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py list
```

Filter by type (keeps output manageable on busy desktops):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py list --kind Node
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py list --kind Port
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py list --kind Link
```

For the full object-type taxonomy see [`references/elements.md`](references/elements.md).

---

## Step 2 — Dump / graph

Full JSON snapshot of every object, matching the output format that `pw-dump` itself
produces:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py dump
```

Stream live updates (useful when diagnosing a node that appears only when an app
is launched):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py dump --monitor
```

Client-side substring filter:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py dump --filter firefox
```

Compact ASCII rendering (nodes on the left, their outgoing links on the right):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py graph
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py graph --kind audio   # audio links only
```

---

## Step 3 — Link / unlink ports

`pw-link` operates at the port level. Each audio node has one port per channel.
To bridge stereo Firefox → Scarlett playback front-left/front-right:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FL' 'alsa_output.usb-Focusrite_Scarlett:playback_FL'
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FR' 'alsa_output.usb-Focusrite_Scarlett:playback_FR'
```

List existing links:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py links
```

Remove a link:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py unlink 'Firefox:output_FL' 'alsa_output.usb-Focusrite_Scarlett:playback_FL'
```

You can pass numeric object ids (from `list`) instead of names.

---

## Step 4 — Play / record files

`pw-cat` is the unified playback+record tool. `pw-play`/`pw-record` are symlinks:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py play path/to/track.wav
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py play path/to/track.wav --target alsa_output.usb-...
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py record captured.wav --duration 10
```

`record` is implemented as `pw-cat --record`. PipeWire negotiates format from the
file extension (WAV / FLAC / RAW). For MIDI use `pw-midiplay` / `pw-midirecord` directly
(not wrapped here — they take SMF files).

---

## Step 5 — Loopback (virtual cable)

`pw-loopback` creates a virtual source↔sink pair that any app can target. Classic
use case: capture system audio into OBS by recording from the loopback source.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py loopback --name MyVirtualCable --channels 2
```

Bridge specific endpoints:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py loopback \
  --name StreamMix \
  --capture 'alsa_input.usb-...' \
  --playback 'alsa_output.usb-...'
```

`pw-loopback` runs in the foreground; kill with SIGINT when done. To make one
permanent, add a module fragment under `~/.config/pipewire/pipewire.conf.d/` or a
WirePlumber Lua script.

---

## Step 6 — Watch DSP load / xruns

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py top                     # curses TUI
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py top --batch-mode --iterations 5
```

Columns: S(tate), id, QUANTum, RATE, WAIT, BUSY, W/Q (wait/quantum%), B/Q (busy/quantum%),
ERR (xruns), FORMAT, NAME.

Rule of thumb: if B/Q > ~70% a node can't keep up with its quantum; drop quantum or
raise the period.

---

## Step 7 — Metadata (default sink/source)

`pw-metadata` reads/writes the shared metadata store. WirePlumber and
`pipewire-pulse` both consult it.

Read the current defaults:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py metadata-get --id 0
```

Change the default audio sink (note the JSON-wrapped value — WirePlumber requires it):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py metadata-set \
  --id 0 --key default.configured.audio.sink \
  --value '{ "name": "alsa_output.usb-Focusrite_Scarlett" }' \
  --type Spa:String:JSON
```

To see WirePlumber's config search paths (where to drop a Lua fragment to persist
changes):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py wireplumber-config
```

---

## Gotchas

- **WirePlumber is the current session manager.** `pipewire-media-session` is
  deprecated and won't match the behavior of a current WirePlumber-based distro.
  Don't look up Lua/Spa-Json config against the old media-session docs.
- **PipeWire's `jackd` shim vs real JACK.** On most modern Linux desktops the `jackd`
  binary on `$PATH` is PipeWire's libjack shim — starting it a second time does not
  change quantum/period/samplerate. To raise/lower quantum under PipeWire use
  `pw-metadata -n settings 0 clock.force-quantum <N>` (set 0 to let WirePlumber pick).
- **Port names can contain spaces, colons, and dots.** Always quote them.
  `pw-link "node name:port name" "other:port"`. Numeric ids are safer for scripts.
- **Channel layout mismatch refuses to link.** Linking a mono source to a stereo
  sink needs two explicit port-level links (or a `channelmap`/loopback). PipeWire
  won't auto-broadcast.
- **`pw-dump` without `--monitor` is a snapshot**, not a live stream. For an app
  that only creates its nodes on startup, run `--monitor` and then launch the app.
- **`pw-cat --record` does not take `--duration`.** This wrapper wraps with `timeout`
  to bound a recording. Without it, record until SIGINT.
- **Changing default sink via `pw-metadata` only persists if WirePlumber policy
  saves it.** For true persistence, add a WirePlumber Lua fragment under
  `~/.config/wireplumber/main.lua.d/`.
- **`pw-loopback` exits as soon as you interrupt it.** For persistent virtual
  cables, load the `libpipewire-module-loopback` module from a config fragment
  instead of running the CLI.
- **`pw-top` measures **graph** time, not CPU %.** A B/Q near 100% means "this
  node is burning almost all of its scheduled quantum", which may or may not be
  the CPU bottleneck.
- **Object IDs change between daemon restarts.** Hardcode node **names**
  (e.g. `alsa_output.usb-Focusrite_Scarlett`) in scripts, not ids.
- **Metadata JSON values need the `Spa:String:JSON` type hint.** Plain strings
  don't deserialize — WirePlumber will silently ignore the write.
- **`pw-jack <app>` vs `jackd`.** `pw-jack firefox` launches Firefox against
  PipeWire's libjack shim for the process only — useful for testing JACK apps
  without replacing system jackd.

---

## Examples

### Example 1 — "Route Firefox to my USB interface"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py list --kind Port      # find port names
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FL' 'alsa_output.usb-Focusrite_Scarlett:playback_FL'
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FR' 'alsa_output.usb-Focusrite_Scarlett:playback_FR'
```

### Example 2 — "Capture system audio for OBS"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py loopback --name OBS_Cable --channels 2
# Point OBS's "Audio Input Capture" at OBS_Cable, then route apps to it:
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FL' 'OBS_Cable:input_FL'
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py link 'Firefox:output_FR' 'OBS_Cable:input_FR'
```

### Example 3 — "My audio keeps dropping; is it xruns?"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py top --batch-mode --iterations 20
# Look at the ERR column. Then raise the quantum:
pw-metadata -n settings 0 clock.force-quantum 1024
```

### Example 4 — "List every link in the graph"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py links
```

### Example 5 — "Change default sink"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/pwctl.py metadata-set \
  --id 0 --key default.configured.audio.sink \
  --value '{ "name": "alsa_output.usb-Focusrite_Scarlett" }' \
  --type Spa:String:JSON
```

---

## Troubleshooting

### Error: `pw-cli: command not found` / `pw-link: command not found`

**Cause:** PipeWire is not installed or `$PATH` missing.
**Fix:** Install the distro package (Fedora: `pipewire`, `pipewire-utils`;
Debian/Ubuntu: `pipewire-bin`, `wireplumber`). Confirm with `pw-cli --version`.

### `pw-link` exits with "port not found"

**Cause:** Port name string doesn't match, or the source/sink doesn't exist yet.
**Fix:** Run `pwctl.py list --kind Port` to see the exact names. Quote shell-special
chars. Or pass numeric ids from `list`.

### `pw-dump` returns empty `[]`

**Cause:** PipeWire daemon not running under the current session. On some minimal
installs the service isn't autostarted.
**Fix:** `systemctl --user start pipewire.service pipewire-pulse.service wireplumber.service`
and retry.

### Loopback disappears after logout

**Cause:** `pw-loopback` CLI is tied to the foreground process.
**Fix:** Persist via `libpipewire-module-loopback` in a config fragment under
`~/.config/pipewire/pipewire.conf.d/`, or a WirePlumber Lua fragment.

### Default sink resets on reboot

**Cause:** WirePlumber's `default-nodes.lua` did not persist the change.
**Fix:** Write a Lua persistence fragment under `~/.config/wireplumber/main.lua.d/`
instead of relying solely on `pw-metadata`.

---

## Reference docs

- Object/type taxonomy (Node, Port, Link, Device, Module, Metadata) and common
  property keys → [`references/elements.md`](references/elements.md).
