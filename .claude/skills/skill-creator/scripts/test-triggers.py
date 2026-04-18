#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Test whether a skill's description triggers correctly across a set of queries.

Runs each query through the `claude` CLI in headless mode and checks whether
the Skill tool was invoked for the target skill. Reports trigger rates for
should-trigger and should-not-trigger queries separately.

Reads trigger-queries.json from the skill's evals/ directory (or a custom path).

Usage:
    python3 scripts/test-triggers.py --skill <path>
    python3 scripts/test-triggers.py --skill <path> --runs 3
    python3 scripts/test-triggers.py --skill <path> --queries /path/to/queries.json
    python3 scripts/test-triggers.py --skill <path> --train-only
    python3 scripts/test-triggers.py --skill <path> --json

Exit codes:
    0  All should-trigger queries hit 100%, all should-not-trigger hit 0%
    1  One or more queries missed target (failures to investigate)
    2  claude CLI not found or other setup issue

Examples:
    python3 scripts/test-triggers.py --skill ~/.claude/skills/my-skill
    python3 scripts/test-triggers.py --skill .claude/skills/my-skill --runs 5 --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def find_claude_cli() -> str | None:
    """Find the claude CLI binary."""
    for candidate in ['claude', 'claude-code']:
        result = subprocess.run(
            ['which', candidate], capture_output=True, text=True
        )
        if result.returncode == 0:
            return candidate
    return None


def run_query(claude_bin: str, skill_name: str, query: str, skill_path: Path, timeout: int = 60) -> dict:
    """
    Run a single query through claude CLI and check if the skill was invoked.
    Returns: {triggered: bool, raw_output: str, error: str|None, duration_ms: int}
    """
    start = time.time()

    cmd = [
        claude_bin,
        '--print',                # non-interactive output
        '--output-format', 'json',
        '--add-dir', str(skill_path.parent),  # make skill available
        query,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        return {
            'triggered': False,
            'raw_output': '',
            'error': f'Timed out after {timeout}s',
            'duration_ms': int((time.time() - start) * 1000),
        }
    except FileNotFoundError:
        return {
            'triggered': False,
            'raw_output': '',
            'error': f'claude CLI not found: {claude_bin}',
            'duration_ms': 0,
        }

    duration_ms = int((time.time() - start) * 1000)
    raw = result.stdout

    triggered = False
    try:
        data = json.loads(raw)
        # Claude Code --output-format json returns a list of messages or a single object
        # Check for Skill tool_use invocations in the message content
        triggered = _check_skill_invoked(data, skill_name)
    except (json.JSONDecodeError, KeyError, TypeError):
        # Fall back to regex scan of raw output
        triggered = _check_skill_invoked_raw(raw, skill_name)

    return {
        'triggered': triggered,
        'raw_output': raw[:2000],  # cap to avoid huge output
        'error': result.stderr[:500] if result.returncode != 0 else None,
        'duration_ms': duration_ms,
    }


def _check_skill_invoked(data, skill_name: str) -> bool:
    """Parse claude JSON output and look for Skill tool_use for skill_name."""
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = [data]
    else:
        return False

    for item in items:
        if not isinstance(item, dict):
            continue
        # Top-level tool_use
        if item.get('type') == 'tool_use' and item.get('name') == 'Skill':
            inp = item.get('input', {})
            if isinstance(inp, dict) and inp.get('skill') == skill_name:
                return True
        # Nested in messages[].content[]
        for msg in item.get('messages', []):
            if not isinstance(msg, dict):
                continue
            for block in msg.get('content', []) if isinstance(msg.get('content'), list) else []:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use' and block.get('name') == 'Skill':
                    inp = block.get('input', {})
                    if isinstance(inp, dict) and inp.get('skill') == skill_name:
                        return True
    return False


def _check_skill_invoked_raw(raw: str, skill_name: str) -> bool:
    """Fallback: regex scan raw text for skill invocation evidence."""
    # Look for patterns like: "skill": "skill-name" or skill=skill-name
    patterns = [
        rf'"skill"\s*:\s*"{re.escape(skill_name)}"',
        rf"'skill'\s*:\s*'{re.escape(skill_name)}'",
        rf'Skill\b.*\b{re.escape(skill_name)}\b',
    ]
    for pattern in patterns:
        if re.search(pattern, raw, re.IGNORECASE):
            return True
    return False


def run_query_n_times(claude_bin: str, skill_name: str, query: str, skill_path: Path,
                      runs: int, timeout: int) -> list[dict]:
    results = []
    for i in range(runs):
        r = run_query(claude_bin, skill_name, query, skill_path, timeout)
        results.append(r)
        if r.get('error') and 'not found' in (r['error'] or ''):
            break  # fatal error, no point retrying
    return results


def load_queries(skill_path: Path, custom_path: str | None = None) -> list[dict]:
    if custom_path:
        p = Path(custom_path).expanduser().resolve()
    else:
        p = skill_path / 'evals' / 'trigger-queries.json'

    if not p.exists():
        print(f"Error: trigger-queries.json not found at {p}", file=sys.stderr)
        print(f"Run first: python3 scripts/init-evals.py --skill {skill_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(p.read_text())
    queries = data.get('queries', [])

    # Filter out REPLACE placeholders
    real_queries = [q for q in queries if 'REPLACE' not in q.get('query', '')]
    if not real_queries:
        print(f"Error: no real queries found in {p}", file=sys.stderr)
        print("Fill in the trigger-queries.json placeholders first.", file=sys.stderr)
        sys.exit(1)

    return real_queries


def split_train_val(queries: list[dict], train_fraction: float = 0.6) -> tuple[list, list]:
    """Split into train (60%) and validation (40%) sets, preserving should/shouldn't balance."""
    should = [q for q in queries if q.get('should_trigger')]
    shouldnt = [q for q in queries if not q.get('should_trigger')]

    def split(lst):
        n_train = max(1, round(len(lst) * train_fraction))
        return lst[:n_train], lst[n_train:]

    tr_s, val_s = split(should)
    tr_n, val_n = split(shouldnt)
    return tr_s + tr_n, val_s + val_n


def compute_trigger_rate(results: list[dict]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r['triggered']) / len(results)


def main():
    parser = argparse.ArgumentParser(
        description="Test skill description triggering across a query set.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skill", required=True,
        help="Path to the skill directory")
    parser.add_argument("--runs", type=int, default=3,
        help="Number of times to run each query (accounts for nondeterminism). Default: 3")
    parser.add_argument("--queries", default=None,
        help="Path to a custom trigger-queries.json (default: <skill>/evals/trigger-queries.json)")
    parser.add_argument("--train-only", action="store_true",
        help="Only test the training set (60%% of queries), reserve validation set")
    parser.add_argument("--timeout", type=int, default=60,
        help="Timeout per claude call in seconds. Default: 60")
    parser.add_argument("--json", action="store_true", dest="json_output",
        help="Output results as JSON")
    parser.add_argument("--save", action="store_true",
        help="Save results to evals/trigger-results.json")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    if not skill_path.exists():
        print(f"Error: skill not found: {skill_path}", file=sys.stderr)
        sys.exit(2)

    # Read skill name
    skill_name = skill_path.name
    skill_md = skill_path / 'SKILL.md'
    if skill_md.exists():
        for line in skill_md.read_text().splitlines():
            if line.startswith('name:'):
                skill_name = line.split(':', 1)[1].strip().strip('"\'')
                break

    # Find claude CLI
    claude_bin = find_claude_cli()
    if not claude_bin:
        print("Error: 'claude' CLI not found in PATH.", file=sys.stderr)
        print("Install Claude Code: https://claude.ai/code", file=sys.stderr)
        sys.exit(2)

    # Load queries
    queries = load_queries(skill_path, args.queries)
    train_set, val_set = split_train_val(queries)
    test_set = train_set if args.train_only else queries

    print(f"\nTesting triggers for: {skill_name}")
    print(f"Skill path: {skill_path}")
    print(f"Queries: {len(test_set)} ({'train set only' if args.train_only else 'full set'})")
    print(f"Runs per query: {args.runs}")
    print()

    all_results = []
    failures = []

    should_trigger_queries = [q for q in test_set if q.get('should_trigger')]
    should_not_queries = [q for q in test_set if not q.get('should_trigger')]

    for q in test_set:
        qid = q.get('id', '?')
        query_text = q['query']
        expected = q.get('should_trigger', True)
        label = "SHOULD trigger" if expected else "should NOT trigger"

        if not args.json_output:
            print(f"  [{qid}] {label}")
            print(f"       Query: {query_text[:80]}{'...' if len(query_text) > 80 else ''}")

        run_results = run_query_n_times(claude_bin, skill_name, query_text, skill_path,
                                        args.runs, args.timeout)

        trigger_rate = compute_trigger_rate(run_results)
        triggered_count = sum(1 for r in run_results if r['triggered'])
        errors = [r['error'] for r in run_results if r.get('error')]

        passed = (expected and trigger_rate >= 0.6) or (not expected and trigger_rate <= 0.4)

        result_entry = {
            'id': qid,
            'query': query_text,
            'should_trigger': expected,
            'trigger_rate': round(trigger_rate, 2),
            'triggered_count': triggered_count,
            'runs': args.runs,
            'passed': passed,
            'errors': errors[:1] if errors else [],
            'in_train_set': q in train_set,
        }
        all_results.append(result_entry)

        if not passed:
            failures.append(result_entry)

        if not args.json_output:
            status = "PASS" if passed else "FAIL"
            print(f"       Triggered {triggered_count}/{args.runs} ({trigger_rate:.0%}) → {status}")
            if errors:
                print(f"       Error: {errors[0][:100]}")
            print()

    # Summary
    n_pass = sum(1 for r in all_results if r['passed'])
    n_fail = len(failures)

    if args.train_only and val_set:
        val_note = f" [{len(val_set)} validation queries reserved — run without --train-only when done optimizing]"
    else:
        val_note = ""

    should_rates = [r['trigger_rate'] for r in all_results if r['should_trigger']]
    shouldnt_rates = [r['trigger_rate'] for r in all_results if not r['should_trigger']]

    avg_should = sum(should_rates) / len(should_rates) if should_rates else 0
    avg_shouldnt = sum(shouldnt_rates) / len(shouldnt_rates) if shouldnt_rates else 0

    output = {
        'skill': skill_name,
        'summary': {
            'total_queries': len(all_results),
            'passed': n_pass,
            'failed': n_fail,
            'should_trigger_avg_rate': round(avg_should, 2),
            'should_not_trigger_avg_rate': round(avg_shouldnt, 2),
        },
        'results': all_results,
        'failures': failures,
    }

    if args.save:
        out_path = skill_path / 'evals' / 'trigger-results.json'
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2))
        if not args.json_output:
            print(f"Results saved to: {out_path}")

    if args.json_output:
        print(json.dumps(output, indent=2))
        sys.exit(0 if n_fail == 0 else 1)

    # Text summary
    print(f"{'─' * 50}")
    print(f"Should trigger avg:      {avg_should:.0%} (target: ≥80%)")
    print(f"Should NOT trigger avg:  {avg_shouldnt:.0%} (target: ≤20%)")
    print(f"Passed: {n_pass}/{len(all_results)}{val_note}")
    print()

    if failures:
        print("Failures to investigate:")
        for f in failures:
            direction = "should trigger but didn't" if f['should_trigger'] else "triggered when it shouldn't"
            print(f"  [{f['id']}] {direction} ({f['trigger_rate']:.0%} rate): {f['query'][:70]}")
        print()
        print("Fix: Revise the description field in SKILL.md.")
        print("  - Under-triggering: broaden scope, add paraphrases, be more explicit about when to use")
        print("  - Over-triggering:  add negative scope ('Do NOT use for X'), be more specific")
        print()
        sys.exit(1)
    else:
        print("All queries passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()