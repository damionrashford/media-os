# Prompts — LLaVA and CLIP/SigLIP prompt library

Read when crafting prompts for LLaVA (description, VQA, video narration) or for CLIP / SigLIP classification (where phrasing heavily influences accuracy).

## CLIP / SigLIP classification

### The "a photo of X" trick

Bare `cat` → ~60 % accuracy on ImageNet-1k.
`"a photo of a cat"` → ~68 %.
Ensemble of 5-10 templates averaged → ~70 %.

Full OpenAI 80-template ensemble lives in the CLIP repo; the top 5 most impactful:

```
"a photo of a {}"
"a photo of the {}"
"a blurry photo of a {}"
"a low resolution photo of a {}"
"a photo of a small {}"
```

Ensemble code (1 image):

```python
templates = ["a photo of a {}", "a photo of the {}", "a blurry photo of a {}", ...]
prompts_per_class = [[t.format(c) for t in templates] for c in classes]
text_embeddings = [clip_encode_text(prompts).mean(axis=0) / np.linalg.norm(...) for prompts in prompts_per_class]
```

The `tag.py classify` and `tag-batch` subcommands accept full-sentence prompts directly via `--labels` — just hand-write them as complete sentences, never as bare nouns.

### Domain-specific prompt engineering

For non-ImageNet content:

- Products: `"a product photograph of a {}"`, `"an e-commerce photo of a {}"`
- Food: `"a photo of a plate of {}"`, `"a close-up of {}"`
- Medical (never for diagnosis, only for content tagging): `"a medical illustration of {}"`, `"an X-ray showing {}"`
- Screenshots: `"a screenshot of {}"`, `"a UI screenshot of {}"`
- Art: `"a painting of {}"`, `"a digital illustration of {}"`, `"a sketch of {}"`

### Negative / safety tagging

For content moderation / safety lists, pair positive and negative prompts:

```
--labels "a safe-for-work photo, a photo containing violence, a photo containing explicit content, a photo of weapons, a photo of drugs"
```

Threshold the score per-class. Do NOT aggregate: safety classification needs human review above a confidence bar, not an auto-decision.

## LLaVA prompts

LLaVA uses a chat template. The script wraps your `--prompt` into `USER: <image>\n{prompt}\nASSISTANT:`. Anything after that is free text.

### Short caption / alt text (WCAG)

```
--prompt "Describe this image in one short sentence suitable for alt text. Do not include decorative words like 'image of' or 'photo of'. Focus on subject, key action, and notable context."
```

Typical output: `A golden retriever jumping over a log in a forest clearing.`

### Detailed description

```
--prompt "Describe this image in detail. Cover the main subjects, their actions, the setting, the lighting and mood, and any notable objects."
```

### Object enumeration

```
--prompt "List every distinct object visible in this image. Output a comma-separated list of nouns, most prominent first. No duplicates."
```

Warning: LLaVA will hallucinate small objects. For rigorous object detection, use `cv-opencv` (YOLO) or `cv-mediapipe` (Object Detector).

### Scene / context analysis

```
--prompt "Where was this photo likely taken? Describe the location type (e.g. beach, forest, urban street), approximate time of day, and weather. Justify each guess in one short clause."
```

### Visual Question Answering (VQA)

```
--prompt "Is there a person in this image wearing a red shirt?"
--prompt "What is the color of the car?"
--prompt "How many cats are there?"
```

Numeric counting is weak. For N > 5, LLaVA gets imprecise.

### Video frame narration

```
--prompt "Describe this video frame in one short sentence, focusing on visible action."
```

Use with `tag.py video-describe --sample-fps 0.5` for a narration track. Merge adjacent identical sentences for scene-level summary.

For a coherent video-level synopsis, concatenate the per-frame descriptions and hand them to a text LLM:

```
"Here are per-second descriptions of a video clip. Summarize the overall content in 3 sentences: {descriptions}"
```

### Style / aesthetic tagging

```
--prompt "Describe the visual style of this image using 3-5 short tags. Use categories like: photographic, illustrated, 3D-rendered, vintage, modern, minimalist, maximalist, warm, cool, low-key, high-key."
```

### Alt text for accessibility (strict)

```
--prompt "You are writing alt text for a screen reader. Write one sentence, maximum 15 words, describing the essential content of this image. Do not start with 'image of' or 'photo of'. Use present tense. Be specific about people, actions, and setting."
```

## BLIP-2 prompting

BLIP-2 responds to a short prefix more than a full instruction:

```
--prompt "a photo of"       → "a golden retriever jumping over a log"
--prompt "Question: what is in this image? Answer:"  → "a dog jumping"
```

Use BLIP-2 for one-shot captions. For anything requiring reasoning ("what is the person doing and why?"), switch to LLaVA.

## Best-practice reminders

- **Short is better** — LLaVA answers improve with specific, narrow prompts.
- **Test your prompt on 5 images** before bulk-running — the prompt that works on one image may underperform at scale.
- **If the output is consistently wrong, change the prompt, not the model** — prompt has a bigger effect than swapping LLaVA-7B for LLaVA-13B.
- **For JSON output, explicitly ask** — "Respond in JSON with keys 'subject', 'setting', 'mood'." LLaVA will oblige most of the time; post-validate anyway.
- **No real-time "streaming"** — the script's `generate` calls are synchronous. For interactive use, integrate `transformers.streamers.TextIteratorStreamer` yourself.
