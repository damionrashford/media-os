#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""
media-batch: run ffmpeg / ImageMagick / ffmpeg-normalize jobs through GNU parallel
with joblog, resume, and retry baked in.

Stdlib only. Non-interactive.

Subcommands:
  check             parallel + ffmpeg available?
  transcode         batch ffmpeg transcode
  resize            batch ImageMagick resize
  audio-normalize   batch ffmpeg-normalize (EBU R128)
  status            summarize a joblog
  retry             re-run failed jobs in a joblog

Examples:
  uv run scripts/batch.py check
  uv run scripts/batch.py transcode --indir raw --outdir mp4 \
    --pattern '*.mov' --ffmpeg-args '-c:v libx264 -crf 20 -c:a aac' \
    --joblog jobs.log --jobs 4
  uv run scripts/batch.py resize --indir photos --outdir out --width 1280 --pattern '*.jpg'
  uv run scripts/batch.py audio-normalize --indir podcast --outdir podcast/norm --target -16
  uv run scripts/batch.py status --joblog jobs.log
  uv run scripts/batch.py retry  --joblog jobs.log
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


# ------------------------- shared helpers -------------------------


def _have(binary: str) -> str | None:
    return shutil.which(binary)


def _eprint(*a, **kw) -> None:
    print(*a, file=sys.stderr, **kw)


def _run(
    cmd: list[str], *, dry_run: bool, verbose: bool, stdin_bytes: bytes | None = None
) -> int:
    shown = " ".join(shlex.quote(c) for c in cmd)
    if dry_run or verbose:
        _eprint(f"$ {shown}")
    if dry_run:
        return 0
    try:
        p = subprocess.run(cmd, input=stdin_bytes, check=False)
        return p.returncode
    except FileNotFoundError as e:
        _eprint(f"error: {e}")
        return 127


def _find_files(indir: Path, pattern: str) -> list[Path]:
    if not indir.exists():
        _eprint(f"error: indir not found: {indir}")
        sys.exit(2)
    # rglob pattern; keep the order deterministic
    return sorted(p for p in indir.rglob(pattern) if p.is_file())


def _ensure_outdir(outdir: Path, dry_run: bool) -> None:
    if dry_run:
        return
    outdir.mkdir(parents=True, exist_ok=True)


def _parallel_bin() -> str:
    p = _have("parallel")
    if not p:
        _eprint(
            "error: GNU parallel not found. brew install parallel / apt install parallel"
        )
        sys.exit(127)
    return p


def _run_parallel(
    *,
    cmd_template: str,
    files: list[Path],
    jobs: int | str,
    joblog: str | None,
    bar: bool,
    resume_failed: bool,
    extra_flags: list[str],
    dry_run: bool,
    verbose: bool,
) -> int:
    parallel = _parallel_bin()
    pcmd = [parallel, "-j", str(jobs)]
    if bar:
        pcmd += ["--bar"]
    if joblog:
        pcmd += ["--joblog", joblog]
    if resume_failed:
        pcmd += ["--resume-failed"]
    pcmd += extra_flags
    pcmd += [cmd_template]

    stdin = ("\n".join(str(f) for f in files) + "\n").encode() if files else b""
    if dry_run or verbose:
        _eprint(f"# files: {len(files)}")
        _eprint(
            f"$ {' '.join(shlex.quote(c) for c in pcmd)} < <stdin: {len(files)} paths>"
        )
    if dry_run:
        # show the first few commands parallel would run
        dry = pcmd + ["--dry-run"]
        p = subprocess.run(dry, input=stdin, capture_output=True)
        head = b"\n".join(p.stdout.splitlines()[:5]).decode(errors="replace")
        if head:
            _eprint("# first 5 commands parallel would run:")
            for line in head.splitlines():
                _eprint(f"  {line}")
        return 0
    p = subprocess.run(pcmd, input=stdin, check=False)
    return p.returncode


# ------------------------- subcommands -------------------------


def cmd_check(args: argparse.Namespace) -> int:
    ok = True
    for tool in ("parallel", "ffmpeg", "ffprobe"):
        path = _have(tool)
        mark = "OK " if path else "MISSING "
        print(f"{mark}{tool:20s} {path or ''}")
        if not path and tool in ("parallel", "ffmpeg"):
            ok = False
    for tool in ("magick", "convert", "ffmpeg-normalize"):
        path = _have(tool)
        mark = "OK " if path else "opt "
        print(f"{mark}{tool:20s} {path or '(optional)'}")
    return 0 if ok else 1


def cmd_transcode(args: argparse.Namespace) -> int:
    indir = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    files = _find_files(indir, args.pattern)
    if not files:
        _eprint(f"no files matched: {indir}/{args.pattern}")
        return 0
    _ensure_outdir(outdir, args.dry_run)

    # output = outdir / <basename-without-ext>.<ext>
    out_ext = args.out_ext.lstrip(".")
    # Use parallel placeholders:
    #   {/.}  = basename without extension
    cmd = (
        "ffmpeg -nostdin -hide_banner -loglevel error -y "
        "-i {} "
        f"{args.ffmpeg_args} "
        f"{shlex.quote(str(outdir))}/{{/.}}.{out_ext}"
    )
    if args.skip_existing:
        cmd = f"[ -f {shlex.quote(str(outdir))}/{{/.}}.{out_ext} ] || " + cmd
    return _run_parallel(
        cmd_template=cmd,
        files=files,
        jobs=args.jobs,
        joblog=args.joblog,
        bar=not args.no_bar,
        resume_failed=args.resume_failed,
        extra_flags=[],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_resize(args: argparse.Namespace) -> int:
    if not (_have("magick") or _have("convert")):
        _eprint("error: ImageMagick not found (need 'magick' or 'convert')")
        return 127
    magick = _have("magick") or _have("convert")
    indir = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    files = _find_files(indir, args.pattern)
    if not files:
        _eprint(f"no files matched: {indir}/{args.pattern}")
        return 0
    _ensure_outdir(outdir, args.dry_run)

    geom = f"{args.width}x{args.width}\\>"  # shrink-only
    cmd = (
        f"{shlex.quote(magick)} {{}} "
        f"-resize {geom} -quality {args.quality} -strip "
        f"{shlex.quote(str(outdir))}/{{/}}"
    )
    return _run_parallel(
        cmd_template=cmd,
        files=files,
        jobs=args.jobs,
        joblog=args.joblog,
        bar=not args.no_bar,
        resume_failed=args.resume_failed,
        extra_flags=[],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


def cmd_audio_normalize(args: argparse.Namespace) -> int:
    if not _have("ffmpeg-normalize"):
        _eprint("error: ffmpeg-normalize not found. pipx install ffmpeg-normalize")
        return 127
    indir = Path(args.indir).resolve()
    outdir = Path(args.outdir).resolve()
    files = _find_files(indir, args.pattern)
    if not files:
        _eprint(f"no files matched: {indir}/{args.pattern}")
        return 0
    _ensure_outdir(outdir, args.dry_run)

    out_ext = args.out_ext.lstrip(".")
    codec = args.codec
    bitrate = args.bitrate
    cmd = (
        "ffmpeg-normalize {} "
        f"-t {args.target} -tp {args.true_peak} -lra {args.lra} "
        f"-c:a {codec} -b:a {bitrate} "
        f"-o {shlex.quote(str(outdir))}/{{/.}}.{out_ext}"
    )
    return _run_parallel(
        cmd_template=cmd,
        files=files,
        jobs=args.jobs,
        joblog=args.joblog,
        bar=not args.no_bar,
        resume_failed=args.resume_failed,
        extra_flags=[],
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


# joblog columns (tab-separated):
#   Seq Host Starttime JobRuntime Send Receive Exitval Signal Command
JOBLOG_COLS = (
    "Seq Host Starttime JobRuntime Send Receive Exitval Signal Command".split()
)


def _read_joblog(path: Path) -> list[dict]:
    if not path.exists():
        _eprint(f"error: joblog not found: {path}")
        sys.exit(2)
    rows: list[dict] = []
    with path.open() as fh:
        header = fh.readline()  # skip header
        if not header:
            return rows
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < len(JOBLOG_COLS):
                # pad with empties
                parts += [""] * (len(JOBLOG_COLS) - len(parts))
            row = dict(zip(JOBLOG_COLS, parts[: len(JOBLOG_COLS)]))
            # tail columns joined back as command in case tabs leaked
            if len(parts) > len(JOBLOG_COLS):
                row["Command"] = "\t".join(parts[len(JOBLOG_COLS) - 1 :])
            rows.append(row)
    return rows


def cmd_status(args: argparse.Namespace) -> int:
    rows = _read_joblog(Path(args.joblog))
    total = len(rows)
    by_exit: dict[str, int] = {}
    runtimes: list[float] = []
    for r in rows:
        by_exit[r["Exitval"]] = by_exit.get(r["Exitval"], 0) + 1
        try:
            runtimes.append(float(r["JobRuntime"]))
        except ValueError:
            pass
    ok = by_exit.get("0", 0)
    failed = total - ok
    print(f"joblog:   {args.joblog}")
    print(f"total:    {total}")
    print(f"success:  {ok}")
    print(f"failed:   {failed}")
    if runtimes:
        runtimes.sort()
        mid = runtimes[len(runtimes) // 2]
        print(
            f"runtime:  min={runtimes[0]:.1f}s  median={mid:.1f}s  max={runtimes[-1]:.1f}s"
        )
    if by_exit:
        print("exit codes:")
        for code, count in sorted(by_exit.items(), key=lambda kv: kv[0]):
            label = {
                "0": "success",
                "1": "ffmpeg/tool error",
                "255": "killed/timeout",
            }.get(code, "other")
            print(f"  {code:>4} ({label:>18}) : {count}")
    if args.show_failed:
        print("failed commands:")
        for r in rows:
            if r["Exitval"] != "0":
                print(f"  [{r['Exitval']}] {r['Command']}")
    return 0 if failed == 0 else 1


def cmd_retry(args: argparse.Namespace) -> int:
    parallel = _parallel_bin()
    joblog = Path(args.joblog)
    if not joblog.exists():
        _eprint(f"error: joblog not found: {joblog}")
        return 2
    pcmd = [parallel, "--retry-failed", "--joblog", str(joblog)]
    if args.retries:
        pcmd += ["--retries", str(args.retries)]
    if not args.no_bar:
        pcmd += ["--bar"]
    if args.verbose or args.dry_run:
        _eprint(f"$ {' '.join(shlex.quote(c) for c in pcmd)}")
    if args.dry_run:
        return 0
    p = subprocess.run(pcmd, check=False)
    return p.returncode


# ------------------------- arg parsing -------------------------


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the parallel command without running",
    )
    p.add_argument("--verbose", action="store_true", help="print progress to stderr")


def _add_parallel_knobs(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--jobs",
        "-j",
        default=str(max(1, (os.cpu_count() or 2) // 2)),
        help="parallel -j value (int, '50%%', '+0'; default: half of CPUs)",
    )
    p.add_argument(
        "--joblog", default=None, help="parallel joblog path (enables --resume-failed)"
    )
    p.add_argument("--no-bar", action="store_true", help="disable --bar progress")
    p.add_argument(
        "--resume-failed",
        action="store_true",
        help="pass --resume-failed to parallel (requires --joblog)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="batch.py",
        description="Batch media processing through GNU parallel (transcode / resize / loudness-normalize).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # check
    sp = sub.add_parser("check", help="verify parallel and ffmpeg are available")
    _add_common(sp)
    sp.set_defaults(func=cmd_check)

    # transcode
    sp = sub.add_parser("transcode", help="batch ffmpeg transcode")
    sp.add_argument("--indir", required=True)
    sp.add_argument("--outdir", required=True)
    sp.add_argument("--pattern", default="*.mov", help="glob pattern (default: *.mov)")
    sp.add_argument(
        "--ffmpeg-args",
        default="-c:v libx264 -crf 20 -preset medium -c:a aac -b:a 192k",
        help="ffmpeg codec/filter args (between -i and output)",
    )
    sp.add_argument("--out-ext", default="mp4", help="output extension (default: mp4)")
    sp.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="skip if output already exists (default: on)",
    )
    sp.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    _add_parallel_knobs(sp)
    _add_common(sp)
    sp.set_defaults(func=cmd_transcode)

    # resize
    sp = sub.add_parser("resize", help="batch ImageMagick resize")
    sp.add_argument("--indir", required=True)
    sp.add_argument("--outdir", required=True)
    sp.add_argument("--pattern", default="*.jpg")
    sp.add_argument(
        "--width",
        type=int,
        default=1280,
        help="max width (also bounds height); shrink-only",
    )
    sp.add_argument("--quality", type=int, default=85)
    _add_parallel_knobs(sp)
    _add_common(sp)
    sp.set_defaults(func=cmd_resize)

    # audio-normalize
    sp = sub.add_parser(
        "audio-normalize",
        help="batch EBU R128 loudness normalization via ffmpeg-normalize",
    )
    sp.add_argument("--indir", required=True)
    sp.add_argument("--outdir", required=True)
    sp.add_argument("--pattern", default="*.wav")
    sp.add_argument(
        "--target",
        type=float,
        default=-16.0,
        help="integrated LUFS target (default: -16)",
    )
    sp.add_argument(
        "--true-peak", type=float, default=-1.0, help="true-peak dBTP (default: -1)"
    )
    sp.add_argument(
        "--lra", type=float, default=11.0, help="loudness range target (default: 11)"
    )
    sp.add_argument("--codec", default="aac")
    sp.add_argument("--bitrate", default="192k")
    sp.add_argument("--out-ext", default="m4a")
    _add_parallel_knobs(sp)
    _add_common(sp)
    sp.set_defaults(func=cmd_audio_normalize)

    # status
    sp = sub.add_parser("status", help="summarize a parallel joblog")
    sp.add_argument("--joblog", required=True)
    sp.add_argument("--show-failed", action="store_true", help="list failed commands")
    _add_common(sp)
    sp.set_defaults(func=cmd_status)

    # retry
    sp = sub.add_parser("retry", help="re-run failed jobs from a parallel joblog")
    sp.add_argument("--joblog", required=True)
    sp.add_argument(
        "--retries", type=int, default=0, help="pass --retries N to parallel"
    )
    sp.add_argument("--no-bar", action="store_true")
    _add_common(sp)
    sp.set_defaults(func=cmd_retry)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
