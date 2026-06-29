from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from engine import run_cg_wl
from loader import load_case
from scores import format_report, score_case


DEFAULT_BUILD = "unknown"


def case_stem(value: str) -> str:
    name = Path(value).name
    for suffix in (
        ".fixture.bin",
        ".gt.bin",
        ".fixture.json",
        ".gt.json",
        ".bin",
        ".json",
    ):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def crate_prefix_from_stem(stem: str) -> str:
    crate = re.sub(r"(?<=_\d)K$", "", stem)
    return f"{crate}::"


def first_existing(candidates: list[str]) -> str:
    for path in candidates:
        if Path(path).exists():
            return path
    return candidates[0]


def fixture_binary_for(stem: str) -> str:
    return first_existing([
        f"bin/{stem}.fixture.bin",
        f"bin/{stem}.bin",
    ])


def gt_binary_for(stem: str) -> str:
    return f"gt_bin/{stem}.gt.bin"


def fixture_json_for(stem: str) -> str:
    return f"fixtures/{stem}.fixture.json"


def gt_json_for(stem: str) -> str:
    return f"ground_truth/{stem}.gt.json"


def run_fixture_only(fixture_path: str) -> None:
    result = run_cg_wl(load_case(fixture_path))
    print(result.rounds)
    print(result.clusters)


def run_pipeline(args: argparse.Namespace) -> None:
    stem = case_stem(args.stem)
    fixture_binary = args.fixture_binary or fixture_binary_for(stem)
    gt_binary = args.gt_binary or gt_binary_for(stem)
    fixture_json = args.fixture_json or fixture_json_for(stem)
    gt_json = args.gt_json or gt_json_for(stem)
    case_name = args.case or stem
    build = args.build or DEFAULT_BUILD
    prefix = args.prefix or crate_prefix_from_stem(stem)

    print(f"stem: {stem}")
    print(f"fixture binary: {fixture_binary}")
    print(f"gt binary: {gt_binary}")
    print(f"fixture json: {fixture_json}")
    print(f"gt json: {gt_json}")

    fixture = extract_fixture(
        binary_path=fixture_binary,
        output_path=fixture_json,
        case_name=case_name,
        build=build,
        max_depth=args.max_depth,
        exclude_regex=args.exclude_regex,
        root=args.root,
    )
    print(f"fixture nodes: {len(fixture['nodes'])}")

    gt = extract_ground_truth(
        binary_path=gt_binary,
        output_path=gt_json,
        fixture_path=fixture_json,
        case_name=case_name,
        build=build,
        prefix=prefix,
    )
    print(f"ground-truth origins: {len(gt['origins'])}")

    result = run_cg_wl(load_case(fixture_json))
    print(f"CG-WL rounds: {result.rounds}")
    print(f"clusters: {result.clusters}")
    print(format_report(score_case(fixture_json, gt_json)))


def extract_fixture(
    *,
    binary_path: str,
    output_path: str,
    case_name: str,
    build: str,
    max_depth: int | None,
    exclude_regex: list[str],
    root: str | None,
) -> dict:
    from binary_extractor import DEFAULT_ID_BIAS, extract_fixture, write_fixture

    args = SimpleNamespace(
        binary=binary_path,
        case=case_name,
        build=build,
        root=root,
        max_depth=max_depth,
        exclude_regex=exclude_regex,
        score_root=False,
        include_imports=False,
        id_bias=DEFAULT_ID_BIAS,
        list_functions=False,
    )
    fixture = extract_fixture(args)
    write_fixture(fixture, output_path)
    return fixture


def extract_ground_truth(
    *,
    binary_path: str,
    output_path: str,
    fixture_path: str,
    case_name: str,
    build: str,
    prefix: str,
) -> dict:
    from gt_extractor import (
        DEFAULT_CONCRETE_REGEX,
        DEFAULT_ID_BIAS,
        make_ground_truth,
        parse_nm_lines,
        run_nm,
        validate_against_fixture,
        write_json,
    )

    symbols = parse_nm_lines(run_nm(binary_path, "nm"))
    gt = make_ground_truth(
        symbols=symbols,
        case=case_name,
        build=build,
        prefix=prefix,
        id_bias=DEFAULT_ID_BIAS,
        concrete_regex=DEFAULT_CONCRETE_REGEX,
    )
    validate_against_fixture(gt, fixture_path)
    write_json(gt, output_path)
    return gt


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run binary extraction, GT extraction, CG-WL, and scoring for one stem."
    )
    parser.add_argument(
        "stem",
        help=(
            "example stem such as family_graph_03. If this is a .fixture.json "
            "path, only CG-WL is run on that fixture."
        ),
    )
    parser.add_argument("--fixture-binary", help="override stripped/fixture binary path")
    parser.add_argument("--gt-binary", help="override non-stripped GT binary path")
    parser.add_argument("--fixture-json", help="override generated fixture JSON path")
    parser.add_argument("--gt-json", help="override generated ground-truth JSON path")
    parser.add_argument("--case", help="case field written into generated JSON")
    parser.add_argument("--build", help=f"build field written into generated JSON. Default: {DEFAULT_BUILD}")
    parser.add_argument("--prefix", help="demangled symbol prefix for GT extraction")
    parser.add_argument("--root", help="root function name/id/address for binary extraction")
    parser.add_argument("--max-depth", type=int, help="maximum BFS depth from root")
    parser.add_argument(
        "--exclude-regex",
        action="append",
        default=[],
        help="drop reachable non-root functions matching this regex",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.stem.endswith(".fixture.json"):
            run_fixture_only(args.stem)
        else:
            run_pipeline(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
