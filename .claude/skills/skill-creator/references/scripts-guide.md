# Using Scripts in Skills

## When to Use Scripts

Use a bundled script in `scripts/` when:
- There's reusable logic the agent would otherwise reimplement each run
- A command is complex enough to get wrong on the first try in natural language
- Validation needs to be deterministic (code beats language for this)
- The agent needs to check its own work programmatically

Use one-off commands (no script needed) when:
- An existing package already does what you need
- The command is simple and low-risk to get slightly wrong

---

## One-Off Commands (no scripts/ directory needed)

### uvx (Python — recommended)
```bash
uvx ruff@0.8.0 check .
uvx black@24.10.0 .
```

### npx (Node.js — ships with npm)
```bash
npx eslint@9 --fix .
npx create-vite@6 my-app
```

### go run
```bash
go run golang.org/x/tools/cmd/goimports@v0.28.0 .
```

**Tips:**
- Pin versions (`npx eslint@9.0.0`) for reproducibility
- State prerequisites in SKILL.md ("Requires Node.js 18+")
- When a command grows complex, move it to scripts/

---

## Referencing Scripts from SKILL.md

Use relative paths from the skill directory root. List available scripts so the agent knows they exist:

```markdown
## Available scripts

- **`scripts/validate.sh`** — Validates configuration files
- **`scripts/process.py`** — Processes input data

## Workflow

1. Run the validation script:
   ```bash
   bash scripts/validate.sh "$INPUT_FILE"
   ```
2. Process the results:
   ```bash
   python3 scripts/process.py --input results.json
   ```
```

Or use `$CLAUDE_SKILL_DIR` for explicit absolute paths:
```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/my_tool.py <action> [flags]
```

---

## Self-Contained Scripts

### Python (PEP 723 — recommended)

Declare dependencies inline so the script runs anywhere with uv:

```python
# /// script
# dependencies = [
#   "beautifulsoup4>=4.12,<5",
# ]
# ///

from bs4 import BeautifulSoup

# your code here
```

Run with:
```bash
uv run scripts/extract.py
```

### Deno (self-contained TypeScript)
```typescript
#!/usr/bin/env -S deno run

import * as cheerio from "npm:cheerio@1.0.0";
// your code here
```
```bash
deno run scripts/extract.ts
```

### Bun (auto-installs packages)
```typescript
#!/usr/bin/env bun
import * as cheerio from "cheerio@1.0.0";
```
```bash
bun run scripts/extract.ts
```

---

## Designing Scripts for Agentic Use (CRITICAL)

### Rule 1: NO interactive prompts

Agents operate in non-interactive shells. A script that blocks on TTY input hangs indefinitely.

```
# Bad — hangs forever
$ python scripts/deploy.py
Target environment: _

# Good — clear error with guidance
$ python scripts/deploy.py
Error: --env is required. Options: development, staging, production.
Usage: python scripts/deploy.py --env staging --tag v1.2.3
```

Accept all input via:
- Command-line flags
- Environment variables
- stdin

### Rule 2: Document usage with `--help`

This is the primary way an agent learns your script's interface. Keep it concise (it enters the context window):

```
Usage: scripts/process.py [OPTIONS] INPUT_FILE

Process input data and produce a summary report.

Options:
  --format FORMAT    Output format: json, csv, table (default: json)
  --output FILE      Write output to FILE instead of stdout
  --verbose          Print progress to stderr

Examples:
  scripts/process.py data.csv
  scripts/process.py --format csv --output report.csv data.csv
```

### Rule 3: Write helpful error messages

When an agent gets an error, the message directly shapes its next attempt:
```
Error: --format must be one of: json, csv, table.
       Received: "xml"
```

### Rule 4: Use structured output

Prefer JSON, CSV, TSV over free-form text. Structured formats can be consumed by the agent and standard tools.

```
# Hard to parse
NAME          STATUS    CREATED
my-service    running   2025-01-15

# Unambiguous
{"name": "my-service", "status": "running", "created": "2025-01-15"}
```

Separate data from diagnostics: structured data → stdout, progress/warnings → stderr.

### Rule 5: Design for agentic reliability

- **Idempotency**: "Create if not exists" is safer than "create and fail on duplicate" — agents retry
- **Input constraints**: Reject ambiguous input with a clear error. Use enums and closed sets.
- **Dry-run**: `--dry-run` flag for destructive/stateful operations so the agent can preview
- **Meaningful exit codes**: Distinct codes for different failure types (not found, invalid args, auth failure)
- **Safe defaults**: Destructive operations should require explicit confirmation flags (`--confirm`, `--force`)
- **Predictable output size**: Many harnesses truncate tool output beyond 10-30K characters. Default to a summary or reasonable limit, and support `--offset` for more.
