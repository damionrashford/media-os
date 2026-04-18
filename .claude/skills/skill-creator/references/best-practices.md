# Skill Authoring Best Practices

## Start from Real Expertise

Never write a skill from general knowledge alone. The highest-quality skills come from:

1. **Extracting from a hands-on task**: Complete a real task in conversation, then extract what worked into a skill. Capture:
   - Steps that worked (the exact sequence)
   - Corrections you made (where you steered the agent)
   - Input/output formats
   - Context you had to provide (project-specific facts, conventions)

2. **Synthesizing from existing artifacts**: Feed internal docs, runbooks, API specs, code review patterns, and real failure cases to an LLM and ask it to synthesize a skill. Domain-specific source material beats generic "best practices" articles.

## Add What the Agent Lacks — Omit What It Knows

Focus on what the agent WOULDN'T know without your skill:
- Project-specific conventions
- Domain-specific procedures
- Non-obvious edge cases
- Specific tools or APIs to use

You don't need to explain what a PDF is, how HTTP works, or what a database migration does.

```markdown
<!-- Too verbose -->
## Extract PDF text
PDF files are a common format. To extract text, use a library. pdfplumber handles most cases.

<!-- Better — skips what the agent knows -->
## Extract PDF text
Use pdfplumber. For scanned documents, fall back to pdf2image with pytesseract.

```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

Ask yourself: "Would the agent get this wrong without this instruction?" If no — cut it.

## Match Specificity to Fragility

**Give freedom** when multiple approaches are valid:
```markdown
## Code review process
1. Check all database queries for SQL injection (use parameterized queries)
2. Verify authentication checks on every endpoint
3. Look for race conditions in concurrent code paths
```

**Be prescriptive** when operations are fragile or order matters:
```markdown
## Database migration
Run exactly this sequence:
```bash
python scripts/migrate.py --verify --backup
```
Do not modify the command or add additional flags.
```

## Provide Defaults, Not Menus

Pick a default and mention alternatives briefly:

```markdown
<!-- Too many options — agent hesitates -->
You can use pypdf, pdfplumber, PyMuPDF, or pdf2image...

<!-- Clear default with escape hatch -->
Use pdfplumber for text extraction:
```python
import pdfplumber
```
For scanned PDFs requiring OCR, use pdf2image with pytesseract instead.
```

## Favor Procedures Over Declarations

Teach the agent HOW to approach a class of problems, not WHAT to produce for a specific instance:

```markdown
<!-- Specific answer — only useful for this exact task -->
Join the `orders` table to `customers` on `customer_id`, filter where `region = 'EMEA'`.

<!-- Reusable method — works for any query -->
1. Read the schema from `references/schema.yaml` to find relevant tables
2. Join tables using the `_id` foreign key convention
3. Apply filters from the user's request as WHERE clauses
4. Aggregate and format as a markdown table
```

## High-Value Content Patterns

### Gotchas Section (highest value)
Environment-specific facts that defy reasonable assumptions:

```markdown
## Gotchas
- The `users` table uses soft deletes. Queries must include `WHERE deleted_at IS NULL`.
- The user ID is `user_id` in the DB, `uid` in the auth service, `accountId` in billing. Same value.
- `/health` returns 200 even if the DB connection is down. Use `/ready` for full health check.
```

When an agent makes a mistake you have to correct, add the correction to Gotchas. This is the most direct way to improve a skill.

### Output Templates
When you need a specific format, provide a template:

```markdown
## Report structure
Use this template:
# [Analysis Title]
## Executive summary
[One-paragraph overview]
## Key findings
- Finding 1 with supporting data
## Recommendations
1. Specific actionable recommendation
```

### Checklists for Multi-Step Workflows
```markdown
## Form processing workflow
Progress:
- [ ] Step 1: Analyze the form (run `scripts/analyze_form.py`)
- [ ] Step 2: Create field mapping (edit `fields.json`)
- [ ] Step 3: Validate mapping (run `scripts/validate_fields.py`)
- [ ] Step 4: Fill the form (run `scripts/fill_form.py`)
- [ ] Step 5: Verify output (run `scripts/verify_output.py`)
```

### Validation Loops
```markdown
## Editing workflow
1. Make your edits
2. Run validation: `python scripts/validate.py output/`
3. If validation fails: review the error, fix the issues, run again
4. Only proceed when validation passes
```

### Plan-Validate-Execute (for batch/destructive operations)
```markdown
1. Extract form fields → produces `form_fields.json`
2. Create `field_values.json` mapping each field to its intended value
3. Validate: `python scripts/validate_fields.py form_fields.json field_values.json`
4. If validation fails, revise `field_values.json` and re-validate
5. Fill: `python scripts/fill_form.py input.pdf field_values.json output.pdf`
```

## Progressive Disclosure in Content

Keep SKILL.md focused. When a skill legitimately needs more content:

- Move detailed reference material to `references/`
- Tell the agent WHEN to load each file:
  ```
  Read `references/api-errors.md` if the API returns a non-200 status code.
  ```
  NOT just: "see references/ for details"

## Iteration Signals

- **Undertriggering** → Add more trigger phrases to description, include technical terms
- **Overtriggering** → Add negative triggers, be more specific in description
- **Instructions not followed** → Put critical rules at top, use CRITICAL headers, add to Gotchas
- **Inconsistent results** → Write a deterministic validation script instead of relying on language
- **Agent tries multiple approaches** → Instructions are too vague — be more prescriptive
- **Agent follows instructions that don't apply** → Scope the instructions more clearly
