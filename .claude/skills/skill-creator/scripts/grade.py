#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Grade eval outputs against assertions and aggregate results into benchmark.json.

Reads eval outputs from the workspace directory produced by run-eval.py.
Uses the claude CLI to grade each assertion against the actual output.
Saves grading.json per eval case and benchmark.json for the full iteration.

Usage:
    python3 scripts/grade.py --skill <path> --iteration <n>
    python3 scripts/grade.py --skill <path> --iteration 1 --eval-id 1
    python3 scripts/grade.py --skill <path> --iteration 1 --human
    python3 scripts/grade.py --skill <path> --benchmark   # just re-aggregate

Output:
    <skill>/evals/workspace/iteration-<n>/eval-<id>/with-skill/grading.json
    <skill>/evals/workspace/iteration-<n>/eval-<id>/without-skill/grading.json
    <skill>/evals/workspace/iteration-<n>/benchmark.json

Exit codes:
    0  Grading complete
    1  Error (missing files, claude not found)

Examples:
    python3 scripts/grade.py --skill .claude/skills/my-skill --iteration 1
    python3 scripts/grade.py --skill ~/.claude/skills/my-skill --iteration 2 --human
    python3 scripts/grade.py --skill .claude/skills/my-skill --benchmark --iteration 1
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def find_claude_cli() -> str | None:
    for candidate in ['claude', 'claude-code']:
        result = subprocess.run(['which', candidate], capture_output=True, text=True)
        if result.returncode == 0:
            return candidate
    return None


def load_evals(skill_path: Path) -> list[dict]:
    evals_json = skill_path / 'evals' / 'evals.json'
    if not evals_json.exists():
        print(f"Error: evals.json not found: {evals_json}", file=sys.stderr)
        print(f"Run first: python3 scripts/init-evals.py --skill {skill_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(evals_json.read_text()).get('evals', [])


def _extract_json(text: str) -> dict | None:
    """Extract a JSON object from text that may have surrounding prose."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def grade_assertion_with_claude(claude_bin: str, assertion: str, output_text: str) -> dict:
    """
    Ask claude to grade one assertion against the actual output.
    Returns: {passed: bool, evidence: str}
    """
    grade_prompt = (
        "You are grading whether an AI assistant's response satisfies an assertion.\n\n"
        f"ASSERTION:\n{assertion}\n\n"
        f"ACTUAL OUTPUT:\n{output_text[:3000]}"
        f"{'... [truncated]' if len(output_text) > 3000 else ''}\n\n"
        "Grade the assertion. Respond with ONLY this JSON (no other text):\n"
        '{"passed": true, "evidence": "specific quote or observation from the output"}\n\n'
        "Rules:\n"
        "- passed: true ONLY if there is concrete evidence the assertion is satisfied\n"
        "- Do NOT give benefit of the doubt — require actual evidence for a PASS\n"
        "- evidence: quote specific text from the output, or state what is absent\n"
        "- If the output is empty or an error message, all assertions fail"
    )

    cmd = [claude_bin, '--print', '--output-format', 'json', grade_prompt]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                                env={**os.environ})
        data = _extract_json(result.stdout.strip())
        if data and 'passed' in data:
            return {
                'passed': bool(data['passed']),
                'evidence': str(data.get('evidence', '')),
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return {'passed': False, 'evidence': '[grading error — claude CLI returned no result]'}


def grade_assertion_human(assertion: str, output_text: str) -> dict:
    """Human-in-the-loop grading. Shows output + assertion, asks PASS/FAIL."""
    print(f"\n{'─' * 60}")
    print(f"ASSERTION: {assertion}")
    print(f"\nOUTPUT (first 1200 chars):\n{output_text[:1200]}")
    if len(output_text) > 1200:
        print(f"... [{len(output_text) - 1200} more chars]")
    print(f"{'─' * 60}")

    while True:
        raw = input("PASS or FAIL? [p/f]: ").strip().lower()
        if raw in ('p', 'pass'):
            ev = input("Evidence (what in the output proves this): ").strip()
            return {'passed': True, 'evidence': ev or 'manually graded PASS'}
        elif raw in ('f', 'fail'):
            ev = input("Evidence (what is absent or wrong): ").strip()
            return {'passed': False, 'evidence': ev or 'manually graded FAIL'}
        print("  Enter 'p' for PASS or 'f' for FAIL.")


def grade_eval_case(
    claude_bin: str | None,
    eval_case: dict,
    workspace_base: Path,
    human_mode: bool,
    modes: list[str],
) -> None:
    eval_id = eval_case['id']
    assertions = eval_case.get('assertions', [])

    if not assertions:
        print(f"  Eval {eval_id}: no assertions — skipping")
        return

    for mode in modes:
        output_file = workspace_base / f'eval-{eval_id}' / mode / 'output.txt'
        grading_file = workspace_base / f'eval-{eval_id}' / mode / 'grading.json'
        timing_file  = workspace_base / f'eval-{eval_id}' / mode / 'timing.json'

        if not output_file.exists():
            print(f"  Eval {eval_id} [{mode}]: output.txt not found — run run-eval.py first")
            continue

        output_text = output_file.read_text()
        timing = {}
        if timing_file.exists():
            try:
                timing = json.loads(timing_file.read_text())
            except json.JSONDecodeError:
                pass

        print(f"  Eval {eval_id} [{mode}]: grading {len(assertions)} assertion(s)...")

        assertion_results = []
        for assertion in assertions:
            if human_mode:
                grade = grade_assertion_human(assertion, output_text)
            elif claude_bin:
                grade = grade_assertion_with_claude(claude_bin, assertion, output_text)
            else:
                grade = {'passed': False, 'evidence': '[ungraded — no claude CLI and not --human mode]'}

            assertion_results.append({
                'text': assertion,
                'passed': grade['passed'],
                'evidence': grade['evidence'],
            })
            status = 'PASS' if grade['passed'] else 'FAIL'
            print(f"    [{status}] {assertion[:65]}{'...' if len(assertion) > 65 else ''}")
            if not grade['passed']:
                print(f"           {grade['evidence'][:110]}")

        n_pass  = sum(1 for r in assertion_results if r['passed'])
        n_total = len(assertion_results)
        pass_rate = round(n_pass / n_total, 2) if n_total else 0.0

        human_feedback = ''
        if human_mode:
            print(f"\n  Overall feedback for eval {eval_id} [{mode}] (Enter to skip):")
            human_feedback = input("  Feedback: ").strip()

        grading = {
            'eval_id': eval_id,
            'mode': mode,
            'assertion_results': assertion_results,
            'human_feedback': human_feedback,
            'duration_ms': timing.get('duration_ms'),
            'token_estimate': timing.get('token_estimate'),
            'summary': {
                'passed': n_pass,
                'failed': n_total - n_pass,
                'total': n_total,
                'pass_rate': pass_rate,
            },
        }

        grading_file.parent.mkdir(parents=True, exist_ok=True)
        grading_file.write_text(json.dumps(grading, indent=2))


def aggregate_benchmark(workspace_base: Path, eval_ids: list[int]) -> dict:
    """Read all grading.json files for an iteration and compute summary stats."""
    modes = ['with-skill', 'without-skill']
    mode_stats: dict[str, dict] = {
        m: {'pass_rates': [], 'durations': [], 'tokens': []} for m in modes
    }

    for eid in eval_ids:
        for mode in modes:
            gf = workspace_base / f'eval-{eid}' / mode / 'grading.json'
            if not gf.exists():
                continue
            try:
                g = json.loads(gf.read_text())
            except json.JSONDecodeError:
                continue
            s = g.get('summary', {})
            if s.get('pass_rate') is not None:
                mode_stats[mode]['pass_rates'].append(s['pass_rate'])
            if g.get('duration_ms'):
                mode_stats[mode]['durations'].append(g['duration_ms'])
            if g.get('token_estimate'):
                mode_stats[mode]['tokens'].append(g['token_estimate'])

    def _stats(lst):
        if not lst:
            return None
        mean = sum(lst) / len(lst)
        stddev = (sum((x - mean) ** 2 for x in lst) / len(lst)) ** 0.5
        return {'mean': round(mean, 3), 'stddev': round(stddev, 3), 'n': len(lst)}

    summary = {}
    for mode in modes:
        s = mode_stats[mode]
        summary[mode] = {
            'pass_rate':   _stats(s['pass_rates']),
            'duration_ms': _stats(s['durations']),
            'tokens':      _stats(s['tokens']),
        }

    ws  = summary.get('with-skill', {})
    wos = summary.get('without-skill', {})
    delta = {}
    if ws.get('pass_rate') and wos.get('pass_rate'):
        delta['pass_rate'] = round(ws['pass_rate']['mean'] - wos['pass_rate']['mean'], 3)
    if ws.get('duration_ms') and wos.get('duration_ms'):
        delta['duration_ms'] = round(ws['duration_ms']['mean'] - wos['duration_ms']['mean'], 0)
    if ws.get('tokens') and wos.get('tokens'):
        delta['tokens'] = round(ws['tokens']['mean'] - wos['tokens']['mean'], 0)

    return {
        'run_summary': summary,
        'delta': delta,
        'eval_ids_graded': eval_ids,
    }


def print_benchmark(benchmark: dict):
    summary = benchmark.get('run_summary', {})
    delta   = benchmark.get('delta', {})

    print("\nBenchmark:")
    print(f"{'─' * 50}")
    for mode, stats in summary.items():
        pr  = stats.get('pass_rate')
        dur = stats.get('duration_ms')
        tok = stats.get('tokens')
        print(f"  {mode}:")
        if pr:
            print(f"    Pass rate:  {pr['mean']:.0%}  (±{pr['stddev']:.0%}, n={pr['n']})")
        if dur:
            print(f"    Duration:   {dur['mean']:.0f}ms avg")
        if tok:
            print(f"    Tokens est: {tok['mean']:.0f} avg")

    if delta:
        print(f"\n  Delta (with-skill minus without-skill):")
        if 'pass_rate' in delta:
            sign = '+' if delta['pass_rate'] >= 0 else ''
            print(f"    Pass rate:  {sign}{delta['pass_rate']:.0%}")
        if 'duration_ms' in delta:
            sign = '+' if delta['duration_ms'] >= 0 else ''
            print(f"    Duration:   {sign}{delta['duration_ms']:.0f}ms")
        if 'tokens' in delta:
            sign = '+' if delta['tokens'] >= 0 else ''
            print(f"    Tokens est: {sign}{delta['tokens']:.0f}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Grade eval outputs and compute benchmark stats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skill", required=True,
        help="Path to the skill directory")
    parser.add_argument("--iteration", type=int, default=1,
        help="Iteration number to grade. Default: 1")
    parser.add_argument("--eval-id", type=int, default=None,
        help="Grade only this eval ID (default: grade all)")
    parser.add_argument("--no-skill-only", action="store_true",
        help="Grade only the without-skill outputs")
    parser.add_argument("--with-skill-only", action="store_true",
        help="Grade only the with-skill outputs")
    parser.add_argument("--human", action="store_true",
        help="Human-in-the-loop grading instead of using the claude CLI")
    parser.add_argument("--benchmark", action="store_true",
        help="Skip grading — just re-aggregate benchmark.json from existing grading files")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    if not skill_path.exists():
        print(f"Error: skill not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    workspace_base = skill_path / 'evals' / 'workspace' / f'iteration-{args.iteration}'

    evals      = load_evals(skill_path)
    real_evals = [e for e in evals if 'REPLACE' not in e.get('prompt', '')]
    cases      = [e for e in real_evals if e['id'] == args.eval_id] if args.eval_id else real_evals
    eval_ids   = [e['id'] for e in cases]

    if not cases:
        ids = [e['id'] for e in real_evals]
        print(f"Error: eval {args.eval_id} not found. Available: {ids}", file=sys.stderr)
        sys.exit(1)

    # Re-aggregate only
    if args.benchmark:
        benchmark = aggregate_benchmark(workspace_base, eval_ids)
        out = workspace_base / 'benchmark.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(benchmark, indent=2))
        print(f"Benchmark written: {out}")
        print_benchmark(benchmark)
        sys.exit(0)

    modes = ['with-skill', 'without-skill']
    if args.no_skill_only:
        modes = ['without-skill']
    elif args.with_skill_only:
        modes = ['with-skill']

    claude_bin = None if args.human else find_claude_cli()
    if not args.human and not claude_bin:
        print("Warning: claude CLI not found — switching to --human mode.", file=sys.stderr)
        args.human = True

    print(f"\nGrading iteration {args.iteration} — {len(cases)} eval(s)")
    print(f"Modes: {', '.join(modes)}")
    print(f"Grader: {'human' if args.human else 'claude CLI'}")
    print()

    for case in cases:
        grade_eval_case(
            claude_bin=claude_bin,
            eval_case=case,
            workspace_base=workspace_base,
            human_mode=args.human,
            modes=modes,
        )
        print()

    benchmark = aggregate_benchmark(workspace_base, eval_ids)
    bench_path = workspace_base / 'benchmark.json'
    bench_path.parent.mkdir(parents=True, exist_ok=True)
    bench_path.write_text(json.dumps(benchmark, indent=2))

    print(f"Benchmark written: {bench_path}")
    print_benchmark(benchmark)

    ws_pr = benchmark.get('run_summary', {}).get('with-skill', {}).get('pass_rate')
    if ws_pr and ws_pr['mean'] < 0.7:
        print("Pass rate below 70% — review failed assertions and update SKILL.md.")
        print("Then increment --iteration and re-run: run-eval.py → grade.py")

    sys.exit(0)


if __name__ == "__main__":
    main()