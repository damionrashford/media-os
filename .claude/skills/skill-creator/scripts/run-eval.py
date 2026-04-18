#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
Run a single eval case from evals.json through the claude CLI.

Saves outputs to a structured workspace directory so results can be
compared across iterations and between with-skill / without-skill runs.

Usage:
    python3 scripts/run-eval.py --skill <path> --eval-id <n>
    python3 scripts/run-eval.py --skill <path> --eval-id <n> --no-skill
    python3 scripts/run-eval.py --skill <path> --all
    python3 scripts/run-eval.py --skill <path> --all --no-skill

Output structure:
    <skill>/evals/workspace/
    └── iteration-1/
        ├── eval-1/
        │   ├── with-skill/
        │   │   ├── output.txt       — raw claude response
        │   │   ├── timing.json      — duration_ms, tokens estimate
        │   │   └── grading.json     — filled in by grade.py
        │   └── without-skill/
        │       ├── output.txt
        │       └── timing.json
        └── eval-2/
            ...

Exit codes:
    0  Eval(s) ran successfully
    1  Eval not found or runtime error
    2  claude CLI not found

Examples:
    python3 scripts/run-eval.py --skill .claude/skills/my-skill --eval-id 1
    python3 scripts/run-eval.py --skill .claude/skills/my-skill --all --iteration 2
    python3 scripts/run-eval.py --skill .claude/skills/my-skill --eval-id 1 --no-skill
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
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
        print(f"Error: evals.json not found at {evals_json}", file=sys.stderr)
        print(f"Run first: python3 scripts/init-evals.py --skill {skill_path}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(evals_json.read_text())
    evals = data.get('evals', [])
    real = [e for e in evals if 'REPLACE' not in e.get('prompt', '')]
    if not real:
        print(f"Error: no real eval cases in {evals_json} — fill in the REPLACE placeholders.", file=sys.stderr)
        sys.exit(1)
    return real


def get_workspace_dir(skill_path: Path, iteration: int, eval_id: int, with_skill: bool) -> Path:
    label = 'with-skill' if with_skill else 'without-skill'
    return skill_path / 'evals' / 'workspace' / f'iteration-{iteration}' / f'eval-{eval_id}' / label


def run_eval_case(
    claude_bin: str,
    skill_path: Path,
    skill_name: str,
    eval_case: dict,
    with_skill: bool,
    workspace_dir: Path,
    timeout: int,
) -> dict:
    prompt = eval_case['prompt']
    input_files = eval_case.get('files', [])

    workspace_dir.mkdir(parents=True, exist_ok=True)

    # Copy input files into workspace
    for file_ref in input_files:
        src = skill_path / file_ref
        if src.exists():
            dst = workspace_dir / src.name
            shutil.copy2(src, dst)
        else:
            print(f"  Warning: input file not found: {src}", file=sys.stderr)

    # Build claude command
    cmd = [claude_bin, '--print', '--output-format', 'stream-json']
    if with_skill:
        cmd += ['--add-dir', str(skill_path.parent)]
    prompt_with_context = prompt
    if input_files and workspace_dir.exists():
        # Tell Claude where to find the input files
        prompt_with_context = f"{prompt}\n\n[Working directory: {workspace_dir}]"

    cmd.append(prompt_with_context)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workspace_dir),
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        error_msg = f"Timed out after {timeout}s"
        (workspace_dir / 'output.txt').write_text(f"[TIMEOUT] {error_msg}")
        (workspace_dir / 'timing.json').write_text(json.dumps({
            'duration_ms': duration_ms, 'error': error_msg
        }, indent=2))
        return {'success': False, 'error': error_msg, 'duration_ms': duration_ms}
    except FileNotFoundError:
        return {'success': False, 'error': f'claude CLI not found: {claude_bin}', 'duration_ms': 0}

    duration_ms = int((time.time() - start) * 1000)

    # Parse streaming JSON to extract text content
    output_text = _extract_text_from_stream(result.stdout)
    if not output_text:
        output_text = result.stdout  # fall back to raw

    # Count rough token estimate from output length
    token_estimate = len(output_text.split()) * 4 // 3

    (workspace_dir / 'output.txt').write_text(output_text)
    (workspace_dir / 'timing.json').write_text(json.dumps({
        'duration_ms': duration_ms,
        'token_estimate': token_estimate,
        'exit_code': result.returncode,
        'stderr': result.stderr[:200] if result.stderr else None,
    }, indent=2))

    # Write empty grading.json placeholder
    grading_path = workspace_dir / 'grading.json'
    if not grading_path.exists():
        grading_path.write_text(json.dumps({
            'eval_id': eval_case['id'],
            'mode': 'with-skill' if with_skill else 'without-skill',
            'assertion_results': [],
            'human_feedback': '',
            'summary': {'passed': 0, 'failed': 0, 'total': 0, 'pass_rate': None},
        }, indent=2))

    return {
        'success': result.returncode == 0,
        'duration_ms': duration_ms,
        'token_estimate': token_estimate,
        'output_path': str(workspace_dir / 'output.txt'),
    }


def _extract_text_from_stream(raw: str) -> str:
    """Extract text content from claude --output-format stream-json output."""
    lines = raw.strip().splitlines()
    text_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # stream-json events: {type: "content_block_delta", delta: {text: "..."}}
            if obj.get('type') == 'content_block_delta':
                delta = obj.get('delta', {})
                if delta.get('type') == 'text_delta':
                    text_parts.append(delta.get('text', ''))
            # Or final message format
            elif obj.get('type') == 'message':
                for block in obj.get('content', []):
                    if isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
            # Simple result object
            elif 'result' in obj:
                text_parts.append(str(obj['result']))
        except (json.JSONDecodeError, KeyError, TypeError):
            # Non-JSON line, include as-is if it looks like text
            if not line.startswith('{') and not line.startswith('['):
                text_parts.append(line)

    return ''.join(text_parts) or raw


def main():
    parser = argparse.ArgumentParser(
        description="Run eval cases from evals.json through the claude CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--skill", required=True,
        help="Path to the skill directory")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--eval-id", type=int,
        help="ID of the eval case to run (from evals.json)")
    group.add_argument("--all", action="store_true",
        help="Run all eval cases")
    parser.add_argument("--no-skill", action="store_true",
        help="Run WITHOUT the skill loaded (for baseline comparison)")
    parser.add_argument("--iteration", type=int, default=1,
        help="Iteration number for workspace directory naming. Default: 1")
    parser.add_argument("--timeout", type=int, default=120,
        help="Timeout per claude call in seconds. Default: 120")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    if not skill_path.exists():
        print(f"Error: skill not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    claude_bin = find_claude_cli()
    if not claude_bin:
        print("Error: 'claude' CLI not found in PATH.", file=sys.stderr)
        print("Install Claude Code: https://claude.ai/code", file=sys.stderr)
        sys.exit(2)

    skill_name = skill_path.name
    skill_md = skill_path / 'SKILL.md'
    if skill_md.exists():
        for line in skill_md.read_text().splitlines():
            if line.startswith('name:'):
                skill_name = line.split(':', 1)[1].strip().strip('"\'')
                break

    evals = load_evals(skill_path)

    if args.eval_id:
        cases = [e for e in evals if e['id'] == args.eval_id]
        if not cases:
            print(f"Error: eval id {args.eval_id} not found. Available: {[e['id'] for e in evals]}", file=sys.stderr)
            sys.exit(1)
    else:
        cases = evals

    with_skill = not args.no_skill
    mode = 'with-skill' if with_skill else 'without-skill'

    print(f"\nRunning {len(cases)} eval(s) — {mode}")
    print(f"Skill: {skill_name}")
    print(f"Iteration: {args.iteration}")
    print()

    errors = 0
    for case in cases:
        eid = case['id']
        workspace = get_workspace_dir(skill_path, args.iteration, eid, with_skill)
        print(f"  Eval {eid}: {case['prompt'][:70]}{'...' if len(case['prompt']) > 70 else ''}")
        print(f"  Output: {workspace}")

        result = run_eval_case(
            claude_bin=claude_bin,
            skill_path=skill_path,
            skill_name=skill_name,
            eval_case=case,
            with_skill=with_skill,
            workspace_dir=workspace,
            timeout=args.timeout,
        )

        if result['success']:
            print(f"  Done in {result['duration_ms']}ms (~{result.get('token_estimate', '?')} tokens)")
        else:
            print(f"  Error: {result.get('error', 'unknown')}")
            errors += 1
        print()

    if errors:
        print(f"{errors} eval(s) failed.")
        sys.exit(1)

    print(f"All done. Review outputs, then grade:")
    print(f"  python3 scripts/grade.py --skill {skill_path} --iteration {args.iteration}")
    sys.exit(0)


if __name__ == "__main__":
    main()