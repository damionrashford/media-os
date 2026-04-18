# ONVIF profile / service matrix

## Profiles (as of 2026)

| Profile | Status | What it covers |
|---|---|---|
| **S** | **Deprecated 2027-03-31** | Streaming over IP (RTSP/RTP, H.264, PTZ, events). Superseded by T. |
| **T** | Active | Successor to S: H.264 + H.265 + metadata + bidirectional audio + imaging + analytics hooks. |
| **G** | Active | On-device recording + search/retrieve of recordings. |
| **Q** | Deprecated | Out-of-box discovery + provisioning. Never widely adopted. |
| **M** | Active | Metadata + events + analytics for video/access. |
| **A** | Active | Access control (doors, access points). |
| **C** | Active | Access control client for VMS integration with A devices. |
| **D** | Active | Access control peripherals (readers, locks). |

## Core services (web-service endpoints)

All services are SOAP 1.2 over HTTP/HTTPS. The device's capability response
returns the XAddr URL for each service (e.g. `http://camera/onvif/ptz_service`).

| Service | Typical XAddr path | Key operations |
|---|---|---|
| Device Management | `/onvif/device_service` | `GetDeviceInformation`, `GetCapabilities`, `GetServices`, `GetUsers`, `SetUser`, `GetSystemDateAndTime`, `GetNetworkInterfaces`, `SystemReboot` |
| Media (v1) | `/onvif/media_service` | `GetProfiles`, `GetStreamUri`, `GetSnapshotUri`, `GetVideoSources`, `GetVideoEncoderConfiguration` |
| Media2 (v2) | `/onvif/media2_service` | `GetProfiles`, `GetStreamUri`, `AddConfiguration` — preferred for Profile T cameras |
| PTZ | `/onvif/ptz_service` | `GetConfigurations`, `ContinuousMove`, `AbsoluteMove`, `RelativeMove`, `Stop`, `GotoPreset`, `SetPreset`, `RemovePreset`, `GotoHomePosition`, `GetStatus` |
| Imaging | `/onvif/imaging_service` | `GetImagingSettings`, `SetImagingSettings`, `GetMoveOptions`, `Move`, `GetStatus` (focus) |
| Events | `/onvif/events_service` | `GetEventProperties`, `CreatePullPointSubscription`, `PullMessages`, `Unsubscribe`, `Subscribe` (basic notification) |
| Analytics | `/onvif/analytics_service` | `GetAnalyticsConfigurations`, `GetSupportedRules` |
| Recording | `/onvif/recording_service` | `CreateRecording`, `GetRecordings`, `DeleteRecording`, `CreateTrack` |
| Search | `/onvif/search_service` | `GetRecordingSummary`, `FindRecordings`, `FindEvents`, `GetRecordingInformation` |
| Replay | `/onvif/replay_service` | `GetReplayUri` → RTSP URL to pull a recording |
| Display | `/onvif/display_service` | On-device display layout (NVR) |

## WS-Security (UsernameToken digest)

SOAP Security header for authenticated calls:

```xml
<Security soap:mustUnderstand="true"
          xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
  <UsernameToken>
    <Username>admin</Username>
    <Password Type=".../wsse-username-token-profile-1.0#PasswordDigest">
      BASE64( SHA1( nonce + created + password ) )
    </Password>
    <Nonce EncodingType="...#Base64Binary">BASE64(random 16 bytes)</Nonce>
    <Created>2026-04-17T12:34:56Z</Created>
  </UsernameToken>
</Security>
```

- `nonce` is raw random bytes (NOT base64) going into the SHA1.
- `created` is XSD dateTime UTC.
- `password` is the cleartext secret; never transmitted.
- Digest format: `Password Type="...#PasswordDigest"`.

Cameras that only support `PasswordText` are non-conformant and rare in the
wild post-2015; digest is the standard.

## WS-Discovery

- Probe: SOAP envelope inside UDP datagram to `239.255.255.250:3702`.
- ProbeType: `dn:NetworkVideoTransmitter` (camera) or `tds:Device`.
- ProbeMatch response returns `<d:XAddrs>` with the Device service URL.
- Hello/Bye announcements broadcast from cameras on cold-start/shutdown.
- NOT routable across subnets — link-local multicast only.

## Per-profile feature matrix (excerpt)

| Feature | S | T | G | M | A/C/D |
|---|---|---|---|---|---|
| RTSP streaming | yes | yes | — | — | — |
| H.264 | yes | yes | — | — | — |
| H.265 | — | yes | — | — | — |
| Metadata stream | opt | yes | — | yes | — |
| Bidirectional audio | opt | yes | — | — | — |
| Imaging/focus | — | yes | — | — | — |
| PTZ | opt | opt | — | — | — |
| On-device recording | — | — | yes | — | — |
| Recording search | — | — | yes | — | — |
| Analytics | — | opt | — | yes | — |
| Access control | — | — | — | — | yes |

## Canonical URLs

- https://www.onvif.org/profiles/
- https://www.onvif.org/profiles/specifications/
- https://www.onvif.org/profiles/profile-s/
- https://www.onvif.org/wp-content/uploads/2018/05/ONVIF_Profile_Feature_overview_v2-1.pdf
