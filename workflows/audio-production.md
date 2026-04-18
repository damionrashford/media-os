# Audio Production Workflow

**What:** Full-stack audio work — system-level routing across macOS/Linux/Windows, MIDI and OSC control surfaces, DAW integration, DSP (EQ/compression/spatial), AI denoise and stem separation, binaural/HRTF, loudness normalization.

**Who:** Audio engineers, DAW users, producers, sound designers, podcast producers, live-sound techs, anyone building an audio-focused pipeline that integrates with more than just a DAW.

---

## Skills used

| Role | Skill | What it does |
|---|---|---|
| System audio routing docs | `audio-routing-docs` | Cross-platform audio-graph reference |
| Linux audio | `audio-pipewire` | `pw-cli`, `pw-link`, `wpctl`, virtual sinks, PulseAudio compat |
| Cross-platform low-latency | `audio-jack` | JACK + `jack_lsp`, `jack_connect`, `jack_transport` |
| macOS audio | `audio-coreaudio` | AUHAL, aggregate devices, BlackHole, Loopback |
| Windows audio | `audio-wasapi` | WASAPI loopback, VB-Cable, VoiceMeeter |
| MIDI | `media-midi` | MIDI 1.0 + 2.0 UMP, CoreMIDI/ALSA/WinMM, sendmidi/amidi, rtpmidi |
| OSC | `media-osc` | Open Sound Control — TouchOSC, Reaper, Max/MSP |
| SoX | `media-sox` | Classical audio DSP |
| FFmpeg audio filter | `ffmpeg-audio-filter` | loudnorm, EQ, resample, compander, channels |
| FFmpeg audio FX | `ffmpeg-audio-fx` | Chorus, flanger, echo, LADSPA/LV2 |
| Spatial / binaural | `ffmpeg-audio-spatial` | HRTF via sofalizer, surround upmix |
| AI denoise | `media-denoise-ai` | DeepFilterNet, RNNoise, Resemble Enhance |
| Stem separation | `media-demucs` | Vocals / drums / bass / other |
| AI music gen | `media-musicgen` | Riffusion / YuE (Apache-2 only) |
| TTS + voice clone | `media-tts-ai` | Kokoro, OpenVoice, Piper (no XTTS-v2/F5-TTS) |
| Whisper ASR | `media-whisper` | Speech-to-text |
| Loudness | `media-ffmpeg-normalize` | EBU R128 / ATSC A/85 / Spotify |
| Captions | `ffmpeg-captions`, `ffmpeg-subtitles` | Broadcast + web captions |

---

## The pipeline — by category

### Platform — system audio routing

#### Linux (PipeWire, modern default)

```bash
# List devices
uv run .claude/skills/audio-pipewire/scripts/pwctl.py list-devices

# Create a virtual sink (for app audio capture)
uv run .claude/skills/audio-pipewire/scripts/pwctl.py create-sink \
  --name "OBS-Mix" --channels 2

# Route Chrome → OBS-Mix
uv run .claude/skills/audio-pipewire/scripts/pwctl.py link \
  --from chrome --to OBS-Mix

# PulseAudio compatibility shim (old apps)
pactl list modules | grep pulse
```

#### macOS (Core Audio)

```bash
# List devices
uv run .claude/skills/audio-coreaudio/scripts/coreaudiolist.py list-devices

# Create aggregate device (multi-mic summing)
uv run .claude/skills/audio-coreaudio/scripts/coreaudiolist.py create-aggregate \
  --name "Podcast-In" \
  --devices "BlackHole 2ch,USB Microphone"

# BlackHole + Loopback for virtual routing
# (external apps; this skill covers AUHAL-level control)
```

#### Windows (WASAPI)

```bash
# List devices
uv run .claude/skills/audio-wasapi/scripts/wasapilist.py list-devices

# WASAPI loopback (capture system audio)
ffmpeg -f dshow -i "audio=Stereo Mix (Realtek)" -ac 2 -ar 48000 system-audio.wav

# VB-Cable / VoiceMeeter virtual routing
# (external apps; covered in reference docs)
```

#### Cross-platform (JACK)

```bash
# Start JACK server
jackd -d coreaudio -r 48000 -p 128  # macOS
jackd -d alsa -r 48000 -p 128       # Linux
jackd -d portaudio -r 48000 -p 128  # Windows

# List ports
uv run .claude/skills/audio-jack/scripts/jackctl.py list-ports

# Connect DAW → SuperCollider
uv run .claude/skills/audio-jack/scripts/jackctl.py connect \
  --from "ardour:master out" --to "SuperCollider:in"

# Transport (play/stop across JACK-aware apps)
uv run .claude/skills/audio-jack/scripts/jackctl.py transport --action play
```

### Control — MIDI + OSC

#### MIDI (1.0 + 2.0 UMP)

```bash
# List MIDI ports
uv run .claude/skills/media-midi/scripts/midictl.py list-ports

# Monitor MIDI input
uv run .claude/skills/media-midi/scripts/midictl.py monitor --json

# Send MIDI note
uv run .claude/skills/media-midi/scripts/midictl.py send-note \
  --port "IAC Bus 1" --channel 1 --note 60 --velocity 100 --duration 0.5

# Map MIDI controller to OBS scene
uv run .claude/skills/media-midi/scripts/midictl.py monitor --json | \
  jq --unbuffered -r 'select(.type=="noteon" and .note==36) | "Main"' | \
  while read scene; do
    uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene "$scene"
  done
```

#### OSC (Open Sound Control)

```bash
# Send OSC message
uv run .claude/skills/media-osc/scripts/oscctl.py send \
  --host 127.0.0.1 --port 8000 \
  --address "/track/1/volume" --args 0.85

# Listen for OSC (TouchOSC, Reaper)
uv run .claude/skills/media-osc/scripts/oscctl.py listen --port 8000 --json

# Bridge OSC to MIDI
uv run .claude/skills/media-osc/scripts/oscctl.py listen --port 8000 --json | \
  jq --unbuffered -r 'select(.address=="/note") | .args[0]' | \
  while read n; do
    uv run .claude/skills/media-midi/scripts/midictl.py send-note \
      --port "IAC Bus 1" --note "$n" --velocity 100
  done
```

### DSP — audio processing

#### Classical DSP (SoX)

```bash
# Multi-effect chain
uv run .claude/skills/media-sox/scripts/soxrun.py process \
  --input raw.wav --output processed.wav \
  --effects "highpass 80 equalizer 3000 1 3 compand 0.3,1 6:-70,-60,-20 -5 -90 0.2 gain -n -1"

# Stem split by frequency
uv run .claude/skills/media-sox/scripts/soxrun.py split-freq \
  --input mix.wav \
  --bands "0-200,200-2000,2000-20000" \
  --output-dir stems/
```

#### FFmpeg audio filters

```bash
# Comprehensive chain in ffmpeg
ffmpeg -i source.wav \
  -af "\
    aresample=48000:filter_size=512:cutoff=0.97, \
    highpass=f=80, \
    acompressor=threshold=-20dB:ratio=3:attack=200:release=1000, \
    equalizer=f=200:w=1:g=-3, \
    equalizer=f=3000:w=1:g=3, \
    alimiter=limit=0.95, \
    loudnorm=I=-16:TP=-1:LRA=11" \
  processed.wav
```

#### LADSPA / LV2 plugins

```bash
# List installed LV2 plugins
uv run .claude/skills/ffmpeg-audio-fx/scripts/afx.py list-lv2

# Apply LV2 plugin
ffmpeg -i voice.wav \
  -af "lv2=p=urn:zamaudio:ZaMultiCompX2" \
  processed.wav
```

#### Spatial audio — HRTF binaural

```bash
uv run .claude/skills/ffmpeg-audio-spatial/scripts/spatial.py hrtf \
  --input mono.wav --output binaural.wav \
  --azimuth 45 --elevation 0 \
  --sofa-file cipic-subject-021.sofa
```

Or upmix stereo → 5.1:
```bash
uv run .claude/skills/ffmpeg-audio-spatial/scripts/spatial.py surround \
  --input stereo.wav --output surround.wav --layout 5.1
```

### AI audio

#### Denoise

```bash
# DeepFilterNet (best general speech, permissive license)
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
  --input noisy.wav --output clean.wav

# RNNoise (lightweight, embeddable)
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py rnnoise \
  --input noisy.wav --output clean.wav

# Resemble Enhance (speech super-resolution)
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py resemble \
  --input phone-call.wav --output enhanced.wav
```

#### Stem separation

```bash
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input song.wav --output-dir stems/ --model htdemucs

# 6-stem (adds piano + guitar)
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input song.wav --output-dir stems/ --model htdemucs_6s
```

#### TTS

```bash
uv run .claude/skills/media-tts-ai/scripts/ttsctl.py kokoro \
  --text "Welcome to the show." --voice af --output intro.wav
```

#### Music generation

```bash
uv run .claude/skills/media-musicgen/scripts/musicctl.py riffusion \
  --prompt "Ambient cinematic pad" --duration 30 --output score.wav
```

#### ASR / transcription

```bash
uv run .claude/skills/media-whisper/scripts/whisper.py transcribe \
  --input interview.wav --output transcript.srt --model medium.en
```

### Loudness compliance

```bash
# Target per spec:
# -23 LUFS EBU R128 (European broadcast)
# -24 LUFS ATSC A/85 (US broadcast)
# -14 LUFS Spotify Master
# -16 LUFS Apple Podcasts
# -19 LUFS ACX audiobook
# -27 LUFS broadcast commercial (pre-Fletcher)

uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input source.wav --output normalized.wav \
  --target -14 --true-peak -1 --lra 11
```

---

## Cross-layer composite workflows

### Live-monitored DAW recording

```bash
# 1. Start JACK with low buffer
jackd -d coreaudio -r 48000 -p 64 &

# 2. Connect DAW I/O
uv run .claude/skills/audio-jack/scripts/jackctl.py connect \
  --from "system:capture_1" --to "ardour:Mic In/in 1"

# 3. MIDI controller → DAW
uv run .claude/skills/media-midi/scripts/midictl.py list-ports | \
  grep "Launch Control XL"

# 4. OSC tablet control
uv run .claude/skills/media-osc/scripts/oscctl.py listen --port 9000 --json | \
  python -c "import json,sys; [print(f'{l[\"address\"]}: {l[\"args\"]}') for l in map(json.loads, sys.stdin)]"
```

### Podcast episode cleanup with AI

See [`podcast-pipeline.md`](podcast-pipeline.md) for the full pipeline. Key audio ops:

```bash
# 1. AI denoise per mic
for t in host guest; do
  uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
    --input raw/${t}.wav --output clean-${t}.wav
done

# 2. Polish with ffmpeg
for t in host guest; do
  ffmpeg -i clean-${t}.wav \
    -af "highpass=f=80,equalizer=f=200:w=1:g=-3,equalizer=f=3000:w=1:g=3,acompressor=threshold=-20dB:ratio=3" \
    polished-${t}.wav
done

# 3. Mix with sidechain ducking
ffmpeg -i polished-host.wav -i polished-guest.wav -i music.wav \
  -filter_complex "[0][1]amix=inputs=2[v];[v]asplit[vk][vm];[2][vk]sidechaincompress=threshold=0.04:ratio=8[duck];[vm][duck]amix" \
  mix.wav

# 4. Loudness normalize
uv run .claude/skills/media-ffmpeg-normalize/scripts/normalize.py ebu \
  --input mix.wav --output final.wav --target -16
```

### Binaural audiodrama from stereo

```bash
# 1. Split stereo to multiple mono tracks for spatial placement
ffmpeg -i stereo.wav -map_channel 0.0.0 left.wav -map_channel 0.0.1 right.wav

# 2. Per-track HRTF positioning
uv run .claude/skills/ffmpeg-audio-spatial/scripts/spatial.py hrtf \
  --input left.wav --output left-binaural.wav --azimuth -90

uv run .claude/skills/ffmpeg-audio-spatial/scripts/spatial.py hrtf \
  --input right.wav --output right-binaural.wav --azimuth 90

# 3. Sum
ffmpeg -i left-binaural.wav -i right-binaural.wav \
  -filter_complex "[0][1]amix=inputs=2:normalize=0" \
  binaural.wav
```

### DAW → OBS system audio routing (macOS)

```bash
# 1. Create aggregate
uv run .claude/skills/audio-coreaudio/scripts/coreaudiolist.py create-aggregate \
  --name "OBS-Mix" --devices "BlackHole 2ch,Built-in Microphone"

# 2. Point DAW output → BlackHole 2ch
# 3. OBS audio source → "OBS-Mix"
# 4. Verify with probe:
ffmpeg -f avfoundation -i ":OBS-Mix" -t 1 -f null -
```

### Control-surface-driven automation

```bash
# A Stream Deck sends MIDI; MIDI drives multiple targets simultaneously
uv run .claude/skills/media-midi/scripts/midictl.py monitor --json | \
  while IFS= read -r msg; do
    NOTE=$(echo "$msg" | jq -r .note)
    TYPE=$(echo "$msg" | jq -r .type)

    if [[ "$TYPE" == "noteon" ]]; then
      case "$NOTE" in
        36) # Scene switch
          uv run .claude/skills/obs-websocket/scripts/wsctl.py scene-switch --scene Main ;;
        37) # DMX lighting
          uv run .claude/skills/media-dmx/scripts/dmxctl.py send \
            --universe 1 --channel 1 --value 255 ;;
        38) # OSC to DAW
          uv run .claude/skills/media-osc/scripts/oscctl.py send \
            --host 127.0.0.1 --port 8000 --address /stop --args 1 ;;
      esac
    fi
  done
```

---

## Gotchas

### Routing / platform

- **BlackHole / Loopback appear as BOTH input AND output** on macOS. Route app → output side, then select input side in your DAW/capture.
- **PipeWire aliases `default` to your current Pulse sink.** When scripting, use the actual sink name (from `pw-cli ls Node`) for determinism.
- **JACK buffer size = latency (frames ÷ sample rate).** 128 at 48kHz = 2.67ms round-trip. Too low = xruns. Too high = sluggish. Start at 128, lower if glitch-free.
- **WASAPI loopback captures the render endpoint, not source.** To capture a specific app, use a virtual cable (VB-Cable / VoiceMeeter) between app and render device.
- **macOS AUHAL aggregate devices clock to the first device in the list.** Drift between devices will appear as phase issues. Make sure first device is your clock master (typically the audio interface).
- **Windows MME vs WASAPI**: MME is legacy, shared mode with higher latency. WASAPI exclusive mode = professional latency, but bypasses system mixer.

### MIDI / OSC

- **MIDI 1.0 messages are 3 bytes; MIDI 2.0 UMP messages are 4-16 bytes**. Wrong protocol = message ignored silently.
- **MIDI channels are 0-15 on the wire, 1-16 in UIs.** Off-by-one is the #1 MIDI bug.
- **MIDI running status** compresses repeated message types. Old hardware uses it; modern mostly doesn't. Parse both.
- **OSC bundle messages contain timed sub-messages.** Parse `{"type":"bundle","elements":[...]}` branches.
- **OSC address pattern matching** supports wildcards (`/track/*/volume`). Server-side wildcards can fire multiple handlers.
- **OSC over TCP is slot (1.1) vs UDP is stateless (1.0)**. Pick one per endpoint — mixing breaks framing.

### DSP

- **`loudnorm` is NOT a limiter.** It normalizes. If peaks exceed true-peak target, it applies downward gain but doesn't shave individual transients. Add explicit `alimiter` for hard-limiting.
- **`aresample` high `filter_size` = better quality but slower.** `filter_size=512` is audiophile; `128` is streaming default.
- **`atempo` chain limit: 0.5-2.0 per instance.** Chain for extremes: `atempo=0.5,atempo=0.5` = 0.25x.
- **`asetrate` changes pitch AND tempo** (the "chipmunk" effect). Use `atempo` + `asetrate` combined for pitch-preserving speed.
- **`aecho` delays in milliseconds, `adelay` in same unit per-channel** — the apply order matters.
- **`sidechaincompress`** needs key input FIRST, signal SECOND in the filter.

### AI audio

- **DeepFilterNet expects 48kHz mono or 16kHz mono** — resample before feeding.
- **RNNoise is hardcoded 48kHz mono 16-bit.** Anything else fails silently.
- **Demucs expects 44.1/48kHz stereo.** Mono input → degraded stems.
- **Whisper wants 16kHz mono for best quality.** It resamples internally but explicit is better.
- **Voice cloning needs CLEAN reference**. Run DeepFilterNet on the reference before cloning.
- **Kokoro TTS output is 24kHz.** Resample to 48kHz before mixing with other audio.

### Loudness

- **`loudnorm -target -14` alone is single-pass** with guardrails; accuracy ±1 LUFS. For compliance certification, use `media-ffmpeg-normalize`'s two-pass mode.
- **"True peak" (`TP`) measures inter-sample peaks** (oversampled 4x). Standard peak (`linear`) misses peaks between samples.
- **Loudness units**: LUFS = Loudness Units relative to Full Scale (equivalent to LKFS). LU = relative (no reference). LRA = loudness range.

---

## Example — "Live mix with DAW, MIDI control, and AI stem iso"

```bash
#!/usr/bin/env bash
set -e

# Start JACK server at low latency
jackd -d coreaudio -r 48000 -p 128 &
JACK_PID=$!
sleep 2

# Connect mic → DAW + monitor
uv run .claude/skills/audio-jack/scripts/jackctl.py connect \
  --from "system:capture_1" --to "ardour:Mic In/in 1"
uv run .claude/skills/audio-jack/scripts/jackctl.py connect \
  --from "ardour:master/out_1" --to "system:playback_1"
uv run .claude/skills/audio-jack/scripts/jackctl.py connect \
  --from "ardour:master/out_2" --to "system:playback_2"

# MIDI control surface → DAW transport via OSC
uv run .claude/skills/media-midi/scripts/midictl.py monitor --json | \
  while read msg; do
    NOTE=$(echo "$msg" | jq -r .note)
    case "$NOTE" in
      36) uv run .claude/skills/media-osc/scripts/oscctl.py send \
          --host 127.0.0.1 --port 3819 --address /transport/play --args 1 ;;
      37) uv run .claude/skills/media-osc/scripts/oscctl.py send \
          --host 127.0.0.1 --port 3819 --address /transport/stop --args 1 ;;
      38) uv run .claude/skills/media-osc/scripts/oscctl.py send \
          --host 127.0.0.1 --port 3819 --address /transport/record --args 1 ;;
    esac
  done &
MIDI_BRIDGE_PID=$!

trap "kill $MIDI_BRIDGE_PID $JACK_PID" EXIT

# After session: iso vocals from recording
echo "Press Ctrl+C when session complete..."
wait

# Post-session AI stem
uv run .claude/skills/media-demucs/scripts/demucs.py separate \
  --input session.wav --output-dir stems/ --model htdemucs

# Clean the vocal stem
uv run .claude/skills/media-denoise-ai/scripts/denoiseai.py deepfilter \
  --input stems/htdemucs/session/vocals.wav \
  --output vocals-clean.wav
```

---

## Further reading

- [`live-production.md`](live-production.md) — OBS-driven live audio routing
- [`podcast-pipeline.md`](podcast-pipeline.md) — podcast-specific audio polish
- [`ai-generation.md`](ai-generation.md) — TTS + music generation workflows
- [`ai-enhancement.md`](ai-enhancement.md) — AI denoise + Demucs details
