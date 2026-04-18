#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Autonomous skill evolution loop — inspired by karpathy/autoresearch.

Give it a skill with evals and let it run overnight. Each iteration:
  1. Asks Claude to propose ONE targeted SKILL.md improvement
  2. Applies the change
  3. Scores it against evals
  4. Keeps if score improved, reverts if not
  5. Repeats

You wake up to a log of experiments and (hopefully) a better skill.

Usage:
    uv run scripts/autoevolve.py --skill <path> [--iterations 20] [--timeout 120]
    uv run scripts/autoevolve.py --skill .claude/skills/my-skill --iterations 50

Prerequisites:
    - evals/evals.json must exist with real eval cases (run init-evals.py first)
    - Assertions in evals.json drive scoring — more specific assertions = better signal

Output:
    <skill>/evals/autoevolve/run-<timestamp>/
    ├── log.jsonl          — one JSON line per iteration (keep/revert/skip + scores)
    ├── best-skill.md      — highest-scoring SKILL.md seen during the run
    └── iteration-N/
        ├── snapshot.md    — SKILL.md at start of this iteration
        ├── proposal.md    — what Claude proposed
        ├── diff.txt       — line diff from previous
        └── score.json     — prev_score, new_score, delta, kept, assertion details

SKILL.md is updated in-place to the best version found at the end of the run.

Exit codes:
    0  Completed (even if no improvements found)
    1  Fatal error (no evals, claude not found, bad skill path)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Claude CLI helpers
# ---------------------------------------------------------------------------

def find_claude_cli() -> str | None:
    for candidate in ['claude', 'claude-code']:
        result = subprocess.run(['which', candidate], capture_output=True, text=True)
        if result.returncode == 0:
            return candidate
    return None


def _extract_text_from_stream(raw: str) -> str:
    """Extract text content from claude --output-format stream-json output."""
    lines = raw.strip().splitlines()
    parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get('type') == 'content_block_delta':
                delta = obj.get('delta', {})
                if delta.get('type') == 'text_delta':
                    parts.append(delta.get('text', ''))
            elif obj.get('type') == 'message':
                for block in obj.get('content', []):
                    if isinstance(block, dict) and block.get('type') == 'text':
                        parts.append(block.get('text', ''))
            elif 'result' in obj:
                parts.append(str(obj['result']))
        except (json.JSONDecodeError, KeyError, TypeError):
            if not line.startswith('{') and not line.startswith('['):
                parts.append(line)
    return ''.join(parts) or raw


def call_claude(
    claude_bin: str,
    prompt: str,
    timeout: int,
    skill_dir: Path | None = None,
) -> tuple[str, bool]:
    """
    Call claude CLI. Returns (text_output, success).
    If skill_dir is given, loads the skill via --add-dir.
    """
    cmd = [claude_bin, '--print', '--output-format', 'stream-json']
    if skill_dir is not None:
        cmd += ['--add-dir', str(skill_dir.parent)]
    cmd.append(prompt)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        text = _extract_text_from_stream(result.stdout)
        return text, result.returncode == 0
    except subprocess.TimeoutExpired:
        return '[TIMEOUT]', False
    except FileNotFoundError:
        return '[CLAUDE_NOT_FOUND]', False


# ---------------------------------------------------------------------------
# Auto-grading
# ---------------------------------------------------------------------------

def grade_assertion(output: str, assertion: str, claude_bin: str, timeout: int) -> bool:
    """
    Grade a single assertion against output. Returns True if passed.

    Assertion formats:
      contains: <value>       — output must contain value (case-insensitive)
      not_contains: <value>   — output must NOT contain value
      anything else           — sent to Claude as a natural-language rubric
    """
    lower = assertion.lower()

    if lower.startswith('contains:'):
        value = assertion[9:].strip().strip('"\'')
        return value.lower() in output.lower()

    if lower.startswith('not_contains:'):
        value = assertion[13:].strip().strip('"\'')
        return value.lower() not in output.lower()

    # LLM-based grading
    prompt = (
        "You are grading an AI output against a single assertion.\n\n"
        f"OUTPUT (first 2000 chars):\n{output[:2000]}\n\n"
        f"ASSERTION: {assertion}\n\n"
        "Does the output satisfy this assertion?\n"
        "Reply with exactly one word on the first line: PASS or FAIL"
    )
    response, _ = call_claude(claude_bin, prompt, timeout)
    first_word = response.strip().split()[0].upper() if response.strip() else 'FAIL'
    return first_word == 'PASS'


def score_skill(
    skill_path: Path,
    claude_bin: str,
    timeout: int,
    run_dir: Path,
    iteration: int,
) -> dict:
    """
    Run all evals using the current SKILL.md on disk. Returns score dict.

    SKILL.md is loaded via --add-dir (same mechanism as real usage).
    """
    evals_json = skill_path / 'evals' / 'evals.json'

    if not evals_json.exists():
        return {
            'error': 'no evals.json — run init-evals.py first',
            'eval_score': None,
            'combined': 0.0,
            'details': [],
            'total': 0,
            'passed': 0,
        }

    data = json.loads(evals_json.read_text())
    evals = [e for e in data.get('evals', []) if 'REPLACE' not in e.get('prompt', '')]

    if not evals:
        return {
            'error': 'no real eval cases — fill in REPLACE placeholders in evals.json',
            'eval_score': None,
            'combined': 0.0,
            'details': [],
            'total': 0,
            'passed': 0,
        }

    iter_dir = run_dir / f'iteration-{iteration}'
    iter_dir.mkdir(parents=True, exist_ok=True)

    total_assertions = 0
    passed_assertions = 0
    details = []

    for case in evals:
        eid = case['id']
        prompt = case['prompt']
        assertions = [a for a in case.get('assertions', []) if 'REPLACE' not in a]

        eval_dir = iter_dir / f'eval-{eid}'
        eval_dir.mkdir(exist_ok=True)

        # Run the eval with the skill loaded
        output, success = call_claude(
            claude_bin, prompt, timeout, skill_dir=skill_path
        )
        (eval_dir / 'output.txt').write_text(output)

        # Grade each assertion
        case_results = []
        for assertion in assertions:
            passed = grade_assertion(output, assertion, claude_bin, timeout)
            case_results.append({'assertion': assertion, 'passed': passed})
            total_assertions += 1
            if passed:
                passed_assertions += 1

        case_score = (
            sum(r['passed'] for r in case_results) / len(case_results)
            if case_results else None
        )
        details.append({'eval_id': eid, 'assertions': case_results, 'score': case_score})
        (eval_dir / 'grading.json').write_text(
            json.dumps({'eval_id': eid, 'assertions': case_results, 'score': case_score}, indent=2)
        )

    eval_score = passed_assertions / total_assertions if total_assertions > 0 else 0.0

    return {
        'eval_score': eval_score,
        'combined': eval_score,
        'details': details,
        'total': total_assertions,
        'passed': passed_assertions,
    }


# ---------------------------------------------------------------------------
# Improvement proposal
# ---------------------------------------------------------------------------

def propose_improvement(
    current_skill_md: str,
    score: dict,
    claude_bin: str,
    timeout: int,
) -> str | None:
    """
    Ask Claude to propose ONE targeted SKILL.md improvement.
    Returns the new SKILL.md content, or None if extraction failed.
    """
    # Summarize failures for context
    failure_lines = []
    for case in score.get('details', []):
        for a in case.get('assertions', []):
            if not a['passed']:
                failure_lines.append(f"  Eval {case['eval_id']}: FAILED — {a['assertion']}")

    failures_text = (
        '\n'.join(failure_lines)
        if failure_lines
        else '  (all assertions passed — propose a clarity or coverage improvement)'
    )

    line_count = len(current_skill_md.splitlines())

    prompt = (
        "You are improving a Claude Code skill (SKILL.md).\n\n"
        f"CURRENT SKILL.MD ({line_count} lines):\n"
        "```\n"
        f"{current_skill_md}\n"
        "```\n\n"
        f"CURRENT SCORE: {score.get('eval_score', 0):.1%} "
        f"({score.get('passed', 0)}/{score.get('total', 0)} assertions passing)\n\n"
        "FAILING ASSERTIONS:\n"
        f"{failures_text}\n\n"
        "Your task: propose exactly ONE targeted change that addresses the most failures.\n\n"
        "Rules:\n"
        "- Keep total lines under 500\n"
        "- Do not remove content that helps passing assertions\n"
        "- Make the minimum effective change (add a gotcha, fix an instruction, "
        "clarify a step, add an example — not a full rewrite)\n"
        "- Preserve the YAML frontmatter exactly\n\n"
        "Output ONLY the complete modified SKILL.md wrapped in triple backticks:\n"
        "```\n"
        "<full modified SKILL.md here>\n"
        "```"
    )

    # Give the proposal step extra time — it needs to read and rewrite SKILL.md
    response, _ = call_claude(claude_bin, prompt, timeout * 4)

    # Extract SKILL.md content from the response
    # Try fenced blocks first, preferring ones that contain frontmatter
    patterns = [
        r'```(?:markdown|md)?\n(---[\s\S]+?)\n```',
        r'```\n(---[\s\S]+?)\n```',
        r'```([\s\S]+?)```',
    ]
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if candidate.startswith('---'):
                return candidate

    # Last resort: response itself is a SKILL.md
    stripped = response.strip()
    if stripped.startswith('---'):
        return stripped

    return None


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------

def make_diff(old: str, new: str) -> str:
    """Simple line-level diff showing what was added and removed."""
    old_set = set(old.splitlines())
    new_set = set(new.splitlines())
    removed = old_set - new_set
    added = new_set - old_set

    lines = (
        [f'- {line}' for line in sorted(removed)]
        + [f'+ {line}' for line in sorted(added)]
    )
    return '\n'.join(lines[:150])


# ---------------------------------------------------------------------------
# Main evolution loop
# ---------------------------------------------------------------------------

def evolve(skill_path: Path, iterations: int, timeout: int, min_delta: float):
    skill_md_path = skill_path / 'SKILL.md'

    if not skill_md_path.exists():
        print(f"Error: SKILL.md not found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    claude_bin = find_claude_cli()
    if not claude_bin:
        print("Error: claude CLI not found in PATH.", file=sys.stderr)
        sys.exit(1)

    # Set up run directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = skill_path / 'evals' / 'autoevolve' / f'run-{timestamp}'
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / 'log.jsonl'

    print(f"\nautoresearch-style skill evolution")
    print(f"Skill:      {skill_path.name}")
    print(f"Iterations: {iterations}")
    print(f"Min delta:  {min_delta:.1%}")
    print(f"Run dir:    {run_dir}\n")

    current_skill_md = skill_md_path.read_text()
    best_skill_md = current_skill_md
    last_score: dict = {}

    # --- Baseline ---
    print("[baseline] scoring current SKILL.md...")
    baseline = score_skill(skill_path, claude_bin, timeout, run_dir, 0)

    if baseline.get('error'):
        print(f"[baseline] {baseline['error']}", file=sys.stderr)
        sys.exit(1)

    best_score = baseline['combined']
    last_score = baseline
    print(
        f"[baseline] score: {best_score:.1%} "
        f"({baseline['passed']}/{baseline['total']} assertions)\n"
    )

    with open(log_path, 'a') as log:
        log.write(json.dumps({'iteration': 0, 'type': 'baseline', **baseline}) + '\n')

    (run_dir / 'best-skill.md').write_text(best_skill_md)

    kept_count = 0
    reverted_count = 0
    skipped_count = 0

    # --- Iteration loop ---
    for i in range(1, iterations + 1):
        iter_start = time.time()
        print(f"[iter {i}/{iterations}] proposing improvement...")

        iter_dir = run_dir / f'iteration-{i}'
        iter_dir.mkdir(exist_ok=True)
        (iter_dir / 'snapshot.md').write_text(current_skill_md)

        # Propose
        proposed = propose_improvement(current_skill_md, last_score, claude_bin, timeout)

        if proposed is None:
            print(f"[iter {i}] could not extract SKILL.md from proposal — skipping")
            skipped_count += 1
            with open(log_path, 'a') as log:
                log.write(json.dumps({'iteration': i, 'type': 'skip', 'reason': 'extraction_failed'}) + '\n')
            continue

        (iter_dir / 'proposal.md').write_text(proposed)

        if proposed.strip() == current_skill_md.strip():
            print(f"[iter {i}] proposal identical to current — skipping")
            skipped_count += 1
            with open(log_path, 'a') as log:
                log.write(json.dumps({'iteration': i, 'type': 'skip', 'reason': 'no_change'}) + '\n')
            continue

        diff = make_diff(current_skill_md, proposed)
        (iter_dir / 'diff.txt').write_text(diff)

        # Apply and score
        skill_md_path.write_text(proposed)
        print(f"[iter {i}] scoring new version...")
        new_score = score_skill(skill_path, claude_bin, timeout, run_dir, i)
        delta = new_score['combined'] - best_score
        kept = delta >= min_delta

        (iter_dir / 'score.json').write_text(json.dumps({
            'prev_score': best_score,
            'new_score': new_score['combined'],
            'delta': delta,
            'kept': kept,
            **new_score,
        }, indent=2))

        elapsed = int(time.time() - iter_start)

        if kept:
            print(
                f"[iter {i}] KEPT    {best_score:.1%} → {new_score['combined']:.1%} "
                f"(+{delta:.1%})  [{elapsed}s]"
            )
            current_skill_md = proposed
            best_score = new_score['combined']
            best_skill_md = proposed
            last_score = new_score
            (run_dir / 'best-skill.md').write_text(best_skill_md)
            kept_count += 1
        else:
            print(
                f"[iter {i}] REVERT  {best_score:.1%} → {new_score['combined']:.1%} "
                f"({delta:+.1%})  [{elapsed}s]"
            )
            skill_md_path.write_text(current_skill_md)
            last_score = new_score
            reverted_count += 1

        with open(log_path, 'a') as log:
            log.write(json.dumps({
                'iteration': i,
                'type': 'kept' if kept else 'reverted',
                'prev_score': best_score if not kept else best_score - delta,
                'new_score': new_score['combined'],
                'delta': delta,
                **new_score,
            }) + '\n')
        print()

    # --- Finalize ---
    skill_md_path.write_text(best_skill_md)

    print("=" * 50)
    print(f"Evolution complete — {iterations} iterations")
    print(f"  kept:     {kept_count}")
    print(f"  reverted: {reverted_count}")
    print(f"  skipped:  {skipped_count}")
    print(f"  best score: {best_score:.1%}")
    print(f"\nSKILL.md updated to best version found.")
    print(f"Best snapshot: {run_dir / 'best-skill.md'}")
    print(f"Full log:      {log_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous skill evolution — autoresearch-style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--skill', required=True,
        help='Path to the skill directory (must contain SKILL.md and evals/evals.json)',
    )
    parser.add_argument(
        '--iterations', type=int, default=20,
        help='Number of improvement attempts. Default: 20',
    )
    parser.add_argument(
        '--timeout', type=int, default=120,
        help='Timeout per claude call in seconds. Default: 120',
    )
    parser.add_argument(
        '--min-delta', type=float, default=0.0,
        help='Minimum score improvement to keep a change (0.0 = keep if no worse). Default: 0.0',
    )
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    if not skill_path.exists():
        print(f"Error: skill not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    evolve(skill_path, args.iterations, args.timeout, args.min_delta)


if __name__ == '__main__':
    main()
