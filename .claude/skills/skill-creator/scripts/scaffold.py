#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Scaffold a new Agent Skill folder with a SKILL.md template.

Usage:
    python3 scripts/scaffold.py --name <skill-name> --output <path>
                                [--description "..."]
                                [--disable-model-invocation]
                                [--with-scripts]
                                [--with-references]
                                [--with-assets]
                                [--context fork]
                                [--agent Explore]
                                [--argument-hint "[argument]"]

Examples:
    python3 scripts/scaffold.py --name my-workflow --output ~/.claude/skills
    python3 scripts/scaffold.py --name deploy --output .claude/skills --disable-model-invocation --with-scripts
    python3 scripts/scaffold.py --name data-reporter --output .claude/skills --with-scripts --with-references --description "Generate weekly data reports"
"""

import argparse
import os
import re
import sys
from pathlib import Path


SKILL_MD_TEMPLATE = """\
---
name: {name}
description: >
  {description}
{extra_fields}\
---

# {title}

**Context:** $ARGUMENTS

## Quick start

- **[Common task 1]:** → Step N
- **[Common task 2]:** → Step N

## When to use

- [Scenario 1]
- [Scenario 2]
- [Scenario 3]

## Step 1 — [First major action]

[Specific, actionable instructions. Not "do X properly" — write exactly what to do.]

{scripts_section}\
{references_section}\
## Gotchas

- [Environment-specific fact that defies reasonable assumptions]
- [Field name mismatch, soft delete, non-obvious default]

## Examples

### Example 1: [common scenario]

Input: ...
Steps: ...
Result: ...

## Troubleshooting

### Error: [message]

Cause: ...
Solution: ...
"""

SCRIPTS_SECTION = """\
## Available scripts

- **`scripts/process.py`** — [what it does]

## Workflow

1. Run the script:
   ```bash
   uv run ${CLAUDE_SKILL_DIR}/scripts/process.py --input $ARGUMENTS
   ```

"""

REFERENCES_SECTION = """\
## Reference docs

- Read [`references/guide.md`](references/guide.md) when [condition]

"""

PLACEHOLDER_SCRIPT = """\
#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
\"\"\"
[Describe what this script does]

Usage:
    uv run scripts/process.py [OPTIONS] INPUT

Options:
    --input FILE    Input file to process
    --output FILE   Write output to FILE instead of stdout (default: stdout)
    --dry-run       Preview what would happen without making changes
    --verbose       Print progress to stderr

Examples:
    uv run scripts/process.py --input data.csv
    uv run scripts/process.py --input data.csv --output results.json
\"\"\"

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="[Describe what this script does]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", required=True, help="Input file to process")
    parser.add_argument("--output", default=None, help="Output file (default: stdout)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    # Validate input
    from pathlib import Path
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        print(f"Usage: uv run scripts/process.py --input <file>", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Processing: {args.input}", file=sys.stderr)

    if args.dry_run:
        print(f"[dry-run] Would process: {args.input}", file=sys.stderr)
        sys.exit(0)

    # TODO: implement processing logic here
    result = {"status": "ok", "input": args.input}

    output = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output)
        if args.verbose:
            print(f"Wrote output to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
"""

PLACEHOLDER_REFERENCE = """\
# [Reference Title]

## Overview

[Brief description of what this reference covers and when to load it.]

## Section 1

[Content]

## Section 2

[Content]

## Gotchas

- [Non-obvious fact]
- [Edge case]
"""


def validate_name(name: str) -> str:
    """Validate and return skill name, or raise with helpful message."""
    if not name:
        raise ValueError("--name is required")
    if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', name) and not re.match(r'^[a-z0-9]$', name):
        raise ValueError(
            f"Invalid skill name '{name}': must be lowercase letters, numbers, and hyphens only. "
            f"No leading/trailing/consecutive hyphens. Example: my-skill-name"
        )
    if '--' in name:
        raise ValueError(f"Invalid skill name '{name}': consecutive hyphens not allowed")
    if len(name) > 64:
        raise ValueError(f"Skill name too long ({len(name)} chars): max 64 characters")
    if name.startswith(('claude', 'anthropic')):
        raise ValueError(f"Skill name '{name}' uses reserved prefix (claude/anthropic)")
    return name


def build_frontmatter_extras(args) -> str:
    lines = []
    if args.argument_hint:
        lines.append(f'argument-hint: "{args.argument_hint}"')
    if args.disable_model_invocation:
        lines.append('disable-model-invocation: true')
    if args.context:
        lines.append(f'context: {args.context}')
    if args.agent:
        lines.append(f'agent: {args.agent}')
    if args.allowed_tools:
        lines.append(f'allowed-tools: {args.allowed_tools}')
    return ('\n'.join(lines) + '\n') if lines else ''


def scaffold(args):
    name = validate_name(args.name)
    output_base = Path(args.output).expanduser().resolve()
    skill_dir = output_base / name

    if skill_dir.exists():
        print(f"Error: directory already exists: {skill_dir}", file=sys.stderr)
        print(f"Delete it first or choose a different --output path.", file=sys.stderr)
        sys.exit(1)

    description = args.description or f"[FILL IN: what this skill does and when to use it — include trigger phrases]"
    title = name.replace('-', ' ').title()
    extra_fields = build_frontmatter_extras(args)
    scripts_section = SCRIPTS_SECTION if args.with_scripts else ''
    references_section = REFERENCES_SECTION if args.with_references else ''

    skill_md = SKILL_MD_TEMPLATE.format(
        name=name,
        title=title,
        description=description,
        extra_fields=extra_fields,
        scripts_section=scripts_section,
        references_section=references_section,
    )

    # Create directories
    skill_dir.mkdir(parents=True)
    created = [str(skill_dir)]

    if args.with_scripts:
        scripts_dir = skill_dir / 'scripts'
        scripts_dir.mkdir()
        script_file = scripts_dir / 'process.py'
        script_file.write_text(PLACEHOLDER_SCRIPT)
        created.append(str(script_file))

    if args.with_references:
        refs_dir = skill_dir / 'references'
        refs_dir.mkdir()
        ref_file = refs_dir / 'guide.md'
        ref_file.write_text(PLACEHOLDER_REFERENCE)
        created.append(str(ref_file))

    if args.with_assets:
        assets_dir = skill_dir / 'assets'
        assets_dir.mkdir()
        created.append(str(assets_dir) + '/')

    skill_md_path = skill_dir / 'SKILL.md'
    skill_md_path.write_text(skill_md)
    created.insert(1, str(skill_md_path))

    # Print result
    print(f"\nScaffolded skill: {name}")
    print(f"Location: {skill_dir}\n")
    print("Created:")
    for f in created:
        label = f.replace(str(skill_dir), name)
        print(f"  {label}")

    needs_description = not args.description
    print(f"\nNext steps:")
    if needs_description:
        print(f"  1. Open {name}/SKILL.md and fill in the description field")
        print(f"  2. Write your step-by-step instructions in the body")
    else:
        print(f"  1. Open {name}/SKILL.md and write your step-by-step instructions")
    if args.with_scripts:
        print(f"  {'3' if needs_description else '2'}. Implement logic in {name}/scripts/process.py")
    if args.with_references:
        step = (4 if needs_description else 3) if args.with_scripts else (3 if needs_description else 2)
        print(f"  {step}. Fill in {name}/references/guide.md")
    print(f"\nTest with: /skill-name  or ask Claude about a task that should trigger it.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new Agent Skill folder.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--name", required=True,
        help="Skill name in kebab-case (e.g. my-workflow). Must match folder name.")
    parser.add_argument("--output", required=True,
        help="Parent directory to create the skill in (e.g. ~/.claude/skills or .claude/skills)")
    parser.add_argument("--description", default=None,
        help="Description text for the frontmatter (what + when + trigger phrases). Max 1024 chars.")
    parser.add_argument("--disable-model-invocation", action="store_true",
        help="Add disable-model-invocation: true (user-only invocation, e.g. deploy, commit)")
    parser.add_argument("--with-scripts", action="store_true",
        help="Create scripts/ directory with a placeholder Python script")
    parser.add_argument("--with-references", action="store_true",
        help="Create references/ directory with a placeholder guide.md")
    parser.add_argument("--with-assets", action="store_true",
        help="Create assets/ directory for templates and static resources")
    parser.add_argument("--context", default=None, choices=["fork"],
        help="Set context: fork to run in an isolated subagent")
    parser.add_argument("--agent", default=None,
        help="Subagent type when context: fork (Explore, Plan, general-purpose)")
    parser.add_argument("--argument-hint", default=None,
        help="Autocomplete hint, e.g. '[issue-number]' or '[filename] [format]'")
    parser.add_argument("--allowed-tools", default=None,
        help="Space-delimited allowed tools, e.g. 'Read Grep Glob'")

    args = parser.parse_args()

    try:
        scaffold(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
