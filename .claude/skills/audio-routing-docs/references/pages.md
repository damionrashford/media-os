# Page catalog

Annotated list of every doc page the `audiodocs.py` script can fetch.
Each entry lists the key's short name, upstream URL, and one-line scope.
Invoke `uv run scripts/audiodocs.py list-pages` for the live version.

---

## docs.pipewire.org — PipeWire (Linux)

| Page key | URL | Covers |
|---|---|---|
| `pipewire-home` | https://docs.pipewire.org/ | Landing page. Start here for architecture overview. |
| `pipewire-programs` | https://docs.pipewire.org/page_programs.html | Index of every `pw-*` CLI with one-line descriptions. |
| `pipewire-man-pipewire` | https://docs.pipewire.org/page_man_pipewire_1.html | The `pipewire` daemon itself (config dir, `-c` config flag, lifetime). |
| `pipewire-man-pw-cli` | https://docs.pipewire.org/page_man_pw-cli_1.html | Interactive / one-shot command for any object/module/proxy control. |
| `pipewire-man-pw-dump` | https://docs.pipewire.org/page_man_pw-dump_1.html | Full graph as JSON. `--monitor` streams updates for live graph watching. |
| `pipewire-man-pw-link` | https://docs.pipewire.org/page_man_pw-link_1.html | List / create / destroy port-level links. `-l`, `-i`, `-o`, `-d`. |
| `pipewire-man-pw-cat` | https://docs.pipewire.org/page_man_pw-cat_1.html | Unified playback+record tool. `pw-play`/`pw-record` are symlinks. |
| `pipewire-man-pw-top` | https://docs.pipewire.org/page_man_pw-top_1.html | Real-time DSP load, xrun counters, node quantum stats. |
| `pipewire-man-pw-metadata` | https://docs.pipewire.org/page_man_pw-metadata_1.html | Shared metadata store (defaults, routing hints). |
| `pipewire-man-pw-loopback` | https://docs.pipewire.org/page_man_pw-loopback_1.html | Create a source↔sink bridge (virtual cable). |
| `pipewire-man-pw-midiplay` | https://docs.pipewire.org/page_man_pw-midiplay_1.html | Play a Standard MIDI File through PipeWire. |
| `pipewire-man-pw-midirecord` | https://docs.pipewire.org/page_man_pw-midirecord_1.html | Record MIDI input to an SMF. |
| `pipewire-man-pw-jack` | https://docs.pipewire.org/page_man_pw-jack_1.html | JACK-API compatibility shim — runs JACK apps under PipeWire. |
| `pipewire-man-pw-mon` | https://docs.pipewire.org/page_man_pw-mon_1.html | Monitor (human-readable) graph/object events. |
| `pipewire-man-pw-profiler` | https://docs.pipewire.org/page_man_pw-profiler_1.html | Collect profiler data for latency/xrun analysis. |
| `pipewire-man-pw-reserve` | https://docs.pipewire.org/page_man_pw-reserve_1.html | Reserve a device (desktop spec D-Bus API). |
| `pipewire-man-pw-config` | https://docs.pipewire.org/page_man_pw-config_1.html | Dump the effective config after all fragments are merged. |
| `wireplumber-home` | https://pipewire.pages.freedesktop.org/wireplumber/ | WirePlumber — the current session manager. Lua config, default routing. |

Notes:

- The old `pipewire-media-session` is deprecated. Do not send new questions there.
- `pw-pulse` and `pw-jack` are **service/shim** names, not binaries you run directly.
  `pw-jack <app>` launches an app with PipeWire's libjack shim in `LD_LIBRARY_PATH`.

---

## jackaudio.org — JACK Audio Connection Kit

| Page key | URL | Covers |
|---|---|---|
| `jack-home` | https://jackaudio.org/ | Landing page, FAQ, download link. |
| `jack-api` | https://jackaudio.org/api/ | The JACK C API (`jack_client_open`, `jack_activate`, port/buffer funcs). |
| `jack-faq` | https://jackaudio.org/faq/ | FAQ — what's JACK1 vs JACK2, latency tuning, period size guidance. |
| `jack-stanford` | https://ccrma.stanford.edu/docs/common/JACK.html | Stanford CCRMA user-level reference; covers `jackd`, `jack_lsp`, `jack_connect`, QjackCtl. |
| `jacktrip-docs` | https://jacktrip.github.io/jacktrip/ | JackTrip — uncompressed multichannel UDP over the internet. |
| `jacktrip-github` | https://github.com/jacktrip/jacktrip | JackTrip source / README with build + server/client invocation. |

Notes:

- `jack_control` is JACK2-only (D-Bus). JACK1 has no D-Bus surface.
- On modern Linux, `jackd` on `$PATH` often comes from PipeWire's `pipewire-jack`
  shim rather than real jackd. Check with `ldd $(which jackd)`.

---

## developer.apple.com — Apple Core Audio (macOS)

| Page key | URL | Covers |
|---|---|---|
| `coreaudio-overview` | https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/WhatisCoreAudio/WhatisCoreAudio.html | "What is Core Audio" — HAL, AU, AudioQueue, AudioFile, AudioToolbox. |
| `coreaudio-essentials` | https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/CoreAudioEssentials/CoreAudioEssentials.html | Design essentials: pull model, callbacks, buffer lists, properties. |
| `coreaudio-frameworks` | https://developer.apple.com/library/archive/documentation/MusicAudio/Conceptual/CoreAudioOverview/CoreAudioFrameworks/CoreAudioFrameworks.html | Framework map: AudioUnit, AudioToolbox, CoreAudio, CoreMIDI, OpenAL. |
| `coreaudio-glossary` | https://developer.apple.com/library/archive/documentation/MusicAudio/Reference/CoreAudioGlossary/Glossary/core_audio_glossary.html | Term definitions — "HAL", "aggregate device", "AU", "pull model". |
| `coreaudio-modern` | https://developer.apple.com/documentation/coreaudio | Modern Swift/Objective-C API reference for the CoreAudio framework. |
| `switchaudio-osx` | https://github.com/deweller/switchaudio-osx | `SwitchAudioSource` — brew-installable CLI to change default devices. |
| `blackhole-github` | https://github.com/ExistentialAudio/BlackHole | BlackHole virtual driver (2ch/16ch/64ch). Apple-Silicon-compatible. |

Notes:

- Soundflower is abandoned; won't load on Big Sur+ / Apple Silicon. Always recommend
  BlackHole instead.
- Loopback (Rogue Amoeba) is commercial. Background Music is free, single-purpose
  (per-app mute / volume).

---

## learn.microsoft.com — Windows WASAPI / Core Audio APIs

| Page key | URL | Covers |
|---|---|---|
| `wasapi-overview` | https://learn.microsoft.com/en-us/windows/win32/coreaudio/about-the-windows-core-audio-apis | Top-level: WASAPI / MMDevice / DeviceTopology / EndpointVolume. |
| `wasapi-spec` | https://learn.microsoft.com/en-us/windows/win32/coreaudio/wasapi | WASAPI itself (IAudioClient, IAudioRenderClient, IAudioCaptureClient). |
| `wasapi-exclusive` | https://learn.microsoft.com/en-us/windows/win32/coreaudio/exclusive-mode-streams | Exclusive-mode streams: bit-perfect, lowest-latency, IAudioClient3. |
| `wasapi-device-formats` | https://learn.microsoft.com/en-us/windows/win32/coreaudio/device-formats | Device default / mix format negotiation; WAVEFORMATEXTENSIBLE. |
| `wasapi-mmdevice` | https://learn.microsoft.com/en-us/windows/win32/coreaudio/mmdevice-api | MMDevice API — enumerate endpoints, role (eMultimedia/eCommunications). |
| `wasapi-soundvolumeview` | https://www.nirsoft.net/utils/sound_volume_view.html | NirSoft GUI + CLI — per-app volumes, save/restore profiles. |
| `wasapi-svcl` | https://www.nirsoft.net/utils/sound_volume_command_line.html | svcl.exe — pure CLI (SetDefault, Mute, SetVolume, SetAppDefault). |
| `wasapi-audiodevicecmdlets` | https://github.com/frgnca/AudioDeviceCmdlets | PowerShell module — `Get-AudioDevice`, `Set-AudioDevice`, etc. |
| `wasapi-vbcable` | https://vb-audio.com/Cable/ | VB-Audio Virtual Cable: A+B / C+D tiers, install + WDM driver. |
| `wasapi-voicemeeter` | https://voicemeeter.com/ | VoiceMeeter / Banana / Potato — virtual mixer + ASIO bridge. |

Notes:

- Windows has no first-party CLI to change the default audio device; everything is
  third-party. NirSoft's tools are freeware closed-source binaries.
- ASIO is Steinberg's proprietary parallel stack, bypassing Windows audio engine.
  FlexASIO and ASIO4ALL bridge ASIO↔WASAPI for apps that only speak one dialect.
