# 자동 채점기
# scores.py
#
# 자동 채점기 (auto scorer)
#   - 쌍별 precision / recall / F1 / ARI
#
# 규칙
#   엔진은 origin 을 모른다. scorer 만 ground truth 를 본다.
#   ground truth 는 origin partition 과 출력용 demangled symbol 만 담는다.
#   채점 유니버스 = fixture 의 scored 노드 == ground truth 의 전체 member.

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from itertools import combinations

from engine import run_cg_wl
from loader import load_case
from model import Case
from paths import DEFAULT_BUILD, resolve_fixture_json, resolve_gt_json, split_case_build


# ---------------------------------------------------------- ground truth model

GROUND_TRUTH_SCHEMA_VERSION = 3


@dataclass(frozen=True)
class OriginGroup:
    origin: str
    members: tuple[str, ...]


@dataclass(frozen=True)
class GroundTruth:
    case: str
    build: str
    schema_version: int
    origins: tuple[OriginGroup, ...]
    symbols: dict[str, tuple[str, ...]]

    def origin_of(self) -> dict[str, str]:
        return {m: g.origin for g in self.origins for m in g.members}


# ---------------------------------------------------------- ground truth loader

def load_ground_truth(path: str) -> GroundTruth:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _validate_ground_truth(data)
    return GroundTruth(
        case=data["case"],
        build=data["build"],
        schema_version=data["schema_version"],
        origins=tuple(
            OriginGroup(
                origin=o["origin"],
                members=tuple(o["members"]),
            )
            for o in data["origins"]
        ),
        symbols={
            member_id: tuple(symbols)
            for member_id, symbols in data["symbols"].items()
        },
    )


def _validate_ground_truth(data) -> None:
    if not isinstance(data, dict):
        raise ValueError("ground truth root must be a JSON object")

    required = {"case", "build", "schema_version", "origins", "symbols"}
    allowed = required | {"note"}
    keys = set(data)
    if required - keys:
        raise ValueError(f"missing field(s): {sorted(required - keys)}")
    if keys - allowed:
        raise ValueError(f"unknown field(s): {sorted(keys - allowed)}")
    if data["schema_version"] != GROUND_TRUTH_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {data['schema_version']}")
    if not isinstance(data["origins"], list) or not data["origins"]:
        raise ValueError("origins must be a non-empty list")

    seen_origins: set[str] = set()
    seen_members: set[str] = set()
    for index, o in enumerate(data["origins"]):
        where = f"origins[{index}]"
        if not isinstance(o, dict) or set(o) != {"origin", "members"}:
            raise ValueError(f"{where} must have exactly origin/members")

        name = o["origin"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{where}.origin must be a non-empty string")
        if name in seen_origins:
            raise ValueError(f"duplicate origin name: {name}")
        seen_origins.add(name)

        members = o["members"]
        if not isinstance(members, list) or not members:
            raise ValueError(f"{name}.members must be a non-empty list")
        for m in members:
            if not isinstance(m, str) or not m.strip():
                raise ValueError(f"{name} has an invalid member id")
            if m in seen_members:
                raise ValueError(f"id appears in more than one origin: {m}")
            seen_members.add(m)

    symbols = data["symbols"]
    if not isinstance(symbols, dict):
        raise ValueError("symbols must be an object mapping member id to symbol list")
    if set(symbols) != seen_members:
        raise ValueError(
            "symbols keys must equal origin members. "
            f"missing symbols: {sorted(seen_members - set(symbols))}; "
            f"unknown symbols: {sorted(set(symbols) - seen_members)}"
        )
    for member_id, names in symbols.items():
        if not isinstance(names, list) or not names:
            raise ValueError(f"symbols[{member_id!r}] must be a non-empty list")
        for name in names:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"symbols[{member_id!r}] has an invalid symbol")


# ---------------------------------------------------------- score result types

@dataclass(frozen=True)
class PairwiseScore:
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float
    recall: float
    f1: float
    ari: float


@dataclass(frozen=True)
class ScoreReport:
    case: str
    build: str
    clusters: tuple[tuple[str, ...], ...]
    cluster_symbols: tuple[tuple[str, ...], ...]
    pairwise: PairwiseScore


# ---------------------------------------------------------- scoring

def score_case(fixture_path: str, ground_truth_path: str) -> ScoreReport:
    case = load_case(fixture_path)
    gt = load_ground_truth(ground_truth_path)
    _check_join(case, gt)

    result = run_cg_wl(case)
    cluster_of = result.cluster_id_by_node      # scored nodes only
    origin_of = gt.origin_of()

    scored_ids = sorted(cluster_of)

    tp = fp = fn = tn = 0

    for a, b in combinations(scored_ids, 2):
        pred_same = cluster_of[a] == cluster_of[b]
        true_same = origin_of[a] == origin_of[b]

        if pred_same and true_same:
            tp += 1
        elif pred_same and not true_same:
            fp += 1
        elif (not pred_same) and true_same:
            fn += 1
        else:
            tn += 1

    pairwise = _pairwise_score(tp, fp, fn, tn)

    return ScoreReport(
        case=case.case,
        build=case.build,
        clusters=tuple(tuple(cluster) for cluster in result.clusters),
        cluster_symbols=tuple(
            tuple(_format_member_symbols(gt, node_id) for node_id in cluster)
            for cluster in result.clusters
        ),
        pairwise=pairwise,
    )


def _pairwise_score(tp: int, fp: int, fn: int, tn: int) -> PairwiseScore:
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return PairwiseScore(tp, fp, fn, tn, precision, recall, f1,
                         _adjusted_rand_index(tp, fp, fn, tn))


def _adjusted_rand_index(tp: int, fp: int, fn: int, tn: int) -> float:
    # ARI from pairwise counts.
    #   index            = sum_ij C(n_ij, 2) = TP
    #   same_cluster     = sum_i  C(a_i,  2) = TP + FP
    #   same_origin      = sum_j  C(b_j,  2) = TP + FN
    #   total node pairs = C(n, 2)           = TP + FP + FN + TN
    index = tp
    same_cluster = tp + fp
    same_origin = tp + fn
    total = tp + fp + fn + tn
    if total == 0:
        return 1.0
    expected = same_cluster * same_origin / total
    maximum = 0.5 * (same_cluster + same_origin)
    if maximum == expected:
        return 1.0
    return (index - expected) / (maximum - expected)


def _check_join(case: Case, gt: GroundTruth) -> None:
    if case.case != gt.case or case.build != gt.build:
        raise ValueError(
            f"case/build mismatch: fixture={case.case}/{case.build} "
            f"vs ground_truth={gt.case}/{gt.build}"
        )
    scored_ids = {n.id for n in case.nodes if n.scored}
    gt_ids = {m for g in gt.origins for m in g.members}
    if scored_ids != gt_ids:
        raise ValueError(
            "scored universe mismatch. "
            f"missing in ground truth: {sorted(scored_ids - gt_ids)}; "
            f"present in ground truth but not scored: {sorted(gt_ids - scored_ids)}"
        )


def _format_member_symbols(gt: GroundTruth, member_id: str) -> str:
    names = tuple(_display_symbol(name, gt.case) for name in gt.symbols[member_id])
    if len(names) == 1:
        return names[0]
    return " | ".join(names)


def _display_symbol(symbol: str, case: str) -> str:
    prefix = f"{case}::"
    if symbol.startswith(prefix):
        symbol = symbol[len(prefix):]
    return re.sub(r"::h[0-9a-fA-F]{16}$", "", symbol)


# ---------------------------------------------------------- pretty print + CLI

def format_report(r: ScoreReport) -> str:
    p = r.pairwise
    lines = [
        f"case : {r.case} / {r.build}",
        "predicted clusters:",
    ]
    lines.extend(
        f"  C{index} = {list(cluster)}"
        for index, cluster in enumerate(r.clusters, start=1)
    )
    lines.append("symbols:")
    lines.extend(
        f"  C{index} = {list(symbols)}"
        for index, symbols in enumerate(r.cluster_symbols, start=1)
    )
    lines.extend([
        f"TP={p.tp} FP={p.fp} FN={p.fn}",
        f"PR={p.precision:.2f} RE={p.recall:.2f} F1={p.f1:.2f} ARI={p.ari:.2f}",
    ])
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score CG-WL clusters against a ground-truth JSON."
    )
    parser.add_argument(
        "fixture",
        help="fixture JSON path, or an example stem",
    )
    parser.add_argument(
        "ground_truth",
        nargs="?",
        help="ground-truth JSON path",
    )
    parser.add_argument("--build", help=f"build/profile. Default: {DEFAULT_BUILD}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.ground_truth is None:
        case, build = split_case_build(args.fixture, args.build)
        fixture_path = resolve_fixture_json(case, build)
        gt_path = resolve_gt_json(case, build)
    else:
        fixture_path = args.fixture
        gt_path = args.ground_truth

    try:
        print(format_report(score_case(fixture_path, gt_path)))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
