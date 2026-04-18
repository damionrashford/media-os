#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Validate an Agent Skill against the spec requirements.

Usage:
    python3 scripts/validate.py <skill-path>
    python3 scripts/validate.py <skill-path> --json
    python3 scripts/validate.py <skill-path> --fix

Examples:
    python3 scripts/validate.py ~/.claude/skills/my-skill
    python3 scripts/validate.py .claude/skills/my-skill --json
    python3 scripts/validate.py .claude/skills/my-skill --fix

Exit codes:
    0  All checks passed
    1  One or more checks failed (errors)
    2  Warnings only (no errors)
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ── ANSI colours (disabled when not a TTY) ──────────────────────────────────

def _supports_colour():
    return sys.stdout.isatty()

PASS  = "\033[32m✓\033[0m" if _supports_colour() else "PASS"
FAIL  = "\033[31m✗\033[0m" if _supports_colour() else "FAIL"
WARN  = "\033[33m!\033[0m" if _supports_colour() else "WARN"
BOLD  = "\033[1m"          if _supports_colour() else ""
RESET = "\033[0m"          if _supports_colour() else ""


# ── YAML frontmatter parser (no external deps) ──────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str, str]:
    """
    Returns (fields, body, error_message).
    fields is empty dict if parsing failed.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != '---':
        return {}, text, "File does not start with '---' frontmatter delimiter"

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return {}, text, "Frontmatter opening '---' has no closing '---'"

    fm_lines = lines[1:end_idx]
    body = ''.join(lines[end_idx + 1:])

    fields = {}
    current_key = None
    current_val_lines = []
    indent_level = 0

    def flush():
        if current_key is not None:
            val = '\n'.join(current_val_lines).strip()
            fields[current_key] = val

    for line in fm_lines:
        stripped = line.rstrip()
        if not stripped or stripped.startswith('#'):
            continue

        leading = len(line) - len(line.lstrip())

        if leading == 0:
            flush()
            current_val_lines = []
            if ':' in stripped:
                key, _, rest = stripped.partition(':')
                current_key = key.strip()
                val = rest.strip()
                if val and not val.startswith('|') and not val.startswith('>'):
                    # strip surrounding quotes
                    if (val.startswith('"') and val.endswith('"')) or \
                       (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    current_val_lines = [val]
                else:
                    current_val_lines = []
                indent_level = 0
        else:
            current_val_lines.append(stripped.strip())

    flush()
    return fields, body, ""


# ── Checks ───────────────────────────────────────────────────────────────────

class Result:
    def __init__(self, level: str, check: str, message: str, fix: str = ""):
        self.level = level   # "error" | "warn" | "pass"
        self.check = check
        self.message = message
        self.fix = fix

    def icon(self):
        return {
            "error": FAIL,
            "warn":  WARN,
            "pass":  PASS,
        }[self.level]


def check_skill(skill_path: Path) -> list[Result]:
    results = []

    def ok(check, msg):
        results.append(Result("pass", check, msg))

    def err(check, msg, fix=""):
        results.append(Result("error", check, msg, fix))

    def warn(check, msg, fix=""):
        results.append(Result("warn", check, msg, fix))

    # ── Directory structure ──────────────────────────────────────────────────

    if not skill_path.exists():
        err("path-exists", f"Path does not exist: {skill_path}")
        return results

    if not skill_path.is_dir():
        err("is-directory", f"Skill path must be a directory, got a file: {skill_path}")
        return results

    ok("is-directory", "Skill path is a directory")

    # ── SKILL.md exists ──────────────────────────────────────────────────────

    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        err("skill-md-exists", "SKILL.md not found in skill directory",
            fix="Create SKILL.md (case-sensitive) at the root of the skill folder")
        # Look for common mistakes
        for variant in ['skill.md', 'SKILL.MD', 'Skill.md', 'skill.MD']:
            if (skill_path / variant).exists():
                err("skill-md-case", f"Found '{variant}' — must be named exactly 'SKILL.md' (case-sensitive)",
                    fix=f"Rename: mv {variant} SKILL.md")
        return results

    ok("skill-md-exists", "SKILL.md found")

    # ── README.md forbidden ──────────────────────────────────────────────────

    if (skill_path / 'README.md').exists():
        warn("no-readme", "README.md found inside skill folder — this is not allowed by the spec",
             fix="Remove README.md. All documentation belongs in SKILL.md or references/")

    # ── Parse frontmatter ────────────────────────────────────────────────────

    text = skill_md.read_text(encoding='utf-8')
    fields, body, parse_err = parse_frontmatter(text)

    if parse_err:
        err("frontmatter-parse", f"Could not parse frontmatter: {parse_err}",
            fix="Ensure the file starts with '---', has valid YAML, and ends the frontmatter block with '---'")
        return results

    ok("frontmatter-parse", "Frontmatter parsed successfully")

    # ── name field ───────────────────────────────────────────────────────────

    folder_name = skill_path.name

    if 'name' not in fields or not fields['name']:
        err("name-required", "Missing required 'name' field in frontmatter",
            fix="Add: name: your-skill-name")
    else:
        name = fields['name']

        if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', name) and not re.match(r'^[a-z0-9]$', name):
            err("name-format", f"name '{name}' is invalid: use only lowercase letters, numbers, hyphens. No leading/trailing/consecutive hyphens.",
                fix=f"Change name to: {re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')}")
        elif '--' in name:
            err("name-no-consecutive-hyphens", f"name '{name}' has consecutive hyphens",
                fix=f"Change to: {re.sub(r'-+', '-', name)}")
        elif len(name) > 64:
            err("name-length", f"name is {len(name)} characters (max 64)",
                fix="Shorten the name field")
        elif name.startswith(('claude', 'anthropic')):
            err("name-reserved", f"name '{name}' uses reserved prefix (claude/anthropic)",
                fix="Choose a different name that doesn't start with 'claude' or 'anthropic'")
        else:
            ok("name-format", f"name '{name}' is valid")

        if name != folder_name:
            warn("name-matches-folder",
                 f"name field '{name}' does not match folder name '{folder_name}'",
                 fix=f"Either rename the folder to '{name}' or change name to '{folder_name}'")
        else:
            ok("name-matches-folder", f"name matches folder name '{folder_name}'")

    # ── description field ────────────────────────────────────────────────────

    if 'description' not in fields or not fields['description']:
        err("description-required", "Missing required 'description' field in frontmatter",
            fix="Add a description that includes WHAT the skill does and WHEN to use it (trigger phrases)")
    else:
        desc = fields['description']
        desc_len = len(desc)

        if desc_len > 1024:
            err("description-length", f"description is {desc_len} characters (max 1024)",
                fix=f"Shorten by {desc_len - 1024} characters")
        else:
            ok("description-length", f"description length OK ({desc_len}/1024 chars)")

        if desc_len < 20:
            warn("description-too-short", f"description is very short ({desc_len} chars) — likely missing trigger phrases",
                 fix="Add 'Use when...' with specific phrases users would actually type")

        if '<' in desc or '>' in desc:
            err("description-no-xml", "description contains XML angle brackets (< >) — forbidden in frontmatter",
                fix="Remove all < and > characters from the description")

        trigger_words = ['use when', 'use for', 'trigger', 'when user', 'when the user', 'when asked']
        has_trigger = any(t in desc.lower() for t in trigger_words)
        if not has_trigger:
            warn("description-has-trigger", "description may be missing 'Use when...' trigger guidance",
                 fix="Add 'Use when the user asks to X, Y, or Z' to help Claude decide when to load this skill")
        else:
            ok("description-has-trigger", "description includes trigger guidance")

        if desc_len > 250:
            warn("description-display-truncation",
                 f"description is {desc_len} chars — only the first 250 are shown in the skill listing. Front-load the key use case.",
                 fix="Move the most important trigger phrases to the first 250 characters")

    # ── XML in frontmatter ───────────────────────────────────────────────────

    fm_text = text.split('---', 2)[1] if '---' in text else ''
    # Check for actual XML tags (e.g. <tag>, </tag>) — not YAML block scalars (description: >)
    if re.search(r'<[a-zA-Z/!?]', fm_text):
        err("no-xml-in-frontmatter", "XML tags found in frontmatter — forbidden (security restriction)",
            fix="Remove all XML tags (< >) from frontmatter fields. Use plain text only.")

    # ── Body content ─────────────────────────────────────────────────────────

    body_lines = body.strip().splitlines()
    body_line_count = len(body_lines)

    if body_line_count == 0:
        warn("body-not-empty", "SKILL.md body is empty — no instructions for Claude to follow",
             fix="Add step-by-step instructions after the frontmatter closing '---'")
    elif body_line_count > 500:
        warn("body-size", f"SKILL.md body is {body_line_count} lines (recommended max: 500)",
             fix="Move detailed reference material to references/ and link to it from SKILL.md")
    else:
        ok("body-size", f"body length OK ({body_line_count} lines)")

    # ── Scripts: no interactive prompts ──────────────────────────────────────

    scripts_dir = skill_path / 'scripts'
    if scripts_dir.exists():
        ok("scripts-dir", f"scripts/ directory found")
        for script in scripts_dir.iterdir():
            if script.is_file() and script.suffix in ('.py', '.sh', '.rb', '.ts', '.js'):
                content = script.read_text(encoding='utf-8', errors='replace')
                # Look for interactive prompt calls (Python input fn, bash read -p)
                _ip = 'input'
                if re.search(rf'\b{_ip}\s*\(', content) and script.suffix == '.py':
                    warn(f"script-no-interactive-{script.name}",
                         f"{script.name}: uses the '{_ip}' function for prompts — agents cannot respond (they run non-interactive)",
                         fix=f"Replace {_ip}() with argparse flags, env vars, or stdin")
                if re.search(r'\bread -p\b', content) and script.suffix == '.sh':
                    warn(f"script-no-interactive-{script.name}",
                         f"{script.name}: contains 'read -p' — agents cannot respond to interactive prompts",
                         fix="Replace with command-line flags")

    # ── References dir ───────────────────────────────────────────────────────

    refs_dir = skill_path / 'references'
    if refs_dir.exists():
        ok("references-dir", "references/ directory found")
        ref_files = list(refs_dir.glob('*.md'))
        if not ref_files:
            warn("references-not-empty", "references/ exists but contains no .md files")

    return results


# ── Formatting ───────────────────────────────────────────────────────────────

def print_report(skill_path: Path, results: list[Result]) -> tuple[int, int]:
    errors = [r for r in results if r.level == "error"]
    warnings = [r for r in results if r.level == "warn"]
    passes = [r for r in results if r.level == "pass"]

    print(f"\n{BOLD}Skill validation: {skill_path.name}{RESET}")
    print(f"Path: {skill_path}\n")

    for r in results:
        print(f"  {r.icon()}  {r.message}")
        if r.fix and r.level != "pass":
            print(f"       Fix: {r.fix}")

    print()
    if errors:
        print(f"{FAIL}  {len(errors)} error(s)  |  {len(warnings)} warning(s)  |  {len(passes)} passed")
    elif warnings:
        print(f"{WARN}  0 errors  |  {len(warnings)} warning(s)  |  {len(passes)} passed")
    else:
        print(f"{PASS}  All {len(passes)} checks passed")
    print()

    return len(errors), len(warnings)


def print_json_report(skill_path: Path, results: list[Result]):
    output = {
        "skill": skill_path.name,
        "path": str(skill_path),
        "summary": {
            "errors": sum(1 for r in results if r.level == "error"),
            "warnings": sum(1 for r in results if r.level == "warn"),
            "passed": sum(1 for r in results if r.level == "pass"),
        },
        "checks": [
            {
                "level": r.level,
                "check": r.check,
                "message": r.message,
                "fix": r.fix,
            }
            for r in results
        ]
    }
    print(json.dumps(output, indent=2))


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Validate an Agent Skill against the spec.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("skill_path",
        help="Path to the skill directory (e.g. ~/.claude/skills/my-skill)")
    parser.add_argument("--json", action="store_true",
        help="Output results as JSON")
    parser.add_argument("--fix", action="store_true",
        help="Show fix instructions for each issue (default: always shown)")

    args = parser.parse_args()

    skill_path = Path(args.skill_path).expanduser().resolve()
    results = check_skill(skill_path)

    if args.json:
        print_json_report(skill_path, results)
        errors = sum(1 for r in results if r.level == "error")
        sys.exit(0 if errors == 0 else 1)
    else:
        errors, warnings = print_report(skill_path, results)
        if errors > 0:
            sys.exit(1)
        elif warnings > 0:
            sys.exit(2)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()