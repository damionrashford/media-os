# Optimizing Skill Descriptions

## How Triggering Works

Agents use progressive disclosure. At startup, they load only the `name` and `description` — just enough to decide when a skill is relevant. When a user's task matches, the agent reads the full SKILL.md into context.

**The description carries the entire burden of triggering.** If it doesn't convey when the skill is useful, the agent won't reach for it.

**Important nuance:** Agents typically only consult skills for tasks requiring knowledge beyond what they handle alone. Simple one-step requests may not trigger even if the description matches perfectly. Tasks involving specialized knowledge, unfamiliar APIs, domain-specific workflows, or uncommon formats — that's where descriptions make a difference.

---

## Writing Effective Descriptions

**Structure:** `[What it does] + [Use when...] + [Key trigger phrases] + [File types/tools if relevant]`

**Rules:**
- Use imperative phrasing: "Use when the user asks to..." not "This skill does..."
- Focus on user intent, not implementation mechanics
- Err on the side of being pushy — explicitly list contexts, including when the user doesn't name the domain directly
- Max 1024 characters. Front-load the key use case (250 char display cap in listing)
- No XML angle brackets (`< >`)

**Good examples:**

```yaml
# Specific and actionable with trigger phrases
description: Analyzes Figma design files and generates developer handoff documentation.
  Use when user uploads .fig files, asks for "design specs", "component documentation",
  or "design-to-code handoff".

# Includes paraphrase coverage — triggers even without the exact keyword
description: >
  Analyze CSV and tabular data files — compute summary statistics, add derived columns,
  generate charts, and clean messy data. Use when the user has a CSV, TSV, or Excel file
  and wants to explore, transform, or visualize the data, even if they don't explicitly
  mention "CSV" or "analysis."

# Clear value + negative scope to prevent over-triggering
description: Advanced data analysis for CSV files. Use for statistical modeling,
  regression, clustering. Do NOT use for simple data exploration (use data-viz skill instead).
```

**Bad examples:**

```yaml
# Too vague — agent has no idea when to load this
description: Helps with projects.

# Missing triggers — no user-facing signals
description: Creates sophisticated multi-page documentation systems.

# Too technical — no one says this when they need the skill
description: Implements the Project entity model with hierarchical relationships.
```

---

## Testing Descriptions

**Manual test:** Ask Claude: "When would you use the `<skill-name>` skill?" — Claude will quote the description back. Adjust based on what's missing.

**Structured test — write trigger eval queries:**

```json
[
  { "query": "I've got a spreadsheet in ~/data/q4_results.xlsx — can you add a profit margin column?", "should_trigger": true },
  { "query": "can you write a python script that reads a csv and uploads each row to postgres", "should_trigger": false }
]
```

Aim for ~20 queries: 8-10 should-trigger, 8-10 should-not-trigger.

**Should-trigger queries — vary along these axes:**
- Phrasing: formal, casual, typos, abbreviations
- Explicitness: some name the domain directly, others just describe the need
- Detail: terse prompts AND context-heavy ones
- Complexity: simple requests AND multi-step ones

**Should-NOT-trigger queries — strongest are near-misses:**

For a CSV analysis skill, weak negatives are "Write a fibonacci function" (no overlap). Strong negatives are:
- `"I need to update the formulas in my Excel budget spreadsheet"` — shares "spreadsheet" but needs editing, not analysis
- `"can you write a python script that reads a csv and uploads each row to postgres"` — involves CSV but task is ETL, not analysis

**Realism tips — real user prompts contain:**
- File paths (`~/Downloads/report_final_v2.xlsx`)
- Personal context ("my manager asked me to...")
- Specific details (column names, company names, data values)
- Casual language, abbreviations, occasional typos

---

## The Optimization Loop

1. Evaluate the current description on train + validation sets
2. Identify failures: which should-trigger queries didn't trigger? Which should-not-trigger did?
3. Revise:
   - Should-trigger failures → description too narrow. Broaden scope or add context
   - Should-not-trigger failures → description too broad. Add specificity or negative triggers
   - Avoid adding specific keywords from failed queries — that's overfitting. Find the general category
   - Keep under 1024 characters
4. Repeat until train set passes
5. Select best iteration by validation pass rate

Five iterations is usually enough.

---

## Before and After

```yaml
# Before — too narrow
description: Process CSV files.

# After — specific what, broad when, paraphrase coverage
description: >
  Analyze CSV and tabular data files — compute summary statistics,
  add derived columns, generate charts, and clean messy data. Use this
  skill when the user has a CSV, TSV, or Excel file and wants to
  explore, transform, or visualize the data, even if they don't
  explicitly mention "CSV" or "analysis."
```
