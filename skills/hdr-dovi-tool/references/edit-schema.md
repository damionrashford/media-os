# dovi_tool editor JSON schema

`dovi_tool editor -i rpu.bin -j edit.json -o edited.bin` applies a JSON edit script to an existing RPU.

## Top-level fields (commonly used)

```jsonc
{
  "mode": 0,                       // conversion mode (0=passthrough)
  "active_area": {                 // optional L5 crop overrides
    "crop": true,
    "presets": [
      { "id": 0, "left": 0, "right": 0, "top": 280, "bottom": 280 }
    ],
    "edits": { "all": 0 }
  },
  "remove_scenes": [               // drop frames (RPU kept at 0 for gap)
    { "start": 0, "end": 240 }
  ],
  "duplicate_scenes": [            // repeat existing RPU frames
    { "source": 500, "offset": 1000, "length": 24 }
  ],
  "scene_cuts": [                  // insert scene-cut flags
    120, 240, 480
  ],
  "offsets": {                     // per-level offsets
    "l1": [ { "start": 0, "end": 100, "offset": 0.05 } ],
    "l6": { "max_cll": 1000, "max_fall": 200 }
  }
}
```

Not every field is always present — author only the keys you need. The `dovi_tool` version determines which keys are honoured.

## Common edits

### Trim first 5 minutes (24fps)

```json
{ "remove_scenes": [ { "start": 0, "end": 7200 } ] }
```

### Force L6 metadata (static MaxCLL/MaxFALL)

```json
{ "offsets": { "l6": { "max_cll": 1000, "max_fall": 200 } } }
```

### Mark scene cuts at known boundaries

```json
{ "scene_cuts": [0, 240, 480, 720, 1200] }
```

### Override L5 active-area crop

```json
{
  "active_area": {
    "crop": true,
    "presets": [ { "id": 0, "left": 0, "right": 0, "top": 140, "bottom": 140 } ],
    "edits": { "all": 0 }
  }
}
```

## Version pinning

The editor schema has changed across dovi_tool versions. When sharing an edit JSON:

1. Record the dovi_tool version in the JSON filename (e.g. `edit-v2.1.0.json`).
2. Or commit both the JSON and `dovi_tool --version` output in VCS alongside.

To check the current authoritative schema: `hdr-dynmeta-docs` skill's `fetch --page dovi-readme`, search for the "editor" section.

## Also useful

- `dovi_tool export -i rpu.bin -o rpu.json` emits a full JSON dump of the RPU you can diff against.
- `dovi_tool plot -i rpu.bin -o before.png` before editing, then `plot` again after, and visually compare.
