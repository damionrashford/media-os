#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Scaffold an evals/ directory inside a skill for trigger and output testing.

Creates:
  evals/evals.json          — functional eval cases (prompts + assertions)
  evals/trigger-queries.json — trigger-only test queries (no Claude output needed)
  evals/files/              — directory for input files referenced in evals

Usage:
    python3 scripts/init-evals.py --skill <path-to-skill>
    python3 scripts/init-evals.py --skill ~/.claude/skills/my-skill

Examples:
    python3 scripts/init-evals.py --skill .claude/skills/data-reporter
    python3 scripts/init-evals.py --skill ~/.claude/skills/my-workflow --force
"""

import argparse
import json
import sys
from pathlib import Path


EVALS_JSON_TEMPLATE = {
    "skill_name": "SKILL_NAME",
    "_instructions": [
        "Add 2-5 realistic eval cases. Each case runs the skill and checks the output.",
        "prompts: what a real user would type (vary phrasing, detail, formality)",
        "expected_output: human-readable description of what success looks like",
        "assertions: verifiable statements about the output (specific, observable, countable)",
        "files: input files in evals/files/ that the eval needs (optional)",
        "Run with: python3 scripts/run-eval.py --skill <path> --eval-id 1 [--no-skill]",
        "Grade with: python3 scripts/grade.py --skill <path> --iteration 1"
    ],
    "evals": [
        {
            "id": 1,
            "prompt": "REPLACE: a realistic user prompt. Include file paths, column names, context.",
            "expected_output": "REPLACE: what a successful output looks like (1-2 sentences).",
            "files": [],
            "assertions": [
                "REPLACE: specific verifiable claim (e.g. 'Output file is valid JSON')",
                "REPLACE: another assertion (e.g. 'Report includes at least 3 recommendations')",
                "REPLACE: format assertion (e.g. 'Chart has labeled axes')"
            ]
        },
        {
            "id": 2,
            "prompt": "REPLACE: a paraphrased or edge-case version of a common request.",
            "expected_output": "REPLACE: what success looks like for this variant.",
            "files": [],
            "assertions": [
                "REPLACE: assertion 1",
                "REPLACE: assertion 2"
            ]
        }
    ]
}

TRIGGER_QUERIES_TEMPLATE = {
    "skill_name": "SKILL_NAME",
    "_instructions": [
        "should_trigger: true  = this query SHOULD load the skill automatically",
        "should_trigger: false = this query should NOT load the skill (near-miss)",
        "Aim for 8-10 should-trigger and 8-10 should-not-trigger queries.",
        "should-trigger: vary phrasing (formal/casual/typos), explicitness, detail, complexity",
        "should-NOT-trigger: use near-misses — queries sharing keywords but needing something else",
        "Run with: python3 scripts/test-triggers.py --skill <path> [--runs 3]"
    ],
    "queries": [
        {
            "id": 1,
            "query": "REPLACE: a request that obviously matches this skill — use the exact domain words",
            "should_trigger": True
        },
        {
            "id": 2,
            "query": "REPLACE: same task phrased casually, with abbreviations or a typo",
            "should_trigger": True
        },
        {
            "id": 3,
            "query": "REPLACE: task described without using the domain name (paraphrase)",
            "should_trigger": True
        },
        {
            "id": 4,
            "query": "REPLACE: same task but very terse — just the file path or one-word request",
            "should_trigger": True
        },
        {
            "id": 5,
            "query": "REPLACE: complex multi-step request clearly in this skill's domain",
            "should_trigger": True
        },
        {
            "id": 6,
            "query": "REPLACE: near-miss — shares a keyword but actually needs something different",
            "should_trigger": False
        },
        {
            "id": 7,
            "query": "REPLACE: near-miss — same file type but different task (e.g. edit not analyze)",
            "should_trigger": False
        },
        {
            "id": 8,
            "query": "REPLACE: near-miss — adjacent domain (e.g. related API but different workflow)",
            "should_trigger": False
        },
        {
            "id": 9,
            "query": "REPLACE: clearly unrelated request in a completely different domain",
            "should_trigger": False
        }
    ]
}


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold evals/ directory in a skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skill", required=True,
        help="Path to the skill directory (e.g. .claude/skills/my-skill)")
    parser.add_argument("--force", action="store_true",
        help="Overwrite existing evals/ directory")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()

    if not skill_path.exists():
        print(f"Error: skill directory not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    skill_md = skill_path / 'SKILL.md'
    if not skill_md.exists():
        print(f"Error: no SKILL.md found at {skill_path} — is this a skill directory?", file=sys.stderr)
        sys.exit(1)

    evals_dir = skill_path / 'evals'
    if evals_dir.exists() and not args.force:
        print(f"Error: evals/ already exists at {evals_dir}", file=sys.stderr)
        print(f"Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    # Read skill name from SKILL.md frontmatter
    skill_name = skill_path.name
    text = skill_md.read_text()
    for line in text.splitlines():
        if line.startswith('name:'):
            skill_name = line.split(':', 1)[1].strip().strip('"\'')
            break

    # Populate templates with skill name
    evals = json.loads(json.dumps(EVALS_JSON_TEMPLATE))
    evals['skill_name'] = skill_name

    triggers = json.loads(json.dumps(TRIGGER_QUERIES_TEMPLATE))
    triggers['skill_name'] = skill_name

    # Create directories
    evals_dir.mkdir(exist_ok=True)
    (evals_dir / 'files').mkdir(exist_ok=True)

    evals_json = evals_dir / 'evals.json'
    triggers_json = evals_dir / 'trigger-queries.json'

    evals_json.write_text(json.dumps(evals, indent=2))
    triggers_json.write_text(json.dumps(triggers, indent=2))

    print(f"\nInitialized evals for: {skill_name}")
    print(f"Location: {evals_dir}\n")
    print("Created:")
    print(f"  evals/evals.json           — functional eval cases (fill in prompts + assertions)")
    print(f"  evals/trigger-queries.json — trigger test queries (fill in should/shouldn't trigger)")
    print(f"  evals/files/               — put input files here that evals reference\n")
    print("Next steps:")
    print(f"  1. Edit evals/trigger-queries.json — replace REPLACE placeholders with real queries")
    print(f"  2. Run trigger tests:  python3 scripts/test-triggers.py --skill {skill_path}")
    print(f"  3. Edit evals/evals.json — replace REPLACE placeholders with real prompts + assertions")
    print(f"  4. Run evals:          python3 scripts/run-eval.py --skill {skill_path} --eval-id 1")
    print(f"  5. Grade results:      python3 scripts/grade.py --skill {skill_path} --iteration 1\n")


if __name__ == "__main__":
    main()