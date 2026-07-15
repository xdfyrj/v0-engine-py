from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

from scores import V0_BASELINE_JOBS


ROOT = Path(__file__).resolve().parent


def run_step(arguments: list[str]) -> None:
    command = [sys.executable, *arguments]
    print(f"\n+ {shlex.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"step failed with exit code {completed.returncode}: "
            f"{shlex.join(command)}"
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild, extract, score, and verify the four canonical V0 baselines."
        )
    )
    parser.add_argument(
        "--rustc-tool",
        default="rustc",
        help="rustc-compatible compiler passed to compile.py. Default: rustc",
    )
    parser.add_argument(
        "--strip-tool",
        default="strip",
        help="strip-compatible tool passed to compile.py. Default: strip",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        for case, build in V0_BASELINE_JOBS:
            run_step([
                "compile.py",
                case,
                "--build",
                build,
                "--rustc-tool",
                args.rustc_tool,
                "--strip-tool",
                args.strip_tool,
            ])
            run_step(["run_case.py", case, "--build", build])

        run_step([
            "scores.py",
            "--baseline",
            "--json-output",
            "results/v0_baseline.json",
        ])
        run_step(["test/test_scores.py"])
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print("\nV0 baseline regeneration PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
