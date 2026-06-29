# 자동 채점기
# scores.py
#
# 자동 채점기 (auto scorer)
#   - 쌍별 precision / recall / F1 / ARI
#   - floor 진단 (false merge 분류 + fragmentation)
#
# 규칙
#   엔진은 origin 을 모른다. scorer 만 ground truth 를 본다.
#   ground truth 는 "소스 사실"(origin, type)만 담는다.
#   floor 라벨은 scorer 가 클러스터 + origin + type 으로 도출한다.
#   채점 유니버스 = fixture 의 scored 노드 == ground truth 의 전체 member.

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from engine import run_cg_wl
from loader import load_case
from model import Case


# ---------------------------------------------------------- ground truth model

ORIGIN_TYPES = {"generic", "concrete"}


def case_stem(value: str) -> str:
    name = Path(value).name
    for suffix in (".fixture.json", ".gt.json", ".json"):
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def fixture_json_for(stem: str) -> str:
    return f"fixtures/{stem}.fixture.json"


def gt_json_for(stem: str) -> str:
    return f"ground_truth/{stem}.gt.json"


@dataclass(frozen=True)
class OriginGroup:
    origin: str
    type: str                        # generic | concrete
    members: tuple[str, ...]


@dataclass(frozen=True)
class GroundTruth:
    case: str
    build: str
    schema_version: int
    origins: tuple[OriginGroup, ...]

    def origin_of(self) -> dict[str, str]:
        return {m: g.origin for g in self.origins for m in g.members}

    def type_of_origin(self) -> dict[str, str]:
        return {g.origin: g.type for g in self.origins}


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
                type=o["type"],
                members=tuple(o["members"]),
            )
            for o in data["origins"]
        ),
    )


def _validate_ground_truth(data) -> None:
    if not isinstance(data, dict):
        raise ValueError("ground truth root must be a JSON object")

    required = {"case", "build", "schema_version", "origins"}
    allowed = required | {"note"}
    keys = set(data)
    if required - keys:
        raise ValueError(f"missing field(s): {sorted(required - keys)}")
    if keys - allowed:
        raise ValueError(f"unknown field(s): {sorted(keys - allowed)}")
    if data["schema_version"] != 1:
        raise ValueError(f"unsupported schema_version: {data['schema_version']}")
    if not isinstance(data["origins"], list) or not data["origins"]:
        raise ValueError("origins must be a non-empty list")

    seen_origins: set[str] = set()
    seen_members: set[str] = set()
    for index, o in enumerate(data["origins"]):
        where = f"origins[{index}]"
        if not isinstance(o, dict) or set(o) != {"origin", "type", "members"}:
            raise ValueError(f"{where} must have exactly origin/type/members")

        name = o["origin"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{where}.origin must be a non-empty string")
        if name in seen_origins:
            raise ValueError(f"duplicate origin name: {name}")
        seen_origins.add(name)

        if o["type"] not in ORIGIN_TYPES:
            raise ValueError(f"{name}.type must be one of {sorted(ORIGIN_TYPES)}")

        members = o["members"]
        if not isinstance(members, list) or not members:
            raise ValueError(f"{name}.members must be a non-empty list")
        for m in members:
            if not isinstance(m, str) or not m.strip():
                raise ValueError(f"{name} has an invalid member id")
            if m in seen_members:
                raise ValueError(f"id appears in more than one origin: {m}")
            seen_members.add(m)


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
class FalseMerge:
    a: str
    b: str
    origin_a: str
    origin_b: str
    floor: str


@dataclass(frozen=True)
class MissedPair:
    a: str
    b: str
    origin: str


@dataclass(frozen=True)
class ScoreReport:
    case: str
    build: str
    pairwise: PairwiseScore
    false_merges: tuple[FalseMerge, ...]
    missed_pairs: tuple[MissedPair, ...]
    floor_summary: dict[str, int]            # floor label -> FP pair count
    fragmented_origins: dict[str, int]       # origin -> #clusters it is split across


# ---------------------------------------------------------- scoring

def score_case(fixture_path: str, ground_truth_path: str) -> ScoreReport:
    case = load_case(fixture_path)
    gt = load_ground_truth(ground_truth_path)
    _check_join(case, gt)

    result = run_cg_wl(case)
    cluster_of = result.cluster_id_by_node      # scored nodes only
    origin_of = gt.origin_of()
    type_of_origin = gt.type_of_origin()

    scored_ids = sorted(cluster_of)

    tp = fp = fn = tn = 0
    false_merges: list[FalseMerge] = []
    missed_pairs: list[MissedPair] = []

    for a, b in combinations(scored_ids, 2):
        pred_same = cluster_of[a] == cluster_of[b]
        true_same = origin_of[a] == origin_of[b]

        if pred_same and true_same:
            tp += 1
        elif pred_same and not true_same:
            fp += 1
            false_merges.append(FalseMerge(
                a=a, b=b,
                origin_a=origin_of[a], origin_b=origin_of[b],
                floor=_floor_label(
                    type_of_origin[origin_of[a]],
                    type_of_origin[origin_of[b]],
                ),
            ))
        elif (not pred_same) and true_same:
            fn += 1
            missed_pairs.append(MissedPair(a=a, b=b, origin=origin_of[a]))
        else:
            tn += 1

    pairwise = _pairwise_score(tp, fp, fn, tn)

    floor_summary: dict[str, int] = {}
    for fm in false_merges:
        floor_summary[fm.floor] = floor_summary.get(fm.floor, 0) + 1

    origin_clusters: dict[str, set[int]] = {}
    for nid, cid in cluster_of.items():
        origin_clusters.setdefault(origin_of[nid], set()).add(cid)
    fragmented = {
        origin: len(cids)
        for origin, cids in origin_clusters.items()
        if len(cids) > 1
    }

    return ScoreReport(
        case=case.case,
        build=case.build,
        pairwise=pairwise,
        false_merges=tuple(false_merges),
        missed_pairs=tuple(missed_pairs),
        floor_summary=floor_summary,
        fragmented_origins=fragmented,
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


def _floor_label(type_a: str, type_b: str) -> str:
    if "concrete" in {type_a, type_b}:
        return "concrete_mirror_floor"
    return "relation_indistinguishable"


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


# ---------------------------------------------------------- pretty print + CLI

def format_report(r: ScoreReport) -> str:
    p = r.pairwise
    lines = [
        f"case : {r.case} / {r.build}",
        f"P={p.precision:.2f}  R={p.recall:.2f}  F1={p.f1:.2f}  ARI={p.ari:.2f}",
        f"TP={p.tp} FP={p.fp} FN={p.fn} TN={p.tn}",
    ]
    if r.floor_summary:
        lines.append("false merges (precision floor):")
        for floor, n in sorted(r.floor_summary.items()):
            lines.append(f"  {floor}: {n} pair(s)")
    if r.fragmented_origins:
        lines.append("fragmentation (recall floor):")
        for origin, k in sorted(r.fragmented_origins.items()):
            lines.append(f"  {origin}: split across {k} clusters")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.ground_truth is None:
        stem = case_stem(args.fixture)
        fixture_path = fixture_json_for(stem)
        gt_path = gt_json_for(stem)
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
