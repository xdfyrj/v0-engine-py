from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paths import (
    DEFAULT_BUILD,
    gt_json_for,
    prefix_for_case,
    resolve_gt_binary,
    split_case_build,
    users_json_for,
)


GT_SCHEMA_VERSION = 3
USERS_SCHEMA_VERSION = 1
DEFAULT_ID_BIAS = 0x100000


@dataclass(frozen=True)
class Symbol:
    addr: int
    kind: str
    name: str


def function_id(addr: int, *, id_bias: int = DEFAULT_ID_BIAS) -> str:
    return f"FUN_{addr + id_bias:08x}"


def parse_int(value: str) -> int:
    return int(value, 0)


def run_nm(binary_path: str, nm_tool: str) -> list[str]:
    result = subprocess.run(
        [nm_tool, "-n", "-C", binary_path],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.splitlines()


def parse_nm_lines(lines: list[str]) -> list[Symbol]:
    symbols: list[Symbol] = []

    for line in lines:
        parts = line.strip().split(maxsplit=2)
        if len(parts) != 3:
            continue

        addr_text, kind, name = parts
        if kind not in {"t", "T"}:
            continue

        try:
            addr = int(addr_text, 16)
        except ValueError:
            continue

        symbols.append(Symbol(addr=addr, kind=kind, name=name))

    return symbols


def origin_from_symbol(demangled_name: str, prefix: str) -> str | None:
    if not demangled_name.startswith(prefix):
        return None

    origin = demangled_name[len(prefix):]
    origin = re.sub(r"::h[0-9a-fA-F]{16}$", "", origin)
    origin = strip_rust_generic_args(origin)

    if origin == "main" or not origin:
        return None

    return origin


def strip_rust_generic_args(name: str) -> str:
    # v0 mangling can demangle monomorphized instances as `foo::<T>`.
    # Ground truth origin is the source path with type arguments removed.
    out: list[str] = []
    i = 0

    while i < len(name):
        if name.startswith("::<", i):
            i += 3
            depth = 1
            while i < len(name) and depth:
                if name[i] == "<":
                    depth += 1
                elif name[i] == ">":
                    depth -= 1
                i += 1
            continue

        out.append(name[i])
        i += 1

    return "".join(out)


def make_ground_truth(
    *,
    symbols: list[Symbol],
    case: str,
    build: str,
    prefix: str,
    id_bias: int,
) -> dict[str, Any]:
    members_by_origin: dict[str, dict[str, int]] = defaultdict(dict)
    member_addr: dict[str, int] = {}
    symbols_by_member: dict[str, list[str]] = {}
    owner_by_member: dict[str, str] = {}
    alias_notes: list[str] = []

    for symbol in symbols:
        origin = origin_from_symbol(symbol.name, prefix)
        if origin is None:
            continue

        member_id = function_id(symbol.addr, id_bias=id_bias)
        owner = owner_by_member.get(member_id)

        if owner is not None:
            if owner == origin:
                if symbol.name not in symbols_by_member[member_id]:
                    symbols_by_member[member_id].append(symbol.name)
                alias_notes.append(
                    f"{member_id}: duplicate symbol for origin {origin!r} "
                    f"kept once ({symbol.name})"
                )
                continue

            raise ValueError(
                f"cross-origin address alias at {member_id}: "
                f"first origin {owner!r}, later origin {origin!r} "
                f"({symbol.name}). Rebuild without cross-origin folding or "
                "exclude/handle this case before scoring."
            )

        owner_by_member[member_id] = origin
        member_addr[member_id] = symbol.addr
        symbols_by_member[member_id] = [symbol.name]
        members_by_origin[origin][member_id] = symbol.addr

    origins = []
    for origin, members in sorted(
        members_by_origin.items(),
        key=lambda item: min(item[1].values()),
    ):
        sorted_members = sorted(
            members.items(),
            key=lambda item: item[1],
        )
        origins.append(
            {
                "origin": origin,
                "members": [member_id for member_id, _addr in sorted_members],
            }
        )

    if not origins:
        raise ValueError(f"no text symbols matched prefix {prefix!r}")

    gt: dict[str, Any] = {
        "case": case,
        "build": build,
        "schema_version": GT_SCHEMA_VERSION,
        "origins": origins,
        "symbols": {
            member_id: symbols_by_member[member_id]
            for member_id, _addr in sorted(
                member_addr.items(),
                key=lambda item: item[1],
            )
        },
    }

    if alias_notes:
        gt["note"] = "address aliases/duplicates: " + "; ".join(alias_notes)

    return gt


def user_addresses(
    *,
    symbols: list[Symbol],
    prefix: str,
) -> list[int]:
    addresses = {
        symbol.addr
        for symbol in symbols
        if origin_from_symbol(symbol.name, prefix) is not None
    }
    return sorted(addresses)


def make_users_json(
    *,
    addresses: list[int],
    case: str,
    build: str,
    binary_path: str,
    prefix: str,
) -> dict[str, Any]:
    return {
        "case": case,
        "build": build,
        "schema_version": USERS_SCHEMA_VERSION,
        "source": binary_path,
        "prefix": prefix,
        "addresses": [f"0x{addr:x}" for addr in addresses],
    }


def validate_against_fixture(gt: dict[str, Any], fixture_path: str) -> None:
    from loader import load_case

    case = load_case(fixture_path)
    scored_ids = {node.id for node in case.nodes if node.scored}
    gt_ids = {
        member
        for origin in gt["origins"]
        for member in origin["members"]
    }

    if scored_ids != gt_ids:
        raise ValueError(
            "generated ground truth does not match fixture scored universe. "
            f"missing in ground truth: {sorted(scored_ids - gt_ids)}; "
            f"present in ground truth but not scored: {sorted(gt_ids - scored_ids)}"
        )


def write_json(data: dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extract this project's ground_truth/*.gt.json from a non-stripped "
            "Rust binary's demangled symbols."
        )
    )
    parser.add_argument("binary", help="non-stripped ELF/Rust binary path, or an example stem")
    parser.add_argument(
        "output",
        nargs="?",
        help="output path. If omitted, writes ground_truth/<case>.<build>.gt.json.",
    )
    parser.add_argument("--case", help="case field written into generated JSON")
    parser.add_argument(
        "--build",
        help=f"build field written into generated JSON. Default: {DEFAULT_BUILD}",
    )
    parser.add_argument(
        "--prefix",
        help=(
            "demangled symbol prefix to keep, e.g. family_graph_01::. "
            "Default inferred from binary name."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_option",
        help="output path. Kept for compatibility; positional output is preferred.",
    )
    parser.add_argument(
        "--fixture",
        help="optional fixture JSON used to validate the scored node universe",
    )
    parser.add_argument("--users", help="output path for user address JSON")
    parser.add_argument(
        "--id-bias",
        type=parse_int,
        default=DEFAULT_ID_BIAS,
        help="value added to raw symbol addresses when formatting FUN_ ids",
    )
    parser.add_argument(
        "--nm-tool",
        default="nm",
        help="nm-compatible symbol tool. Default: nm",
    )
    return parser


def apply_cli_defaults(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.output and args.output_option and args.output != args.output_option:
        parser.error("use either positional output or --output, not both")

    args.output = args.output_option or args.output
    case, build = split_case_build(args.binary, args.build)

    if not Path(args.binary).exists():
        args.binary = resolve_gt_binary(case, build)
    args.output = args.output or gt_json_for(case, build)
    args.users = args.users or users_json_for(case, build)
    args.case = args.case or case
    args.build = build
    args.prefix = args.prefix or prefix_for_case(args.case)


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    apply_cli_defaults(args, parser)

    try:
        output_path = args.output
        prefix = args.prefix
        case = args.case
        build = args.build

        symbols = parse_nm_lines(run_nm(args.binary, args.nm_tool))
        user_addrs = user_addresses(symbols=symbols, prefix=prefix)
        gt = make_ground_truth(
            symbols=symbols,
            case=case,
            build=build,
            prefix=prefix,
            id_bias=args.id_bias,
        )

        if args.fixture:
            validate_against_fixture(gt, args.fixture)

        if output_path:
            write_json(gt, output_path)
            print(f"wrote {output_path}")
            print(f"origins={len(gt['origins'])}")
        else:
            print(json.dumps(gt, indent=2))

        if args.users:
            users_json = make_users_json(
                addresses=user_addrs,
                case=case,
                build=build,
                binary_path=args.binary,
                prefix=prefix,
            )
            write_json(users_json, args.users)
            print(f"wrote {args.users}")
            print(f"users={len(user_addrs)}")
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
