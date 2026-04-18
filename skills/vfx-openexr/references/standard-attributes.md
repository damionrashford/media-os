# OpenEXR Standard Attributes

Full reference. Load when the user asks about specific attributes
(chromaticities, timeCode, keyCode, etc.).

Source: `https://openexr.com/en/latest/StandardAttributes.html`.

## Camera / exposure

| Attribute | Type | Meaning |
|---|---|---|
| `owner` | string | Name of the photographer / artist |
| `comments` | string | Freeform notes |
| `capDate` | string | ISO-8601 capture date |
| `utcOffset` | float | Hours offset from UTC when captured |
| `longitude` | float | GPS longitude (degrees) |
| `latitude` | float | GPS latitude (degrees) |
| `altitude` | float | GPS altitude (meters) |
| `focus` | float | Camera focus distance (meters) |
| `expTime` | float | Exposure time (seconds) |
| `aperture` | float | Lens f-number |
| `isoSpeed` | float | ISO film speed |

## Color science

| Attribute | Type | Meaning |
|---|---|---|
| `chromaticities` | chromaticities | (red.xy, green.xy, blue.xy, white.xy) of the working primaries |
| `whiteLuminance` | float | cd/m^2 of the white point (typically 100 for SDR, up to 10000 for HDR) |
| `adoptedNeutral` | V2f | (x,y) chromaticity of the "adopted neutral" (usually same as white) |
| `renderingTransform` | string | Name of the "rendering transform" (display/output transform) applied to make this image viewable |
| `lookModTransform` | string | Name of a creative look applied on top of renderingTransform |

**Common chromaticities values:**

- Rec.709 / sRGB: `red=(0.640,0.330); green=(0.300,0.600); blue=(0.150,0.060); white=(0.3127,0.3290)`
- DCI-P3: `red=(0.680,0.320); green=(0.265,0.690); blue=(0.150,0.060); white=(0.314,0.351)`
- Rec.2020: `red=(0.708,0.292); green=(0.170,0.797); blue=(0.131,0.046); white=(0.3127,0.3290)`
- ACES 2065-1 / AP0: `red=(0.7347,0.2653); green=(0.0,1.0); blue=(0.0001,-0.0770); white=(0.32168,0.33767)`
- ACEScg / AP1: `red=(0.713,0.293); green=(0.165,0.830); blue=(0.128,0.044); white=(0.32168,0.33767)`

## Image geometry

| Attribute | Type | Meaning |
|---|---|---|
| `xDensity` | float | Horizontal pixels per unit (usually per inch) |
| `wrapModes` | string | How the image is meant to tile: `clamp`, `black`, `periodic` in X and Y |
| `screenWindowCenter` | V2f | CG-origin screen window center (for NDC) |
| `screenWindowWidth` | float | CG-origin screen window width |
| `pixelAspectRatio` | float | Horizontal-to-vertical pixel aspect |

## Environment map

| Attribute | Type | Meaning |
|---|---|---|
| `envmap` | envmap | Integer enum: 0 = latlong, 1 = cube |

## Film / broadcast

| Attribute | Type | Meaning |
|---|---|---|
| `keyCode` | keyCode | Film key-code for round-tripping: filmMfcCode, filmType, prefix, count, perfOffset, perfsPerFrame, perfsPerCount |
| `timeCode` | timeCode | SMPTE timecode: hrs, mins, secs, frame, dropFrame, colorFrame, fieldPhase, bgf0/1/2, userData |
| `framesPerSecond` | rational | Intended frame rate for a sequence |

## Multi-part / multi-view

| Attribute | Type | Meaning |
|---|---|---|
| `name` | string | Part name (multi-part files) |
| `type` | string | One of `scanlineimage`, `tiledimage`, `deepscanline`, `deeptile` |
| `view` | string | View name (stereo: `left` / `right`) |
| `multiView` | string[] | List of view names present (on the first part) |

## Deep

| Attribute | Type | Meaning |
|---|---|---|
| `version` | int | File format version |
| `chunkCount` | int | Number of chunks (tiles/scanlines) in the part |

## Utility attributes

| Attribute | Type | Meaning |
|---|---|---|
| `dataWindow` | box2i | Rendered / stored area (per-pixel limits) |
| `displayWindow` | box2i | Intended canvas (cropping reference) |
| `lineOrder` | lineOrder | `INCREASING_Y`, `DECREASING_Y`, or `RANDOM_Y` |
| `compression` | compression | See `references/compression.md` |
| `channels` | channelList | Per-channel: name, pixelType (HALF/FLOAT/UINT), xSampling, ySampling, pLinear |

## Gotchas

- **`chromaticities` is per-EXR, not per-session.** Tools that assume Rec.709 when `chromaticities` is missing will silently get wrong color in wide-gamut pipelines.
- **`timeCode` vs `framesPerSecond` roundtrip:** the timeCode is absolute; the FPS tells readers how to interpret `frame` sub-count. Always write both.
- **`dataWindow` with negative origin:** overscan renders have dataWindow starting at (-N, -N). Comp apps must handle this.
- **Signed vs unsigned pixel types in `channels`:** HALF and FLOAT are signed (IEEE 754); UINT is unsigned 32-bit.
- **`view` attribute vs `multiView`:** On multi-view EXRs, each part has its own `view` set, and the first part lists all views in `multiView`. Older tools look for the `multiView` enum first.
