# macOS virtual audio drivers

Comparison + install notes for the three drivers that actually work on current
macOS (Apple Silicon, macOS 12+). Everything on this page assumes DriverKit /
AudioDriverKit — the legacy kext path (Soundflower, old Loopback) is gone.

---

## Comparison

| Feature | BlackHole | Loopback | Background Music |
|---|---|---|---|
| License | GPL-3.0 open source | Commercial ($119 / single) | GPL-3.0 open source |
| Channels | 2, 16, 64 (pick one) | Up to 64 per virtual device | 2 |
| Multiple simultaneous devices | No (one per variant) | Yes — build as many named cables as you want | No |
| Per-app routing | No — system-wide cable | Yes — GUI patchbay for per-app routing | Yes — per-app volume / mute |
| Architecture support | Intel + Apple Silicon | Intel + Apple Silicon | Intel + Apple Silicon |
| Install | `brew install --cask blackhole-2ch` (or `-16ch`, `-64ch`) | Download from Rogue Amoeba | `brew install --cask background-music` |
| Best for | Screen-recording system audio into OBS/QuickTime | Pro multi-app routing, podcasting, streaming with complex patchbay | Per-app volume on a single machine |
| URL | <https://github.com/ExistentialAudio/BlackHole> | <https://rogueamoeba.com/loopback/> | <https://github.com/kyleneideck/BackgroundMusic> |

---

## BlackHole

Simple, free, reliable. Ideal as a "virtual cable" used with a Multi-Output
Device so you can monitor AND route simultaneously.

Install:

```bash
brew install --cask blackhole-2ch           # 2-channel
brew install --cask blackhole-16ch          # 16-channel
brew install --cask blackhole-64ch          # 64-channel (heaviest)
```

Uninstall:

```bash
brew uninstall --cask blackhole-2ch
# Driver remains until you delete:
sudo rm -rf /Library/Audio/Plug-Ins/HAL/BlackHole*.driver
sudo pkill coreaudiod
```

Typical pattern — route system audio to OBS:

1. Install `blackhole-2ch`.
2. Audio MIDI Setup → + → Create Multi-Output Device →
   check "BlackHole 2ch" and your speakers/headphones.
3. System Settings → Sound → Output → pick the Multi-Output Device.
4. In OBS → Settings → Audio → Mic/Auxiliary Audio → BlackHole 2ch.
5. Audio now plays to your ears AND feeds OBS.

Known issue: The Multi-Output Device doesn't carry system-alert audio; those
still need a real physical output endpoint.

---

## Loopback (Rogue Amoeba)

Commercial, GUI-first. Build named virtual devices with arbitrary channel
counts and per-application routing rules:

- Drag apps in (e.g. Zoom, Spotify, Chrome).
- Drag "Pass-Thru" outputs to real devices.
- Add "Monitor" channels to hear what Loopback is doing without it polluting
  your recording.
- Save as named device visible system-wide.

CLI control is limited; primarily a GUI tool. Use when your routing exceeds
what a single Multi-Output + BlackHole can express (ducking, per-app EQ,
transcript-friendly per-speaker tracks).

---

## Background Music

Narrow, free. Installs as a small menu-bar app + virtual driver. Main value:

- Per-app volume sliders in the menu bar (macOS itself has none).
- Per-app mute.
- Auto-pause music when a phone/VoIP call starts.

Routing is deliberately simple — not a patchbay. Use alongside BlackHole when
the user wants both system-level routing and per-app volume.

---

## Creating an Aggregate Device programmatically (Swift)

For the path the CLI prints about, here's the Swift snippet that uses the
private-but-documented `AudioHardwareCreateAggregateDevice`:

```swift
import CoreAudio
import Foundation

let description: [String: Any] = [
    kAudioAggregateDeviceNameKey as String: "Studio Aggregate",
    kAudioAggregateDeviceUIDKey as String: "com.example.studio.aggregate",
    kAudioAggregateDeviceIsPrivateKey as String: 0,  // 1 = per-process only
    kAudioAggregateDeviceIsStackedKey as String: 0,  // 1 = Multi-Output, 0 = Aggregate
    kAudioAggregateDeviceSubDeviceListKey as String: [
        [
            kAudioSubDeviceUIDKey as String: "BlackHole2ch_UID",
            kAudioSubDeviceDriftCompensationKey as String: 1,
        ],
        [
            kAudioSubDeviceUIDKey as String:
                "AppleHDAEngineOutputDP:11DD,AA00,1000C0CC,0,1,0:0",
            kAudioSubDeviceDriftCompensationKey as String: 0,  // master
        ],
    ],
    kAudioAggregateDeviceMasterSubDeviceKey as String:
        "AppleHDAEngineOutputDP:11DD,AA00,1000C0CC,0,1,0:0",
]

var aggregateDevice: AudioDeviceID = 0
let status = AudioHardwareCreateAggregateDevice(
    description as CFDictionary, &aggregateDevice)
print("status = \(status), deviceID = \(aggregateDevice)")
```

Build as a one-file Swift script:

```bash
swiftc create_aggregate.swift -o create_aggregate
./create_aggregate
```

To destroy:

```swift
AudioHardwareDestroyAggregateDevice(aggregateDevice)
```

Member UIDs come from `SwitchAudioSource -a -f json` or
`AudioObjectGetPropertyData(... kAudioDevicePropertyDeviceUID ...)`.

---

## HAL plug-in file layout

Each `*.driver` is a standard bundle:

```
BlackHole2ch.driver/
  Contents/
    Info.plist
    MacOS/BlackHole2ch
    Resources/
```

`Info.plist` lists bundle identifier + `IOKitPersonalities` (for kext-style
legacy) or `NSExtensionPointIdentifier = com.apple.audio.driver-extension`
(for DriverKit). Don't hand-edit — use the installer pkg.

After install / remove, `coreaudiod` must rescan:

```bash
sudo pkill coreaudiod   # restarts automatically
```

All CoreAudio-using processes will momentarily glitch; DAWs/meeting apps should
be quit first.
