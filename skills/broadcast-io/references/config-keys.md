# gphoto2 config-key cheat sheet (per manufacturer)

Key paths are **per-camera driver**, not a universal schema. The same
concept (aperture, ISO, shutter) sits at different paths on Canon vs
Nikon vs Sony. Always `config-list` on an unknown body first.

## Canonical key paths by manufacturer

| Concept | Canon | Nikon | Sony | Fujifilm |
|---|---|---|---|---|
| Shutter speed | `/main/capturesettings/shutterspeed` | `/main/capturesettings/shutterspeed` | `/main/capturesettings/shutterspeed` | `/main/capturesettings/shutterspeed` |
| Aperture | `/main/capturesettings/aperture` | `/main/capturesettings/f-number` | `/main/capturesettings/f-number` | `/main/capturesettings/f-number` |
| ISO | `/main/imgsettings/iso` | `/main/imgsettings/iso` | `/main/imgsettings/iso` | `/main/imgsettings/iso` |
| White balance | `/main/imgsettings/whitebalance` | `/main/imgsettings/whitebalance` | `/main/imgsettings/whitebalance` | `/main/imgsettings/whitebalance` |
| Exposure mode (P/A/S/M) | `/main/capturesettings/autoexposuremode` | `/main/capturesettings/expprogram` | `/main/capturesettings/expprogram` | `/main/capturesettings/expprogram` |
| Exposure compensation | `/main/capturesettings/exposurecompensation` | `/main/capturesettings/exposurecompensation` | `/main/capturesettings/exposurebiascompensation` | `/main/capturesettings/exposurecompensation` |
| Focus mode | `/main/capturesettings/focusmode` | `/main/capturesettings/focusmode2` | `/main/capturesettings/focusmode` | `/main/capturesettings/focusmode` |
| Autofocus drive (one-shot) | `/main/actions/autofocusdrive` | `/main/actions/autofocusdrive` | `/main/actions/autofocus` | `/main/actions/autofocusdrive` |
| Manual focus drive | `/main/actions/manualfocusdrive` | `/main/actions/manualfocusdrive` | (not exposed) | `/main/actions/manualfocusdrive` |
| Image format (JPG/RAW) | `/main/imgsettings/imageformat` | `/main/imgsettings/imagequality` | `/main/imgsettings/imagesize` + `/main/imgsettings/imagequality` | `/main/imgsettings/imagequality` |
| Drive mode (single/cont) | `/main/capturesettings/drivemode` | `/main/capturesettings/drivemode` | `/main/capturesettings/drivemode` | `/main/capturesettings/drivemode` |
| Battery level | `/main/status/batterylevel` | `/main/status/batterylevel` | `/main/status/batterylevel` | `/main/status/batterylevel` |
| Capture target (card / SDRAM) | `/main/settings/capturetarget` | `/main/settings/capturetarget` | `/main/settings/capturetarget` | `/main/settings/capturetarget` |
| Flash mode | `/main/capturesettings/flashmode` | `/main/capturesettings/flashmode` | `/main/capturesettings/flashmode` | `/main/capturesettings/flashmode` |
| Bulb mode trigger | `/main/actions/bulb` | `/main/actions/bulb` | `/main/actions/bulb` | `/main/actions/bulb` |

## Value formats

- **Shutter speed:** fraction strings like `1/125`, `1/60`, `1"` (for 1 second), `30"` (30 seconds), `bulb`.
- **Aperture / f-number:** decimal string: `2.8`, `5.6`, `8`, `11`.
- **ISO:** integer string: `100`, `200`, `400`, `800`, `1600`, `3200`, `Auto`.
- **White balance:** enum strings, per camera — common: `Auto`, `Daylight`, `Cloudy`, `Tungsten`, `Fluorescent`, `Flash`, `Custom`.
- **Exposure compensation:** fraction string: `-2`, `-1.3`, `0`, `+0.7`, `+2`.
- **Focus mode:** `Manual`, `AF-S` (single), `AF-C` (continuous), `AF-A` (auto-select).
- **Drive mode:** `Single`, `Continuous`, `ContinuousHigh`, `ContinuousLow`, `Timer10s`.
- **Capture target:** `0` = internal RAM, `1` = memory card, `2` = card 2.

## Setting shortcuts

```bash
# By literal value:
gphoto2 --set-config /main/imgsettings/iso=400

# By the index of the allowed-list from --get-config:
gphoto2 --set-config-index /main/imgsettings/iso=3   # pick the 4th choice

# Value-only (drops type prefix when camera returns `0=Single,1=Cont`):
gphoto2 --set-config-value /main/capturesettings/drivemode=Continuous
```

## Gotchas

- **Canon `aperture` vs Nikon `f-number`.** Hard-coded "aperture" scripts won't work on Nikon — branch on `config-list` output or query both.
- **Sony does not expose manual focus drive** over PTP. Use the camera's focus ring, or pre-focus with AF-S then switch to MF on the body.
- **Bulb mode needs `/main/actions/bulb=1` to open shutter, `0` to close.** Pair with your own timer.
- **`capturetarget=0` saves to camera RAM only** — file is in the camera's DRAM and disappears if not downloaded before the next shot on most bodies.
- **Allowed values depend on current mode.** In A (aperture priority) mode, `shutterspeed` may be read-only. Check `Type:` field from `config-get` (`Range` vs `Radio` vs `Text`).
- **Values are case-sensitive and camera-specific.** `"AF-S"` on Nikon may be `"Single AF"` on Canon. Always query allowed choices via `config-get` before setting.
