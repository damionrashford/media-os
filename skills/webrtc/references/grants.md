# LiveKit Token Grants

Tokens are JWT HS256 with a `video` claim that describes the participant's permissions. Full schema: `https://docs.livekit.io/home/get-started/authentication/`.

## JWT top-level claims

| Claim       | Meaning                                    |
|-------------|--------------------------------------------|
| `iss`       | API key (server recognizes this sender)    |
| `sub`       | Participant identity (unique per room)     |
| `iat`       | Issued-at (seconds since epoch)            |
| `nbf`       | Not-before                                 |
| `exp`       | **Required** expiration                    |
| `name`      | Display name (optional)                    |
| `metadata`  | Free-form per-participant metadata         |
| `video`     | VideoGrant (see below)                     |

## `video` (VideoGrant) keys

### Room admin
| Key            | Type  | Meaning                                      |
|----------------|-------|----------------------------------------------|
| `roomCreate`   | bool  | Can create rooms via server API              |
| `roomList`     | bool  | Can list all rooms                           |
| `roomRecord`   | bool  | Can start/stop egress                        |
| `roomAdmin`    | bool  | Can manage participants in the room          |
| `ingressAdmin` | bool  | Can create ingress endpoints                 |

### Participant (room-scoped)
| Key                   | Type   | Meaning                                            |
|-----------------------|--------|----------------------------------------------------|
| `room`                | string | **Required for `roomJoin`** — room name            |
| `roomJoin`            | bool   | Can join the named room                            |
| `canPublish`          | bool   | Can publish tracks                                 |
| `canPublishData`      | bool   | Can send DataPackets                               |
| `canSubscribe`        | bool   | Can subscribe to others' tracks                    |
| `canPublishSources`   | []str  | Optional whitelist: `camera`, `microphone`, `screen_share`, `screen_share_audio`, `unknown` |
| `canUpdateOwnMetadata`| bool   | Can call `updateParticipantMetadata`               |
| `hidden`              | bool   | Participant not shown in room lists                |
| `recorder`            | bool   | Mark this participant as a recorder (excluded from composite layouts) |
| `agent`               | bool   | Mark as a LiveKit Agent (system-managed)           |

### Default when missing

Permissions default to `false` if not specified. You MUST set at least `roomJoin:true` + a `room` value for a user to enter a room.

## Example payloads

### A regular meeting participant

```json
{
  "iss": "API_KEY",
  "sub": "alice",
  "exp": 1710003600,
  "video": {
    "room": "daily-standup",
    "roomJoin": true,
    "canPublish": true,
    "canSubscribe": true,
    "canPublishData": true
  }
}
```

### A hidden room admin (transcription, moderation bot)

```json
{
  "iss": "API_KEY",
  "sub": "transcriber-7",
  "exp": 1710003600,
  "video": {
    "room": "daily-standup",
    "roomJoin": true,
    "roomAdmin": true,
    "canSubscribe": true,
    "canPublishData": true,
    "hidden": true
  }
}
```

### An egress recorder

```json
{
  "iss": "API_KEY",
  "sub": "rec-bot",
  "exp": 1710003600,
  "video": {
    "room": "daily-standup",
    "roomJoin": true,
    "canSubscribe": true,
    "recorder": true,
    "hidden": true
  }
}
```

### A server-side admin (no room, just REST API)

```json
{
  "iss": "API_KEY",
  "sub": "backend",
  "exp": 1710003600,
  "video": {
    "roomCreate": true,
    "roomList": true,
    "roomAdmin": true,
    "roomRecord": true,
    "ingressAdmin": true
  }
}
```

## Source-type constants

When using `canPublishSources` whitelist:

- `camera`
- `microphone`
- `screen_share`
- `screen_share_audio`
- `unknown`

Matches enum `TrackSource` in proto definitions.

## Signing

- Algorithm: **HS256** (HMAC-SHA256 with the API secret).
- Base64url-encoded header + payload + signature, joined by `.`.
- The helper in `scripts/livekit.py mint-token` implements this with stdlib only (no pyjwt).
