---
name: obs-websocket
description: >
  Remote-control a running OBS Studio instance via obs-websocket (WebSocket API, default port 4455): authenticate with SHA-256 challenge+salt, Identify handshake, start/stop streaming and recording, switch scenes, toggle sources and filters, set audio mixer levels, trigger replay buffer + virtual camera, subscribe to live events, send request batches. Use when the user asks to control OBS from a script, switch OBS scenes remotely, start or stop recording programmatically, automate a stream, send an obs-websocket request, subscribe to CurrentProgramSceneChanged events, connect to ws://host:4455, or build a browser/CLI OBS remote.
argument-hint: "[request]"
---

# obs-websocket

**Context:** $ARGUMENTS

Remote-control a running OBS Studio instance via the bundled `obs-websocket` plugin (WebSocket RPC, protocol v5, default URL `ws://localhost:4455`). Scope: the WIRE PROTOCOL — auth handshake, Requests, Events, RequestBatch. For C++ plugins see `obs-plugins`; for Python/Lua inside OBS see `obs-scripting`; for installing/configuring OBS itself see `obs-config`.

## MANDATORY verification

Before you claim a Request, Event, or OpCode exists, confirm it against the live protocol docs:

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/skills/obs-docs/scripts/obsdocs.py \
  search --query "<RequestOrEvent>" --page obs-websocket-protocol --limit 3
```

Every name/field/status in this skill was verified against `obs-websocket-protocol` (5.x) at authoring time. Do NOT invent Request names — the server closes the connection with `UnknownRequestType (204)`.

## Quick start

- **Ping OBS (auth + GetVersion):** → Step 1 → Step 2 → Step 3
- **Switch scenes from a script:** → Step 2 → Step 3 (`SetCurrentProgramScene`)
- **Start/stop record or stream:** → Step 3 (`StartRecord` / `StopRecord` / `ToggleStream`)
- **Subscribe to live scene changes:** → Step 4 (`eventSubscriptions` = `Scenes`)
- **Fire N ops atomically:** → Step 5 (OpCode 8 RequestBatch)

## When to use

- Automate OBS from a CLI, bot, or web UI without writing a C++ plugin.
- Remote control OBS on another machine (producer → operator laptop over LAN).
- Drive scene switches from chat / MIDI / HTTP webhooks.
- Subscribe to `CurrentProgramSceneChanged`, `RecordStateChanged`, etc., from a monitor dashboard.

If the user needs code that runs INSIDE OBS's own Python/Lua VM, use `obs-scripting` instead. If they need a native source / output / encoder, use `obs-plugins`.

## Step 1 — Enable obs-websocket in OBS

OBS 28+ ships obs-websocket v5 BUNDLED. Older OBS needs the plugin installed manually from the obs-websocket GitHub repo.

1. OBS menu: **Tools → obs-websocket Settings**.
2. Tick **Enable WebSocket server**.
3. Default port: `4455`.
4. Password is enabled by default in newer releases — either click **Show Connect Info** to copy the current password, or disable auth (not recommended) or set your own.
5. Click **OK**.

Test that the port is open:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py check
```

## Step 2 — Connect and authenticate

v5 handshake (NOT v4.x — protocol completely changed, v4 is EOL).

```
Client ─── HTTP Upgrade ──▶ Server
Client ◀── OpCode 0 Hello ─ Server           (authentication.{challenge,salt} if password set)
Client ── OpCode 1 Identify ▶ Server         (rpcVersion=1, authentication=<hash>, eventSubscriptions=<mask>)
Client ◀── OpCode 2 Identified ─ Server      (connection ready)
```

Auth algorithm (exact — verified against protocol spec):

```
secret  = base64( sha256( password + salt ) )
auth    = base64( sha256( secret + challenge ) )
```

Both base64 calls use STANDARD base64 (not URL-safe). SHA-256 is invoked twice. If `authentication` is absent from `Hello`, NO password is set — omit the field in `Identify`.

Minimal Python (websocket-client):

```python
import json, base64, hashlib, uuid, websocket

ws = websocket.create_connection("ws://localhost:4455")
hello = json.loads(ws.recv())
d = hello["d"]
auth_field = {}
if "authentication" in d:
    c, s = d["authentication"]["challenge"], d["authentication"]["salt"]
    secret = base64.b64encode(hashlib.sha256(("pw" + s).encode()).digest()).decode()
    auth_field["authentication"] = base64.b64encode(hashlib.sha256((secret + c).encode()).digest()).decode()
ws.send(json.dumps({"op": 1, "d": {"rpcVersion": 1, **auth_field, "eventSubscriptions": 4}}))
identified = json.loads(ws.recv())
assert identified["op"] == 2
```

## Step 3 — Send a Request (OpCode 6)

```python
req = {
  "op": 6,
  "d": {
    "requestType": "SetCurrentProgramScene",
    "requestId": str(uuid.uuid4()),
    "requestData": {"sceneName": "Starting Soon"}
  }
}
ws.send(json.dumps(req))
resp = json.loads(ws.recv())   # op=7 RequestResponse
assert resp["d"]["requestStatus"]["result"] is True
```

`requestId` is client-generated and echoed verbatim in the response — use it to correlate async replies. If a Request has no fields, omit `requestData` entirely (or send `{}`).

Via the helper CLI (see `scripts/wsctl.py`). **The CLI is fully automatic** — URL and password are discovered from OBS's own `plugin_config/obs-websocket/config.json`. No `--url` / `--password` flags exist. Override via `OBS_WEBSOCKET_URL` / `OBS_WEBSOCKET_PASSWORD` env vars (e.g. remote host):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py ping
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py scene-switch --scene "Starting Soon"
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py record --action toggle
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py request --type GetStats
```

## Step 4 — Subscribe to Events (OpCode 5)

Events arrive unsolicited once you're Identified and subscribed. Pass `eventSubscriptions` as a bitmask in the `Identify` message (or later in `Reidentify`, OpCode 3).

Categories (verified):

| Bit | Name | Value |
|-----|------|-------|
| 0 | General | 1 |
| 1 | Config | 2 |
| 2 | Scenes | 4 |
| 3 | Inputs | 8 |
| 4 | Transitions | 16 |
| 5 | Filters | 32 |
| 6 | Outputs | 64 |
| 7 | SceneItems | 128 |
| 8 | MediaInputs | 256 |
| 9 | Vendors | 512 |
| 10 | Ui | 1024 |
| 11 | Canvases | 2048 |
| — | **All** | **4095** (OR of the above) |
| 16 | InputVolumeMeters (high-volume) | 65536 |
| 17 | InputActiveStateChanged (high-volume) | 131072 |
| 18 | InputShowStateChanged (high-volume) | 262144 |
| 19 | SceneItemTransformChanged (high-volume) | 524288 |

HIGH-VOLUME events (bits 16–19) are NOT in `All`. Opt in explicitly by ORing them in.

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py events --subscribe scenes,outputs
```

Event frame shape:

```json
{"op": 5, "d": {"eventType": "CurrentProgramSceneChanged",
                 "eventIntent": 4,
                 "eventData": {"sceneName": "Main", "sceneUuid": "..."}}}
```

## Step 5 — RequestBatch (OpCode 8)

Atomic or parallel fan-out of multiple Requests in one message.

```json
{"op": 8, "d": {
  "requestId": "batch-1",
  "haltOnFailure": false,
  "executionType": 0,
  "requests": [
    {"requestType": "SetCurrentProgramScene", "requestData": {"sceneName": "BRB"}},
    {"requestType": "SetInputMute",           "requestData": {"inputName": "Mic", "inputMuted": true}}
  ]
}}
```

`executionType`: `-1` None, `0` SerialRealtime (default, ordered, gap for realtime tick), `1` SerialFrame (ordered, lockstepped to video frame), `2` Parallel (faster, NO ordering guarantee).

Helper:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py batch --requests-file scene-reset.json
```

## Gotchas

- **v5 ≠ v4.** The v4.x protocol is EOL and incompatible. Always target v5. Libraries like `obs-websocket-py` must be v1.0+.
- **Base64 flavor.** Auth strings use STANDARD base64 (with `+/=`), not URL-safe.
- **Double SHA-256.** Inner hash = `password + salt`, outer hash = `base64(inner) + challenge`.
- **`All` mask is 4095, not 2047.** The enum includes `Vendors` (512) and `Canvases` (2048) in addition to the bit-0..bit-10 categories. High-volume bits (16–19) are deliberately excluded — add them manually if you need volume meters, active/show state, or scene-item transform change events.
- **HighVolume events flood the socket.** `InputVolumeMeters` fires every 50 ms. Only subscribe if you'll consume.
- **`requestId` is yours.** Client-generated, returned verbatim. Use it for request/response correlation in async clients.
- **Request fields optional by default.** Many Requests (e.g. `GetVersion`, `GetStats`, `GetSceneList`) take no `requestData` — omit the key entirely.
- **`sceneName` vs `sceneUuid`.** Most scene Requests accept EITHER `sceneName` (string) or `sceneUuid`. Prefer name unless scenes can be renamed at runtime.
- **SceneItemID is an integer** scoped to a scene, not a GUID. Look it up with `GetSceneItemId` (query by source name) or iterate `GetSceneItemList`.
- **Input-kind strings are platform-specific.** `coreaudio_input_capture` (macOS) vs `wasapi_input_capture` (Windows) vs `pulse_input_capture` (Linux). Always call `GetInputKindList` before creating an input programmatically.
- **`SetInputVolume`** accepts `inputVolumeMul` (0–20) OR `inputVolumeDb` (-100–26). Pass only one.
- **Cannot change encoder settings while an output is running.** `OutputRunning (500)` is the error code; stop the output first.
- **`CallVendorRequest`** is how plugins like StreamFX expose custom RPC — it's NOT an error, it's a passthrough channel.
- **Close codes 4xxx are non-negotiable.** `4009 AuthenticationFailed` means wrong password; `4010 UnsupportedRpcVersion` means you advertised an `rpcVersion` the server doesn't speak; `4007 NotIdentified` means you sent a Request before Identified.
- **Parallel RequestBatch drops ordering.** `executionType=2` is fastest but do not rely on sequencing between requests. Use `0` if order matters.
- **`wsctl.py` has NO `--url` / `--password` flags.** URL (from `server_port`) and password (from `server_password` when `auth_required=true`) are read straight from the local OBS's `plugin_config/obs-websocket/config.json`. To point at a remote or non-default instance, set `OBS_WEBSOCKET_URL` / `OBS_WEBSOCKET_PASSWORD` in the environment. Config paths: `~/Library/Application Support/obs-studio/...` on macOS, `%APPDATA%/obs-studio/...` on Windows, `~/.config/obs-studio/...` on Linux.

## Examples

### Example 1: Hotkey-driven scene switcher

```bash
# bind MIDI note 36 to switch to scene "Wide"
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py scene-switch --scene "Wide"
```

### Example 2: Toggle mute from voice-activity detector

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py mute --input "Mic/Aux" --action toggle
```

### Example 3: Save a replay buffer highlight

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py replay-buffer --action save
```

### Example 4: Stream live events to jq

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py events --subscribe scenes,outputs \
    | jq 'select(.d.eventType=="CurrentProgramSceneChanged")'
```

### Example 5: Escape hatch — any Request

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py request \
    --type GetSceneItemTransform \
    --data '{"sceneName":"Main","sceneItemId":42}'
```

### Example 6: Remote host (override via env)

```bash
OBS_WEBSOCKET_URL=ws://10.0.0.42:4455 \
OBS_WEBSOCKET_PASSWORD=hunter2 \
    uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py ping
```

## Reference docs

- [`references/protocol.md`](references/protocol.md) — OpCodes, RequestStatus (100–703), close codes (4000–4012), EventSubscriptions bitmask, RequestBatch executionType, auth pseudocode, commonly-used Requests/Events grouped by category, client snippets for Python/Node/Go/browser, handshake diagram, keepalive strategy.

## Troubleshooting

### Error: `connection refused` on port 4455

Cause: obs-websocket server disabled, OBS not running, or bound to a different interface.
Solution: Tools → obs-websocket Settings → Enable WebSocket server. Verify port with `uv run ${CLAUDE_SKILL_DIR}/scripts/wsctl.py check`.

### Close code 4009 AuthenticationFailed

Cause: Discovered password doesn't match the running server — usually because the user rotated the password from Tools → obs-websocket Settings but the file on disk hasn't been reloaded.
Solution: The helper reads `plugin_config/obs-websocket/config.json` at call time; if OBS hasn't flushed the config yet, restart OBS or override once with `OBS_WEBSOCKET_PASSWORD=...`. For custom clients: verify STANDARD base64 and hash TWICE (inner: `pw+salt`, outer: `b64secret+challenge`).

### Close code 4010 UnsupportedRpcVersion

Cause: You advertised `rpcVersion` the server doesn't speak — usually a v4 client hitting a v5 server.
Solution: Use `rpcVersion: 1` and a v5-compatible client library.

### Close code 4007 NotIdentified

Cause: Sent a Request (OpCode 6) before receiving Identified (OpCode 2).
Solution: Wait for the OpCode 2 message. Never pipeline Requests ahead of identification.

### RequestStatus 204 UnknownRequestType

Cause: Typo or v4-era name. Common trap: `SetCurrentScene` (v4) vs `SetCurrentProgramScene` (v5).
Solution: Verify via the `obs-docs` search command before sending.

### RequestStatus 600 ResourceNotFound

Cause: Bad `sceneName`, `inputName`, or `sceneItemId`.
Solution: Enumerate with `GetSceneList`, `GetInputList`, or `GetSceneItemList` first.

### RequestStatus 500 OutputRunning / 501 OutputNotRunning

Cause: Tried to mutate encoder/output state while output was in the wrong state.
Solution: Stop the output (`StopStream`/`StopRecord`), reconfigure, then restart.

### Event flood / CPU spike

Cause: Subscribed to high-volume events (`InputVolumeMeters` fires every 50 ms).
Solution: Re-Identify (OpCode 3) with a narrower `eventSubscriptions` mask.
