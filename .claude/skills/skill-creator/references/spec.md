# Agent Skills Specification — Reference

## Directory Structure

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
└── ...               # Any additional files
```

## SKILL.md Frontmatter Fields

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | Max 64 chars. Lowercase letters, numbers, hyphens only. No leading/trailing/consecutive hyphens. Must match folder name. |
| `description` | Yes | Max 1024 chars. Non-empty. Describes what + when. |
| `license` | No | License name or file reference. |
| `compatibility` | No | Max 500 chars. Environment requirements. |
| `metadata` | No | Arbitrary key-value mapping. |
| `allowed-tools` | No | Space-delimited list of pre-approved tools. (Experimental) |

## Claude Code Extensions (beyond the open standard)

| Field | Description |
|---|---|
| `argument-hint` | Hint in autocomplete, e.g. `[issue-number]` |
| `disable-model-invocation` | `true` = only user can invoke. Default: `false` |
| `user-invocable` | `false` = hide from `/` menu (Claude-only). Default: `true` |
| `model` | Model to use when skill is active |
| `effort` | `low`, `medium`, `high`, `max` (Opus 4.6 only) |
| `context` | `fork` = run in isolated subagent |
| `agent` | Subagent type: `Explore`, `Plan`, `general-purpose`, custom |
| `hooks` | Hooks scoped to this skill |
| `paths` | Glob patterns limiting activation scope |
| `shell` | `bash` (default) or `powershell` for `!`command`` blocks |

## Invocation Control Matrix

| Frontmatter | User can invoke | Claude can invoke | Context |
|---|---|---|---|
| (default) | Yes | Yes | Description in context, full skill on invoke |
| `disable-model-invocation: true` | Yes | No | Description NOT in context |
| `user-invocable: false` | No | Yes | Description in context |

## String Substitutions

| Variable | Description |
|---|---|
| `$ARGUMENTS` | All arguments passed at invocation |
| `$ARGUMENTS[N]` | Specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing the skill's SKILL.md |

## Dynamic Context Injection

`` !`<command>` `` syntax runs shell commands and injects output before the skill content is sent to Claude:

```yaml
---
name: pr-summary
context: fork
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`
```

## Security Restrictions

- No XML angle brackets (`< >`) anywhere in frontmatter
- Skills named with "claude" or "anthropic" prefix are reserved
- No `README.md` inside the skill folder

## Validation

```bash
skills-ref validate ./my-skill
```

## Progressive Disclosure — Three Tiers

| Tier | Content | When loaded | Token cost |
|---|---|---|---|
| 1 | `name` + `description` | Session start | ~50-100 tokens per skill |
| 2 | Full `SKILL.md` body | When skill activated | Under 5,000 tokens recommended |
| 3 | Scripts, references, assets | When instructions reference them | Varies |

## Size Limits

- SKILL.md body: under 500 lines / 5,000 tokens recommended
- Move detailed reference material to `references/`
- Max 20-50 skills enabled simultaneously before context degradation
