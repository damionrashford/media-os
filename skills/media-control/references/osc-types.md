# OSC type tags and address-pattern grammar

## Type-tag reference

Type tag is a single OSC-string that starts with `,` then one character per argument, in order. The string is null-terminated and padded to 4 bytes.

### OSC 1.0 required types

| Tag | Name | Wire form | Size |
|---|---|---|---|
| `i` | int32 | big-endian signed 32-bit | 4 B |
| `f` | float32 | IEEE 754 big-endian | 4 B |
| `s` | OSC-string | null-terminated ASCII + pad to 4 | var |
| `b` | blob | i32 size + bytes + pad to 4 | var |

### OSC 1.0 optional / 1.1 required

| Tag | Name | Wire form | Size |
|---|---|---|---|
| `h` | int64 | big-endian signed 64-bit | 8 B |
| `t` | OSC-timetag | 64-bit NTP | 8 B |
| `d` | float64 (double) | IEEE 754 big-endian | 8 B |
| `S` | alternate string type | same as `s` | var |
| `c` | ASCII char | 32-bit, value in low byte | 4 B |
| `r` | RGBA color | 4 bytes (R,G,B,A) in 32-bit word | 4 B |
| `m` | MIDI message | 4 bytes (port, status, data1, data2) | 4 B |
| `T` | True | no payload | 0 B |
| `F` | False | no payload | 0 B |
| `N` | Nil | no payload | 0 B |
| `I` | Impulse / Infinitum | no payload | 0 B |
| `[` / `]` | array begin/end | no payload | 0 B |

### NTP timetag

- 64-bit: high 32 bits = seconds since 1900-01-01 UTC; low 32 bits = fractional.
- `ntp_seconds = unix_seconds + 2208988800`.
- Special value `0x0000000000000001` = "immediate" (process as soon as received).
- Values with `seconds == 0 && fractional != 1` are reserved.

## Address-pattern grammar

OSC 1.0 matching rules:

| Syntax | Meaning |
|---|---|
| `?` | exactly one char that is not `/` |
| `*` | zero or more chars that are not `/` |
| `[abc]` | any char in set |
| `[a-z]` | any char in range |
| `[!abc]` | any char NOT in set |
| `{foo,bar}` | any of the listed strings |
| literal | must match exactly |

OSC 1.1 adds:

| Syntax | Meaning |
|---|---|
| `//` | zero or more path segments (like shell globstar) |

Examples:

```
/fader/[1-8]           matches /fader/1, /fader/2, ..., /fader/8
/chan/?/vol            matches /chan/1/vol, /chan/a/vol
/mixer/{master,aux}/gain  matches /mixer/master/gain or /mixer/aux/gain
//fader                (1.1) matches /fader, /a/fader, /a/b/fader
```

## SLIP framing (OSC 1.1 TCP)

Byte-stuffing to mark packet boundaries:

```
END = 0xC0
ESC = 0xDB
ESC END -> 0xDB 0xDC
ESC ESC -> 0xDB 0xDD
```

Each packet is framed as:

```
END <data with stuffing> END
```

Most apps use length-prefix (4-byte i32 before each packet) instead of SLIP; check docs.

## Canonical sources

- https://opensoundcontrol.stanford.edu/spec-1_0.html — Matt Wright, 2002 (CCRMA / UC Berkeley lineage, now hosted at Stanford CCRMA).
- https://opensoundcontrol.stanford.edu/spec-1_1.html — Wright & Freed, NIME 2009.
- **Do NOT reference `opensoundcontrol.org`** — that domain is dead.
