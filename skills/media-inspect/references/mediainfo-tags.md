# MediaInfo reference

Deep reference for the MediaInfo CLI. Pair with `SKILL.md` for task-oriented recipes.

---

## `--Output` preset catalog

`--Output` (capital O) picks a renderer. The underlying engine is the same — only the serializer changes.

| Preset        | Use case                                                  |
| ------------- | --------------------------------------------------------- |
| *default*     | Human-readable tree (NOT stable — don't parse)            |
| `JSON`        | Stable machine-readable output — use this for automation  |
| `XML`         | XML tree mirror of the JSON                               |
| `HTML`        | Browseable single-page report                             |
| `CSV`         | Flat CSV rows — one per track attribute                   |
| `EBU`         | EBU Core XML — broadcast archives                         |
| `PBCore`      | PBCore 2 XML — US public-media archives                   |
| `MPEG-7`      | ISO/IEC 15938 MPEG-7 description                          |
| `OLDXML`      | Legacy XML format                                         |

```bash
mediainfo --Output=JSON   in.mp4
mediainfo --Output=XML    in.mp4
mediainfo --Output=HTML   in.mp4 > report.html
mediainfo --Output=EBU    in.mxf
mediainfo --Output=PBCore in.mxf
mediainfo --Output=MPEG-7 in.mp4
mediainfo --Output=CSV    in.mp4
```

---

## `%Field%` catalog by stream type

Used with `--Inform="<StreamType>;<template>"`. Stream type is case-sensitive.

### General (container)

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | Container (MPEG-4, Matroska, MXF, ...)         |
| `Format/String`       | Human-readable container name                  |
| `CompleteName`        | Absolute path                                  |
| `FileSize`            | Bytes, integer                                 |
| `FileSize/String`     | "1.23 GiB"                                     |
| `Duration`            | Milliseconds, integer-as-string                |
| `Duration/String1`    | "1 h 23 min"                                   |
| `Duration/String3`    | "01:23:45.678" (canonical timecode form)       |
| `OverallBitRate`      | Bits per second, integer                       |
| `OverallBitRate/String` | "8 000 kb/s"                                 |
| `OverallBitRate_Mode` | "CBR" / "VBR"                                  |
| `EncodedDate`         | "UTC 2024-01-15 10:30:00"                      |
| `TaggedDate`          | Often equal to EncodedDate                     |
| `Format_Profile`      | Container profile (isom, qt, ...)              |
| `Movie`               | Title                                          |
| `VideoCount`, `AudioCount`, `TextCount`, `MenuCount` | Stream counts |

### Video

| Field                     | Meaning                                        |
| ------------------------- | ---------------------------------------------- |
| `Format`                  | AVC, HEVC, AV1, VP9, ProRes, ...               |
| `CodecID`                 | Container codec tag (avc1, hvc1, dvhe, ...)    |
| `Format_Profile`          | "High@L4.1" / "Main 10@L5.1@High" / ...        |
| `Format_Level`            | Level only                                     |
| `Format_Tier`             | HEVC tier: Main / High                         |
| `Width`, `Height`         | Pixels                                         |
| `PixelAspectRatio`        | 1.000 typically                                |
| `DisplayAspectRatio`      | 16:9, 2.40:1, etc                              |
| `FrameRate`               | Current effective frame rate                   |
| `FrameRate_Mode`          | "CFR" / "VFR"                                  |
| `FrameRate_Original`      | Pre-conversion frame rate (IVTC sources)       |
| `FrameCount`              | Total frame count                              |
| `BitRate`                 | bps, integer                                   |
| `BitRate/String`          | "8 000 kb/s"                                   |
| `BitDepth`                | 8 / 10 / 12                                    |
| `ChromaSubsampling`       | 4:2:0 / 4:2:2 / 4:4:4                          |
| `ColorSpace`              | YUV / RGB                                      |
| `colour_primaries`        | BT.709 / BT.2020 / Display P3 / ...            |
| `transfer_characteristics`| BT.709 / PQ / HLG / sRGB / ...                 |
| `matrix_coefficients`     | BT.709 / BT.2020 non-constant / ...            |
| `colour_range`            | Limited / Full                                 |
| `ScanType`                | Progressive / Interlaced / MBAFF               |
| `ScanOrder`               | TFF / BFF                                      |
| `HDR_Format`              | "Dolby Vision, Version 1.0, Profile 8.1, dvhe.08.06" |
| `HDR_Format_Commercial`   | "HDR10" / "HDR10+ Profile A" / "Dolby Vision"  |
| `MasteringDisplay_ColorPrimaries` | e.g. "Display P3" or "BT.2020"         |
| `MasteringDisplay_Luminance`      | "min: 0.0050 cd/m2, max: 1000 cd/m2"   |
| `MaxCLL`                  | Maximum Content Light Level (cd/m2)            |
| `MaxFALL`                 | Maximum Frame-Average Light Level (cd/m2)      |

### Audio

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | AAC / AC-3 / E-AC-3 / DTS / FLAC / Opus / ...  |
| `Format_Profile`      | AAC: "LC" / "HE" / "HE v2"                     |
| `Format_Commercial`   | "Dolby Digital Plus with Dolby Atmos"          |
| `Format_Settings_Mode`| CBR / VBR / ABR                                |
| `CodecID`             | mp4a.40.2, ac-3, ec-3, ...                     |
| `Channels`            | Integer channel count                          |
| `ChannelLayout`       | "L R C LFE Ls Rs" etc                          |
| `ChannelPositions`    | Human-readable layout                          |
| `SamplingRate`        | 44100 / 48000 / 96000 ...                      |
| `SamplingRate/String` | "48.0 kHz"                                     |
| `BitDepth`            | 16 / 24                                        |
| `BitRate`             | bps                                            |
| `BitRate_Mode`        | CBR / VBR                                      |
| `Language`            | ISO 639-2 code                                 |
| `Title`               | Track title                                    |

### Text (subtitles / CC)

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | UTF-8 / TTML / PGS / VobSub / SCC / SRT / CEA-608 |
| `CodecID`             | e.g. tx3g, mov_text, S_TEXT/UTF8, S_TEXT/ASS   |
| `Language`            | ISO 639-2                                      |
| `Title`               | Track title                                    |
| `Default`, `Forced`   | Flags                                          |

### Other (timecode, chapters)

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | "Time code" / "Chapters"                       |
| `TimeCode_FirstFrame` | e.g. "01:00:00:00"                             |
| `TimeCode_Striped`    | Yes / No                                       |

### Image (still images inside a container — cover art)

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | JPEG / PNG                                     |
| `Width`, `Height`     | Pixels                                         |

### Menu (DVD-style chapter menus)

| Field                 | Meaning                                        |
| --------------------- | ---------------------------------------------- |
| `Format`              | "DVD-Video" / "BD"                             |
| `Chapters_Pos_Begin`, `Chapters_Pos_End` | Chapter pointer offsets     |

---

## HDR metadata field signatures

### HDR10 (static metadata, SMPTE ST 2086 + ST 2094-10)

```
transfer_characteristics     : PQ
colour_primaries             : BT.2020
MasteringDisplay_ColorPrimaries : Display P3 (or BT.2020)
MasteringDisplay_Luminance   : min: 0.0050 cd/m2, max: 1000 cd/m2
MaxCLL                       : 1000 cd/m2
MaxFALL                      : 400 cd/m2
```

### HDR10+ (dynamic metadata, SMPTE ST 2094-40)

`HDR_Format` line contains `SMPTE ST 2094-40` or the string `HDR10+`:

```
HDR format                   : SMPTE ST 2086, HDR10 compatible
HDR format                   : SMPTE ST 2094-40, Version 1, HDR10+ Profile A
```

### HLG (Hybrid Log-Gamma, ARIB STD-B67)

```
transfer_characteristics     : HLG  (or "ARIB STD-B67")
colour_primaries             : BT.2020
```
No static metadata required.

### Dolby Vision profile signatures

`HDR_Format` line carries the profile number and codec string:

| Profile | Base layer | Enhancement layer | Typical container | `HDR_Format` fragment                        |
| ------- | ---------- | ----------------- | ----------------- | -------------------------------------------- |
| 5       | HEVC       | n/a (IPTPQc2)     | MP4 / MKV         | `Profile 5, dvhe.05.06`                      |
| 7       | HEVC       | HEVC (EL+RPU)     | MKV (dual-track)  | `Profile 7, dvhe.07.06`                      |
| 8.1     | HEVC       | none (RPU only)   | MP4 / MKV (HDR10 compatible) | `Profile 8.1, dvhe.08.06`         |
| 8.2     | HEVC       | none              | SDR base          | `Profile 8.2`                                |
| 8.4     | HEVC       | none              | HLG base          | `Profile 8.4`                                |
| 9       | AVC        | none              | MP4               | `Profile 9, dvav.09.xx` (web SDR base)       |
| 10      | AV1        | none              | MP4               | `Profile 10, dav1.10.xx`                     |

---

## MXF-specific fields

```
Format_Profile                : OP-1a / OP-1b / OP-Atom
Format_Settings_Wrapping      : Frame / Clip
MXF_MetadataScheme            : Descriptive / Operational
Format_Commercial             : XDCAM HD422 / AVC-Intra Class 100 / ProRes / DNxHD / IMX / ...
```

For IMF (SMPTE ST 2067), MediaInfo reports `Format : MXF` with `Format_Profile : App2e` or `App5` on the image essence.

---

## jq parsing examples

Given `data = $(mediainfo --Output=JSON --Full in.mp4)`:

```bash
# list tracks with type+format
echo "$data" | jq '.media.track[] | {type: ."@type", format: .Format}'

# video resolution + profile + bit depth
echo "$data" | jq '.media.track[] | select(."@type"=="Video") |
  {w:.Width, h:.Height, prof:.Format_Profile, bd:.BitDepth}'

# HDR flags
echo "$data" | jq '.media.track[] | select(."@type"=="Video") |
  {hdr:.HDR_Format, transfer:.transfer_characteristics,
   primaries:.colour_primaries, maxCLL:.MaxCLL, maxFALL:.MaxFALL}'

# every audio track codec + channels
echo "$data" | jq '.media.track[] | select(."@type"=="Audio") |
  {codec:.Format, ch:.Channels, layout:.ChannelLayout, lang:.Language}'

# Dolby Vision profile number
echo "$data" | jq -r '.media.track[] | select(."@type"=="Video") |
  .HDR_Format // empty' | grep -oE "Profile [0-9.]+"

# container + duration (ms)
echo "$data" | jq -r '.media.track[] | select(."@type"=="General") |
  [.Format, .Duration] | @tsv'
```

---

## MediaInfo vs ffprobe field crosswalk

| Concept                | MediaInfo `%Field%`                     | ffprobe JSON                                              |
| ---------------------- | --------------------------------------- | --------------------------------------------------------- |
| Container format       | `Format` (General)                      | `format.format_name`                                      |
| Duration (seconds)     | `Duration` / 1000                       | `format.duration`                                         |
| Overall bit rate       | `OverallBitRate`                        | `format.bit_rate`                                         |
| Codec                  | `Format` (Video/Audio)                  | `streams[].codec_name`                                    |
| Codec tag              | `CodecID`                               | `streams[].codec_tag_string`                              |
| Profile + level        | `Format_Profile`                        | `streams[].profile` + `streams[].level`                   |
| Width / Height         | `Width` / `Height`                      | `streams[].width` / `streams[].height`                    |
| Frame rate             | `FrameRate`                             | `streams[].r_frame_rate` (fraction) / `avg_frame_rate`    |
| Frame count            | `FrameCount`                            | `streams[].nb_frames`                                     |
| Bit depth              | `BitDepth`                              | `streams[].bits_per_raw_sample`                           |
| Pixel format           | — (inferred)                            | `streams[].pix_fmt`                                       |
| Color primaries        | `colour_primaries`                      | `streams[].color_primaries`                               |
| Transfer               | `transfer_characteristics`              | `streams[].color_transfer`                                |
| Color matrix           | `matrix_coefficients`                   | `streams[].color_space`                                   |
| Color range            | `colour_range`                          | `streams[].color_range`                                   |
| HDR10 static meta      | `MasteringDisplay_*`, `MaxCLL`, `MaxFALL` | `-show_frames -show_entries side_data` only            |
| Dolby Vision profile   | `HDR_Format` (contains "Profile X.Y")   | `streams[].side_data_list[].dv_profile` (frame-level)     |
| Scan type              | `ScanType`                              | `streams[].field_order`                                   |
| Audio channels         | `Channels`                              | `streams[].channels`                                      |
| Audio channel layout   | `ChannelLayout`                         | `streams[].channel_layout`                                |
| Audio sample rate      | `SamplingRate`                          | `streams[].sample_rate`                                   |
| Track language         | `Language` (ISO 639-2)                  | `streams[].tags.language`                                 |
| MXF operational pattern| `Format_Profile` (General) = "OP-1a"    | — (not surfaced cleanly)                                  |

---

## Recipe book

### Broadcast QC pre-flight

```bash
mediainfo --Full in.mxf | grep -i -E \
  "^(Format|Duration|Bit rate|Width|Height|Frame rate|Scan type|Color space|Bit depth|Time code|Channel|Sampling rate)"
```

Check (a) `Format_Profile : OP-1a` for broadcast exchange, (b) `Format_Commercial` matches the target (`XDCAM HD422 50` for 1080i50 news, `AVC-Intra Class 100` for mastering, `ProRes 422 HQ` for post), (c) `TimeCode_FirstFrame` starts at the expected head-of-programme offset (`01:00:00:00` for SMPTE convention or `10:00:00:00` for some broadcasters).

### Delivery spec compliance (Netflix UHD HDR10 example)

Checked by `scripts/mediainfo.py netflix-check`:
- Codec: HEVC
- Profile: Main 10
- Bit depth: 10
- Resolution: ≥ 3840x2160
- Color primaries: BT.2020
- Transfer: PQ
- HDR metadata present (MasteringDisplay + MaxCLL + MaxFALL)
- Bit rate: ≥ 16 Mb/s for 4K HDR10

### HDR verification

```bash
uv run scripts/mediainfo.py hdr --input in.mkv
# Distinguishes SDR / HDR10 / HDR10+ / HLG / DolbyVision and reports DV profile
```

Cross-check against frame-level:

```bash
ffprobe -v error -select_streams v:0 -read_intervals "%+#1" \
  -show_entries frame=side_data_list -of json in.mkv
```

### Codec audit for a folder

```bash
for f in *.mp4; do
  printf '%s\t' "$f"
  mediainfo --Inform="Video;%Format% %Format_Profile% %Width%x%Height% %BitDepth%bit %FrameRate%fps %BitRate/String%" "$f"
done
```

### Check if two encodes differ structurally

```bash
uv run scripts/mediainfo.py compare --inputs source.mov encode.mp4
```

### Parse Dolby Vision profile in a script

```bash
mediainfo --Inform="Video;%HDR_Format%" in.mkv | grep -oE "Profile [0-9.]+"
```

### Detect VFR (variable frame rate)

```bash
mediainfo --Inform="Video;%FrameRate_Mode%" in.mp4
# VFR | CFR
```

### Detect IVTC sources

If `FrameRate` = 23.976 and `FrameRate_Original` = 29.970 → telecined source that has been IVTC'd.

### Read a field non-interactively with a known path

```bash
mediainfo --Inform="General;%Duration/String3%" in.mp4    # -> 01:23:45.678
mediainfo --Inform="Video;%Width%x%Height%"    in.mp4    # -> 3840x2160
mediainfo --Inform="Audio;%Format% %Channels%ch %SamplingRate%Hz" in.mp4
```

### Read over HTTP without downloading the whole file

```bash
mediainfo --Output=JSON https://example.com/movie.mp4
```

MediaInfo uses Range requests to fetch only the moov/index boxes. If the server does not support Range, MediaInfo falls back to full download.

### Parse CMAF fragment structure

```bash
mediainfo --Full init.mp4 | grep -i -E "moof|mdat|sidx|fragment"
```
