from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from paths import (
    DEFAULT_BUILD,
    fixture_binary_for,
    gt_binary_for,
    source_rs_for,
    split_case_build,
)


RUSTC_EDITION = "2024"
STRIP_FLAGS = ["--strip-all"]

# Exact per-profile rustc flags from rust-loss scripts/lib_build.sh.
# The checked-in corpus binaries were built with these flags; keep them
# byte-for-byte identical so local rebuilds reproduce the same binaries
# under the same rustc version.
_O3_FLAGS = [
    "-C", "opt-level=3",
    "-C", "codegen-units=1",
    "-C", "lto=off",
    "-C", "panic=unwind",
    "-C", "debuginfo=0",
    "-C", "debug-assertions=off",
    "-C", "overflow-checks=off",
]

PROFILE_FLAGS: dict[str, list[str]] = {
    "O3": _O3_FLAGS,
    "O3K": _O3_FLAGS + ["--cfg", "keep"],
}

# Evaluation build -> compiled (non-stripped) source profile.
# Mirrors rust-loss source_profile_for_stripped.
COMPILED_PROFILE_BY_BUILD = {
    "O3S": "O3",
    "O3KS": "O3K",
}


def compiled_profile_for_build(build: str) -> str:
    profile = COMPILED_PROFILE_BY_BUILD.get(build)
    if profile is None:
        raise ValueError(
            f"unsupported build for compilation: {build}. "
            f"Supported builds: {sorted(COMPILED_PROFILE_BY_BUILD)}"
        )
    return profile


def rustc_command(
    *,
    source: str,
    case: str,
    profile: str,
    output: str,
    rustc_tool: str = "rustc",
) -> list[str]:
    # rust-loss uses --emit=llvm-ir,asm,link into an --out-dir. Only the
    # linked binary is needed here, and --emit=link -o produces a
    # byte-identical binary under the same rustc.
    return [
        rustc_tool,
        source,
        *PROFILE_FLAGS[profile],
        "--crate-type", "bin",
        "--crate-name", case,
        "--edition", RUSTC_EDITION,
        "--emit=link",
        "-o", output,
    ]


def compile_gt_binary(
    *,
    source: str,
    case: str,
    profile: str,
    output: str,
    rustc_tool: str,
) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path_for(path)

    try:
        command = rustc_command(
            source=source,
            case=case,
            profile=profile,
            output=str(temporary),
            rustc_tool=rustc_tool,
        )
        _run_tool(command)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def derive_fixture_binary(
    *,
    gt_binary: str,
    output: str,
    strip_tool: str,
) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path_for(path)

    try:
        shutil.copyfile(gt_binary, temporary)
        shutil.copymode(gt_binary, temporary)
        _run_tool([strip_tool, *STRIP_FLAGS, str(temporary)])
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _temporary_path_for(output: Path) -> Path:
    handle, name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(handle)
    return Path(name)


def _require_tool(tool: str) -> None:
    if not shutil.which(tool):
        raise RuntimeError(
            f"{tool} executable was not found. Install it before running "
            "compile.py."
        )


def _run_tool(command: list[str]) -> None:
    _require_tool(command[0])

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{command[0]} failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )


def tool_version_line(tool: str) -> str:
    result = subprocess.run(
        [tool, "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.stdout.splitlines()[0] if result.stdout else "unknown"


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_info_path_for(binary_path: str) -> str:
    return str(Path(binary_path).with_suffix("")) + ".build_info.txt"


def make_gt_build_info(
    *,
    source: str,
    case: str,
    build: str,
    profile: str,
    output: str,
    rustc_tool: str,
) -> str:
    lines = [
        f"source={source}",
        f"case={case}",
        f"build={build}",
        f"profile={profile}",
        f"rustc={tool_version_line(rustc_tool)}",
        f"flags={' '.join(PROFILE_FLAGS[profile])}",
        f"crate_name={case}",
        f"edition={RUSTC_EDITION}",
        "emit=link",
        f"source_sha256={sha256_file(source)}",
        f"binary_sha256={sha256_file(output)}",
        "role=non-stripped ground-truth symbol source",
    ]
    return "\n".join(lines) + "\n"


def make_fixture_build_info(
    *,
    source: str,
    case: str,
    build: str,
    profile: str,
    gt_binary: str,
    output: str,
    strip_tool: str,
) -> str:
    lines = [
        f"source={source}",
        f"case={case}",
        f"build={build}",
        f"profile={profile}",
        f"derived_from={gt_binary}",
        f"strip={tool_version_line(strip_tool)}",
        f"strip_flags={' '.join(STRIP_FLAGS)}",
        f"source_binary_sha256={sha256_file(gt_binary)}",
        f"binary_sha256={sha256_file(output)}",
        "role=stripped fixture evaluation binary",
    ]
    return "\n".join(lines) + "\n"


def write_build_info(text: str, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def compile_case(args: argparse.Namespace) -> list[str]:
    profile = compiled_profile_for_build(args.build)

    # Validate the complete toolchain before replacing either binary.
    _require_tool(args.rustc_tool)
    _require_tool(args.strip_tool)

    compile_gt_binary(
        source=args.source,
        case=args.case,
        profile=profile,
        output=args.gt_binary,
        rustc_tool=args.rustc_tool,
    )
    derive_fixture_binary(
        gt_binary=args.gt_binary,
        output=args.fixture_binary,
        strip_tool=args.strip_tool,
    )

    gt_info_path = build_info_path_for(args.gt_binary)
    fixture_info_path = build_info_path_for(args.fixture_binary)

    write_build_info(
        make_gt_build_info(
            source=args.source,
            case=args.case,
            build=args.build,
            profile=profile,
            output=args.gt_binary,
            rustc_tool=args.rustc_tool,
        ),
        gt_info_path,
    )
    write_build_info(
        make_fixture_build_info(
            source=args.source,
            case=args.case,
            build=args.build,
            profile=profile,
            gt_binary=args.gt_binary,
            output=args.fixture_binary,
            strip_tool=args.strip_tool,
        ),
        fixture_info_path,
    )

    return [args.gt_binary, args.fixture_binary, gt_info_path, fixture_info_path]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile one Rust example source into this project's non-stripped "
            "gt_bin/ and stripped bin/ evaluation binaries."
        )
    )
    parser.add_argument("source", help="Rust source path, or an example stem")
    parser.add_argument("--case", help="case name and rustc crate name")
    parser.add_argument(
        "--build",
        help=(
            f"evaluation build. O3S compiles the O3 profile, O3KS compiles the "
            f"O3K (--cfg keep) profile. Default: {DEFAULT_BUILD}"
        ),
    )
    parser.add_argument("--gt-binary", help="override non-stripped output path")
    parser.add_argument("--fixture-binary", help="override stripped output path")
    parser.add_argument(
        "--rustc-tool",
        default="rustc",
        help="rustc-compatible compiler. Default: rustc",
    )
    parser.add_argument(
        "--strip-tool",
        default="strip",
        help="strip-compatible tool. Default: strip",
    )
    return parser


def apply_cli_defaults(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    case, build = split_case_build(args.source, args.build)

    if not Path(args.source).exists():
        args.source = source_rs_for(case)

    if not Path(args.source).exists():
        parser.error(f"source not found: {args.source}")

    args.case = args.case or case
    args.build = build
    args.gt_binary = args.gt_binary or gt_binary_for(args.case, build)
    args.fixture_binary = args.fixture_binary or fixture_binary_for(args.case, build)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    apply_cli_defaults(args, parser)

    try:
        outputs = compile_case(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
