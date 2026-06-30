from __future__ import annotations

import argparse
import sys
from types import SimpleNamespace

from engine import run_cg_wl
from loader import load_case
from paths import (
    DEFAULT_BUILD,
    fixture_binary_for,
    fixture_json_for,
    gt_binary_for,
    gt_json_for,
    prefix_for_case,
    split_case_build,
    users_json_for,
)
from scores import format_report, score_case


def run_fixture_only(fixture_path: str) -> None:
    result = run_cg_wl(load_case(fixture_path))
    print(result.rounds)
    print(result.clusters)


def run_pipeline(args: argparse.Namespace) -> None:
    case_from_stem, build = split_case_build(args.stem, args.build)
    case_name = args.case or case_from_stem
    fixture_binary = args.fixture_binary or fixture_binary_for(case_from_stem, build)
    gt_binary = args.gt_binary or gt_binary_for(case_from_stem, build)
    fixture_json = args.fixture_json or fixture_json_for(case_name, build)
    gt_json = args.gt_json or gt_json_for(case_name, build)
    users_json = args.users or users_json_for(case_name, build)
    prefix = args.prefix or prefix_for_case(case_name)

    print(f"case: {case_name}")
    print(f"build: {build}")
    print(f"fixture binary: {fixture_binary}")
    print(f"gt binary: {gt_binary}")
    print(f"fixture json: {fixture_json}")
    print(f"gt json: {gt_json}")
    print(f"users: {users_json}")

    gt = extract_ground_truth(
        binary_path=gt_binary,
        output_path=gt_json,
        users_path=users_json,
        case_name=case_name,
        build=build,
        prefix=prefix,
    )
    print(f"ground-truth origins: {len(gt['origins'])}")

    fixture = extract_fixture(
        binary_path=fixture_binary,
        output_path=fixture_json,
        case_name=case_name,
        build=build,
        root=args.root,
        users_path=users_json,
    )
    print(f"fixture nodes: {len(fixture['nodes'])}")

    from gt_extractor import validate_against_fixture

    validate_against_fixture(gt, fixture_json)

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
    root: str | None,
    users_path: str | None,
) -> dict:
    from binary_extractor import DEFAULT_ID_BIAS, extract_fixture, write_fixture

    args = SimpleNamespace(
        binary=binary_path,
        case=case_name,
        build=build,
        root=root,
        score_root=False,
        include_imports=False,
        id_bias=DEFAULT_ID_BIAS,
        list_functions=False,
        users=users_path,
    )
    fixture = extract_fixture(args)
    write_fixture(fixture, output_path)
    return fixture


def extract_ground_truth(
    *,
    binary_path: str,
    output_path: str,
    users_path: str,
    case_name: str,
    build: str,
    prefix: str,
) -> dict:
    from gt_extractor import (
        DEFAULT_CONCRETE_ORIGIN_REGEX,
        DEFAULT_ID_BIAS,
        make_ground_truth,
        make_users_json,
        parse_nm_lines,
        run_nm,
        user_addresses,
        write_json,
    )

    symbols = parse_nm_lines(run_nm(binary_path, "nm"))
    user_addrs = user_addresses(symbols=symbols, prefix=prefix)
    gt = make_ground_truth(
        symbols=symbols,
        case=case_name,
        build=build,
        prefix=prefix,
        id_bias=DEFAULT_ID_BIAS,
        concrete_regex=DEFAULT_CONCRETE_ORIGIN_REGEX,
    )
    write_json(gt, output_path)
    write_json(
        make_users_json(
            addresses=user_addrs,
            case=case_name,
            build=build,
            binary_path=binary_path,
            prefix=prefix,
        ),
        users_path,
    )
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
    parser.add_argument("--users", help="override generated user address JSON path")
    parser.add_argument("--case", help="case field written into generated JSON")
    parser.add_argument("--build", help=f"build/profile. Default: {DEFAULT_BUILD}")
    parser.add_argument("--prefix", help="demangled symbol prefix for GT extraction")
    parser.add_argument("--root", help="root function name/id/address for binary extraction")
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
