# JACK backends

`jackd -d <backend> [-d <device>] [-r rate] [-p period] [-n nperiods] …`

JACK always takes exactly one backend. The backend-specific flags come *after*
the backend's `-d` and before the ones the backend itself consumes. Per-backend
details below. Man page: `jackd(1)`. Interactive flag discovery: `jackd -d <backend> --help`.

---

## `alsa` (Linux)

The default Linux backend. Talks ALSA directly (`/dev/snd/...`).

Common flags:

| Flag | Meaning |
|---|---|
| `-d <hw:0>` / `-d plughw:USB` | ALSA device name. `hw:` is bit-perfect, `plughw:` lets ALSA do sample-format conversion. |
| `-r 48000` | Sample rate. |
| `-p 256` | Period size (frames). |
| `-n 2` | Number of periods in the hardware buffer. USB class-compliant often needs 3. |
| `-D` | Duplex mode (capture + playback). Default when supported. |
| `-P <hw:0>` / `-C <hw:0>` | Playback-only / capture-only device (useful for async split). |
| `-s` | Enable software monitoring (loopback). |
| `-S` | 16-bit mode (truncate instead of dither). |
| `-o 2` / `-i 2` | Limit playback / capture channel counts. |
| `-z shaped` | Dither type: `rectangular`, `triangular`, `shaped`, `none`. |
| `-X seq` / `-X raw` | MIDI driver: `seq` (ALSA sequencer) or `raw` (rawmidi). |

Pitfalls:

- `plughw:` introduces SRC; use `hw:` for low-latency bit-perfect.
- Default `asoundrc` that routes through `dmix` competes with JACK for the device;
  either tell JACK to grab it directly (`-d hw:0`) or route ALSA through JACK.

---

## `coreaudio` (macOS)

Wraps the macOS HAL (`AudioObject*` APIs).

| Flag | Meaning |
|---|---|
| `-d <UID>` | Device UID. Find with `jackd -d coreaudio -l`. |
| `-r 48000` | Sample rate (must match device). |
| `-p 256` | Period size. |
| `-n 2` | Number of periods. macOS prefers 2; bump if xruns. |
| `-D` | Duplex. |
| `-P <UID>` / `-C <UID>` | Playback-only / capture-only. |
| `-I 1` | Capture channel offset. |
| `-O 1` | Playback channel offset. |

Pitfalls:

- Use Audio MIDI Setup to build an Aggregate Device when driving multiple
  physical interfaces. JACK drives the Aggregate as one.
- Apple Silicon macOS has no legacy kext audio drivers; aggregate + DriverKit
  (BlackHole, Loopback) are the only virtualization options.

---

## `portaudio` (Windows / cross-platform)

Wraps PortAudio. On Windows this is the path to WASAPI / MME / DirectSound / WDMKS.

| Flag | Meaning |
|---|---|
| `-d <index>` | PortAudio device index (see `jackd -d portaudio -l`). |
| `-r 44100` | Sample rate. |
| `-p 256` | Period size. |
| `-n 2` | Number of periods. |
| `-i <n>` / `-o <n>` | Input / output channel counts. |

Pitfalls:

- PortAudio's default on Windows is MME, which is laggy. Prefer a WASAPI or
  WDM/KS-backed PortAudio build.
- For ASIO on Windows, JACK has a separate ASIO backend; see below.

---

## ASIO (Windows, Steinberg)

ASIO is Steinberg's parallel stack bypassing the Windows audio engine.
JACK's ASIO backend is `jackd -d asio` on Windows builds; the flags match
portaudio but use the ASIO driver directly:

| Flag | Meaning |
|---|---|
| `-d <ASIO driver name>` | e.g. "ASIO4ALL v2", "Focusrite USB ASIO". |
| `-r 48000 -p 256 -n 2` | As elsewhere. |

Pitfalls:

- Only one process can hold the ASIO driver at a time. If your DAW is open and
  has the driver, JACK can't claim it.
- ASIO4ALL is a WDM-KS shim; FlexASIO is a WASAPI bridge. For JACK↔ASIO app
  bridging see FlexASIO + FlexASIO_GUI.

---

## `dummy`

Runs JACK with no actual hardware — scheduling loop only. Useful for
non-audio testing or CI.

```bash
jackd -d dummy -r 48000 -p 1024
```

---

## Sample-rate + buffer-size cheat sheet

One-way output latency = `period * nperiods / samplerate`.

| Rate | Period | nperiods | One-way latency |
|---|---|---|---|
| 44100 | 64 | 2 | 2.9 ms |
| 48000 | 64 | 2 | 2.7 ms |
| 48000 | 128 | 2 | 5.3 ms |
| 48000 | 128 | 3 | 8.0 ms |
| 48000 | 256 | 2 | 10.7 ms |
| 48000 | 256 | 3 | 16.0 ms |
| 48000 | 512 | 2 | 21.3 ms |
| 96000 | 128 | 2 | 2.7 ms |
| 96000 | 256 | 2 | 5.3 ms |
