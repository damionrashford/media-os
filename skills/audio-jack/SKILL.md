---
name: audio-jack
description: >
  Route professional low-latency audio with JACK Audio Connection Kit (jackaudio.org): jackd server (ALSA/CoreAudio/PortAudio/ASIO backends), jack_control (D-Bus JACK2 config), jack_lsp (list ports/connections), jack_connect/jack_disconnect (manage links), jack_cpu_load, jack_samplerate, jack_bufsize (runtime period size), jack_transport, jack_rec (multi-channel WAV recording), jack_iodelay (round-trip latency), jack_wait, jack_midi_dump. JACK1 C maintenance vs JACK2 C++ multicore. Modern Linux swaps jackd for PipeWire's libjack shim — same client API. JackTrip for uncompressed multichannel UDP over the Internet. Use when the user asks to run a JACK server, connect audio clients, measure roundtrip latency, record from JACK ports, set JACK period size, or bridge JACK over the network with JackTrip.
argument-hint: "[action]"
---

# Audio JACK

**Context:** $ARGUMENTS

## Quick start

- **Start a JACK server:** → Step 1 (`jackctl.py start`)
- **List ports / connections:** → Step 2 (`jackctl.py ports`)
- **Connect two clients:** → Step 3 (`jackctl.py link`)
- **Check buffer size / rate / CPU:** → Step 4 (`jackctl.py status`)
- **Measure round-trip latency:** → Step 5 (`jackctl.py latency`)
- **Record N ports to WAV:** → Step 6 (`jackctl.py record`)
- **Send audio over the internet:** → Step 7 (`jackctl.py jacktrip`)

## When to use

- User wants guaranteed low-latency routing between pro-audio apps that speak the
  JACK client API (Ardour, Reaper, Carla, SuperCollider, Pure Data, Bitwig, REAPER).
- User wants to bridge multichannel audio across the internet with JackTrip.
- User wants explicit control over period size / number of periods / sample rate.
- User's distro runs PipeWire — the libjack shim still answers all these commands,
  but see Gotchas.

Not for: generic Linux desktop routing (use `audio-pipewire`), macOS default-device
changes (use `audio-coreaudio`), Windows default-device changes (use `audio-wasapi`).

---

## Step 1 — Start a JACK server

`jackd` accepts a single backend driver after `-d`. This wrapper picks a per-OS
default (`alsa` on Linux, `coreaudio` on macOS, `portaudio` on Windows).

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py start \
  --rate 48000 --period 256 --nperiods 2
```

Force backend + device:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py start \
  --backend alsa --device hw:0 --rate 48000 --period 128
```

Typical period / nperiods:

| Scenario | `--period` | `--nperiods` |
|---|---|---|
| Live performance, PCIe / Thunderbolt card | 64–128 | 2 |
| Tracking / monitoring, USB class-compliant | 128–256 | 3 |
| Mixing, offline | 512–1024 | 2 |

See [`references/backends.md`](references/backends.md) for per-backend flag quirks.

On JACK2 systems with D-Bus, `jack_control` can drive the server instead — this
wrapper does not (jack_control is interactive by design; scripts should call
`jackd` directly as shown).

---

## Step 2 — List ports and connections

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports                 # just port names
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --connections   # -c: who connects to what
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --types         # -t: audio vs midi
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --input         # -i: input ports only
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --output        # -o: output ports only
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --latency       # -l: port latency info
```

Flags combine.

---

## Step 3 — Link / unlink ports

JACK ports use the `client:port` naming convention. The physical device typically
lives under the `system` client:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py link 'Ardour:MixL' 'system:playback_1'
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py link 'Ardour:MixR' 'system:playback_2'
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py unlink 'Ardour:MixL' 'system:playback_1'
```

Quote names with shell-special chars (spaces, colons, parens).

---

## Step 4 — Inspect runtime state

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py status
```

Prints `jack_samplerate`, `jack_bufsize`, and `jack_cpu_load` back-to-back.
High CPU load combined with xruns = lower `--period` isn't achievable on this
host/backend; raise it.

Change buffer size at runtime (JACK2 only):

```bash
jack_bufsize 512     # bare jack tool — wrapper intentionally doesn't wrap this
```

---

## Step 5 — Measure round-trip latency

`jack_iodelay` creates a client named `jack_delay` with one input + one output.
To measure a loopback you have to wire it:

```bash
# Start the tool
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py latency \
  --capture-port system:capture_1 --playback-port system:playback_1
```

With the suggestion printed, in another shell connect the loopback cable
path (physical or virtual):

```bash
jack_connect jack_delay:out system:playback_1
jack_connect system:capture_1 jack_delay:in
```

`jack_iodelay` reports round-trip delay in frames + milliseconds. Divide by 2 to
get one-way.

---

## Step 6 — Record from JACK ports

`jack_rec` writes a multichannel interleaved WAV from a list of ports:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py record out.wav \
  --channels system:capture_1 system:capture_2 --duration 30
```

The wrapper uses `timeout` for `--duration`. Without `--duration`, record until
SIGINT.

---

## Step 7 — Network audio with JackTrip

JackTrip sends uncompressed multichannel audio over UDP for remote ensembles.
Requires one peer in server mode and one in client mode:

```bash
# On the host with a static / known IP:
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py jacktrip server --channels 2

# On the other side:
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py jacktrip client \
  --host studio.example.com --channels 2
```

See [`references/jacktrip.md`](references/jacktrip.md) for hub mode, FEC, and
port/firewall details.

---

## Gotchas

- **On modern Linux, `jackd` is almost always PipeWire's libjack shim.** Running
  `jackctl.py start` under PipeWire starts a second jackd that PipeWire's shim
  already emulates — usually a no-op / error. Check with `ldd $(which jackd)`
  or `pw-cli info 0`. For PipeWire environments, use `audio-pipewire` instead;
  existing JACK client apps already work against PipeWire's shim.
- **JACK1 vs JACK2 matter.** JACK1 is single-process C, no D-Bus, no
  `jack_control`. JACK2 is multi-process C++ with D-Bus. Only JACK2 can
  dynamically change buffer size via `jack_bufsize` at runtime. If you need the
  D-Bus API, require JACK2.
- **There is no `jackd stop`.** Server exits when its controlling process does,
  or on SIGTERM / SIGKILL. This wrapper's `stop` sends SIGTERM after trying
  `jack_control exit` for JACK2.
- **Period size × nperiods = latency.** Total latency (one-way, output) is
  roughly `(period * nperiods) / samplerate`. At 48 kHz, 256 × 2 ≈ 10.7 ms.
  USB class-compliant interfaces often need `nperiods=3`.
- **Connecting two **output** ports or two **input** ports fails silently.**
  JACK doesn't broadcast direction errors — `jack_connect` just returns non-zero.
- **`system:capture_*` and `system:playback_*` are **from the server's POV**.**
  `capture_1` is an **output** port (audio captured from the device, flowing into
  the graph). `playback_1` is an **input** port (audio leaving the graph into
  the device). This trips everyone at least once.
- **JACK port names are not identifiers — they're full strings with `:` in them.**
  Always quote when passing to a shell.
- **Mixing sample rates is impossible.** Every JACK client must run at the server's
  sample rate. If a clip is 44.1 kHz and the server is 48 kHz, resample upstream.
- **Multiple physical interfaces need a single aggregate.** JACK can only drive
  one backend device. For multiple cards on Linux use ALSA's `dmix`/`multi`
  plugins or `zita-ajbridge`; on macOS build an Aggregate Device first
  (see `audio-coreaudio`).
- **JackTrip needs UDP port `4464` open by default** plus the per-channel data
  ports. If you're behind NAT with no port forwarding, use hub mode through a
  public relay.
- **`jack_rec` on some distros is missing or replaced by `jack_capture`.**
  Check `which jack_rec`. If absent, install the `jack-example-tools` / `jack-tools`
  package.
- **`jack_iodelay` doesn't know the actual latency path.** It just reports what
  a round-trip through its own ports measured. You have to wire that round-trip.

---

## Examples

### Example 1 — "Start JACK with 5ms latency at 48k"

```bash
# 128 frames / 48000 Hz = 2.67 ms per period. 2 periods = 5.33 ms output latency.
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py start --rate 48000 --period 128 --nperiods 2
```

### Example 2 — "Patch Ardour's master bus to the physical outputs"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py ports --output       # find Ardour's ports
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py link 'Ardour:Master/out-L' 'system:playback_1'
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py link 'Ardour:Master/out-R' 'system:playback_2'
```

### Example 3 — "Multichannel record from a Scarlett 18i20"

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py record session.wav \
  --channels system:capture_1 system:capture_2 system:capture_3 system:capture_4 \
             system:capture_5 system:capture_6 system:capture_7 system:capture_8 \
  --duration 300
```

### Example 4 — "Ensemble rehearsal across two cities"

On the rehearsal space with the static IP:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py jacktrip server --channels 4
```

On the guest player's machine:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py jacktrip client --host rehearsal.example.com --channels 4
```

Both sides then wire `JackTrip:receive_*` and `JackTrip:send_*` to their monitors
and interfaces with `jack_connect`.

### Example 5 — "What's my actual round-trip latency?"

```bash
# Physical loopback: patch playback_1 back into capture_1 with a TRS cable.
uv run ${CLAUDE_SKILL_DIR}/scripts/jackctl.py latency \
  --capture-port system:capture_1 --playback-port system:playback_1
# Then in another shell run the two jack_connect commands it prints.
```

---

## Troubleshooting

### `Cannot lock down memory area` / `Cannot use real-time scheduling`

**Cause:** Running `jackd` without RT privileges.
**Fix:** Add the user to the `audio` group (Linux) and ensure
`/etc/security/limits.d/95-jack.conf` has `@audio - rtprio 95` and
`@audio - memlock unlimited`. Log out / in to pick up. On macOS `jackd`
requests RT automatically if entitled.

### `JACK server not running or cannot be started`

**Cause:** Trying to connect a client before `jackd` has started, or the backend
device is busy (e.g. ALSA device grabbed by PulseAudio/PipeWire).
**Fix:** On PipeWire-based distros, don't run `jackd` — use PipeWire's shim.
On PulseAudio, suspend it: `pactl suspend-sink 1 && pactl suspend-source 1`.

### XRuns constantly

**Cause:** Period too small for the host or the backend, or IRQ contention.
**Fix:** Raise `--period` (256 → 512 → 1024). Check `jack_cpu_load` — above
~60% on long stretches is risky. On Linux, confirm a low-latency / RT kernel.

### Connecting two output ports does nothing

**Cause:** Direction mismatch — JACK rejects silently (return code only).
**Fix:** Source must be an **output** port (flows out of a client) and
destination must be an **input** port.

### `jack_iodelay` prints "no port found"

**Cause:** `jack_iodelay` starts a client named `jack_delay` — if a previous run
didn't clean up, the name is taken.
**Fix:** Kill any stale `jack_iodelay`, then retry.

### JackTrip works but audio is one-way

**Cause:** Only the server's firewall is open. UDP requires both sides to accept
the return path.
**Fix:** Ensure both peers allow inbound UDP on the jacktrip port
(default `4464`) plus the negotiated per-channel data ports.

---

## Reference docs

- Per-backend driver flag catalog (ALSA, CoreAudio, PortAudio, ASIO) →
  [`references/backends.md`](references/backends.md).
- JackTrip server/client/hub mode, FEC, port list →
  [`references/jacktrip.md`](references/jacktrip.md).
