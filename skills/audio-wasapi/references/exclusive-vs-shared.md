# WASAPI: Shared mode vs Exclusive mode

Deep dive on the two WASAPI stream sharing modes. Most real Windows audio bugs
are really "shared-mode resampling surprise" or "exclusive-mode format
negotiation failure". This doc explains both paths end-to-end.

Microsoft refs:

- <https://learn.microsoft.com/en-us/windows/win32/coreaudio/about-the-windows-core-audio-apis>
- <https://learn.microsoft.com/en-us/windows/win32/coreaudio/wasapi>
- <https://learn.microsoft.com/en-us/windows/win32/coreaudio/exclusive-mode-streams>
- <https://learn.microsoft.com/en-us/windows/win32/coreaudio/device-formats>

---

## Stack

Top to bottom for a single audio app:

```
App (Spotify, DAW, game)
  ↓  WASAPI (IAudioClient, IAudioRenderClient)
  ↓  MMDevice API (endpoint enumeration, default-device role)
  ↓  Windows Audio Engine (audiodg.exe, APO / Audio Processing Objects)
  ↓  WDM / KS (kernel streaming)
  ↓  Driver (AVStream minidriver or USB Audio class driver)
  ↓  Hardware
```

- Shared mode streams pass through **audiodg.exe** and get mixed + resampled.
- Exclusive mode bypasses audiodg — the driver hands its buffer directly to
  the single holding process.

ASIO is a parallel path that goes App → ASIO driver → Hardware, bypassing
WASAPI / Audio Engine entirely. FlexASIO bridges ASIO → WASAPI for apps that
only speak ASIO.

---

## Shared mode (default)

`IAudioClient::Initialize(AUDCLNT_SHAREMODE_SHARED, ...)`

What happens:

1. App requests any format.
2. Audio Engine presents a **mix format** — a fixed WAVE format the endpoint
   uses internally (typically 48 kHz 24-bit float, per Sound Control Panel →
   Properties → Advanced).
3. If app format ≠ mix format, the engine inserts a resampler / bit-depth
   converter. Every stream gets mixed into the engine buffer.
4. The mix is fed to the driver's periodic buffer.

Latency:

- Historically ~10–30 ms (engine period × 2).
- With `IAudioClient3::InitializeSharedAudioStream` on Win10+, sub-3 ms is
  achievable *if* the driver's `GetSharedModeEnginePeriod` reports a small
  fundamental period.
- Event-driven mode (`AUDCLNT_STREAMFLAGS_EVENTCALLBACK`) vs timer-driven
  mode matters: event mode lets the driver signal the app, trimming a period
  of jitter.

Advantages: Every app works; no exclusive locking; bit-depth/rate can be
anything reasonable.

Disadvantages: All streams are resampled through the engine mix format — not
bit-perfect. Not truly low-latency without `IAudioClient3`.

---

## Exclusive mode

`IAudioClient::Initialize(AUDCLNT_SHAREMODE_EXCLUSIVE, ...)`

What happens:

1. App requests a **specific** WAVE format (sample rate, bit depth, channels,
   channel mask).
2. Driver accepts or rejects. **No resampler in this path.** If the hardware
   can't do 96 kHz 24-bit 5.1, you get `AUDCLNT_E_UNSUPPORTED_FORMAT`.
3. If accepted, the audio engine evicts the device — no other app can play to
   it.
4. App writes samples directly into the driver's buffer on periodic
   callback.

Latency: ~1–10 ms achievable. With event-driven callbacks and a 3 ms period,
round-trip DSP is viable (DAW monitoring).

Advantages: Bit-perfect. No engine resampling. Lowest attainable Windows
latency for a given driver.

Disadvantages: Blocks every other app. System sounds are silent while the
exclusive app is holding the device.

---

## The "exclusive mode allowed" registry toggle

Per endpoint:

```
HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\<GUID>\
  Properties\
    {b3f8fa53-0004-438e-9003-51a46e139bfc},2   (REG_DWORD)
```

Values:

- `1` — "Allow applications to take exclusive control of this device" checked.
- `0` — Blocked. Any exclusive-mode request returns
  `AUDCLNT_E_EXCLUSIVE_MODE_NOT_ALLOWED`.

Same toggle: Sound Control Panel → Playback → device → Properties → Advanced.

Capture endpoints live under `...\Audio\Capture\<GUID>\` with the same
property GUID.

---

## Format negotiation pitfalls

Apps typically try a ladder of formats in exclusive mode: 44.1/16, 48/16,
44.1/24, 48/24, 96/24, 192/24. Whichever the driver agrees to "wins".

Common failures:

- **Channel mask mismatch.** Requesting 5.1 (FL FR FC LFE BL BR) against a
  stereo endpoint. Driver rejects even if rate + bit depth match.
- **Bit depth mismatch.** Device supports 24-bit packed (3 bytes) but the app
  asks for 24-bit in 32-bit container (4 bytes with 8 zero bits). Use
  `WAVEFORMATEXTENSIBLE` with `wValidBitsPerSample=24` and
  `wBitsPerSample=32` — some drivers require the latter encoding.
- **Rate mismatch.** A driver at "44.1 kHz fixed" refuses any other rate —
  common in old USB DACs.

Debug pattern:

1. Sound Control Panel → device → Properties → Advanced → click each
   "Default Format" option. These are the **guaranteed** shared-mode formats.
2. For exclusive mode, the driver's supported exclusive formats are usually
   a subset. Some apps (foobar2000, JRiver) can probe via "Output device →
   Exclusive format".

---

## IAudioClient3 low-latency shared mode

New in Win10 1803+. Lets a shared-mode stream run at a small engine period
without exclusive locking.

Flow:

```cpp
IAudioClient3* client;
client->GetSharedModeEnginePeriod(
    mixFormat,
    &defaultPeriod,   // what audiodg normally uses (e.g. 480 frames)
    &fundamentalPeriod,
    &minPeriod,       // what you can request (e.g. 64 frames)
    &maxPeriod);

client->InitializeSharedAudioStream(
    AUDCLNT_STREAMFLAGS_EVENTCALLBACK,
    minPeriod,    // request 64 frames @ 48k = 1.3 ms
    mixFormat,
    nullptr);
```

Caveats:

- Only supported if the driver opts in (most USB Audio Class 2.0 + WASAPI
  drivers do).
- `minPeriod` is hardware-dependent; some drivers return 480 frames regardless.
- Even at 64 frames the stream still passes through audiodg APOs, so not
  bit-perfect — just low-latency.

---

## Latency cheatsheet (48 kHz)

Approximate one-way output latency:

| Path | Period (frames) | One-way latency |
|---|---|---|
| Shared-mode default (no IAudioClient3) | 480 × 2 | ~20 ms |
| Shared-mode `IAudioClient3` min period | 64 | ~1.3 ms |
| Exclusive-mode event-driven | 128 | ~2.7 ms |
| Exclusive-mode event-driven | 64 | ~1.3 ms |
| ASIO typical | 64–128 | ~2–3 ms |

Real numbers depend heavily on driver, USB topology, and hardware buffer
architecture.

---

## Event-driven vs timer-driven callbacks

`AUDCLNT_STREAMFLAGS_EVENTCALLBACK` + `SetEventHandle`:

- Driver signals a kernel event when its buffer has room.
- App wakes and writes. No polling, no wasted wakeups.
- Needed to hit the latency numbers above.

Timer-driven (default, no flag):

- App sets a periodic timer, polls the buffer.
- Works but adds one period of jitter.

Always use event-driven for pro-audio code.

---

## ASIO sideline

ASIO (Steinberg Audio Stream Input/Output) is a parallel driver model. Its
latency numbers are comparable to exclusive-mode WASAPI + event-driven, but
on Windows ASIO has one key advantage: apps that only speak ASIO (older
DAWs, some plugins) can still hit low latency via ASIO4ALL or FlexASIO
bridging to WDM/KS or WASAPI. There is no "ASIO audio engine" — each ASIO
driver is its own kernel path.

FlexASIO (<https://github.com/dechamps/FlexASIO>) is a thin WASAPI shared or
exclusive mode wrapper exposed as an ASIO driver. Useful for apps that want
ASIO but hardware that speaks WASAPI.
