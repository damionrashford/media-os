# PipeWire graph elements

The PipeWire graph is an in-memory typed-object system. Every CLI ultimately
manipulates these objects. This file lists the object types + property keys you
will encounter in `pw-cli list-objects` / `pw-dump`.

---

## Object types

| Type (pw-dump shows `PipeWire:Interface:<X>`) | What it is |
|---|---|
| `Core` | The daemon itself. Exactly one. Properties describe the running PipeWire version. |
| `Client` | Every process connected to the daemon (including `pw-cli` itself). |
| `Module` | A loaded `libpipewire-module-*.so`. Drives loopback / protocol / suspend-on-idle / etc. |
| `Factory` | Object factory exposed by a module (e.g. `adapter` factory creates nodes). |
| `Device` | A hardware device backed by ALSA / V4L2 / Bluez / etc. A device exposes 1+ nodes. |
| `Node` | A point in the graph that processes data. Audio sources, sinks, filters, apps. |
| `Port` | A channel-level I/O endpoint on a node. One port per audio channel (mono = 1, stereo = 2). |
| `Link` | A directed edge from an output port to an input port. Carries raw sample buffers. |
| `Session` | Session-manager concept (WirePlumber). Groups endpoints. |
| `Endpoint` | High-level routing target (set of nodes + policy). Used by session managers. |
| `EndpointStream` | Sub-stream of an endpoint. |
| `Metadata` | Shared key-value store. `default.audio.sink`, route state, etc. Object id 0 = default metadata. |

---

## Node properties (common keys)

Found in `info.props` of each Node object. Quote exactly:

| Key | Meaning |
|---|---|
| `node.name` | Stable ID-like name (e.g. `alsa_output.usb-Focusrite_Scarlett-00.iec958-stereo`). Use this in scripts. |
| `node.description` | Human label ("Scarlett Solo Analog Stereo"). Show to humans only. |
| `node.nick` | Short nickname. |
| `media.class` | e.g. `Audio/Sink`, `Audio/Source`, `Audio/Duplex`, `Stream/Output/Audio`, `Stream/Input/Audio`, `Video/Source`, `Midi/Sink`. |
| `media.role` | App-declared role (`Music`, `Movie`, `Game`, `Communication`). WirePlumber policy uses this. |
| `application.name` / `application.process.binary` | The producing app. |
| `audio.channels` / `audio.position` | Channel count + layout (`[ FL, FR ]`, `[ FL, FR, FC, LFE, RL, RR ]`, etc.). |
| `node.rate` / `clock.rate` | Allowed sample rates (fraction `1/48000`). |
| `clock.quantum-limit` | Max quantum this node can request. |
| `priority.driver` | Higher = more likely to be chosen as graph driver. |

## Port properties

| Key | Meaning |
|---|---|
| `port.direction` | `in` (input) or `out` (output). |
| `port.name` | e.g. `output_FL`, `playback_FR`, `input_0`. |
| `port.alias` | Alternative name. |
| `port.id` | Zero-indexed per-node port index. |
| `format.dsp` | e.g. `32 bit float mono audio`, `8 bit raw midi`. |
| `node.id` | ID of the owning Node. |

## Link properties

| Key | Meaning |
|---|---|
| `link.output-port` / `link.input-port` | Port IDs. |
| `link.output-node` / `link.input-node` | Node IDs. |

## Device properties

| Key | Meaning |
|---|---|
| `device.api` | `alsa`, `v4l2`, `bluez5`, etc. |
| `device.name` | Stable name. |
| `device.description` | Human label. |
| `device.nick` | Short name. |
| `device.profile.name` | Current ALSA/Bluetooth profile (e.g. `analog-stereo`, `a2dp-sink`, `pro-audio`). |

---

## Metadata keys (object id 0 unless noted)

Written with `pw-metadata 0 <key> <value> <type>`. Values that look like dicts
require `Spa:String:JSON`.

| Key | Value shape | Used by |
|---|---|---|
| `default.configured.audio.sink` | `{ "name": "<node.name>" }` | WirePlumber → sets persistent default sink |
| `default.configured.audio.source` | `{ "name": "<node.name>" }` | WirePlumber → default source |
| `default.audio.sink` | same | Runtime-effective default sink |
| `default.audio.source` | same | Runtime-effective default source |
| `target.node` (per-stream metadata) | node id | Pin a specific stream to a specific node |

Per-stream targeting uses the stream's subject id, not object 0.

---

## Node `media.class` quick matrix

- **`Audio/Sink`** — a device that plays audio. Ports are `playback_*`.
- **`Audio/Source`** — a device that captures audio. Ports are `capture_*`.
- **`Audio/Duplex`** — both (most pro-audio interfaces).
- **`Stream/Output/Audio`** — an app playing audio. Ports are `output_*`.
- **`Stream/Input/Audio`** — an app recording audio. Ports are `input_*`.
- **`Audio/Source/Virtual`** — loopback/null sources (from `pw-loopback` or null-sink modules).

So to route an app to a device:

```
Stream/Output/Audio : output_FL  →  Audio/Sink : playback_FL
```

Those are the two names you pass to `pw-link`.

---

## Useful `pw-cli` one-liners

- `pw-cli info 0` — Core info (version, API version).
- `pw-cli info <id>` — Full object info for an id.
- `pw-cli ls Node` — All nodes, one line each.
- `pw-cli ls Node -r` — Same + all properties.
- `pw-cli dump 0` — Core object as JSON.
- `pw-cli destroy <id>` — Force-destroy an object (e.g. rogue loopback).

And WirePlumber:

- `wpctl status` — Colored, human-readable live graph.
- `wpctl set-default <id>` — Set default sink/source for the running session.
- `wpctl set-volume <id> <0-1.0>` — Set volume.
