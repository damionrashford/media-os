# obs-websocket v5 protocol reference

All tables and enum values were verified against the official protocol document
(`https://raw.githubusercontent.com/obsproject/obs-websocket/master/docs/generated/protocol.md`)
via `obs-docs` at authoring time. If a field name looks unfamiliar, re-verify:

```bash
# If you have the obs-docs skill installed separately, use its search command \
    search --query "<RequestOrEvent>" --page obs-websocket-protocol --limit 3
```

## Frame shape

Every message has a top-level `op` (integer) and `d` (object).

```json
{"op": <int>, "d": { ... }}
```

Default URL: `ws://localhost:4455`. TLS is `wss://`. Subprotocols:
`obswebsocket.json` (default, text frames) or `obswebsocket.msgpack` (binary).

## OpCodes

| OpCode | Name                  | Direction       | Purpose                                                              |
|:------:|-----------------------|-----------------|----------------------------------------------------------------------|
| 0      | Hello                 | Server → Client | First message on connect. Carries `rpcVersion`, `authentication`?.   |
| 1      | Identify              | Client → Server | Response to Hello. Carries `rpcVersion`, `authentication`, mask.     |
| 2      | Identified            | Server → Client | Server accepted Identify. Connection is live.                        |
| 3      | Reidentify            | Client → Server | Change `eventSubscriptions` mid-session without reconnecting.        |
| 5      | Event                 | Server → Client | Unsolicited event broadcast.                                         |
| 6      | Request               | Client → Server | Single RPC call (see Requests).                                      |
| 7      | RequestResponse       | Server → Client | Reply to a Request, correlated by `requestId`.                       |
| 8      | RequestBatch          | Client → Server | Multiple Requests in one message (serial or parallel).               |
| 9      | RequestBatchResponse  | Server → Client | Replies for a RequestBatch.                                          |

Note: **OpCode 4 does not exist** in the spec (reserved / skipped).

## Handshake sequence

```
Client                                              Server
  │                HTTP Upgrade                       │
  │──────────────────────────────────────────────────▶│
  │                 101 Switching                     │
  │◀──────────────────────────────────────────────────│
  │                                                   │
  │◀────────── op:0 Hello (challenge?, salt?) ────────│
  │                                                   │
  │  if Hello.d.authentication is present:            │
  │    secret = base64(sha256(password + salt))       │
  │    auth   = base64(sha256(secret + challenge))    │
  │                                                   │
  │──── op:1 Identify (rpcVersion, auth, mask) ──────▶│
  │                                                   │
  │◀─────────── op:2 Identified (negotiatedRpcVersion)│
  │                                                   │
  │  At any time:                                     │
  │──── op:6 Request ────────────────────────────────▶│
  │◀──── op:7 RequestResponse ────────────────────────│
  │◀──── op:5 Event ──────────────────────────────────│
  │──── op:3 Reidentify (new mask) ──────────────────▶│
  │◀──── op:2 Identified (again) ─────────────────────│
  │                                                   │
  │  On bad input:                                    │
  │◀───── WebSocket close frame with code 4xxx ───────│
```

## Authentication algorithm (pseudocode)

```
if hello.authentication is None:
    auth_field = None                      # no password required
else:
    salt       = hello.authentication.salt
    challenge  = hello.authentication.challenge
    secret     = base64_std(sha256(password_utf8 + salt_utf8))     # first hash
    auth_field = base64_std(sha256(secret     + challenge_utf8))   # second hash
```

Base64 gotchas:
- STANDARD base64 (`+` and `/`), NOT URL-safe (`-` and `_`).
- Include `=` padding as needed.
- Inputs to `sha256()` are treated as raw UTF-8 byte concatenations, not Base64-decoded first.

## RequestStatus codes

All verified. `result: true` iff `code == 100` (Success). Any other code = failure.

| Code | Name                                  | Meaning                                                   |
|-----:|---------------------------------------|-----------------------------------------------------------|
|   0  | Unknown                               | Unknown status, should never occur in the wild.           |
|  10  | NoError                               | No error, used internally (not usually seen).             |
| 100  | Success                               | Request succeeded.                                        |
| 203  | MissingRequestType                    | `requestType` missing from Request.                       |
| 204  | UnknownRequestType                    | Server doesn't know the `requestType`.                    |
| 205  | GenericError                          | Unspecified error; `comment` holds detail.                |
| 206  | UnsupportedRequestBatchExecutionType  | `executionType` invalid for this server.                  |
| 207  | NotReady                              | Server not yet ready to serve this request.               |
| 300  | MissingRequestField                   | A required field is absent from `requestData`.            |
| 301  | MissingRequestData                    | Request needed `requestData` but none was sent.           |
| 400  | InvalidRequestField                   | Field value invalid (wrong semantic).                     |
| 401  | InvalidRequestFieldType               | Field type wrong (string where number expected, etc).     |
| 402  | RequestFieldOutOfRange                | Numeric field outside allowed range.                      |
| 403  | RequestFieldEmpty                     | String field empty but non-empty required.                |
| 404  | TooManyRequestFields                  | Mutually exclusive fields both set.                       |
| 500  | OutputRunning                         | Can't do that while the output is running.                |
| 501  | OutputNotRunning                      | Can't do that while the output is not running.            |
| 502  | OutputPaused                          | Can't do that while the output is paused.                 |
| 503  | OutputNotPaused                       | Can't do that while the output is not paused.             |
| 504  | OutputDisabled                        | Output is administratively disabled.                      |
| 505  | StudioModeActive                      | Can't do that while Studio Mode is active.                |
| 506  | StudioModeNotActive                   | Can't do that while Studio Mode is inactive.              |
| 600  | ResourceNotFound                      | Named scene/input/filter/item not found.                  |
| 601  | ResourceAlreadyExists                 | Would create a duplicate resource.                        |
| 602  | InvalidResourceType                   | Resource is of the wrong type for this op.                |
| 603  | NotEnoughResources                    | Resource quota exhausted.                                 |
| 604  | InvalidResourceState                  | Resource is in a state incompatible with this op.         |
| 605  | InvalidInputKind                      | Unknown input kind (platform mismatch common).            |
| 606  | ResourceNotConfigurable               | Cannot edit this resource's settings.                     |
| 607  | InvalidFilterKind                     | Unknown filter kind.                                      |
| 700  | ResourceCreationFailed                | Backend refused to create the resource.                   |
| 701  | ResourceActionFailed                  | Backend refused the action.                               |
| 702  | RequestProcessingFailed               | Backend crashed while processing.                         |
| 703  | CannotAct                             | Backend refuses to act (misc. logical reject).            |

## WebSocket close codes

| Code | Name                    | Meaning                                                   |
|-----:|-------------------------|-----------------------------------------------------------|
|    0 | DontClose               | Sentinel. Do not actually close.                          |
| 4000 | UnknownReason           | Catch-all.                                                |
| 4002 | MessageDecodeError      | JSON/MsgPack parse failure.                               |
| 4003 | MissingDataField        | Required top-level field missing.                         |
| 4004 | InvalidDataFieldType    | Wrong type for a top-level field.                         |
| 4005 | InvalidDataFieldValue   | Top-level field value invalid.                            |
| 4006 | UnknownOpCode           | `op` is not recognized.                                   |
| 4007 | NotIdentified           | Sent non-Identify message before Identified.              |
| 4008 | AlreadyIdentified       | Sent a second Identify on a live session.                 |
| 4009 | AuthenticationFailed    | Bad password or malformed auth string.                    |
| 4010 | UnsupportedRpcVersion   | Advertised `rpcVersion` not supported.                    |
| 4011 | SessionInvalidated      | Server invalidated your session.                          |
| 4012 | UnsupportedFeature      | Used a feature the server refuses.                        |

## EventSubscription bitmask

Default `Identify.eventSubscriptions` = `All` (4095). You must OR in HIGH-VOLUME
bits explicitly.

| Bit  | Name                      | Value    | High-volume? |
|-----:|---------------------------|---------:|:------------:|
| —    | None                      | 0        |              |
| 0    | General                   | 1        |              |
| 1    | Config                    | 2        |              |
| 2    | Scenes                    | 4        |              |
| 3    | Inputs                    | 8        |              |
| 4    | Transitions               | 16       |              |
| 5    | Filters                   | 32       |              |
| 6    | Outputs                   | 64       |              |
| 7    | SceneItems                | 128      |              |
| 8    | MediaInputs               | 256      |              |
| 9    | Vendors                   | 512      |              |
| 10   | Ui                        | 1024     |              |
| 11   | Canvases                  | 2048     |              |
| —    | **All**                   | **4095** |              |
| 16   | InputVolumeMeters         | 65536    | yes (~50 ms) |
| 17   | InputActiveStateChanged   | 131072   | yes          |
| 18   | InputShowStateChanged     | 262144   | yes          |
| 19   | SceneItemTransformChanged | 524288   | yes          |

All-inclusive mask (everything, including high-volume):
`4095 | 65536 | 131072 | 262144 | 524288 = 987135`.

## RequestBatch.executionType

| Value | Name            | Behavior                                                             |
|:-----:|-----------------|----------------------------------------------------------------------|
|  -1   | None            | Do not execute (server may reject). Rarely used.                     |
|   0   | SerialRealtime  | Default. Execute in order; a tick yields to realtime graphics loop.  |
|   1   | SerialFrame     | Execute in order, stepping one request per rendered video frame.     |
|   2   | Parallel        | Dispatch all requests simultaneously — NO ordering guarantee.        |

## Request catalog (common, grouped)

Every name below was verified against the live spec. For exhaustive schemas,
use `obsdocs.py fetch --page obs-websocket-protocol`.

### General

- `GetVersion` → `obsVersion`, `obsWebSocketVersion`, `rpcVersion`, `availableRequests[]`, `supportedImageFormats[]`, `platform`, `platformDescription`.
- `GetStats` → `cpuUsage`, `memoryUsage`, `availableDiskSpace`, `activeFps`, `averageFrameRenderTime`, `renderSkippedFrames`, `renderTotalFrames`, `outputSkippedFrames`, `outputTotalFrames`, `webSocketSessionIncomingMessages`, `webSocketSessionOutgoingMessages`.
- `BroadcastCustomEvent({eventData})` → broadcasts a `CustomEvent`.
- `CallVendorRequest({vendorName, requestType, requestData?})` → passthrough to plugins (StreamFX etc.).
- `Sleep({sleepMillis | sleepFrames})` — VALID ONLY INSIDE A RequestBatch.

### Config

- `GetPersistentData({realm, slotName})`, `SetPersistentData({realm, slotName, slotValue})` — `realm` ∈ `OBS_WEBSOCKET_DATA_REALM_{GLOBAL,PROFILE}`.
- `GetSceneCollectionList`, `SetCurrentSceneCollection({sceneCollectionName})`, `CreateSceneCollection({sceneCollectionName})`.
- `GetProfileList`, `SetCurrentProfile`, `CreateProfile`, `RemoveProfile`.
- `GetProfileParameter({parameterCategory, parameterName})`, `SetProfileParameter({parameterCategory, parameterName, parameterValue})`.
- `GetVideoSettings`, `SetVideoSettings({baseWidth, baseHeight, outputWidth, outputHeight, fpsNumerator, fpsDenominator})`.
- `GetStreamServiceSettings`, `SetStreamServiceSettings({streamServiceType, streamServiceSettings})`.
- `GetRecordDirectory`, `SetRecordDirectory({recordDirectory})`.

### Scenes

- `GetSceneList` → `currentProgramSceneName`, `currentPreviewSceneName`, `scenes[]`.
- `GetGroupList`, `GetCurrentProgramScene`, `GetCurrentPreviewScene`.
- `SetCurrentProgramScene({sceneName | sceneUuid})`.
- `SetCurrentPreviewScene({sceneName | sceneUuid})` (Studio Mode).
- `CreateScene({sceneName})`, `RemoveScene({sceneName | sceneUuid})`, `SetSceneName`.
- `GetSceneSceneTransitionOverride`, `SetSceneSceneTransitionOverride`.

### Inputs

- `GetInputList({inputKind?})`, `GetInputKindList`, `GetSpecialInputs`.
- `CreateInput({sceneName|sceneUuid, inputName, inputKind, inputSettings?, sceneItemEnabled?})`, `RemoveInput`.
- `SetInputName`, `GetInputSettings`, `SetInputSettings`.
- `GetInputDefaultSettings`, `GetInputMute`, `SetInputMute({inputName|inputUuid, inputMuted})`, `ToggleInputMute`.
- `GetInputVolume`, `SetInputVolume({inputName|inputUuid, inputVolumeMul? | inputVolumeDb?})`.
- `GetInputAudioBalance`, `SetInputAudioBalance`.
- `GetInputAudioSyncOffset`, `SetInputAudioSyncOffset`.
- `GetInputAudioMonitorType`, `SetInputAudioMonitorType` — types: `OBS_MONITORING_TYPE_{NONE,MONITOR_ONLY,MONITOR_AND_OUTPUT}`.
- `GetInputAudioTracks`, `SetInputAudioTracks`.
- `GetInputDeinterlaceMode`, `SetInputDeinterlaceMode`, `GetInputDeinterlaceFieldOrder`, `SetInputDeinterlaceFieldOrder`.
- `GetInputPropertiesListPropertyItems({inputName, propertyName})`, `PressInputPropertiesButton`.

### Filters

- `GetSourceFilterKindList`, `GetSourceFilterList({sourceName|sourceUuid})`.
- `GetSourceFilterDefaultSettings({filterKind})`.
- `CreateSourceFilter({sourceName, filterName, filterKind, filterSettings?})`, `RemoveSourceFilter`.
- `SetSourceFilterName`, `SetSourceFilterIndex`, `SetSourceFilterSettings`, `SetSourceFilterEnabled`.
- `GetSourceFilter({sourceName, filterName})`.

### Scene Items

- `GetSceneItemList({sceneName|sceneUuid})`, `GetGroupSceneItemList`.
- `GetSceneItemId({sceneName, sourceName, searchOffset?})` → `sceneItemId`.
- `GetSceneItemSource({sceneName, sceneItemId})`.
- `CreateSceneItem({sceneName, sourceName|sourceUuid, sceneItemEnabled?})`, `RemoveSceneItem`.
- `DuplicateSceneItem({sceneName, sceneItemId, destinationSceneName?})`.
- `GetSceneItemTransform`, `SetSceneItemTransform({sceneName, sceneItemId, sceneItemTransform})`.
- `GetSceneItemEnabled`, `SetSceneItemEnabled({sceneName, sceneItemId, sceneItemEnabled})`.
- `GetSceneItemLocked`, `SetSceneItemLocked`.
- `GetSceneItemIndex`, `SetSceneItemIndex`.
- `GetSceneItemBlendMode`, `SetSceneItemBlendMode`.

### Outputs (record / stream / virtualcam / replay buffer)

- Record: `GetRecordStatus`, `StartRecord`, `StopRecord`, `ToggleRecord`, `PauseRecord`, `ResumeRecord`, `ToggleRecordPause`, `SplitRecordFile`, `CreateRecordChapter({chapterName?})`.
- Stream: `GetStreamStatus`, `StartStream`, `StopStream`, `ToggleStream`, `SendStreamCaption({captionText})`.
- VirtualCam: `GetVirtualCamStatus`, `StartVirtualCam`, `StopVirtualCam`, `ToggleVirtualCam`.
- Replay buffer: `GetReplayBufferStatus`, `StartReplayBuffer`, `StopReplayBuffer`, `ToggleReplayBuffer`, `SaveReplayBuffer`, `GetLastReplayBufferReplay`.
- Generic outputs: `GetOutputList`, `GetOutputStatus({outputName})`, `ToggleOutput`, `StartOutput`, `StopOutput`, `GetOutputSettings`, `SetOutputSettings`.

### Transitions

- `GetTransitionKindList`, `GetSceneTransitionList`.
- `GetCurrentSceneTransition`, `SetCurrentSceneTransition`, `SetCurrentSceneTransitionDuration`, `SetCurrentSceneTransitionSettings`.
- `GetCurrentSceneTransitionCursor` (0.0..1.0 during transition).
- `TriggerStudioModeTransition`, `SetTBarPosition({position, release?})`.

### Media Inputs

- `GetMediaInputStatus({inputName})` → `mediaState` ∈ `OBS_MEDIA_STATE_*`, `mediaDuration`, `mediaCursor`.
- `SetMediaInputCursor({inputName, mediaCursor})`, `OffsetMediaInputCursor({mediaCursorOffset})`.
- `TriggerMediaInputAction({inputName, mediaAction})` — `mediaAction` ∈ `OBS_WEBSOCKET_MEDIA_INPUT_ACTION_{NONE,PLAY,PAUSE,STOP,RESTART,NEXT,PREVIOUS}`.

### Hotkeys

- `GetHotkeyList` → array of hotkey name strings.
- `TriggerHotkeyByName({hotkeyName, contextName?})`.
- `TriggerHotkeyByKeySequence({keyId, keyModifiers: {shift, control, alt, command}})`.

### UI

- `GetStudioModeEnabled`, `SetStudioModeEnabled({studioModeEnabled})`.
- `GetMonitorList`.
- `OpenInputPropertiesDialog({inputName})`, `OpenInputFiltersDialog`, `OpenInputInteractDialog`.
- `OpenSourceProjector({sourceName, monitorIndex?, projectorGeometry?})`, `OpenVideoMixProjector({videoMixType, ...})`.

### Sources (screenshots)

- `GetSourceActive({sourceName})`.
- `GetSourceScreenshot({sourceName, imageFormat, imageWidth?, imageHeight?, imageCompressionQuality?})` → `imageData` (base64 data URL).
- `SaveSourceScreenshot({sourceName, imageFormat, imageFilePath, ...})`.

## Event catalog (common, grouped)

Events fire only if the matching category bit is in your subscription mask.
Every event body is `{"op": 5, "d": {"eventType": ..., "eventIntent": ..., "eventData": {...}}}`.

### General

- `ExitStarted` (OBS is shutting down).
- `VendorEvent({vendorName, eventType, eventData})` — from plugins.
- `CustomEvent({eventData})` — broadcast by a client via `BroadcastCustomEvent`.

### Config

- `CurrentSceneCollectionChanging`, `CurrentSceneCollectionChanged`, `SceneCollectionListChanged`.
- `CurrentProfileChanging`, `CurrentProfileChanged`, `ProfileListChanged`.

### Scenes

- `SceneCreated({sceneName, sceneUuid, isGroup})`.
- `SceneRemoved({sceneName, sceneUuid, isGroup})`.
- `SceneNameChanged({sceneUuid, oldSceneName, sceneName})`.
- `CurrentProgramSceneChanged({sceneName, sceneUuid})`.
- `CurrentPreviewSceneChanged({sceneName, sceneUuid})`.
- `SceneListChanged({scenes})`.

### Inputs

- `InputCreated`, `InputRemoved`, `InputNameChanged`, `InputSettingsChanged`.
- `InputMuteStateChanged({inputName, inputUuid, inputMuted})`.
- `InputVolumeChanged({inputName, inputUuid, inputVolumeMul, inputVolumeDb})`.
- `InputAudioSyncOffsetChanged`, `InputAudioTracksChanged`, `InputAudioMonitorTypeChanged`, `InputAudioBalanceChanged`.
- High-volume: `InputActiveStateChanged`, `InputShowStateChanged`, `InputVolumeMeters` (every 50 ms, `inputs[].inputLevelsMul` 3-channel array).

### Transitions

- `CurrentSceneTransitionChanged`, `CurrentSceneTransitionDurationChanged`.
- `SceneTransitionStarted`, `SceneTransitionEnded`, `SceneTransitionVideoEnded`.

### Filters

- `SourceFilterCreated`, `SourceFilterRemoved`, `SourceFilterNameChanged`.
- `SourceFilterEnableStateChanged({sourceName, filterName, filterEnabled})`.
- `SourceFilterSettingsChanged`, `SourceFilterListReindexed`.

### Scene Items

- `SceneItemCreated`, `SceneItemRemoved`, `SceneItemListReindexed`, `SceneItemSelected`.
- `SceneItemEnableStateChanged({sceneName, sceneItemId, sceneItemEnabled})`.
- `SceneItemLockStateChanged`.
- High-volume: `SceneItemTransformChanged`.

### Outputs

- `StreamStateChanged({outputActive, outputState})` — `outputState` ∈ `OBS_WEBSOCKET_OUTPUT_*`.
- `RecordStateChanged({outputActive, outputState, outputPath?})`.
- `RecordFileChanged({newOutputPath})`.
- `VirtualcamStateChanged({outputActive, outputState})`.
- `ReplayBufferStateChanged`, `ReplayBufferSaved({savedReplayPath})`.

### Media Inputs

- `MediaInputPlaybackStarted`, `MediaInputPlaybackEnded`.
- `MediaInputActionTriggered`.

### UI

- `StudioModeStateChanged({studioModeEnabled})`.
- `ScreenshotSaved({savedScreenshotPath})`.

### Canvases

- `CanvasCreated`, `CanvasRemoved`, `CanvasNameChanged`.

## Language snippets

### Python (`websocket-client`)

```python
import json, base64, hashlib, uuid, websocket

def connect(url, password):
    ws = websocket.WebSocket(subprotocols=["obswebsocket.json"])
    ws.connect(url)
    hello = json.loads(ws.recv())
    d = {"rpcVersion": 1, "eventSubscriptions": 4}   # Scenes only
    if "authentication" in hello["d"]:
        salt = hello["d"]["authentication"]["salt"]
        chal = hello["d"]["authentication"]["challenge"]
        sec  = base64.b64encode(hashlib.sha256((password + salt).encode()).digest()).decode()
        d["authentication"] = base64.b64encode(hashlib.sha256((sec + chal).encode()).digest()).decode()
    ws.send(json.dumps({"op": 1, "d": d}))
    assert json.loads(ws.recv())["op"] == 2
    return ws

def request(ws, rtype, rdata=None):
    rid = str(uuid.uuid4())
    msg = {"op": 6, "d": {"requestType": rtype, "requestId": rid}}
    if rdata: msg["d"]["requestData"] = rdata
    ws.send(json.dumps(msg))
    while True:
        resp = json.loads(ws.recv())
        if resp["op"] == 7 and resp["d"]["requestId"] == rid:
            return resp["d"]
```

### Node.js (`ws`)

```js
import WebSocket from "ws";
import { createHash, randomUUID } from "crypto";

const ws = new WebSocket("ws://localhost:4455", "obswebsocket.json");

function sha256b64(...parts) {
  return createHash("sha256").update(parts.join("")).digest("base64");
}

ws.on("message", (raw) => {
  const msg = JSON.parse(raw);
  if (msg.op === 0) {
    const d = { rpcVersion: 1, eventSubscriptions: 4095 };
    if (msg.d.authentication) {
      const { salt, challenge } = msg.d.authentication;
      const secret = sha256b64(process.env.OBS_PW, salt);
      d.authentication = sha256b64(secret, challenge);
    }
    ws.send(JSON.stringify({ op: 1, d }));
  } else if (msg.op === 2) {
    ws.send(JSON.stringify({
      op: 6, d: { requestType: "GetVersion", requestId: randomUUID() }
    }));
  } else if (msg.op === 7) {
    console.log(msg.d.responseData);
  } else if (msg.op === 5) {
    console.log("event", msg.d.eventType, msg.d.eventData);
  }
});
```

### Go (`gorilla/websocket`)

```go
package main

import (
    "crypto/sha256"
    "encoding/base64"
    "encoding/json"
    "github.com/google/uuid"
    "github.com/gorilla/websocket"
    "os"
)

func sha(parts ...string) string {
    h := sha256.New()
    for _, p := range parts { h.Write([]byte(p)) }
    return base64.StdEncoding.EncodeToString(h.Sum(nil))
}

type hello struct {
    Op int `json:"op"`
    D  struct {
        Authentication *struct { Challenge, Salt string } `json:"authentication,omitempty"`
    } `json:"d"`
}

func main() {
    c, _, _ := websocket.DefaultDialer.Dial("ws://localhost:4455",
        map[string][]string{"Sec-WebSocket-Protocol": {"obswebsocket.json"}})
    defer c.Close()

    var h hello
    _ = c.ReadJSON(&h)

    id := map[string]any{"rpcVersion": 1, "eventSubscriptions": 4}
    if h.D.Authentication != nil {
        secret := sha(os.Getenv("OBS_PW"), h.D.Authentication.Salt)
        id["authentication"] = sha(secret, h.D.Authentication.Challenge)
    }
    _ = c.WriteJSON(map[string]any{"op": 1, "d": id})

    var identified map[string]any
    _ = c.ReadJSON(&identified)

    _ = c.WriteJSON(map[string]any{
        "op": 6,
        "d": map[string]any{
            "requestType": "SetCurrentProgramScene",
            "requestId":   uuid.NewString(),
            "requestData": map[string]any{"sceneName": "Main"},
        },
    })

    var resp map[string]any
    _ = c.ReadJSON(&resp)
    b, _ := json.Marshal(resp); println(string(b))
}
```

### Browser (native `WebSocket`)

```html
<script>
async function sha256b64(input) {
  const enc = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", enc);
  return btoa(String.fromCharCode(...new Uint8Array(digest)));
}

const ws = new WebSocket("ws://localhost:4455", "obswebsocket.json");
ws.onmessage = async (e) => {
  const m = JSON.parse(e.data);
  if (m.op === 0) {
    const d = { rpcVersion: 1, eventSubscriptions: 4095 };
    if (m.d.authentication) {
      const { salt, challenge } = m.d.authentication;
      const secret = await sha256b64("PASSWORD" + salt);
      d.authentication = await sha256b64(secret + challenge);
    }
    ws.send(JSON.stringify({ op: 1, d }));
  } else if (m.op === 2) {
    ws.send(JSON.stringify({
      op: 6, d: { requestType: "GetSceneList", requestId: crypto.randomUUID() }
    }));
  } else {
    console.log(m);
  }
};
</script>
```

## Keepalive and reconnect

- obs-websocket does **not** send application-layer pings. The TCP/WS layer
  handles ping/pong transparently. `websocket-client` and `ws` respond to
  server-initiated pings automatically.
- On network failure or `SessionInvalidated (4011)`, reconnect from scratch:
  re-open the socket, redo Hello/Identify, resubscribe events, re-issue any
  in-flight Requests (your `requestId` dictionary will tell you which).
- Backoff: initial 500 ms, doubling to a cap of 30 s, with jitter.
- Do NOT pipeline Requests ahead of Identified — `NotIdentified (4007)` will
  drop the socket.
- Use `Reidentify` (OpCode 3) to change event mask without reconnecting; a
  fresh `Identified` (OpCode 2) is returned.

## Request correlation

`requestId` is client-generated and echoed verbatim. Keep a Map from id →
pending Promise/Future. For RequestBatch, the top-level `requestId` appears
in `RequestBatchResponse.d.requestId`; each inner result carries its own
`requestId` if you set one. Without per-request ids, inner results are in
input order when `executionType != Parallel`.
