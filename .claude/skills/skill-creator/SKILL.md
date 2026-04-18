---
name: skill-creator
description: >
  Use when building a skill, creating a SKILL.md, packaging a workflow, making a slash
  command, or asked "how do I make a skill". Scaffolds the folder, generates SKILL.md
  from a template, validates against spec. Produces a complete ready-to-deploy skill
  folder: scripts, references, assets. Also use to review or improve an existing skill.
argument-hint: "[what the skill should do — describe the workflow or task]"
---

# Skill Creator

**What you're building:** $ARGUMENTS

## Available scripts

- **`scripts/scaffold.py`** — Creates skill folder + SKILL.md from template. Run this first.
- **`scripts/validate.py`** — Validates a skill against spec requirements. Run after writing.
- **`scripts/init-evals.py`** — Scaffolds `evals/` with `evals.json` + `trigger-queries.json` templates.
- **`scripts/test-triggers.py`** — Runs trigger queries through claude CLI, reports trigger rates.
- **`scripts/run-eval.py`** — Runs a single eval case (with-skill or without) via claude CLI.
- **`scripts/grade.py`** — Grades assertions against outputs, writes `grading.json` + `benchmark.json`.

---

## Phase 1 — Gather what you need

Ask the user these questions up front (all at once):

1. **What task or workflow should the skill handle?** What does the user type that should trigger it?
2. **Who invokes it — you, Claude, or both?**
   - User-only (deploy, commit, send slack) → `--disable-model-invocation`
   - Claude-auto only → will set `user-invocable: false` in body
   - Both → default, no flag
3. **Personal or project-scoped?**
   - Personal (all your projects): `~/.claude/skills`
   - Project-only: `.claude/skills`
4. **Does it need scripts?** Reusable logic, validation, commands too complex to get right by language alone → `--with-scripts`
5. **Does it need reference docs?** API guides, schemas, style guides, gotchas too long for SKILL.md → `--with-references`
6. **Does it depend on an MCP server or external tool?**

If `$ARGUMENTS` already covers these, confirm and proceed.

---

## CRITICAL — Scaffold before writing anything

**NEVER write SKILL.md, scripts, or references manually before running scaffold.py.**

scaffold.py generates correct frontmatter, folder structure, and placeholder files. Writing files first produces wrong frontmatter, breaks validation, and wastes time fixing structural issues.

**If the target folder already exists: delete it first, then scaffold.**

```bash
rm -rf <output>/<name>
uv run ${CLAUDE_SKILL_DIR}/scripts/scaffold.py --name <name> --output <output> ...
```

scaffold.py exits non-zero if the folder exists. Do not use `--force`. Delete and re-scaffold cleanly.

---

## Phase 2 — Scaffold the folder

Run scaffold.py to create the structure. Build the command from answers in Phase 1:

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/scaffold.py \
  --name <kebab-case-name> \
  --output <~/.claude/skills or .claude/skills> \
  [--description "What it does. Use when the user asks to X, Y, or Z."] \
  [--disable-model-invocation] \
  [--with-scripts] \
  [--with-references] \
  [--with-assets] \
  [--argument-hint "[arg]"] \
  [--context fork] \
  [--agent Explore]
```

The scaffold creates:

- `<name>/SKILL.md` — template with frontmatter pre-filled
- `<name>/scripts/process.py` — placeholder with `--help`, argparse, PEP 723 deps (if `--with-scripts`)
- `<name>/references/guide.md` — placeholder reference doc (if `--with-references`)
- `<name>/assets/` — empty dir (if `--with-assets`)

For the description flag: structure it as `"What it does. Use when the user asks to X, Y, or Z."` — max 1024 chars, no XML brackets. Read `references/description-optimization.md` for optimization guidance.

---

## Phase 3 — Write the SKILL.md body

Open the scaffolded SKILL.md. The template at `assets/skill-template.md` shows the full canonical structure.

**Write the body following this structure:**

```markdown
# Skill Name

**Context:** $ARGUMENTS ← keep if the skill takes arguments

## Quick start

3 bullet points → "Most common task: → Step N"

## When to use

Bullet list of scenarios this covers.

## Step 1 — [Action]

Specific, actionable instructions. Not "validate properly" — write exactly what to do.
Include exact commands, field names, expected outputs.

## Gotchas ← HIGHEST VALUE SECTION — never skip this

- [Non-obvious fact that the agent would get wrong without it]
- Add every correction you've had to make manually

## Examples

Input → Steps → Result

## Troubleshooting

Error message → Cause → Solution
```

**Key rules — read `references/best-practices.md` for full guidance:**

- Under 500 lines. Move detailed docs to `references/` and link with "Read `references/X.md` when [condition]"
- Add only what the agent wouldn't know on its own — skip general knowledge
- Prescriptive when operations are fragile; give freedom when approaches are flexible
- Defaults not menus: "Use pdfplumber. For scanned PDFs, use pdf2image instead."

**SKILL.md body = agent instructions, not documentation.**

Write what to run, exact commands, expected output, what fails. Do NOT write:
- Explanations of how things work internally
- Background context the agent doesn't need to act
- README-style prose or tutorials

If you catch yourself explaining *why* something works, stop. Write what the agent should *do* instead.

**If scripts/ was created:**

scaffold.py creates `scripts/process.py` as a placeholder. You have two choices:
1. **Your script is named `process.py`** → replace the TODO section with real logic. Keep the existing `--help`, argparse, PEP 723 inline deps, and stdout/stderr separation.
2. **Your script has a different name** (e.g. `mail.py`, `imessage.py`) → write the new file, then **delete `scripts/process.py`**. Leaving the placeholder causes confusion and may trigger validate.py warnings.

Never add interactive prompts (`input()`) — agents can't respond.

**If references/ was created:**

Fill `references/guide.md` with content too large for SKILL.md. Link it from the body: `Read references/guide.md if [condition]` — not a generic "see references/".

---

## Phase 4 — Validate (mandatory gate)

**Do not consider the skill done until validate.py passes.**

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/validate.py <path-to-skill>
```

Exit codes:
- **0** — all pass. Done.
- **2** — warnings only. Acceptable. Document why if you skip any warning.
- **1** — spec violations. **Must fix before shipping.** The skill will not load correctly.

Fix every error, then re-run. Do not move to Phase 5 with exit code 1.

Common issues and fixes:

- `name-matches-folder` warning → either rename the folder or fix the `name` field
- `description-has-trigger` warning → add "Use when the user asks to..." to the description
- `body-size` warning → move reference material to `references/`
- `script-no-interactive` warning → replace `input()` with `argparse` flags
- `description-length` warning → shorten description, front-load key trigger phrases within 250 chars

---

## Phase 5 — Test triggering

**Quick check:** Ask Claude: "When would you use the `<skill-name>` skill?" — Claude quotes the description back. Adjust if the answer doesn't match user intent.

**Structured test with script:**

```bash
# 1. Scaffold the evals directory
uv run ${CLAUDE_SKILL_DIR}/scripts/init-evals.py --skill <path-to-skill>

# 2. Fill in evals/trigger-queries.json — replace REPLACE placeholders with:
#    - 5-10 "should trigger" queries (vary phrasing, formality, explicitness)
#    - 5-10 "should NOT trigger" near-misses (share keywords, need something different)

# 3. Run trigger tests (3 runs per query for nondeterminism)
uv run ${CLAUDE_SKILL_DIR}/scripts/test-triggers.py --skill <path-to-skill> --runs 3 --save
```

Reads results: trigger rate per query. Target: should-trigger avg ≥80%, should-not-trigger avg ≤20%.

If failing: revise `description` in SKILL.md and re-run. Read `references/description-optimization.md` for the full optimization loop. Use `--train-only` to reserve 40% of queries for final validation.

---

## Phase 6 — Install and smoke test

The skill is already in place from Phase 2 (`--output ~/.claude/skills` or `--output .claude/skills`).

```
/skill-name          ← direct invocation (if user-invocable)
```

Or say something that matches the description to test auto-triggering.

---

## Phase 7 — Run evals (measure output quality)

Use this when you need to measure whether the skill actually improves output quality, not just triggering.

```bash
# 1. Fill in evals/evals.json — add realistic prompts + assertions per eval case
#    Put input files in evals/files/

# 2. Run each eval WITH skill (iteration 1)
uv run ${CLAUDE_SKILL_DIR}/scripts/run-eval.py --skill <path> --all --iteration 1

# 3. Run same evals WITHOUT skill (baseline)
uv run ${CLAUDE_SKILL_DIR}/scripts/run-eval.py --skill <path> --all --iteration 1 --no-skill

# 4. Grade assertions — uses claude CLI to grade each claim against actual output
uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py --skill <path> --iteration 1

# Or grade manually (human-in-the-loop):
uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py --skill <path> --iteration 1 --human
```

Reads `benchmark.json`: pass rates with-skill vs without-skill, delta, token/time cost.

---

## Phase 8 — Iterate

After grading, three signal sources tell you what to fix:

- **Failed assertions** → specific gaps in instructions, missing steps, unhandled cases
- **Human feedback** → broader quality issues the assertions didn't catch
- **Execution transcripts** → WHY things went wrong (agent tried multiple approaches = instructions too vague)

Fix SKILL.md, then re-run in a new iteration:

```bash
# Increment iteration to keep results separate
uv run ${CLAUDE_SKILL_DIR}/scripts/run-eval.py --skill <path> --all --iteration 2
uv run ${CLAUDE_SKILL_DIR}/scripts/run-eval.py --skill <path> --all --iteration 2 --no-skill
uv run ${CLAUDE_SKILL_DIR}/scripts/grade.py --skill <path> --iteration 2
```

Stop when: pass rate plateaus, human feedback is consistently empty, or delta is satisfactory.

| Signal                           | Cause                         | Fix                                                    |
| -------------------------------- | ----------------------------- | ------------------------------------------------------ |
| Skill never triggers             | Description too narrow        | Add trigger phrases, re-run test-triggers.py           |
| Triggers too often               | Description too broad         | Add negative scope or `disable-model-invocation: true` |
| Instructions not followed        | Critical rules buried         | Move to top, use CRITICAL headers, add to Gotchas      |
| Inconsistent results across runs | Instructions ambiguous        | Add deterministic validation script                    |
| Pass rate low vs baseline        | Skill adding noise not signal | Trim instructions to what agent actually lacks         |
| Skill slow / large context       | SKILL.md too big              | Move content to `references/`                          |
