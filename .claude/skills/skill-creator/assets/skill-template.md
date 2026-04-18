---
name: SKILL_NAME
description: >
  WHAT_IT_DOES. Use when the user asks to TRIGGER_PHRASE_1,
  TRIGGER_PHRASE_2, or TRIGGER_PHRASE_3. Also triggers when
  PARAPHRASE_WITHOUT_EXACT_KEYWORD.
argument-hint: "[OPTIONAL_ARG_HINT]"
# Uncomment if this skill should only be user-invoked (deploy, commit, send, etc.):
# disable-model-invocation: true
# Uncomment if this skill should run in an isolated subagent:
# context: fork
# agent: Explore
---

# SKILL_TITLE

**Context:** $ARGUMENTS

## Quick start

- **Most common task:** → Step N
- **Second common task:** → Step N
- **Edge case:** → Step N

## When to use

- Scenario 1
- Scenario 2
- Scenario 3

---

## Step 1 — [First major action]

[Specific instructions. What exactly to do, not "handle this properly". Include exact
commands, field names, expected outputs.]

```bash
# Example command if applicable
command --flag value
```

Expected output: [what success looks like]

## Step 2 — [Next action]

[Instructions...]

If [condition], do [X]. Otherwise, do [Y].

---

## Gotchas

<!-- THIS SECTION IS THE HIGHEST VALUE CONTENT. Add every correction you've had to make manually.
     If the agent makes a mistake and you correct it — add it here. -->

- [Non-obvious fact]: [what the agent would assume] is wrong — [what is actually true]
- [Field name mismatch]: `field_name_in_X` is called `different_name_in_Y` — they're the same value
- [Soft delete pattern]: Queries must include `WHERE deleted_at IS NULL` or results include deleted records

---

## Examples

### Example 1: [most common scenario]

**Input:** [what the user provides]

**Steps:**
1. [What Claude does]
2. [Next step]

**Result:** [What the output looks like]

### Example 2: [edge case]

**Input:** [edge case input]

**Steps:**
1. [How to handle this differently]

**Result:** [edge case output]

---

## Troubleshooting

### Error: [exact error message or symptom]

**Cause:** [why this happens]

**Solution:** [exact steps to fix it]

### Error: [another common error]

**Cause:** [...]

**Solution:** [...]